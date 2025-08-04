from flask import Blueprint, request, jsonify, send_file, render_template, session
import os
import uuid
import json
from werkzeug.utils import secure_filename
from app.subtitle_extractor import SubtitleExtractor
from ..UserUtils import UserUtils
from app.api.userAPI import check_login
import logging
from app.chatHistoryUtils import chatHistoryUtils
from app.r2_storage import R2Storage

logger = logging.getLogger(__name__)

subtitleview_bp = Blueprint('subtitle', __name__)

# 支持的视频格式
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm', 'mp3', 'wav', 'm4a', 'aac', 'ogg', 'flac'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@subtitleview_bp.route('/subtitle', methods=['GET'])
def subtitle_page():
    """字幕提取页面"""
    if 'user_name' in session:
        u = UserUtils()
        userInfo = u.getUserInfo(session['user_id'])
        balance = userInfo['balance']
        return render_template('subtitle.html', user_name=session['user_name'], balance=round(balance, 2))
    else:
        return render_template('subtitle.html')

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
        
        if use_r2:
            # 保存到临时文件然后上传到R2
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                file.save(temp_file.name)
                temp_path = temp_file.name
            
            # 生成唯一文件名
            file_ext = file.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
            object_key = f"uploads/{unique_filename}"
            
            # 上传到R2
            success, result = r2_storage.upload_file(
                temp_path, 
                object_key=object_key,
                content_type=file.content_type
            )
            
            # 清理临时文件
            os.unlink(temp_path)
            
            if success:
                logger.info(f"文件上传到R2成功: {result}")
                return jsonify({
                    'success': True,
                    'message': '文件上传成功',
                    'file_path': result,  # R2对象键
                    'original_filename': file.filename,
                    'use_r2': True
                })
            else:
                logger.error(f"上传到R2失败: {result}")
                return jsonify({'success': False, 'message': f'上传失败: {result}'}), 500
        else:
            # 本地存储
            file_ext = file.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
            
            upload_folder = "uploads"
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, unique_filename)
            file.save(file_path)
            
            logger.info(f"文件上传成功: {file_path}")
            
            return jsonify({
                'success': True,
                'message': '文件上传成功',
                'file_path': file_path,
                'original_filename': file.filename,
                'use_r2': False
            })
        
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        return jsonify({'success': False, 'message': f'上传失败: {str(e)}'}), 500

@subtitleview_bp.route('/api/subtitle/process', methods=['POST'])
def process_subtitle():
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
        
        data = request.get_json()
        file_path = data.get('file_path')
        output_format = data.get('output_format', 'srt')
        language = data.get('language', 'zh')
        use_r2 = data.get('use_r2', False)
        
        # 检查文件是否存在（本地文件或R2文件）
        if use_r2:
            # R2文件，需要先下载到本地
            try:
                r2_storage = R2Storage()
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
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
        logger.error(f"处理字幕失败: {str(e)}")
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