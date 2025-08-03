from flask import Blueprint, request, jsonify, send_file, render_template, session
import os
import uuid
import json
from werkzeug.utils import secure_filename
from app.subtitle_extractor import SubtitleExtractor
from ..UserUtils import UserUtils
from app.api.userAPI import check_login
import logging

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
        
        # 生成唯一文件名
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
        
        # 保存文件
        upload_folder = "uploads"
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        logger.info(f"文件上传成功: {file_path}")
        
        return jsonify({
            'success': True,
            'message': '文件上传成功',
            'file_path': file_path,
            'original_filename': file.filename
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
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'success': False, 'message': '文件不存在'}), 400
        
        # 初始化字幕提取器
        extractor = SubtitleExtractor(openai_api_key=os.getenv('OPENAI_API_KEY'))
        
        # 处理字幕
        result = extractor.process_video_subtitles(file_path, output_format)
        
        if result['success']:
            # 获取相对路径用于下载
            subtitle_filename = os.path.basename(result['subtitle_file'])
            download_url = f"/api/subtitle/download/{subtitle_filename}"
            
            return jsonify({
                'success': True,
                'message': result['message'],
                'processing_type': result['processing_type'],
                'subtitle_format': result['subtitle_format'],
                'download_url': download_url,
                'filename': subtitle_filename
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