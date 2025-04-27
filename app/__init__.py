from flask import Flask,session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
from cryptography.fernet import Fernet
from flask_cors import CORS
from app.OpenAI import OpenAI
from datetime import timedelta
from logging.handlers import RotatingFileHandler
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
import os
from app.alifacepay import AliFacePay
from threading import Lock

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# 创建一个 limiter 对象，此时不绑定 app
limiter = Limiter(
    key_func=get_remote_address,
    # default_limits=["200 per day", "50 per hour"]
)



def create_app():
    app = Flask(__name__)


        # 配置全局日志
    # log_level = logging.INFO
    
    # 设置日志级别为DEBUG，以便记录所有级别的日志消息
    logging.basicConfig(level=logging.DEBUG)


        # 指定日志文件夹的相对路径，例如'logs/'
    log_folder = 'logs/'

    # 获取当前文件的绝对路径
    current_file_directory = os.path.dirname(os.path.abspath(__file__))

    # 组合日志文件夹的绝对路径
    log_folder_path = os.path.join(os.path.dirname(current_file_directory),log_folder)

    # 创建日志文件夹
    os.makedirs(log_folder_path, exist_ok=True)



    # 创建一个CustomTimedRotatingFileHandler，每天生成一个日志文件，文件名格式为ap_20240427.log
    file_handler = CustomTimedRotatingFileHandler(os.path.join(log_folder_path, 'app.log'), when='midnight', interval=1, backupCount=50)
    file_handler.setLevel(logging.INFO)

    # 创建一个格式化程序，定义日志的格式
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)



    

    # 获取蓝图的logger
    openAI_logger = logging.getLogger('log')
    openAI_logger.addHandler(file_handler)

    # from auth import auth_bp
    # app.register_blueprint(auth_bp)



    #--------

    limiter.init_app(app) 
    CORS(app, origins=["https://nightwish.tech","https://www.nightwish.tech"])
   
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
    secretkey='eUadKO0oaGOYDIRqaN21IbSrFuu_xpKeA4mLmGGMzGs='
    # 配置JWT
    app.config["JWT_SECRET_KEY"] = secretkey # 保持这个秘钥的安全,login jwt
    # jwt = JWTManager(app)

    app.secret_key = secretkey  # 用于会话管理的密钥
    app.logger.info(f'key:{secretkey}')
    cipher = Fernet(secretkey.encode('utf-8'))

    app.openai = OpenAI(cipher)
    
    
    sandbox = False
    if sandbox:
            app_id = os.getenv('SANDBOX_APPID')      
            folderPath=os.getenv('SANDBOX_KEY_PATH')     
            with open( os.path.join(folderPath, "alipay_public_key.pem"), 'r') as f:
                alipay_public_key_string = f.read()         
            with open(os.path.join(folderPath,"alipay_private_key.pem"), 'r') as f:
                app_private_key_string = f.read()
    else:
            app_id = os.getenv('PRODUCTION_APPID')   
            folderPath=os.getenv('PRODUCTION_KEY_PATH')     
            with open( os.path.join(folderPath, "alipay_public_key.pem"), 'r') as f:
                alipay_public_key_string = f.read()         
            with open(os.path.join(folderPath,"alipay_private_key.pem"), 'r') as f:
                app_private_key_string = f.read()
    ali_face_pay = AliFacePay(app_id, app_private_key_string, alipay_public_key_string,
                    'https://nightwish.tech/alipay_nofity', sandbox)
    app.ali_face_pay=ali_face_pay

    from .views.chat import chatview_bp
    from .views.image import imageview_bp
    from .views.user import userview_bp
    from .views.orderCreation import orderCreationview_bp

    from .api.userAPI import userAPI_bp 
    from .api.allAPI import allAPI_bp 
    from .OpenAI import openai_bp
    
    

    app.register_blueprint(chatview_bp)
    app.register_blueprint(imageview_bp)
    app.register_blueprint(userview_bp)
    app.register_blueprint(orderCreationview_bp)

    app.register_blueprint(userAPI_bp)
    app.register_blueprint(allAPI_bp)
    app.register_blueprint(openai_bp)
    

    # app.register_blueprint(auth_bp, url_prefix='/auth') userview_bp

    return app


class CustomTimedRotatingFileHandler(TimedRotatingFileHandler):
    def __init__(self, filename, **kwargs):
        self.suffix = "%Y%m%d.log"
        super().__init__(filename, **kwargs)

    def doRollover(self):
        """
        Override base class method to use custom suffix
        """
        if self.stream:
            self.stream.close()
            self.stream = None
        self.baseFilename = "logs//app.log." + datetime.now().strftime(self.suffix)
        if not self.delay:
            self.stream = self._open()