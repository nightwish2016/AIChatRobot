from app.DB.SqlLiteUtil import SqlLiteUtil
import redis
import json
import datetime
import logging
from app.SendMail import SendMail
logger = logging.getLogger('log')
class UserUtils:
    def __init__(self):
        self.db = SqlLiteUtil()

    
    def register(self,user, email, password,level,confirmation_token): 
        confirmation_expires_at = datetime.datetime.now() + datetime.timedelta(hours=72)     
        self.db.insertUser(user,email, password,level,confirmation_token,confirmation_expires_at)
        rows=self.userQuery(email)
        userid=rows[0]['id']
        self.db.insertCustomer(userid,0.1)        
        self.db.cursor.close()
        self.db.conn.close()  
    
    def updateTokenForResetPassword(self,email,token):
        self.db.updateTokenForResetPassword(email,token)
        self.db.cursor.close()
        self.db.conn.close()  

    def userQuery(self,email):
        query="select * from user where email=?"
        # query="select * from users "
        return self.db.query(query, (email,))  
    
    def userQueryByTokenAndEmail(self,token,email):
        query="select * from user where confirmationToken=? and email=? "
        # query="select * from users "
        return self.db.query(query,(token,email))  
     
    def activateUser(self,token,email):
        rows=self.userQueryByTokenAndEmail(token,email)
        if len(rows)==1 :
            if rows[0]["activate"]==0 and datetime.datetime.strptime(rows[0]["confirmationExpiration"],"%Y-%m-%d %H:%M:%S.%f")>datetime.datetime.now():
                userid=rows[0]["id"]
                self.db.activateUser(userid)
                email=rows[0]["email"]
                user=rows[0]["user"]
                recipients = [email]
                    
                m=SendMail()
                subject=user+",Your account already activate!"
                body=user+',your account alread activated,Please login,https://nightwish.tech/loginPage'
                result=m.sendMail(recipients,"",subject,body)
                if result==False:
                    # email send failure:
                    s=SqlLiteUtil()
                    s.insertEmailFailure((recipients[0]["email"],2,result['text']))
            elif rows[0]["activate"]==1:
                logger.info("user activated,token:"+token)
                return True
            else:
                return "activation url already expired"
        else:
            return "Page not found"
        rows=self.userQueryByTokenAndEmail(token,email)
        if rows[0]["activate"]==1:
            logger.info("user activated")
            return True
        else:
            logger.info("user activated unsuccessfully")
            return False

    
    def getBalanceByUserId(self,userid):
        query="select * from customer where userid=?"
        return self.db.query(query, (userid,))
    
    def getUserInfoByUserId(self,userid):
        query="select u.id,u.user,u.email,u.activate,u.level,c.balance from user as u join Customer  as c on c.userid=u.id where userid=?"
        return self.db.query(query, (userid,))

    def updatePassword(self,email,password):
        self.db.updatePassword(email,password)
        self.db.cursor.close()
        self.db.conn.close()

        
    def getUserInfo(self,userid):   
        redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
        result=redis_client.get(f'useid:{userid}') 
        if result==None:
            #getBalance
            u=UserUtils()
            rows=self.getUserInfoByUserId(userid)
            balance=rows[0]['balance']
            redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
            userInfo=dict()
            userInfo["user_id"]=userid
            userInfo["balance"]=balance
            userInfo["activate"]=rows[0]['activate']
            redis_client.set(f'useid:{userid}',  json.dumps(userInfo),ex=120)   
        else:   
            userInfo=json.loads(result)       
        return userInfo

# u=UserUtils()
# u.createdb()
