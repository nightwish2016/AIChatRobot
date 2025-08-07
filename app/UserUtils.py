from app.DB.SqlLiteUtil import SqlLiteUtil
import redis
import json
import datetime
import logging
from app.SendMail import SendMail
from app.currency_utils import get_currency_converter
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
    
    def getUserInfoWithCurrency(self, userid, currency_preference="CNY"):
        """
        获取用户信息，包含货币转换后的余额显示
        
        Args:
            userid: 用户ID
            currency_preference: 首选货币 CNY/USD，默认CNY
            
        Returns:
            dict: 包含用户信息和货币显示的字典
        """
        userInfo = self.getUserInfo(userid)
        
        # 添加货币转换功能
        converter = get_currency_converter()
        balance_usd = userInfo["balance"]  # 数据库中存储的是美元
        
        # 将美元余额转换为人民币
        balance_cny = converter.usd_to_cny(balance_usd)
        
        # 准备双货币信息
        currency_info = {
            "cny": {
                "amount": balance_cny,
                "formatted": converter.format_currency(balance_cny, "CNY")
            },
            "usd": {
                "amount": balance_usd,
                "formatted": converter.format_currency(balance_usd, "USD")
            },
            "display": f"¥{balance_cny:.2f} (${balance_usd:.2f})"
        }
        
        # 根据首选货币设置主要显示
        if currency_preference == "USD":
            userInfo["balance_display"] = currency_info["usd"]["formatted"]
            userInfo["balance_secondary"] = currency_info["cny"]["formatted"]
            userInfo["balance_amount"] = currency_info["usd"]["amount"]
        else:
            userInfo["balance_display"] = currency_info["cny"]["formatted"]
            userInfo["balance_secondary"] = currency_info["usd"]["formatted"]
            userInfo["balance_amount"] = currency_info["cny"]["amount"]
        
        # 添加完整的货币信息
        userInfo["currency_info"] = currency_info
        userInfo["currency_preference"] = currency_preference
        
        return userInfo

# u=UserUtils()
# u.createdb()
