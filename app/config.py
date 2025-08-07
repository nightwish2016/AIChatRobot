"""
配置管理模块
处理环境变量的加载和Creem环境的切换
"""

import os
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

class CreemConfig:
    """Creem配置管理类"""
    
    def __init__(self):
        self.environment = os.getenv('CREEM_ENVIRONMENT', 'sandbox').lower()
        
    def get_api_key(self):
        """获取当前环境的API密钥"""
        if self.environment == 'production':
            return os.getenv('CREEM_PRODUCTION_API_KEY')
        else:
            return os.getenv('CREEM_SANDBOX_API_KEY')
    
    def get_base_url(self):
        """获取当前环境的API基础URL"""
        if self.environment == 'production':
            return os.getenv('CREEM_PRODUCTION_BASE_URL', 'https://api.creem.io/v1')
        else:
            return os.getenv('CREEM_SANDBOX_BASE_URL', 'https://test-api.creem.io/v1')
    
    def get_webhook_secret(self):
        """获取当前环境的Webhook密钥"""
        if self.environment == 'production':
            return os.getenv('CREEM_PRODUCTION_WEBHOOK_SECRET')
        else:
            return os.getenv('CREEM_SANDBOX_WEBHOOK_SECRET')
    
    def is_production(self):
        """检查是否为生产环境"""
        return self.environment == 'production'
    
    def is_sandbox(self):
        """检查是否为沙盒环境"""
        return self.environment == 'sandbox'
    
    def get_environment_info(self):
        """获取当前环境信息"""
        return {
            'environment': self.environment,
            'api_key': self.get_api_key()[:10] + '...' if self.get_api_key() else None,
            'base_url': self.get_base_url(),
            'webhook_secret': self.get_webhook_secret()[:10] + '...' if self.get_webhook_secret() else None,
            'is_production': self.is_production()
        }

# 全局配置实例
creem_config = CreemConfig()

# 向后兼容的函数
def get_creem_api_key():
    """获取Creem API密钥"""
    return creem_config.get_api_key()

def get_creem_base_url():
    """获取Creem API基础URL"""
    return creem_config.get_base_url()

def get_creem_webhook_secret():
    """获取Creem Webhook密钥"""
    return creem_config.get_webhook_secret()

def get_current_environment():
    """获取当前环境"""
    return creem_config.environment

# 其他配置
class AppConfig:
    """应用配置类"""
    
    # 数据库配置
    DB_PATH = os.getenv('DB_PATH', './DB/OpenAI.db')
    
    # Flask配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    
    # Redis配置
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    
    # 邮件配置
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587)) if os.getenv('MAIL_PORT') else 587
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')

# 全局应用配置实例
app_config = AppConfig()