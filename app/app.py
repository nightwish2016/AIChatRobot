from flask import Flask, request, jsonify,make_response
from flask import Flask, request,session
from flask_restx import Api, Resource, fields

from flask_cors import CORS
from flask import  redirect, url_for, session,render_template,send_from_directory
from authlib.integrations.flask_client import OAuth
from UserUtils  import UserUtils
import json
from werkzeug.security import generate_password_hash,check_password_hash
from datetime import timedelta
import os
from cryptography.fernet import Fernet
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_jwt_extended import JWTManager, jwt_required, create_access_token
import uuid
from chatHistoryUtils import chatHistoryUtils
import logging 
from OpenAI import OpenAI





app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
CORS(app, origins=["https://nightwish.tech","https://www.nightwish.tech"])
limiter = Limiter(
  
    app=app,  # 绑定Flask应用
    key_func=get_remote_address,  # 使用客户端IP地址作为限制键值
    # default_limits=["500 per day", "50 per hour"]
)


# app.secret_key = 'your_very_secret_key_here'   # 用于会话管理的密钥




  
   




  

    
   

    # print(response['choices'][0]['message'])
 
          
   









if __name__ == '__main__':
    # app.run(debug=True)
    app.run(host='0.0.0.0',port=5000,debug=True)
