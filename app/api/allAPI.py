from flask import Blueprint, render_template,session,request,jsonify,current_app,make_response,Response
# from flask import Flask, request,session
import logging 
# from app import logger
# from userAPI import check_login
import json
from app.api.userAPI import check_login
from app import limiter 
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import uuid
import redis
import json
import logging
from ..UserUtils import UserUtils
from app.utils import TokenNumber 


from flask import Flask, render_template, request, send_file
from google import genai
from google.genai import types
import io
import os
import wave # Import wave module
import tiktoken


allAPI_bp = Blueprint('allapi', __name__)

logger = logging.getLogger('log')
# 用户ID作为限流键的函数
def user_id_key_func():
    return session.get('user_id', None)

def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    """
    Saves raw PCM data to a WAV file.
    This is primarily for debugging the raw audio data from Gemini.
    """
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)

# 用户level作为限流键的函数
def user_level_key_func():
    # return session.get('user_level', None)
    level = session.get('user_level')
    if level == 0:
        return "special_level_0"
    elif level == 1:
        return "special_level_1"
    else:
        return get_remote_address()  # 或其他默认键

# IP地址作为限流键的函数
def ip_key_func():
    return get_remote_address()



@allAPI_bp.errorhandler(429)
def ratelimit_handler(e):
    # return jsonify(error="Too many request,Please try later"), 429
    error="Too many request,Please retry later"
    result = {           
            "error": "Too Many Requests",
            "statusCode":429,
            "message": error
        }
    response = make_response(jsonify(result), 429)   
    return response



@allAPI_bp.route('/api/v1/chat', methods=['POST'])
# @jwt_required()
@limiter.limit("30 per minute,100 per hour,500 per day", key_func=user_id_key_func)
@limiter.limit("30 per minute,100 per hour,500 per day", key_func=ip_key_func)
def chat():
    # 获取 JSON 请求体中的数据
    data = request.json

    # 这里可以添加处理数据的逻辑
    # 例如，我们仅仅返回接收到的数据
   

    data = request.json
    prompt = data['prompt']    
    model = data['model']

    
 
    # response = openai.chat.completions.create(
    #     model=model,
    #     messages=[{"role": "system", "content": "You are a helpful assistant."},
    #                       {"role": "user", "content": prompt}]
    # )
    loginResult=check_login()
    resLogin=json.loads(loginResult.get_data(as_text=True))["logged_in"]
    if resLogin==True:
        response=current_app.openai.chat_with_gpt(prompt,model)       
        return jsonify(response),response['statusCode']      
    else:
        return jsonify({"error": "Unauthorized", "message": "please login"}), 401
    



@allAPI_bp.route('/api/v1/image', methods=['POST'])
@limiter.limit("2 per minute,3 per hour,4 per day", key_func=lambda: "special_level_0" if session.get('user_level') == 0 else get_remote_address())
@limiter.limit("5 per minute,10 per hour,20 per day", key_func=user_id_key_func)
@limiter.limit("5 per minute,10 per hour,20 per day", key_func=ip_key_func)
def imageGeneration():   
    data = request.json
    prompt = data['prompt']    
    model = data['model']
    pixl=data['pixl']

    loginResult=check_login()
    resLogin=json.loads(loginResult.get_data(as_text=True))["logged_in"]
    logger.info(resLogin)
    if resLogin==True:
        u=UserUtils()
        userInfo=u.getUserInfo(session['user_id'])
        activate=userInfo['activate']
        balance = round(userInfo['balance'],2)    
        if balance<=0 :
            return jsonify({"error": "Payment Required", "message": "your balance:"+str(balance)+",Please fund for your account with https://nightwish.tech/orderPreCreate or  contact with admin kzhou2017@outlook.com"}), 402
        if activate==0:
            return jsonify({"error": "Account Activation Required", "message": "your account is not activated,Please activate your account with email link"}), 402
        # imageUrl="https://lh3.googleusercontent.com/a/ACg8ocLyYBQLGnbfPm-6UdUVF_D4Avc_rzmzInouMfHteVAUvFhWLg=s96-c"
        response=current_app.openai.image_with_gpt(prompt,model,pixl)
        
        # 这里可以添加处理数据的逻辑
        # 例如，我们仅仅返回接收到的数据
        # response = {
         
        #     "data": imageUrl
        # }
        return jsonify(response),response['statusCode']
    else:
        return jsonify({"error": "Unauthorized", "message": "please login"}), 401



@allAPI_bp.route('/chatStream', methods=['POST'])
@limiter.limit("10 per minute,30 per hour,100 per day", key_func=lambda: "special_level_0" if session.get('user_level') == 0 else get_remote_address())
@limiter.limit("30 per minute,100 per hour,500 per day", key_func=user_id_key_func)
@limiter.limit("30 per minute,100 per hour,500 per day", key_func=ip_key_func)
# @allAPI_bp.route('/chatStream')
def generate():   
    data = request.json
    prompt = data['prompt']    
    model = data['model']
    conversationid=data['conversationid']
    # prompt = 'hi' 
    # prompt = 'sqlite如何使用事务' 
    # model = "gpt-4-turbo-2024-04-09" 
    statusCode=200    
    response=""
    error=""
    message=""
    logger.debug("redis**********1")
    redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
    logger.debug("redis**********2")
    loginResult=check_login()
    resLogin=json.loads(loginResult.get_data(as_text=True))["logged_in"]    
    
    if resLogin==True:   
        u=UserUtils()
        userInfo=u.getUserInfo(session['user_id'])
        activate=userInfo['activate']
        balance = round(userInfo['balance'],2)    
        if balance<=0 :
            return jsonify({"error": "Payment Required", "message": "your balance:"+str(balance)+",Please fund for your account with https://nightwish.tech/orderPreCreate or  contact with admin kzhou2017@outlook.com"}), 402
        if activate==0:
            return jsonify({"error": "Account Activation Required", "message": "your account is not activated,Please activate your account with email link"}), 402
        sessionDict=dict()
        sessionDict["user_id"]=session['user_id']

        # sessionid=session["sessionid"]

        newSession=False
        logger.debug("redis**********3")
        str_conversation_history=redis_client.get(f'conversation:{conversationid}') 
        logger.debug("redis**********4")
        logger.debug(str_conversation_history)
        if str_conversation_history==None:
            newSession=True
        if newSession: #new session          
            sessionDict["conversationid"]=conversationid
            sessionDict[f'conversation:{conversationid}']=[]           
        else:                       
            conversation_history=json.loads(str_conversation_history)
            sessionDict["conversationid"]=conversationid
            sessionDict[f'conversation:{conversationid}']=conversation_history
        
       
       
        # sessionid=""
        # if conversation_history==None or len(conversation_history)==0:
        #     conversation_history=[]
        #     sessionid=str(uuid.uuid4())
        #     session["sessionid"]=sessionid
        #     logger.info("create sessionid:"+sessionid)
        # else:
        #     sessionid=session["sessionid"]
        # sessionDict["sessionid"]=sessionid
        # sessionDict["conversation_history"]=conversation_history


        results= make_response(current_app.openai.chat_with_gpt_stream2(prompt,model,sessionDict))
        return results   
    else:
        return jsonify({"error": "Unauthorized", "message": "please login"}), 401
    

@allAPI_bp.route('/generate_audio', methods=['POST'])
def generate_audio():
    """
    Generates audio from user-provided text.
    Returns the audio as a byte stream for browser playback or download.
    """
    text = request.form.get('text', '')
    voice_name = request.form.get('voice', 'Kore') # Get selected voice, default to 'Kore'
    
    if not text:
        return "请输入文本！", 400
    
    loginResult=check_login()
    resLogin=json.loads(loginResult.get_data(as_text=True))["logged_in"]
    logger.info(resLogin)
    if resLogin==True:
        u=UserUtils()
        userInfo=u.getUserInfo(session['user_id'])
        activate=userInfo['activate']
        balance = round(userInfo['balance'],2) 
        # u=TokenNumber() 
        # promptTokens=u.num_tokens_from_messages(text,"gpt-4o")   
       
        enc = tiktoken.encoding_for_model("gpt-4o")
        promptTokens=len(enc.encode(text))
        if balance<=0 :
            return jsonify({"error": "Payment Required", "message": "your balance:"+str(balance)+",Please fund for your account with https://nightwish.tech/orderPreCreate or  contact with admin kzhou2017@outlook.com"}), 402
        if activate==0:
            return jsonify({"error": "Account Activation Required", "message": "your account is not activated,Please activate your account with email link"}), 402
        if balance<=1 and promptTokens>20 :
            return jsonify({"error": "Payment Required", "message": "余额小于1,只支持20个字符转换,请减少输入字符尝试"}), 402
        try:

            response=current_app.genminiai.generateVoice(text,voice_name)
            
            # 添加调试信息
            logger.info(f"API响应类型: {type(response)}")
            logger.info(f"API响应属性: {dir(response)}")
            
            print(response.usage_metadata.prompt_token_count)
            print(response.usage_metadata.candidates_token_count)
            print(response.usage_metadata.total_token_count)

            # 尝试安全地访问音频数据
            try:
                audio_data_pcm = response.candidates[0].content.parts[0].inline_data.data
                logger.info(f"音频数据长度: {len(audio_data_pcm)}")
            except (AttributeError, IndexError, TypeError) as e:
                logger.error(f"无法访问音频数据: {e}")
                logger.error(f"响应结构: {response}")
                return "生成音频失败：API响应格式不正确，请稍后重试", 500

            # --- Debugging code: Save to disk for local verification ---
            # debug_dir = 'audio_debug'
            # if not os.path.exists(debug_dir):
            #     os.makedirs(debug_dir)
            # debug_file_path = os.path.join(debug_dir, 'temp_output.wav')      
            
            # (debug_file_path, audio_data_pcm) # Use the wave_file function to create a playable WAV
            # print(f"调试：音频文件已保存到 {debug_file_path}")
            # --- End of debugging code ---

            # Create an in-memory byte stream for the WAV file
            # We need to wrap the raw PCM data with a WAV header for browser compatibility.
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wf:
                wf.setnchannels(1)        # Assuming mono channel
                wf.setsampwidth(2)        # Assuming 16-bit samples (2 bytes)
                wf.setframerate(24000)    # Assuming 24000 Hz sample rate
                wf.writeframes(audio_data_pcm)
            
            # Reset buffer position to the beginning before sending
            wav_buffer.seek(0) 

            # Send the complete WAV file from the in-memory buffer
            return send_file(
                wav_buffer,
                mimetype='audio/wav',
                as_attachment=False,  # Not as an attachment, play directly in browser
                download_name='output.wav' # Provide a default download filename
            )

        except Exception as e:
            logger.error(f"生成音频时发生错误: {str(e)}")
            return f"生成音频时发生错误: {e}", 500
    else:
        return jsonify({"error": "Unauthorized", "message": "please login"}), 401