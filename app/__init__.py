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
            app_id = '9021000137634851'
            alipay_public_key_string = '''-----BEGIN PUBLIC KEY-----
    MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAo3XUTdshfLg3a415orD2APguhRTdN/fLeVetJndYJYxhE33n7MHdR6zntHc/z4dBuekxBivUoQ5kkN+iFBSa3DFWz5qIsOqizdjUrvFf+xVvgcw3AteKx7MslCIhRACzKweLzMkGdPt+MRTuZIOE01KbeSu7yR5DaYuwIFSYJAmpzG0rN37TiaJz9dsQPF/JGvVnQ7XMNNp1se8Cb/PQN5RS6hoyOjilBFF162rZmunqNRtMZzKcwq88he6HGncu6gNB02TloLdSMhD29gO5kSrO10sBiGBtW8khQPE0mFsW+ps/8dJiH0D8eWFC2V6LzUvUfT+TMLMoInsM2495uQIDAQAB
    -----END PUBLIC KEY-----'''
            app_private_key_string ='''-----BEGIN RSA PRIVATE KEY-----
    MIIEowIBAAKCAQEAhHUCnphzIcEV7Al3NqgtXhReYbQ4X4smAAzMdTkbXMIP30FNqzLi8pXPPQJFmWoK2CXUlxTCEQtuFF5VHJligRbvjEwY5uwMJtAWBYFOA1wAXHUe7COSFlvhU/PPP0jue14ZRgzRC+Tj9F+05o0ZeWU/HL9zkRohFbzKNGWK5WdXZhZFQDiI1P2HOHKoIZVhtpA7qkiUzBnynmBML2bHJ8W0PZ5HKY7/mSF9v3wCP5pEfE8HJUKb6mznQm29I6mRES3vNWWGdxS4jHGwI8q56Bm/aKBDN6esC2+25goAoUaUprzv0jer37sMS5m8Et17W+/e5erXK6K641/soc+Y4QIDAQABAoIBAGDky47CjG4jteqdngRwkAdjNQuZ7ycNPjYJJsOVi8uV9lBlj/BtYBD+v8OsVsd8CATH37TJLZGUX+ksfGxYU/OEmKVzwT+jatw1mfZa+XuBoI4B6yXoe2Q5wCJOlst/iVzbn/dbRszBmnNYU5fXncvs4XchIeQCTjN9kBk2Mp3OpmNqTVoY8V4Zgy4r5RsGbz7MwgPEnD8wptSXb56J4YrC69iCh3sBmJynuylkulhiofMFrkR11F4gXh+yiuUBZ/T+QGyBYwTYow+YlYZw1sliCfAipqEpJ9d6McBXSz67cxshYO2CrzfDvPkLR0uqGVZVhZEYDkg7wvm2nmIqBNUCgYEAvPSdYsGZP+QxVI2rak0oSUVBlpp4y9Fzi6CnTrNmKNKEGCWTuournQrvdxCWPL20GxwTp023+J5UOBvRbuMtwmwJruawfwUAOCielab/331tYIKOxOOc5JVNxNex4bd6Z0/F5zj/BndOS2O+zqNlVmSwPAO7U1B8mKm4q/i1Cq8CgYEAs3R5kcpmLBghyMdUj3dwjIfc5+zWW8CoxerKkAm519MDg6EplFiXi2IJuLb2HO0f00xxukcXa3rDYMQg7fW+rHDfovq3h9u0gFiR7I21DfTJDLCn0XM7zKSjN8a1kjev2uuvEUbFHnCKrKRWEE4lcKgTHjn91gOgCX5dK/LBOW8CgYA9jZ37fr+SbZ6YQbI2Zb4a6EGuctGo66ktMf9uhshfwfwf9ZXDLh6QgPBzI+cdEFssfZ/1Xz7v8XvT71PxQHY2oIUjAak7J4Djym+mpokx36USzFT/1HnWiMCVwAIFWoS4ROdeJFYHYDQUIQEWRWoMk65JTpnmURDVlmw/MTygpwKBgHGZE7PUWeUjyY8dj0vaIebzwkUWSYN/a9cNj/iqD3it3RWgGYAMrLHQ97J0L0uUV4ccZwmyIwMojTFeNjIsU+047nhvGWrpC1QLvSPveGNDR1m/IhyWQ46B0chnA11x3uJIO2RGVlW0jDRJOynLLiwoWSHTN/oYBWC9GyHM48AFAoGBALVms3TZe6MAqf/cLnqpYn+8hmJAY+tWNQNYo/aqL8wMvlbz2cRgSa5g3CQ1YTuvmXiXaDOFE2RMfjnWR3AdCIYBc4m017PdcnhzdlEwRZkpdGyrx/7+AP2dogOCENPU1nMGcaNFk+Kqf6xbl+YTQY+SeoEQBfwCdpsfsYyVdww1
    -----END RSA PRIVATE KEY-----'''
    else:
            app_id = '2021004147613257'
            alipay_public_key_string = '''-----BEGIN PUBLIC KEY-----
    MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAg72eX+UrgOmblsV/EWpNyTtJPhQ2TVi6ZQAIX6Q2m8RdMUcEH7/aSuSlMqsbnDVrj+QafYpsI4sj6VOCle4PPg8E51NpuC2qMXLlQ4jlNcVu5CxDXPn/pk6zSL2Ptb0LcIird3M76+KHJmTjWFmUUxT+MCVOCP5OcV413k3WtZWoSuVO4AmRXioRUwNQZBxcodLZDNI3OpzG9a0ibVF3FmIj13C1uLDqqSc/VjdSX0KrzClI1BmDhEnmX9YmleMohG81yVJG5v1geG3SErYsa+VAhhrb+Ta4avH3TccIQA/8Fix66xfwF0v8FGFQUq5j3yGMWJ4CbR387irk52zMkwIDAQAB
    -----END PUBLIC KEY-----'''        

            app_private_key_string ='''-----BEGIN RSA PRIVATE KEY-----
    MIIEpQIBAAKCAQEAlvZAeljS6UJy4whts05ekFywZ/zyrl7sOCZWro8JCMdENTW9Hbetaq7xtNeb92iH/JZ2Lyobl5TDkHw6NsJJVVv8Qptk5fJikJiF0n8UtN+/P6jrY3CP4tbE6dl+PrIL8KtHQWL0MBKbr9Uegdihku/S4ApslLC4BiaghRIKa5dGia2awNQjtozI/IW9wq4qnrRBAcuj/jsPXR8GcW/TyD2gZ/rWfqD6NflRYVAFt9STbCiHOYN/a8Zo9ko+GOXW0apCXeDyCpp0+t2k1/pxS176FTMTH+INpDpA7WmsQ8RbMBItahVhj6visg9eZymIF4lctSPun99cCBprdk01bQIDAQABAoIBAQCMY5fU79O8r1oOPqFeNcyFbl1zZ238sTP2h9jm3wgkzMNmxIIKJ+2zH9ySNEzMSb7lLLvd4sfkMKmqLY0prYbrRe8TtlWf7siw9dbFyf7ksou11Q6K3HxDFT3sx6G7BnNKLs7GRRMXvcZhP83uLRsdfcBbL/aIVMvelH+FISDlqkxnCB5nbrtft1FsTIlKqNedQNGmRANoYfuqRnUZ5pgZCtIxyOyiKLSAD4Mzu6ZaLaUu7iEmhuyYB128pVDtzPRDqA9o+yufmsV9kofT6g7ld3Gz78IfKLV76njqXDk+t0knX4DXx9uLLklOJWDaA3+3F3/E7kpiKRsV+Sb1IZYBAoGBAMkj/g5QyJWrdQFm7/BDQrlH3tWF5MRA9F9MshxNnf8IklGMJesRUK12rk27Enhypq4UvqxpWnivAbJs48JXj40pMgi50RHLVj3GcTNpuQ96eaa6ig2+JqBaeqd9xeOAAztqnorWW63ecY2NNFC70sYFOBZwPavx8oH9tvCcA/WBAoGBAMAisRv6lMk2SnGkYy+PC2VZ1t19dz8NcVi1PTSJDurDrk1KGFvpn0oI54tOxthEwUszxaQSNfVwwSTJupF3aTkEkd4+rNurb9x9/A98DMXzXNRjT6H3vZ3mikFfL7RWqP5Xi9YxuCrcYQUpszVslXmXd+SuHC76TpBcjiSym23tAoGBALwF8ETTkV4P5BWGcz7msSXgIFb7jelDSu0XFdxNVieEjLq8RunhysgMjE3PVSnRCyzp6X/kEBWGixCOp64RCfkMDGCJyv1WVezzZviHmN32QGfyMoE8QoFdcxDFCspq7RqKxV/Fl/gFW6LV35Skrxg64r5e99eXGXoYgP2U6kKBAoGAIYhsfMOZIBz3lSnpna1Lgd7SH0n8e+aut5q6Gecp0VNhol+iLLhzcopnTurqzWgCjEt23RHIlROewfrrMuQyWx8vDijGJnifR049pb4yxIGa2/6RMWV5lItd6dbhDoppaCqDX1jCGcjorev/OP3AgL4s0J6KkLBi8dMVg9YgRmkCgYEAhrTE1d8p/5y75PCcyKg314Q2CYzrzN9rfTPsKgRAlqlK+FyAwaDZcYZTCFrZaYIP8y0RUU7LJHzMYGk89tHtcdjncr82Atu7pFBHpe+r2ReD1JtfYxjaRVQo4U5j75nJfkTZFDiV1RNpwci29MrMRwUJEx573mrbGDg9SRpM6uY=
    -----END RSA PRIVATE KEY-----'''
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