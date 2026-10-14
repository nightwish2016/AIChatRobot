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
import csv
from concurrent.futures import ThreadPoolExecutor
from app.r2_storage import R2Storage

# 尝试导入ffmpeg，如果失败则使用subprocess
try:
    import ffmpeg
    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False
    logging.warning("ffmpeg-python 未安装，将使用 subprocess 调用 ffmpeg")

logger = logging.getLogger('log')

class SubtitleExtractor:
    MAX_OPENAI_AUDIO_BYTES = 24 * 1024 * 1024
    TRANSCRIPTION_CHUNK_SECONDS = 600
    TRANSCRIPTION_CONCURRENCY = 3

    def __init__(self, upload_folder: str = "uploads", output_folder: str = "subtitles", openai_api_key: str = None, use_r2: bool = True):
        self.upload_folder = upload_folder
        self.output_folder = output_folder
        self.openai_api_key = openai_api_key
        self.use_r2 = use_r2
        
        # 初始化R2存储（如果启用）
        if self.use_r2:
            try:
                self.r2_storage = R2Storage()
                logger.info("R2存储初始化成功")
            except Exception as e:
                logger.warning(f"R2存储初始化失败，将使用本地存储: {str(e)}")
                self.use_r2 = False
        
        # 只有在不使用R2时才创建本地文件夹
        if not self.use_r2:
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
            started = time.perf_counter()
            with OpenAI(api_key=self.openai_api_key) as client:
                duration = self.get_video_duration(audio_path)
                if duration > self.TRANSCRIPTION_CHUNK_SECONDS:
                    transcript = self._transcribe_long_audio(client, audio_path, language)
                else:
                    transcript = self._transcribe_audio_part(client, audio_path, language)
            
            # 保存为SRT格式
            self._save_openai_whisper_result_as_srt(transcript, output_path)
            
            logger.info(f"成功生成字幕: {output_path}")

            #计算费用
          
            usage = transcript.get('usage') or {}
            billed_seconds = usage.get('seconds', transcript.get('duration', duration))
            params= (userId,'whisper-1',billed_seconds,created,chargeStatus)
        
            u=chatHistoryUtils()
            u.insertTranscriptionHistory(params)
            logger.info(f"语音识别完成，耗时 {time.perf_counter() - started:.1f} 秒")

            return True
            
        except Exception as e:
            logger.error(f"使用OpenAI Whisper API生成字幕时出错: {str(e)}")
            return False

    def _transcribe_audio_part(self, client, audio_path: str, language: str) -> dict:
        with open(audio_path, 'rb') as audio_file:
            transcript = client.audio.transcriptions.create(
                model='whisper-1',
                file=audio_file,
                language=language if language != 'auto' else None,
                response_format='verbose_json'
            )
        return transcript.model_dump()

    def _transcribe_long_audio(self, client, audio_path: str, language: str) -> dict:
        with tempfile.TemporaryDirectory(prefix='subtitle_audio_') as chunk_directory:
            manifest_path = os.path.join(chunk_directory, 'segments.csv')
            codec_args = ['-c:a', 'copy'] if audio_path.lower().endswith('.mp3') else [
                '-c:a', 'libmp3lame', '-ac', '1', '-ar', '16000', '-b:a', '48k'
            ]
            subprocess.run([
                'ffmpeg', '-v', 'error', '-i', audio_path, '-map', '0:a:0',
                *codec_args, '-f', 'segment',
                '-segment_time', str(self.TRANSCRIPTION_CHUNK_SECONDS),
                '-reset_timestamps', '1', '-segment_list', manifest_path,
                '-segment_list_type', 'csv',
                os.path.join(chunk_directory, 'audio_%04d.mp3'), '-y'
            ], capture_output=True, check=True)
            with open(manifest_path, newline='', encoding='utf-8') as manifest_file:
                chunks = list(csv.reader(manifest_file))
            if not chunks:
                raise ValueError('音频切段结果为空')
            initial_start = float(chunks[0][1])
            logger.info(f"长音频切为 {len(chunks)} 段，并发识别数 {self.TRANSCRIPTION_CONCURRENCY}")

            def transcribe_chunk(chunk):
                chunk_path = os.path.join(chunk_directory, os.path.basename(chunk[0]))
                if os.path.getsize(chunk_path) > self.MAX_OPENAI_AUDIO_BYTES:
                    raise ValueError('音频分段超过识别大小限制')
                result = self._transcribe_audio_part(client, chunk_path, language)
                logger.info(f"音频分段识别完成: {os.path.basename(chunk_path)}")
                return result

            with ThreadPoolExecutor(max_workers=self.TRANSCRIPTION_CONCURRENCY) as executor:
                results = list(executor.map(transcribe_chunk, chunks))

            segments = []
            billed_seconds = 0
            for chunk, result in zip(chunks, results):
                offset = float(chunk[1]) - initial_start
                duration = float(chunk[2]) - float(chunk[1])
                billed_seconds += (result.get('usage') or {}).get('seconds', result.get('duration', duration))
                for segment in result.get('segments', []):
                    adjusted = dict(segment)
                    adjusted['start'] = offset + max(0, min(float(segment['start']), duration))
                    adjusted['end'] = offset + max(0, min(float(segment['end']), duration))
                    if adjusted['end'] > adjusted['start']:
                        segments.append(adjusted)
            return {
                'segments': segments,
                'usage': {'seconds': billed_seconds},
                'duration': float(chunks[-1][2]) - initial_start
            }
    
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
                stream = ffmpeg.output(stream, audio_path, vn=None, acodec='libmp3lame', ac=1, ar=16000, audio_bitrate='48k')
                ffmpeg.run(stream, overwrite_output=True, quiet=True)
            else:
                # 使用subprocess调用ffmpeg
                result = subprocess.run([
                    'ffmpeg', '-i', video_path, '-vn', '-acodec', 'libmp3lame',
                    '-ac', '1', '-ar', '16000', '-b:a', '48k', audio_path, '-y'
                ], capture_output=True)
                if result.returncode != 0:
                    raise Exception(f"ffmpeg failed: {result.stderr.decode()}")
            
            return os.path.exists(audio_path) and os.path.getsize(audio_path) > 0
            
        except Exception as e:
            logger.error(f"提取音频时出错: {str(e)}")
            return False

    def is_supported_audio_file(self, file_path: str) -> bool:
        return os.path.splitext(file_path)[1].lower() in self.supported_audio_formats

    def should_transcribe_directly(self, file_path: str) -> bool:
        return os.path.getsize(file_path) <= self.MAX_OPENAI_AUDIO_BYTES

    def compress_audio_for_transcription(self, input_path: str, output_path: str) -> bool:
        try:
            logger.info(f"音频文件超过接口限制，开始压缩: {input_path}")
            if FFMPEG_AVAILABLE:
                stream = ffmpeg.input(input_path)
                stream = ffmpeg.output(stream, output_path, vn=None, acodec='libmp3lame', ac=1, ar=16000, audio_bitrate='48k')
                ffmpeg.run(stream, overwrite_output=True, quiet=True)
            else:
                result = subprocess.run([
                    'ffmpeg', '-i', input_path, '-vn', '-acodec', 'libmp3lame',
                    '-ac', '1', '-ar', '16000', '-b:a', '48k', output_path, '-y'
                ], capture_output=True)
                if result.returncode != 0:
                    raise Exception(f"ffmpeg failed: {result.stderr.decode()}")

            if not os.path.exists(output_path) or os.path.getsize(output_path) <= 0:
                return False

            output_size = os.path.getsize(output_path)
            logger.info(f"音频压缩完成: {output_path}, size={output_size}")
            if output_size > self.MAX_OPENAI_AUDIO_BYTES:
                logger.error(f"压缩后的音频仍超过接口限制: {output_size}")
                return False
            return True

        except Exception as e:
            logger.error(f"压缩音频时出错: {str(e)}")
            return False
    
    def process_video_subtitles(self, video_path: str, output_format: str = 'srt', language: str = 'zh') -> dict:
        result = {
            'success': False,
            'message': '',
            'subtitle_file': None,
            'subtitle_format': output_format,
            'processing_type': None,
            'r2_object_key': None,
            'download_url': None
        }
        
        try:
            subtitle_info = self.check_video_subtitles(video_path)
            
            if subtitle_info['has_embedded_subtitles']:
                logger.info("检测到内嵌字幕，开始提取...")
                base_name = os.path.splitext(os.path.basename(video_path))[0]
                
                if self.use_r2:
                    # 使用临时文件进行提取
                    with tempfile.NamedTemporaryFile(suffix='.srt', delete=False) as temp_file:
                        temp_srt = temp_file.name
                    
                    if self.extract_embedded_subtitles(video_path, temp_srt):
                        # 上传到R2
                        success, object_key = self.r2_storage.upload_file(
                            temp_srt, 
                            object_key=f"subtitles/{base_name}.srt",
                            content_type='text/plain'
                        )
                        
                        if success:
                            result['processing_type'] = 'embedded_subtitle'
                            result['success'] = True
                            result['message'] = '成功提取内嵌字幕'
                            result['subtitle_file'] = temp_srt  # 临时文件路径
                            result['r2_object_key'] = object_key
                            
                            # 生成下载URL
                            url_success, download_url = self.r2_storage.get_file_url(object_key)
                            if url_success:
                                result['download_url'] = download_url
                        else:
                            result['message'] = f'上传字幕到R2失败: {object_key}'
                    else:
                        result['message'] = '提取内嵌字幕失败'
                    
                    # 清理临时文件
                    if os.path.exists(temp_srt):
                        os.remove(temp_srt)
                else:
                    # 本地存储
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
                
                if self.use_r2:
                    # 上传外挂字幕到R2
                    base_name = os.path.splitext(os.path.basename(video_path))[0]
                    success, object_key = self.r2_storage.upload_file(
                        external_subtitle,
                        object_key=f"subtitles/{base_name}.srt",
                        content_type='text/plain'
                    )
                    
                    if success:
                        result['processing_type'] = 'external_subtitle'
                        result['success'] = True
                        result['message'] = '使用外挂字幕文件'
                        result['subtitle_file'] = external_subtitle
                        result['r2_object_key'] = object_key
                        
                        # 生成下载URL
                        url_success, download_url = self.r2_storage.get_file_url(object_key)
                        if url_success:
                            result['download_url'] = download_url
                    else:
                        result['message'] = f'上传字幕到R2失败: {object_key}'
                else:
                    result['processing_type'] = 'external_subtitle'
                    result['success'] = True
                    result['message'] = '使用外挂字幕文件'
                    result['subtitle_file'] = external_subtitle
                    
            else:
                logger.info("未检测到字幕，开始语音识别...")
                is_audio_file = self.is_supported_audio_file(video_path)
                
                if self.use_r2:
                    temp_audio = None
                    if is_audio_file:
                        if self.should_transcribe_directly(video_path):
                            audio_for_transcription = video_path
                            audio_ready = True
                            logger.info("检测到未超限音频文件，直接使用原始音频进行语音识别")
                        else:
                            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_audio_file:
                                temp_audio = temp_audio_file.name
                            audio_for_transcription = temp_audio
                            audio_ready = self.compress_audio_for_transcription(video_path, temp_audio)
                    else:
                        # 使用临时文件
                        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_audio_file:
                            temp_audio = temp_audio_file.name
                        audio_for_transcription = temp_audio
                        audio_ready = self.extract_audio_from_video(video_path, temp_audio)
                    
                    if audio_ready:
                        base_name = os.path.splitext(os.path.basename(video_path))[0]
                        
                        # 使用临时文件生成字幕
                        with tempfile.NamedTemporaryFile(suffix=f'.{output_format}', delete=False) as temp_subtitle_file:
                            final_output = temp_subtitle_file.name
                        
                        if self.generate_subtitles_with_whisper(audio_for_transcription, final_output, language):
                            # 上传到R2
                            success, object_key = self.r2_storage.upload_file(
                                final_output,
                                object_key=f"subtitles/{base_name}.{output_format}",
                                content_type='text/plain'
                            )
                            
                            if success:
                                result['processing_type'] = 'speech_recognition'
                                result['success'] = True
                                result['message'] = '成功通过语音识别生成字幕'
                                result['subtitle_file'] = final_output
                                result['r2_object_key'] = object_key
                                
                                # 生成下载URL
                                url_success, download_url = self.r2_storage.get_file_url(object_key)
                                if url_success:
                                    result['download_url'] = download_url
                            else:
                                result['message'] = f'上传字幕到R2失败: {object_key}'
                        else:
                            result['message'] = '语音识别生成字幕失败'
                        
                        # 清理临时文件
                        if temp_audio and os.path.exists(temp_audio):
                            os.remove(temp_audio)
                        if os.path.exists(final_output):
                            os.remove(final_output)
                    else:
                        result['message'] = '提取音频失败'
                else:
                    if is_audio_file:
                        if self.should_transcribe_directly(video_path):
                            temp_audio = None
                            audio_for_transcription = video_path
                            audio_ready = True
                            logger.info("检测到未超限音频文件，直接使用原始音频进行语音识别")
                        else:
                            temp_audio = os.path.join(self.output_folder, f"temp_{os.path.splitext(os.path.basename(video_path))[0]}.mp3")
                            audio_for_transcription = temp_audio
                            audio_ready = self.compress_audio_for_transcription(video_path, temp_audio)
                    else:
                        # 本地存储
                        temp_audio = os.path.join(self.output_folder, f"temp_{os.path.splitext(os.path.basename(video_path))[0]}.mp3")
                        audio_for_transcription = temp_audio
                        audio_ready = self.extract_audio_from_video(video_path, temp_audio)
                    
                    if audio_ready:
                        base_name = os.path.splitext(os.path.basename(video_path))[0]
                        final_output = os.path.join(self.output_folder, f"{base_name}.{output_format}")
                        
                        if self.generate_subtitles_with_whisper(audio_for_transcription, final_output, language):
                            result['processing_type'] = 'speech_recognition'
                            result['success'] = True
                            result['message'] = '成功通过语音识别生成字幕'
                            result['subtitle_file'] = final_output
                        else:
                            result['message'] = '语音识别生成字幕失败'
                        
                        if temp_audio and os.path.exists(temp_audio):
                            os.remove(temp_audio)
                    else:
                        result['message'] = '提取音频失败'
            
            return result
            
        except Exception as e:
            logger.error(f"处理视频字幕时出错: {str(e)}")
            result['message'] = f'处理失败: {str(e)}'
            return result 
