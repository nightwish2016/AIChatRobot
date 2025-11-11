import boto3
import os
import logging
from botocore.exceptions import ClientError, NoCredentialsError
from boto3.s3.transfer import TransferConfig
from typing import Optional, Tuple
import tempfile
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv


load_dotenv()

logger = logging.getLogger(__name__)

class R2Storage:
    def __init__(self, 
                 account_id: str = None,
                 access_key_id: str = None, 
                 secret_access_key: str = None,
                 bucket_name: str = None,
                 region: str = 'auto',
                 transfer_config: TransferConfig = None):
        """
        初始化Cloudflare R2存储
        
        Args:
            account_id: Cloudflare账户ID
            access_key_id: R2访问密钥ID
            secret_access_key: R2秘密访问密钥
            bucket_name: R2存储桶名称
            region: 区域（通常为'auto'）
        """
        self.account_id = account_id or os.getenv('CLOUDFLARE_ACCOUNT_ID')
        self.access_key_id = access_key_id or os.getenv('R2_ACCESS_KEY_ID')
        self.secret_access_key = secret_access_key or os.getenv('R2_SECRET_ACCESS_KEY')
        self.bucket_name = bucket_name or os.getenv('R2_BUCKET_NAME')
        self.region = region
        self.transfer_config = transfer_config or self._build_transfer_config()
        
        if not all([self.account_id, self.access_key_id, self.secret_access_key, self.bucket_name]):
            raise ValueError("缺少必要的R2配置参数")
        
        # 创建S3客户端（R2兼容S3 API）
        self.s3_client = boto3.client(
            's3',
            endpoint_url=f'https://{self.account_id}.r2.cloudflarestorage.com',
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region
        )

    def _build_transfer_config(self) -> TransferConfig:
        """
        根据环境变量构建多线程分片上传配置，降低大文件写入耗时
        """
        threshold_mb = max(int(os.getenv('R2_MULTIPART_THRESHOLD_MB', '8')), 5)
        chunk_mb = max(int(os.getenv('R2_MULTIPART_CHUNK_MB', '8')), 5)
        max_concurrency = max(int(os.getenv('R2_MAX_CONCURRENCY', '4')), 1)

        return TransferConfig(
            multipart_threshold=threshold_mb * 1024 * 1024,
            multipart_chunksize=chunk_mb * 1024 * 1024,
            max_concurrency=max_concurrency,
            use_threads=max_concurrency > 1
        )
    
    def upload_file(self, file_path: str, object_key: str = None, 
                   content_type: str = None, public: bool = False) -> Tuple[bool, str]:
        """
        上传文件到R2
        
        Args:
            file_path: 本地文件路径
            object_key: R2对象键（如果不提供，将自动生成）
            content_type: 内容类型
            public: 是否公开访问
            
        Returns:
            (success, object_key_or_error_message)
        """
        try:
            if not os.path.exists(file_path):
                return False, f"文件不存在: {file_path}"
            
            if not object_key:
                # 生成唯一的对象键
                file_ext = os.path.splitext(file_path)[1]
                object_key = f"uploads/{uuid.uuid4().hex}{file_ext}"
            
            # 上传文件
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            self.s3_client.upload_file(
                file_path, 
                self.bucket_name, 
                object_key,
                ExtraArgs=extra_args,
                Config=self.transfer_config
            )
            
            logger.info(f"文件上传成功: {object_key}")
            return True, object_key
            
        except Exception as e:
            error_msg = f"上传文件失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def upload_fileobj(self, file_obj, object_key: str = None,
                      content_type: str = None, public: bool = False) -> Tuple[bool, str]:
        """
        上传文件对象到R2，避免先落地临时文件

        Args:
            file_obj: 一个file-like对象
            object_key: R2对象键
            content_type: 内容类型
            public: 是否公开访问

        Returns:
            (success, object_key_or_error_message)
        """
        try:
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)

            if not object_key:
                file_ext = ''
                if hasattr(file_obj, 'name'):
                    _, file_ext = os.path.splitext(file_obj.name)
                object_key = f"uploads/{uuid.uuid4().hex}{file_ext}"

            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type

            self.s3_client.upload_fileobj(
                Fileobj=file_obj,
                Bucket=self.bucket_name,
                Key=object_key,
                ExtraArgs=extra_args,
                Config=self.transfer_config
            )

            logger.info(f"文件对象上传成功: {object_key}")
            return True, object_key

        except Exception as e:
            error_msg = f"上传文件对象失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def download_file(self, object_key: str, local_path: str) -> Tuple[bool, str]:
        """
        从R2下载文件到本地
        
        Args:
            object_key: R2对象键
            local_path: 本地保存路径
            
        Returns:
            (success, error_message)
        """
        try:
            # 确保本地目录存在
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            self.s3_client.download_file(
                self.bucket_name,
                object_key,
                local_path
            )
            
            logger.info(f"文件下载成功: {object_key} -> {local_path}")
            return True, ""
            
        except Exception as e:
            error_msg = f"下载文件失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_file_url(self, object_key: str, expires_in: int = 3600) -> Tuple[bool, str]:
        """
        获取文件的预签名URL
        
        Args:
            object_key: R2对象键
            expires_in: URL过期时间（秒）
            
        Returns:
            (success, url_or_error_message)
        """
        try:
            # 获取文件扩展名以设置正确的Content-Type
            file_ext = os.path.splitext(object_key)[1].lower()
            content_type = 'text/plain'  # 默认类型
            if file_ext in ['.srt', '.vtt', '.ass', '.ssa']:
                content_type = 'text/plain'
            elif file_ext in ['.mp4', '.avi', '.mov', '.mkv']:
                content_type = 'video/mp4'
            
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name, 
                    'Key': object_key,
                    'ResponseContentType': content_type,
                    'ResponseContentDisposition': f'attachment; filename="{os.path.basename(object_key)}"'
                },
                ExpiresIn=expires_in
            )
            return True, url
            
        except Exception as e:
            error_msg = f"生成预签名URL失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def delete_file(self, object_key: str) -> Tuple[bool, str]:
        """
        删除R2中的文件
        
        Args:
            object_key: R2对象键
            
        Returns:
            (success, error_message)
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            logger.info(f"文件删除成功: {object_key}")
            return True, ""
            
        except Exception as e:
            error_msg = f"删除文件失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def file_exists(self, object_key: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            object_key: R2对象键
            
        Returns:
            文件是否存在
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=object_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                logger.error(f"检查文件存在性时出错: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"检查文件存在性时出错: {str(e)}")
            return False
    
    def get_file_size(self, object_key: str) -> Optional[int]:
        """
        获取文件大小
        
        Args:
            object_key: R2对象键
            
        Returns:
            文件大小（字节），如果失败返回None
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=object_key)
            return response['ContentLength']
        except Exception as e:
            logger.error(f"获取文件大小时出错: {str(e)}")
            return None
    
    def list_files(self, prefix: str = "", max_keys: int = 1000) -> Tuple[bool, list]:
        """
        列出指定前缀的文件
        
        Args:
            prefix: 文件前缀
            max_keys: 最大返回数量
            
        Returns:
            (success, file_list_or_error_message)
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified']
                    })
            
            return True, files
            
        except Exception as e:
            error_msg = f"列出文件失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def cleanup_temp_files(self, prefix: str = "temp/", max_age_hours: int = 24) -> Tuple[bool, str]:
        """
        清理临时文件
        
        Args:
            prefix: 临时文件前缀
            max_age_hours: 文件最大保留时间（小时）
            
        Returns:
            (success, result_message)
        """
        try:
            success, files = self.list_files(prefix)
            if not success:
                return False, files
            
            deleted_count = 0
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            for file_info in files:
                if file_info['last_modified'].replace(tzinfo=None) < cutoff_time:
                    success, _ = self.delete_file(file_info['key'])
                    if success:
                        deleted_count += 1
            
            return True, f"清理了 {deleted_count} 个临时文件"
            
        except Exception as e:
            error_msg = f"清理临时文件失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg 
