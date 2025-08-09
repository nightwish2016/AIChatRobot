from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.utils import secure_filename
import logging
import json
from ..attachment_processor import AttachmentProcessor
from .userAPI import check_login

logger = logging.getLogger(__name__)

attachment_bp = Blueprint('attachment_api', __name__)

@attachment_bp.route('/api/v1/upload_attachment', methods=['POST'])
def upload_attachment():
    """上传附件API"""
    try:
        # 检查用户登录状态
        login_result = check_login()
        res_login = json.loads(login_result.get_data(as_text=True))["logged_in"]
        
        if not res_login:
            return jsonify({
                "success": False,
                "error": "Unauthorized", 
                "message": "请先登录"
            }), 401
        
        # 检查是否有文件上传
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "message": "没有选择文件"
            }), 400
        
        file = request.files['file']
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({
                "success": False,
                "message": "无法获取用户信息"
            }), 400
        
        # 处理附件
        processor = AttachmentProcessor()
        result = processor.process_attachment(file, str(user_id))
        
        if result['success']:
            # 成功处理
            response_data = {
                "success": True,
                "message": result['message'],
                "attachment": {
                    "id": result['attachment_info']['id'],
                    "filename": result['attachment_info']['original_filename'],
                    "file_type": result['attachment_info']['file_type'],
                    "file_size": result['attachment_info']['file_size'],
                    "upload_time": result['attachment_info']['upload_time'],
                    "has_text_content": result['attachment_info']['has_text_content'],
                    "content_preview": result['attachment_info']['content_preview']
                }
            }
            
            # 将完整内容存储到Redis中，供聊天时使用（避免session过大）
            import redis
            redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
            
            attachment_key = f"attachment:{session['user_id']}:{result['attachment_info']['id']}"
            attachment_data = {
                'info': result['attachment_info'],
                'full_content': result.get('full_content', '')
            }
            
            # 存储到Redis，设置1小时过期时间
            redis_client.set(attachment_key, json.dumps(attachment_data), ex=3600)
            
            # 在session中只记录附件ID列表，避免session过大
            if 'attachment_ids' not in session:
                session['attachment_ids'] = []
            
            if result['attachment_info']['id'] not in session['attachment_ids']:
                session['attachment_ids'].append(result['attachment_info']['id'])
            
            return jsonify(response_data), 200
        else:
            # 处理失败
            return jsonify({
                "success": False,
                "message": result['message']
            }), 400
            
    except Exception as e:
        error_msg = f"上传附件时发生错误: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "success": False,
            "message": "服务器内部错误"
        }), 500

@attachment_bp.route('/api/v1/get_attachment/<attachment_id>', methods=['GET'])
def get_attachment_info(attachment_id):
    """获取附件信息"""
    try:
        # 检查用户登录状态
        login_result = check_login()
        res_login = json.loads(login_result.get_data(as_text=True))["logged_in"]
        
        if not res_login:
            return jsonify({
                "success": False,
                "error": "Unauthorized", 
                "message": "请先登录"
            }), 401
        
        # 从Redis中获取附件信息
        import redis
        redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
        
        attachment_key = f"attachment:{session['user_id']}:{attachment_id}"
        attachment_data_str = redis_client.get(attachment_key)
        
        if not attachment_data_str:
            return jsonify({
                "success": False,
                "message": "附件不存在或已过期"
            }), 404
        
        attachment_data = json.loads(attachment_data_str)
        attachment_info = attachment_data['info']
        
        # 生成下载URL
        processor = AttachmentProcessor()
        success, download_url = processor.get_attachment_download_url(attachment_info['r2_key'])
        
        response_data = {
            "success": True,
            "attachment": {
                "id": attachment_info['id'],
                "filename": attachment_info['original_filename'],
                "file_type": attachment_info['file_type'],
                "file_size": attachment_info['file_size'],
                "upload_time": attachment_info['upload_time'],
                "has_text_content": attachment_info['has_text_content'],
                "content_preview": attachment_info['content_preview'],
                "download_url": download_url if success else None
            }
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        error_msg = f"获取附件信息时发生错误: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "success": False,
            "message": "服务器内部错误"
        }), 500

@attachment_bp.route('/api/v1/delete_attachment/<attachment_id>', methods=['DELETE'])
def delete_attachment(attachment_id):
    """删除附件"""
    try:
        # 检查用户登录状态
        login_result = check_login()
        res_login = json.loads(login_result.get_data(as_text=True))["logged_in"]
        
        if not res_login:
            return jsonify({
                "success": False,
                "error": "Unauthorized", 
                "message": "请先登录"
            }), 401
        
        # 从Redis中删除附件信息
        import redis
        redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
        
        attachment_key = f"attachment:{session['user_id']}:{attachment_id}"
        
        if redis_client.exists(attachment_key):
            # 删除Redis中的附件数据
            redis_client.delete(attachment_key)
            
            # 从session的附件ID列表中移除
            if 'attachment_ids' in session and attachment_id in session['attachment_ids']:
                session['attachment_ids'].remove(attachment_id)
            
            return jsonify({
                "success": True,
                "message": "附件已删除"
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "附件不存在"
            }), 404
            
    except Exception as e:
        error_msg = f"删除附件时发生错误: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "success": False,
            "message": "服务器内部错误"
        }), 500
