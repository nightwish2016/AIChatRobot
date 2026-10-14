from flask import Blueprint, request, jsonify, send_file, render_template, session, copy_current_request_context
import os
import uuid
import json
import tempfile
import time
import fcntl
import glob
from contextlib import contextmanager
from functools import lru_cache
from threading import Thread
from werkzeug.utils import secure_filename
from app.subtitle_extractor import SubtitleExtractor
from ..UserUtils import UserUtils
from app.api.userAPI import check_login
import logging
from app.chatHistoryUtils import chatHistoryUtils
from app.r2_storage import R2Storage

logger = logging.getLogger('log')

subtitleview_bp = Blueprint('subtitle', __name__)

# 支持的视频格式
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm', 'mp3', 'wav', 'm4a', 'aac', 'ogg', 'flac'}
MAX_SUBTITLE_UPLOAD_BYTES = 5 * 1024 * 1024 * 1024
CLIENT_UPLOAD_PART_BYTES = 1024 * 1024
R2_UPLOAD_PART_BYTES = 8 * 1024 * 1024
SUBTITLE_UPLOAD_STAGE_FOLDER = os.path.join(tempfile.gettempdir(), 'subtitle_uploads')

@lru_cache(maxsize=1)
def _get_upload_storage() -> R2Storage:
    return R2Storage()

def _upload_stage_paths(upload_token):
    return (
        os.path.join(SUBTITLE_UPLOAD_STAGE_FOLDER, f'{upload_token}.json'),
        os.path.join(SUBTITLE_UPLOAD_STAGE_FOLDER, f'{upload_token}.part')
    )

def _load_upload_metadata(upload_token):
    metadata_path, _ = _upload_stage_paths(upload_token)
    with open(metadata_path, 'r', encoding='utf-8') as metadata_file:
        return json.load(metadata_file)

def _save_upload_metadata(upload_token, metadata):
    os.makedirs(SUBTITLE_UPLOAD_STAGE_FOLDER, exist_ok=True)
    metadata_path, _ = _upload_stage_paths(upload_token)
    temp_metadata_path = f'{metadata_path}.tmp'
    with open(temp_metadata_path, 'w', encoding='utf-8') as metadata_file:
        json.dump(metadata, metadata_file)
    os.replace(temp_metadata_path, metadata_path)

def _cleanup_upload_stage(upload_token):
    for stage_path in _upload_stage_paths(upload_token):
        if os.path.exists(stage_path):
            os.unlink(stage_path)
    for chunk_path in glob.glob(
        os.path.join(SUBTITLE_UPLOAD_STAGE_FOLDER, f'{upload_token}.chunk-*')
    ):
        os.unlink(chunk_path)

@contextmanager
def _upload_stage_lock(upload_token: str):
    metadata_path, _ = _upload_stage_paths(upload_token)
    with open(f'{metadata_path}.lock', 'a', encoding='utf-8') as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@subtitleview_bp.route('/subtitle', methods=['GET'])
def subtitle_page():
    """字幕提取页面"""
    if 'user_name' in session:
        u = UserUtils()
        # 获取用户的货币偏好，默认显示人民币，但同时提供美元等值
        currency_preference = request.args.get('currency', 'CNY')
        userInfo = u.getUserInfoWithCurrency(session['user_id'], currency_preference)
        
        return render_template('subtitle.html', 
                             user_name=session['user_name'],
                             balance=round(userInfo['balance'],2),
                             balance_display=userInfo['balance_display'],
                             balance_secondary=userInfo['balance_secondary'],
                             currency_info=userInfo['currency_info'],
                             currency_preference=currency_preference,
                             user_email=session.get('user_email', ''))
    else:
        return render_template('subtitle.html')

@subtitleview_bp.route('/api/subtitle/upload-initiate', methods=['POST'])
def initiate_subtitle_upload():
    """创建R2分片上传任务。"""
    try:
        login_result = check_login()
        logged_in = json.loads(login_result.get_data(as_text=True))["logged_in"]
        if not logged_in:
            return jsonify({'success': False, 'message': '请先登录'}), 401

        user_info = UserUtils().getUserInfo(session['user_id'])
        balance = round(user_info['balance'], 2)
        if balance <= 0:
            return jsonify({
                'success': False,
                'message': f'当前余额: ¥{balance}，余额不足无法使用字幕提取功能'
            }), 402
        if user_info['activate'] == 0:
            return jsonify({'success': False, 'message': '您的账户尚未激活'}), 402

        data = request.get_json(silent=True) or {}
        filename = data.get('filename', '')
        file_size = data.get('file_size')
        content_type = data.get('content_type') or 'application/octet-stream'

        if not allowed_file(filename):
            return jsonify({'success': False, 'message': '不支持的文件格式'}), 400
        if not isinstance(file_size, int) or file_size <= 0:
            return jsonify({'success': False, 'message': '文件大小无效'}), 400
        if file_size > MAX_SUBTITLE_UPLOAD_BYTES:
            return jsonify({'success': False, 'message': '文件超过5 GB，无法上传'}), 413

        file_ext = filename.rsplit('.', 1)[1].lower()
        object_key = f"uploads/{uuid.uuid4().hex}.{file_ext}"
        r2_storage = R2Storage()
        previous_token = session.get('subtitle_pending_upload_token')
        if previous_token:
            try:
                previous_metadata = _load_upload_metadata(previous_token)
                r2_storage.abort_multipart_upload(
                    previous_metadata['object_key'],
                    previous_metadata['upload_id']
                )
            except (FileNotFoundError, KeyError, json.JSONDecodeError):
                pass
            _cleanup_upload_stage(previous_token)

        success, upload_id = r2_storage.create_multipart_upload(
            object_key=object_key,
            content_type=content_type
        )
        if not success:
            return jsonify({'success': False, 'message': upload_id}), 500

        upload_token = uuid.uuid4().hex
        _save_upload_metadata(upload_token, {
            'object_key': object_key,
            'upload_id': upload_id,
            'expected_size': file_size,
            'received_size': 0,
            'received_parts': [],
            'user_id': session['user_id'],
            'r2_parts': []
        })
        session['subtitle_pending_upload_token'] = upload_token
        return jsonify({
            'success': True,
            'file_path': object_key,
            'original_filename': filename,
            'part_size': CLIENT_UPLOAD_PART_BYTES,
            'concurrency': 3,
            'use_r2': True
        })
    except Exception as e:
        logger.exception("创建字幕分片上传失败")
        return jsonify({'success': False, 'message': f'创建上传任务失败: {str(e)}'}), 500

@subtitleview_bp.route('/api/subtitle/upload-part', methods=['PUT'])
def upload_subtitle_part():
    """上传一个小于Cloudflare限制的文件分片。"""
    try:
        if 'user_id' not in session or 'user_email' not in session:
            return jsonify({'success': False, 'message': '请先登录'}), 401

        upload_token = session.get('subtitle_pending_upload_token')
        part_number = request.args.get('part_number', type=int)
        if not upload_token:
            return jsonify({'success': False, 'message': '上传任务无效或已过期'}), 400

        if not part_number or part_number < 1:
            return jsonify({'success': False, 'message': '分片编号无效'}), 400
        if request.content_length is None or request.content_length > CLIENT_UPLOAD_PART_BYTES:
            return jsonify({'success': False, 'message': '分片大小无效'}), 400
        part_data = request.get_data(cache=False)
        with _upload_stage_lock(upload_token):
            try:
                metadata = _load_upload_metadata(upload_token)
            except (FileNotFoundError, json.JSONDecodeError):
                return jsonify({'success': False, 'message': '上传任务无效或已过期'}), 400
            if metadata.get('user_id') != session['user_id']:
                return jsonify({'success': False, 'message': '上传任务无效或已过期'}), 400
            expected_size = metadata['expected_size']
            expected_parts = (expected_size + CLIENT_UPLOAD_PART_BYTES - 1) // CLIENT_UPLOAD_PART_BYTES
            if part_number > expected_parts:
                return jsonify({'success': False, 'message': '分片编号无效'}), 400
            expected_part_size = min(
                CLIENT_UPLOAD_PART_BYTES,
                expected_size - ((part_number - 1) * CLIENT_UPLOAD_PART_BYTES)
            )
            if len(part_data) != expected_part_size:
                return jsonify({'success': False, 'message': '分片大小无效'}), 400

            chunk_path = os.path.join(SUBTITLE_UPLOAD_STAGE_FOLDER, f'{upload_token}.chunk-{part_number}')
            if part_number not in metadata['received_parts']:
                with open(chunk_path, 'wb') as chunk_file:
                    chunk_file.write(part_data)
                metadata['received_parts'].append(part_number)
                metadata['received_size'] += len(part_data)
                _save_upload_metadata(upload_token, metadata)

            chunks_per_r2_part = R2_UPLOAD_PART_BYTES // CLIENT_UPLOAD_PART_BYTES
            r2_part_number = ((part_number - 1) // chunks_per_r2_part) + 1
            first_chunk = (r2_part_number - 1) * chunks_per_r2_part + 1
            group_chunks = list(range(first_chunk, min(first_chunk + chunks_per_r2_part, expected_parts + 1)))
            already_uploaded = any(part['PartNumber'] == r2_part_number for part in metadata['r2_parts'])
            if not already_uploaded and all(chunk in metadata['received_parts'] for chunk in group_chunks):
                group_data = []
                group_paths = []
                for chunk in group_chunks:
                    group_path = os.path.join(SUBTITLE_UPLOAD_STAGE_FOLDER, f'{upload_token}.chunk-{chunk}')
                    with open(group_path, 'rb') as chunk_file:
                        group_data.append(chunk_file.read())
                    group_paths.append(group_path)
                success, etag = _get_upload_storage().upload_part(
                    object_key=metadata['object_key'],
                    upload_id=metadata['upload_id'],
                    part_number=r2_part_number,
                    data=b''.join(group_data)
                )
                if not success:
                    return jsonify({'success': False, 'message': etag}), 500
                metadata['r2_parts'].append({'PartNumber': r2_part_number, 'ETag': etag})
                _save_upload_metadata(upload_token, metadata)
                for group_path in group_paths:
                    os.unlink(group_path)
        return jsonify({'success': True, 'part_number': part_number})
    except Exception as e:
        logger.exception("上传字幕文件分片失败")
        return jsonify({'success': False, 'message': f'上传分片失败: {str(e)}'}), 500

@subtitleview_bp.route('/api/subtitle/upload-complete', methods=['POST'])
def complete_subtitle_upload():
    """合并R2分片并校验最终文件。"""
    try:
        login_result = check_login()
        logged_in = json.loads(login_result.get_data(as_text=True))["logged_in"]
        if not logged_in:
            return jsonify({'success': False, 'message': '请先登录'}), 401

        upload_token = session.get('subtitle_pending_upload_token')
        if not upload_token:
            return jsonify({'success': False, 'message': '上传任务无效或已过期'}), 400

        try:
            metadata = _load_upload_metadata(upload_token)
        except (FileNotFoundError, json.JSONDecodeError):
            return jsonify({'success': False, 'message': '上传任务无效或已过期'}), 400

        object_key = metadata['object_key']
        expected_size = metadata['expected_size']
        if metadata['received_size'] != expected_size or not metadata['r2_parts']:
            return jsonify({'success': False, 'message': '分片数量不完整'}), 400

        r2_storage = R2Storage()
        success, result = r2_storage.complete_multipart_upload(
            object_key=object_key,
            upload_id=metadata['upload_id'],
            parts=sorted(metadata['r2_parts'], key=lambda part: part['PartNumber'])
        )
        if not success:
            return jsonify({'success': False, 'message': result}), 500

        actual_size = r2_storage.get_file_size(object_key)
        if actual_size is None:
            return jsonify({'success': False, 'message': '云端未找到上传文件'}), 400
        if actual_size != expected_size:
            r2_storage.delete_file(object_key)
            return jsonify({
                'success': False,
                'message': f'文件上传不完整（{actual_size}/{expected_size} 字节）'
            }), 400

        session['subtitle_upload_key'] = object_key
        session.pop('subtitle_pending_upload_token', None)
        _cleanup_upload_stage(upload_token)
        logger.info(f"字幕文件分片上传R2成功: {object_key}, size={actual_size}")
        return jsonify({'success': True, 'message': '文件上传成功'})
    except Exception as e:
        logger.exception("确认字幕上传失败")
        return jsonify({'success': False, 'message': f'确认上传失败: {str(e)}'}), 500

@subtitleview_bp.route('/api/subtitle/upload-abort', methods=['POST'])
def abort_subtitle_upload():
    """取消当前R2分片上传任务。"""
    try:
        login_result = check_login()
        logged_in = json.loads(login_result.get_data(as_text=True))["logged_in"]
        if not logged_in:
            return jsonify({'success': False, 'message': '请先登录'}), 401

        upload_token = session.get('subtitle_pending_upload_token')
        if upload_token:
            try:
                metadata = _load_upload_metadata(upload_token)
                R2Storage().abort_multipart_upload(
                    metadata['object_key'],
                    metadata['upload_id']
                )
            except (FileNotFoundError, KeyError, json.JSONDecodeError):
                pass
            _cleanup_upload_stage(upload_token)
        session.pop('subtitle_pending_upload_token', None)
        return jsonify({'success': True})
    except Exception as e:
        logger.exception("取消字幕上传失败")
        return jsonify({'success': False, 'message': f'取消上传失败: {str(e)}'}), 500

@subtitleview_bp.route('/api/subtitle/upload', methods=['POST'])
def upload_video():
    """上传视频文件"""
    try:
        # 检查登录状态
        loginResult = check_login()
        resLogin = json.loads(loginResult.get_data(as_text=True))["logged_in"]
        
        if resLogin == False:
            return jsonify({"error": "Unauthorized", "message": "please login"}), 401
        
        # 检查用户余额和账户状态
        u = UserUtils()
        userInfo = u.getUserInfo(session['user_id'])
        activate = userInfo['activate']
        balance = round(userInfo['balance'], 2)
        
        if balance <= 0:
            return jsonify({
                "error": "余额不足", 
                "message": f"当前余额: ¥{balance}，余额不足无法使用字幕提取功能。请点击充值链接进行充值，或联系管理员 kzhou2017@outlook.com"
            }), 402
        
        if activate == 0:
            return jsonify({
                "error": "账户未激活", 
                "message": "您的账户尚未激活，请通过邮件链接激活账户"
            }), 402
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '没有选择文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'message': '不支持的文件格式'}), 400
        
        # 尝试使用R2存储
        use_r2 = True
        try:
            r2_storage = R2Storage()
        except Exception as e:
            logger.warning(f"R2存储初始化失败，使用本地存储: {str(e)}")
            use_r2 = False
        
        upload_start = time.perf_counter()

        if use_r2:
            file_ext = file.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
            object_key = f"uploads/{unique_filename}"
            temp_path = None

            try:
                with tempfile.NamedTemporaryFile(suffix=f'.{file_ext}', delete=False) as temp_file:
                    temp_path = temp_file.name
                    file.save(temp_file)

                success, result = r2_storage.upload_file(
                    file_path=temp_path,
                    object_key=object_key,
                    content_type=file.content_type
                )
            finally:
                if temp_path and os.path.exists(temp_path):
                    os.unlink(temp_path)

            duration_ms = round((time.perf_counter() - upload_start) * 1000, 2)

            if success:
                session['subtitle_upload_key'] = result
                logger.info(f"文件上传到R2成功: {result}，耗时 {duration_ms} ms")
                return jsonify({
                    'success': True,
                    'message': '文件上传成功',
                    'file_path': result,  # R2对象键
                    'original_filename': file.filename,
                    'use_r2': True,
                    'upload_duration_ms': duration_ms
                })
            else:
                logger.error(f"上传到R2失败: {result}，耗时 {duration_ms} ms")
                return jsonify({
                    'success': False,
                    'message': f'上传失败: {result}',
                    'upload_duration_ms': duration_ms
                }), 500
        else:
            # 本地存储
            file_ext = file.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
            
            upload_folder = "uploads"
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, unique_filename)
            file.save(file_path)
            
            duration_ms = round((time.perf_counter() - upload_start) * 1000, 2)
            logger.info(f"文件上传成功: {file_path}，耗时 {duration_ms} ms")
            
            return jsonify({
                'success': True,
                'message': '文件上传成功',
                'file_path': file_path,
                'original_filename': file.filename,
                'use_r2': False,
                'upload_duration_ms': duration_ms
            })
        
    except Exception as e:
        logger.exception("文件上传失败")
        return jsonify({'success': False, 'message': f'上传失败: {str(e)}'}), 500

@subtitleview_bp.route('/api/subtitle/process', methods=['POST'])
def process_subtitle():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    request.get_json(silent=True)
    task_id = uuid.uuid4().hex
    user_id = session['user_id']
    task_token = f'process-{task_id}'
    _save_upload_metadata(task_token, {
        'user_id': user_id, 'status': 'processing'
    })

    @copy_current_request_context
    def run_processing():
        try:
            result = _process_subtitle()
            response = result[0] if isinstance(result, tuple) else result
            payload = response.get_json()
        except Exception:
            logger.exception('后台字幕处理失败')
            payload = {'success': False, 'message': '字幕处理失败，请稍后重试'}
        _save_upload_metadata(task_token, {
            'user_id': user_id, 'status': 'complete', 'result': payload
        })

    Thread(target=run_processing, daemon=True).start()
    return jsonify({'success': True, 'task_id': task_id, 'status': 'processing'}), 202

@subtitleview_bp.route('/api/subtitle/process-status/<task_id>', methods=['GET'])
def subtitle_process_status(task_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    if len(task_id) != 32 or any(character not in '0123456789abcdef' for character in task_id):
        return jsonify({'success': False, 'message': '任务不存在'}), 404
    try:
        task = _load_upload_metadata(f'process-{task_id}')
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({'success': False, 'message': '任务不存在'}), 404
    if task['user_id'] != session['user_id']:
        return jsonify({'success': False, 'message': '任务不存在'}), 404
    response = jsonify({
        'success': True, 'status': task['status'], 'result': task.get('result')
    })
    response.headers['Cache-Control'] = 'no-store'
    return response

def _process_subtitle():
    """处理视频字幕"""
    try:
        # 检查登录状态
        loginResult = check_login()
        resLogin = json.loads(loginResult.get_data(as_text=True))["logged_in"]
        
        if resLogin == False:
            return jsonify({"error": "未授权", "message": "请先登录"}), 401
        
        # 检查用户余额和账户状态
        u = UserUtils()
        userInfo = u.getUserInfo(session['user_id'])
        activate = userInfo['activate']
        balance = round(userInfo['balance'], 2)
        
        if balance <= 0:
            return jsonify({
                "error": "余额不足", 
                "message": f"当前余额: ¥{balance}，余额不足无法使用字幕提取功能。请点击充值链接进行充值，或联系管理员 kzhou2017@outlook.com"
            }), 402
        
        if activate == 0:
            return jsonify({
                "error": "账户未激活", 
                "message": "您的账户尚未激活，请通过邮件链接激活账户"
            }), 402
        
        data = request.get_json(silent=True) or {}
        file_path = data.get('file_path')
        output_format = data.get('output_format', 'srt')
        language = data.get('language', 'zh')
        use_r2 = data.get('use_r2', False)
        
        # 检查文件是否存在（本地文件或R2文件）
        if use_r2:
            if file_path != session.get('subtitle_upload_key'):
                return jsonify({'success': False, 'message': '上传文件无效或已过期'}), 400
            # R2文件，需要先下载到本地
            try:
                file_suffix = os.path.splitext(file_path or '')[1].lower()
                if file_suffix not in {f'.{ext}' for ext in ALLOWED_EXTENSIONS}:
                    return jsonify({'success': False, 'message': '文件格式无效'}), 400

                r2_storage = R2Storage()
                with tempfile.NamedTemporaryFile(suffix=file_suffix, delete=False) as temp_file:
                    local_file_path = temp_file.name
                
                success, error = r2_storage.download_file(file_path, local_file_path)
                if not success:
                    return jsonify({'success': False, 'message': f'下载文件失败: {error}'}), 400
                
                file_path = local_file_path
                temp_file_created = True
            except Exception as e:
                return jsonify({'success': False, 'message': f'R2存储初始化失败: {str(e)}'}), 500
        else:
            # 本地文件
            if not file_path or not os.path.exists(file_path):
                return jsonify({'success': False, 'message': '文件不存在'}), 400
            temp_file_created = False
        
        # 初始化字幕提取器
        extractor = SubtitleExtractor(openai_api_key=os.getenv('OPENAI_API_KEY'), use_r2=use_r2)
        
        # 检查视频字幕情况
        subtitle_info = extractor.check_video_subtitles(file_path)
        
        # 如果需要使用OpenAI API进行语音识别，检查余额是否足够
        if not subtitle_info['has_embedded_subtitles'] and not subtitle_info['has_external_subtitles']:
            # 获取视频时长（分钟）
            video_duration_seconds = extractor.get_video_duration(file_path)
            # video_duration_minutes = video_duration_seconds / 60.0
            
            # 计算所需费用（每分钟0.0006元）
            required_cost = video_duration_seconds * 0.0006/60*8
            
            # 检查余额是否足够
            if balance < required_cost:
                return jsonify({
                    "error": "余额不足", 
                    "message": f"当前余额: ¥{balance}，视频时长: {video_duration_seconds:.1f}秒，预计需要: ¥{required_cost:.4f}。由于余额不足无法进行这么长的视频解析，请充值"
                }), 402
        
        # 处理字幕
        result = extractor.process_video_subtitles(file_path, output_format, language)
        
        # 清理临时文件
        if temp_file_created and os.path.exists(file_path):
            os.unlink(file_path)
        
        if result['success']:
            if use_r2 and result.get('download_url'):
                # 使用R2的预签名URL
                return jsonify({
                    'success': True,
                    'message': result['message'],
                    'processing_type': result['processing_type'],
                    'subtitle_format': result['subtitle_format'],
                    'download_url': result['download_url'],
                    'filename': os.path.basename(result['r2_object_key']),
                    'use_r2': True
                })
            else:
                # 本地文件下载
                subtitle_filename = os.path.basename(result['subtitle_file'])
                download_url = f"/api/subtitle/download/{subtitle_filename}"
                
                return jsonify({
                    'success': True,
                    'message': result['message'],
                    'processing_type': result['processing_type'],
                    'subtitle_format': result['subtitle_format'],
                    'download_url': download_url,
                    'filename': subtitle_filename,
                    'use_r2': False
                })
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 500
            
    except Exception as e:
        logger.exception("处理字幕失败")
        return jsonify({'success': False, 'message': f'处理失败: {str(e)}'}), 500

@subtitleview_bp.route('/api/subtitle/download/<filename>', methods=['GET'])
def download_subtitle(filename):
    """下载字幕文件"""
    try:
        # 使用绝对路径
        subtitle_path = os.path.join(os.getcwd(), "subtitles", filename)
        
        if not os.path.exists(subtitle_path):
            logger.error(f"字幕文件不存在: {subtitle_path}")
            return jsonify({'success': False, 'message': '文件不存在'}), 404
        
        logger.info(f"下载字幕文件: {subtitle_path}")
        return send_file(
            subtitle_path,
            as_attachment=True,
            download_name=filename,
            mimetype='text/plain'
        )
        
    except Exception as e:
        logger.error(f"下载字幕文件失败: {str(e)}")
        return jsonify({'success': False, 'message': f'下载失败: {str(e)}'}), 500

@subtitleview_bp.route('/api/subtitle/download_r2/<path:object_key>', methods=['GET'])
def download_subtitle_r2(object_key):
    """从R2下载字幕文件"""
    try:
        # 尝试使用R2存储
        try:
            r2_storage = R2Storage()
        except Exception as e:
            logger.error(f"R2存储初始化失败: {str(e)}")
            return jsonify({'success': False, 'message': 'R2存储不可用'}), 500
        
        # 检查文件是否存在
        if not r2_storage.file_exists(object_key):
            logger.error(f"R2文件不存在: {object_key}")
            return jsonify({'success': False, 'message': '文件不存在'}), 404
        
        # 生成预签名URL
        success, url = r2_storage.get_file_url(object_key, expires_in=3600)
        if not success:
            logger.error(f"生成预签名URL失败: {url}")
            return jsonify({'success': False, 'message': '生成下载链接失败'}), 500
        
        logger.info(f"生成R2下载链接: {object_key}")
        return jsonify({
            'success': True,
            'download_url': url,
            'filename': os.path.basename(object_key)
        })
        
    except Exception as e:
        logger.error(f"从R2下载字幕文件失败: {str(e)}")
        return jsonify({'success': False, 'message': f'下载失败: {str(e)}'}), 500

@subtitleview_bp.route('/api/subtitle/check', methods=['POST'])
def check_subtitle():
    """检查视频字幕信息"""
    try:
        data = request.get_json()
        file_path = data.get('file_path')
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'success': False, 'message': '文件不存在'}), 400
        
        # 初始化字幕提取器
        extractor = SubtitleExtractor(openai_api_key=os.getenv('OPENAI_API_KEY'))
        
        # 检查字幕信息
        subtitle_info = extractor.check_video_subtitles(file_path)
        
        return jsonify({
            'success': True,
            'subtitle_info': subtitle_info
        })
        
    except Exception as e:
        logger.error(f"检查字幕信息失败: {str(e)}")
        return jsonify({'success': False, 'message': f'检查失败: {str(e)}'}), 500 
