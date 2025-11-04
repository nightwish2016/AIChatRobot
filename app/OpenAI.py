from typing import Optional
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
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

openai_bp = Blueprint('oepnai', __name__)

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
logger = logging.getLogger('log')
class OpenAI:
    def __init__(self,cipher):
        # self.logger=    current_app.logger      
        encrypted_from_env = os.getenv('API_KEY')
        # print("加密后的环境变量:", encrypted_from_env)

        # 解密环境变量
        # api_key = cipher.decrypt(encrypted_from_env).decode()
        # print("解密后的环境变量:", api_key)
        self.open_api_key=os.getenv('OPENAI_API_KEY')
        self.openai_base_url="https://api.openai.com/v1/"
       
        self.ds_api_key=os.getenv('DS_API_KEY')
        self.ds_ai_base_url="https://api.deepseek.com"


        print("OPenAIKEY:"+str(self.open_api_key))
        print("DSAPIKEY:"+str(self.ds_api_key))

        openai.api_key = self.open_api_key
        openai.base_url=self.openai_base_url
    
        self.openai=openai

    def _encoding_for_logging(self, model_name: str):
        target_model = "gpt-4o" if model_name == "deepseek-chat" else model_name
        try:
            return tiktoken.encoding_for_model(target_model)
        except KeyError:
            logger.warning("Encoding for model %s not found, falling back to o200k_base", target_model)
            return tiktoken.get_encoding("o200k_base")

    def _now_timestamp(self) -> int:
        return int(datetime.datetime.now().timestamp())

    def _store_chat_log(
        self,
        session_id: str,
        user_id: Optional[int],
        role: str,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        created: int,
        gpt_content: str,
        prompt: str,
        charge_status: int,
    ) -> None:
        if not session_id or user_id is None:
            logger.debug(
                "Skip storing chat history: session_id=%s user_id=%s role=%s",
                session_id,
                user_id,
                role,
            )
            return
        params = (
            session_id,
            user_id,
            role,
            model_name,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            created,
            gpt_content,
            prompt,
            charge_status,
        )
        try:
            chatHistoryUtils().insertChatHistory(params)
        except Exception as exc:
            logger.exception(
                "Failed to persist chat history for session=%s role=%s: %s",
                session_id,
                role,
                exc,
            )

    def _log_user_message(self, session_id: str, user_id: Optional[int], model_name: str, prompt: str) -> None:
        encoding = self._encoding_for_logging(model_name)
        prompt_tokens = len(encoding.encode(prompt))
        timestamp = self._now_timestamp()
        self._store_chat_log(
            session_id,
            user_id,
            "user",
            model_name,
            prompt_tokens,
            0,
            prompt_tokens,
            timestamp,
            prompt,
            prompt,
            0,
        )

    def chat_with_gpt(self,prompt,model): 
        statusCode=200    
        response=""
        error=""
        message=""

        conversation_history=session.get("chatHistory")
        sessionid=session.get("sessionid")
        if not conversation_history:
            conversation_history=[]
            sessionid=str(uuid.uuid4())
            session["sessionid"]=sessionid
            logger.info("create sessionid:%s", sessionid)
        elif not sessionid:
            sessionid=str(uuid.uuid4())
            session["sessionid"]=sessionid
            logger.info("regenerate sessionid:%s", sessionid)

        conversation_history.append({"role": "user", "content": prompt})
        session["chatHistory"]=conversation_history
        user_id=session.get('user_id')
        self._log_user_message(sessionid, user_id, model, prompt)

        try:
            logger.info("open ai call start**********1")
            current_time2 = datetime.datetime.now()
            logger.info(current_time2)
            response = self.openai.chat.completions.create(
                model=model,
                messages=conversation_history,
            
            )  
            logger.info("open ai call end**********2")
            current_time3= datetime.datetime.now()
          
            logger.info(current_time3)
            logger.info(response) 
            message =response.choices[0].message.content
            conversation_history.append({"role": "assistant", "content": message})

            session["chatHistory"]=conversation_history
            userId=user_id  
            role=response.choices[0].message.role  
            response_model=response.model    
            complettionTokens=response.usage.completion_tokens
            promptTokens=response.usage.prompt_tokens
            totalTokens=response.usage.total_tokens
            created=response.created
            GptContent=message
            chargeStatus=1
            
            logger.info("db call start**********3")
            current_time = datetime.datetime.now()
            logger.info(current_time)
            self._store_chat_log(
                sessionid,
                userId,
                role,
                response_model,
                promptTokens,
                complettionTokens,
                totalTokens,
                created,
                GptContent,
                prompt,
                chargeStatus,
            )
            logger.info("db call start end**********4")
            current_time2 = datetime.datetime.now()
            logger.info(current_time2)
            logger.info(message)
        except Exception as e:
            logger.error(str(e)) 
            error=getattr(e, "code", "unknown_error")
            statusCode=getattr(e, "status_code", 500)  
            if hasattr(e, "body") and isinstance(e.body, dict):
                message= e.body.get("message", "")
            else:
                message=str(e)
                
        if(statusCode!=200):
            result={"error":error,"statusCode":statusCode,"message":message}
        else:
            result={"statusCode":statusCode,"message":message}  
    
        return result


    def chat_with_gpt_stream2(self,prompt,model,sessionDict):
        

        # 连接到本地Redis 服务
        logger.debug("chat_with_gpt_stream2**********1")
        redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
        logger.debug("chat_with_gpt_stream2**********2")
        statusCode=200    
        response=""
        error=""        
        message=""     
        conversationid=sessionDict["conversationid"]   
        conversation_history=sessionDict[f'conversation:{conversationid}']
        result=""
        # conversation_history=[]
    
        sessionid=conversationid
        userid=sessionDict["user_id"]

        requested_model=model
        conversation_history.append({"role": "user", "content": prompt})
        user_encoding = self._encoding_for_logging(requested_model)
        user_prompt_tokens = len(user_encoding.encode(prompt))
        self._store_chat_log(
            sessionid,
            userid,
            "user",
            requested_model,
            user_prompt_tokens,
            0,
            user_prompt_tokens,
            self._now_timestamp(),
            prompt,
            prompt,
            0,
        )
        token_counter=TokenNumber()
        try:
            logger.debug("open ai call start**********1")
            current_time2 = datetime.datetime.now()
            logger.debug(current_time2)    
            if requested_model=="deepseek-chat":
                self.openai.api_key=self.ds_api_key
                self.openai.base_url=self.ds_ai_base_url
            else:
                self.openai.api_key=self.open_api_key
                self.openai.base_url=self.openai_base_url
            response = self.openai.chat.completions.create(
                model=requested_model,
                messages=conversation_history,
                stream=True,
                
            ) 
            
            finalMessages="" 
            response_model_name=requested_model
            for chunk in response:
                if getattr(chunk, "model", None):
                    response_model_name = chunk.model
                if chunk.choices[0].delta.content is not None:          
                    text=chunk.choices[0].delta.content                    
                    finalMessages+=text
                    yield text
                elif chunk.choices[0].finish_reason == "stop":
                    logger.info("stream finished**********")
                else:
                    logger.info("stream stop due to reach max_token**********")
                    yield "\n\n\n**Reach max token, please input 'continue' to resume.**"
                
         
                            
            logger.debug(finalMessages)
            logger.debug("open ai call end**********2")
            current_time3= datetime.datetime.now()
          
            logger.debug(current_time3)
         
            created_timestamp = self._now_timestamp()                        
            role="assistant"
           
            completion_encoding = self._encoding_for_logging(response_model_name)
            complettionTokens=len(completion_encoding.encode(finalMessages))
            if requested_model!="deepseek-chat":
                promptTokens=token_counter.num_tokens_from_messages(conversation_history,response_model_name) 
            else:
                promptTokens=token_counter.num_tokens_from_messages(conversation_history,"gpt-4o") 
            
            totalTokens=complettionTokens+promptTokens
            GptContent=finalMessages          
            self._store_chat_log(
                sessionid,
                userid,
                role,
                response_model_name,
                promptTokens,
                complettionTokens,
                totalTokens,
                created_timestamp,
                GptContent,
                prompt,
                1,
            )
            conversation_history.append({"role": "assistant", "content": finalMessages}) 
            redis_client.hset("conversation_models", conversationid, response_model_name)      
            redis_client.set(f'conversation:{conversationid}',  json.dumps(conversation_history),ex=3600)   
        except Exception as e:
            logger.error(str(e)) 
            error=getattr(e, "code", "unknown_error")
            statusCode=getattr(e, "status_code", 500)  
            if hasattr(e, "body") and isinstance(e.body, dict):
                message= e.body.get("message", "")
            else:
                message=str(e)                    
            if(statusCode!=200):
                result={"error":error,"statusCode":statusCode,"message":message}
            else:
                result={"statusCode":statusCode,"message":message}  
            yield  result['error']+":"+result['message']
    
            # return result
        


    def image_with_gpt(self,prompt,model,pixl):
        statusCode=200    
        response=""
        error=""
        message=""
        
        try:
            self.openai.api_key=self.open_api_key
            self.openai.base_url=self.openai_base_url
            response = self.openai.images.generate(
                model=model,
                prompt=prompt,
            size=pixl,                
                n=1
            )
            sessionid=str(uuid.uuid4())
            userId=session['user_id'] 
            created=response.created
            dataList=response.data
            for data in dataList:
                revised_prompt=data.revised_prompt
                url=data.url
                quality="standard"
                chargeStatus=1
                params=(sessionid,userId,created,revised_prompt,url,model,prompt,quality,pixl,chargeStatus)
                u=chatHistoryUtils()
                u.insertImageHistory(params)        
            image_url = response.data[0].url                                         
        except Exception as e:     
            logger.error(str(e))      
            error=getattr(e, "code", "unknown_error")
            statusCode=getattr(e, "status_code", 500)  
            if hasattr(e, "body") and isinstance(e.body, dict):
                message= e.body.get("message", "")
            else:
                message=str(e)
            
        # statusCode=e.status_code
        # result=e.message   
        if(statusCode!=200):
            result={"error":error,"statusCode":statusCode,"message":message}
        else:
            result={"url":image_url,"statusCode":statusCode,"message":message}  
    
        return result
        
        # return image_url
