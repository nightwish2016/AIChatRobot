import os
import tempfile
import subprocess
import json
import logging
from typing import Optional, Tuple, List
import pysrt
import webvtt
from datetime import datetime, timedelta
import re
import openai
from app.chatHistoryUtils import chatHistoryUtils
from flask import Flask, request,session,jsonify
import time

# 尝试导入ffmpeg，如果失败则使用subprocess
try:
    import ffmpeg
    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False
    logging.warning("ffmpeg-python 未安装，将使用 subprocess 调用 ffmpeg")

logger = logging.getLogger(__name__)

class SubtitleExtractor:
    def __init__(self, upload_folder: str = "uploads", output_folder: str = "subtitles", openai_api_key: str = None):
        self.upload_folder = upload_folder
        self.output_folder = output_folder
        self.openai_api_key = openai_api_key
        
        os.makedirs(upload_folder, exist_ok=True)
        os.makedirs(output_folder, exist_ok=True)
        
        self.supported_video_formats = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
        self.supported_audio_formats = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac']
        
        # 设置OpenAI API密钥
        if openai_api_key:
            self.openai_api_key = openai_api_key
        else:
            # 尝试从环境变量获取
            self.openai_api_key = os.getenv('OPENAI_API_KEY')
    
    def get_video_duration(self, video_path: str) -> float:
        """获取视频时长（秒）"""
        try:
            if FFMPEG_AVAILABLE:
                probe = ffmpeg.probe(video_path)
            else:
                # 使用subprocess调用ffprobe
                result = subprocess.run([
                    'ffprobe', '-v', 'quiet', '-print_format', 'json', 
                    '-show_format', video_path
                ], capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception(f"ffprobe failed: {result.stderr}")
                probe = json.loads(result.stdout)
            
            duration = float(probe['format']['duration'])
            return duration
            
        except Exception as e:
            logger.error(f"获取视频时长时出错: {str(e)}")
            return 0.0

    def check_video_subtitles(self, video_path: str) -> dict:
        try:
            if FFMPEG_AVAILABLE:
                probe = ffmpeg.probe(video_path)
            else:
                # 使用subprocess调用ffprobe
                result = subprocess.run([
                    'ffprobe', '-v', 'quiet', '-print_format', 'json', 
                    '-show_streams', video_path
                ], capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception(f"ffprobe failed: {result.stderr}")
                probe = json.loads(result.stdout)
            
            subtitle_info = {
                'has_embedded_subtitles': False,
                'has_external_subtitles': False,
                'subtitle_streams': [],
                'external_subtitle_files': []
            }
            
            for stream in probe.get('streams', []):
                if stream.get('codec_type') == 'subtitle':
                    subtitle_info['has_embedded_subtitles'] = True
                    subtitle_info['subtitle_streams'].append({
                        'index': stream.get('index'),
                        'codec_name': stream.get('codec_name'),
                        'language': stream.get('tags', {}).get('language', 'unknown'),
                        'title': stream.get('tags', {}).get('title', '')
                    })
            
            video_dir = os.path.dirname(video_path)
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            
            subtitle_extensions = ['.srt', '.vtt', '.ass', '.ssa', '.sub']
            for ext in subtitle_extensions:
                subtitle_file = os.path.join(video_dir, f"{video_name}{ext}")
                if os.path.exists(subtitle_file):
                    subtitle_info['has_external_subtitles'] = True
                    subtitle_info['external_subtitle_files'].append(subtitle_file)
            
            return subtitle_info
            
        except Exception as e:
            logger.error(f"检查视频字幕时出错: {str(e)}")
            return {
                'has_embedded_subtitles': False,
                'has_external_subtitles': False,
                'subtitle_streams': [],
                'external_subtitle_files': [],
                'error': str(e)
            }
    
    def extract_embedded_subtitles(self, video_path: str, output_path: str, stream_index: int = 0) -> bool:
        try:
            if FFMPEG_AVAILABLE:
                stream = ffmpeg.input(video_path)
                stream = ffmpeg.output(stream[f's:{stream_index}'], output_path, f='srt')
                ffmpeg.run(stream, overwrite_output=True, quiet=True)
            else:
                # 使用subprocess调用ffmpeg
                result = subprocess.run([
                    'ffmpeg', '-i', video_path, '-map', f'0:s:{stream_index}',
                    '-f', 'srt', output_path, '-y'
                ], capture_output=True)
                if result.returncode != 0:
                    raise Exception(f"ffmpeg failed: {result.stderr.decode()}")
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"成功提取内嵌字幕到: {output_path}")
                return True
            else:
                logger.warning(f"提取的字幕文件为空或不存在: {output_path}")
                return False
                
        except Exception as e:
            logger.error(f"提取内嵌字幕时出错: {str(e)}")
            return False
    
    def generate_subtitles_with_whisper(self, audio_path: str, output_path: str, 
                                       language: str = 'zh') -> bool:
        userId=session['user_id']                      
        current_timestamp = time.time()
        created=current_timestamp    
        chargeStatus=1
        # params= (userId,'whisper-1',20,created,chargeStatus)
        # u=chatHistoryUtils()
        # u.insertTranscriptionHistory(params)
        try:
            logger.info(f"开始使用OpenAI Whisper API转录音频: {audio_path}")
            
            # 检查API密钥
            if not self.openai_api_key:
                raise Exception("OpenAI API密钥未设置")
            
            # 使用新版本的OpenAI API
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)
            
            # 打开音频文件
            with open(audio_path, "rb") as audio_file:
                # 调用OpenAI Whisper API
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language if language != 'auto' else None,
                    response_format="verbose_json"
                )
            
            # 保存为SRT格式
            self._save_openai_whisper_result_as_srt(transcript.model_dump(), output_path)
            
            logger.info(f"成功生成字幕: {output_path}")

            #计算费用
          
            params= (userId,'whisper-1',transcript.usage.seconds,created,chargeStatus)
        
            u=chatHistoryUtils()
            u.insertTranscriptionHistory(params)

            return True
            
        except Exception as e:
            logger.error(f"使用OpenAI Whisper API生成字幕时出错: {str(e)}")
            return False
    
    def _save_openai_whisper_result_as_srt(self, transcript: dict, output_path: str):
        with open(output_path, 'w', encoding='utf-8-sig') as f:
            for i, segment in enumerate(transcript['segments'], 1):
                start_time = self._seconds_to_srt_time(segment['start'])
                end_time = self._seconds_to_srt_time(segment['end'])
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{segment['text'].strip()}\n\n")
    
    def _seconds_to_srt_time(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    def extract_audio_from_video(self, video_path: str, audio_path: str) -> bool:
        try:
            if FFMPEG_AVAILABLE:
                stream = ffmpeg.input(video_path)
                stream = ffmpeg.output(stream, audio_path, acodec='pcm_s16le', ac=1, ar=16000)
                ffmpeg.run(stream, overwrite_output=True, quiet=True)
            else:
                # 使用subprocess调用ffmpeg
                result = subprocess.run([
                    'ffmpeg', '-i', video_path, '-acodec', 'pcm_s16le',
                    '-ac', '1', '-ar', '16000', audio_path, '-y'
                ], capture_output=True)
                if result.returncode != 0:
                    raise Exception(f"ffmpeg failed: {result.stderr.decode()}")
            
            return os.path.exists(audio_path) and os.path.getsize(audio_path) > 0
            
        except Exception as e:
            logger.error(f"提取音频时出错: {str(e)}")
            return False
    
    def process_video_subtitles(self, video_path: str, output_format: str = 'srt') -> dict:
        result = {
            'success': False,
            'message': '',
            'subtitle_file': None,
            'subtitle_format': output_format,
            'processing_type': None
        }
        
        try:
            subtitle_info = self.check_video_subtitles(video_path)
            
            if subtitle_info['has_embedded_subtitles']:
                logger.info("检测到内嵌字幕，开始提取...")
                base_name = os.path.splitext(os.path.basename(video_path))[0]
                temp_srt = os.path.join(self.output_folder, f"{base_name}.srt")
                
                if self.extract_embedded_subtitles(video_path, temp_srt):
                    result['processing_type'] = 'embedded_subtitle'
                    result['success'] = True
                    result['message'] = '成功提取内嵌字幕'
                    result['subtitle_file'] = temp_srt
                else:
                    result['message'] = '提取内嵌字幕失败'
                    
            elif subtitle_info['has_external_subtitles']:
                logger.info("检测到外挂字幕文件")
                external_subtitle = subtitle_info['external_subtitle_files'][0]
                result['processing_type'] = 'external_subtitle'
                result['success'] = True
                result['message'] = '使用外挂字幕文件'
                result['subtitle_file'] = external_subtitle
                    
            else:
                logger.info("未检测到字幕，开始语音识别...")
                temp_audio = os.path.join(self.output_folder, f"temp_{os.path.basename(video_path)}.wav")
                
                if self.extract_audio_from_video(video_path, temp_audio):
                    # 使用原始文件名作为基础，避免路径问题
                    base_name = os.path.splitext(os.path.basename(video_path))[0]
                    final_output = os.path.join(self.output_folder, f"{base_name}.{output_format}")
                    
                    if self.generate_subtitles_with_whisper(temp_audio, final_output):
                        result['processing_type'] = 'speech_recognition'
                        result['success'] = True
                        result['message'] = '成功通过语音识别生成字幕'
                        result['subtitle_file'] = final_output
                    else:
                        result['message'] = '语音识别生成字幕失败'
                    
                    if os.path.exists(temp_audio):
                        os.remove(temp_audio)
                else:
                    result['message'] = '提取音频失败'
            
            return result
            
        except Exception as e:
            logger.error(f"处理视频字幕时出错: {str(e)}")
            result['message'] = f'处理失败: {str(e)}'
            return result 