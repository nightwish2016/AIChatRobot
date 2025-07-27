from app.chatHistoryUtils import chatHistoryUtils
from flask import Flask, request,session,jsonify
import uuid
import logging 
import openai
import os
import datetime
import tiktoken
from app.utils import TokenNumber 
import redis
import json
from flask import  current_app
from flask import Blueprint

from google import genai
from google.genai import types
import io
import os
import wave # Import wave module
import time


genminiai_bp = Blueprint('geminiai', __name__)

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
logger = logging.getLogger('log')
class GeminiAPI:
    def __init__(self):
        # 配置Google API密钥
        google_api_key = os.getenv('GOOGLE_API_KEY')
        if google_api_key:
            genai.configure(api_key=google_api_key)
        else:
            logger.warning("未设置GOOGLE_API_KEY环境变量")


    def generateVoice(self,text,voice_name):
        client = genai.Client()
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=text,
            config=types.GenerateContentConfig(
                # Removed response_modality="AUDIO" as it might be redundant/forbidden for this specific model
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name, # Use the selected voice name
                        )
                    )
                ),
            )
        )
        
        print(response.usage_metadata.prompt_token_count)
        print(response.usage_metadata.candidates_token_count)
        print(response.usage_metadata.total_token_count)
       
        userId=session['user_id']         
        model=response.model_version    
        complettionTokens=response.usage_metadata.candidates_token_count
        promptTokens=response.usage_metadata.prompt_token_count
        totalTokens=response.usage_metadata.total_token_count
      
        current_timestamp = time.time()
        created=current_timestamp    
        chargeStatus=1
        # prompt=prompt
        # params=(userId,role,model,promptTokens,complettionTokens,totalTokens,created,GptContent,prompt,sessionid)
        params= ( userId,model ,promptTokens ,complettionTokens ,totalTokens,created,chargeStatus )
        
        u=chatHistoryUtils()
        u.insertTtsHistory(params)
        return response

