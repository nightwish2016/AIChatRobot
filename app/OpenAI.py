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

    def chat_with_gpt(self,prompt,model): 
        statusCode=200    
        response=""
        error=""
        message=""

        conversation_history=session["chatHistory"]
        sessionid=""
        if conversation_history==None or len(conversation_history)==0:
            conversation_history=[]
            sessionid=str(uuid.uuid4())
            session["sessionid"]=sessionid
            logger.info("create sessionid:"+sessionid)
        else:
            sessionid=session["sessionid"]
    
            
        conversation_history.append({"role": "user", "content": prompt})

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
            userId=session['user_id']  
            role=response.choices[0].message.role  
            model=response.model    
            complettionTokens=response.usage.completion_tokens
            promptTokens=response.usage.prompt_tokens
            totalTokens=response.usage.total_tokens
            created=response.created
            GptContent=message
            chargeStatus=1
            # prompt=prompt
            # params=(userId,role,model,promptTokens,complettionTokens,totalTokens,created,GptContent,prompt,sessionid)
            params= (sessionid ,userId,role ,model ,promptTokens ,complettionTokens ,totalTokens,created ,GptContent , prompt, chargeStatus)
            
            u=chatHistoryUtils()
            logger.info("db call start**********3")
            current_time = datetime.datetime.now()
            logger.info(current_time)
            u.insertChatHistory(params)
            logger.info("db call start end**********4")
            current_time2 = datetime.datetime.now()
            logger.info(current_time2)
            logger.info(message)
        except Exception as e:
            logger.error(str(e)) 
            error=e.code
            statusCode=e.status_code  
            message= e.body["message"]
                
        if(statusCode!=200):
            result={"error":error,"statusCode":statusCode,"message":message}
        else:
            result={"statusCode":statusCode,"message":message}  
    
        return result


    def chat_with_gpt_stream2(self,prompt,model,sessionDict):
        

        # 连接到本地 Redis 服务
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

        conversation_history.append({"role": "user", "content": prompt})
        enc=0
        if model!="deepseek-chat":
            enc = tiktoken.encoding_for_model(model)
        else:
            enc = tiktoken.encoding_for_model("gpt-4o")
        u=TokenNumber()
        try:
            logger.debug("open ai call start**********1")
            current_time2 = datetime.datetime.now()
            logger.debug(current_time2)    
            if model=="deepseek-chat":
                self.openai.api_key=self.ds_api_key
                self.openai.base_url=self.ds_ai_base_url
            else:
                self.openai.api_key=self.open_api_key
                self.openai.base_url=self.openai_base_url
            response = self.openai.chat.completions.create(
                model=model,
                messages=conversation_history,
                stream=True,
                # max_tokens=500
            
            ) 
            
            finalMessages="" 
            for chunk in response:
                model=chunk.model
                if chunk.choices[0].delta.content is not None:          
                    # print(chunk.choices[0].delta.content, end="")
                    text=chunk.choices[0].delta.content                    
                    finalMessages+=text
                    # logger.info(text)
                    # print(text)
                    yield text
                    # session["aa"]=123
                elif chunk.choices[0].finish_reason == "stop":
                    logger.info("stream finished**********")
                    # pass
                else:
                    logger.info("stream stop due to reach max_token**********")
                    yield "\n\n\n**Reach max token,please input continue(达到最大token,如果还需要这个问答,请输入继续**)"
                
         
                            
            logger.debug(finalMessages)
            logger.debug("open ai call end**********2")
            current_time3= datetime.datetime.now()
          
            logger.debug(current_time3)
            # logger.info(response)        
         
            current_time = datetime.datetime.now()
            timestamp = int(current_time.timestamp())                        
            userId=userid
            role="assistant"
            
            
            #print(len(res))
           
            res=enc.encode(prompt)
            complettionTokens=len(enc.encode(finalMessages))
            promptTokens=0
            if model!="deepseek-chat":
                promptTokens=u.num_tokens_from_messages(conversation_history,model) 
            else:
                promptTokens=u.num_tokens_from_messages(conversation_history,"gpt-4o") 
            
            totalTokens=complettionTokens+promptTokens
            created=timestamp
            GptContent=finalMessages          
            params= (sessionid ,userId,role ,model ,promptTokens ,complettionTokens ,totalTokens,created ,GptContent , prompt,1 )            
            u=chatHistoryUtils()
            u.insertChatHistory(params)    
            conversation_history.append({"role": "assistant", "content": finalMessages}) 
            redis_client.hset("conversation_models", conversationid, model)      
            redis_client.set(f'conversation:{conversationid}',  json.dumps(conversation_history),ex=3600)   
        except Exception as e:
            logger.error(str(e)) 
            error=e.code
            statusCode=e.status_code  
            message= e.body["message"]                    
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
            error=e.code
            statusCode=e.status_code  
            message= e.body["message"]
            
        # statusCode=e.status_code
        # result=e.message   
        if(statusCode!=200):
            result={"error":error,"statusCode":statusCode,"message":message}
        else:
            result={"url":image_url,"statusCode":statusCode,"message":message}  
    
        return result
        
        # return image_url
