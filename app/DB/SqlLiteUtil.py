import sqlite3
import datetime
import os

class SqlLiteUtil:
    def __init__(self):
        # self.conn = sqlite3.connect('C:\\Users\\kzhou\OneDrive - GREEN DOT CORPORATION\\Documents\\GitRepo\\MyCode\\AIWEB\\DB\\OpenAI.db')
        # self.conn = sqlite3.connect('C:\\Users\\Kevin\Documents\\ai\\AIWEB\\DB\\OpenAI.db')
        self.conn= sqlite3.connect(os.getenv("DB_PATH"))
        # self.conn = sqlite3.connect('/root/myai/DB/OpenAI.db')
        # self.conn = sqlite3.connect('OpenAI.db')
        self.conn.row_factory = sqlite3.Row 
        self.cursor = self.conn.cursor()
        # self.cursor.execute('''CREATE TABLE IF NOT EXISTS users 
        #         (id INTEGER PRIMARY KEY, email TEXT, password INTEGER)''')
        # self.conn.commit()
    def createdb(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                (id INTEGER PRIMARY KEY, email TEXT, password INTEGER)''')
        self.conn.commit()
        self.cursor.close()
        self.conn.close()

    def insertUser(self,user, email, password,level,confirmation_token,confirmation_expires_at):
        createDateTime = datetime.datetime.now() 
        self.cursor.execute("INSERT INTO user (user,email, password,level,confirmationToken,confirmationExpiration,activate,created) VALUES (?,?, ?,?,?,?,?,?)", (user,email, password,0,confirmation_token,confirmation_expires_at,0,createDateTime))
        self.conn.commit()
        # self.cursor.close()
        # self.conn.close()
    def updateTokenForResetPassword(self,email,token):
        expirationdate = datetime.datetime.now() + datetime.timedelta(hours=24)    
        self.cursor.execute("update user set confirmationToken=? ,confirmationExpiration=? where email in (?)",(token,expirationdate,email))
        self.conn.commit()

    def insertCustomer(self,userid, balance):
        self.cursor.execute("INSERT INTO customer (userid,balance) VALUES (?,?)", (userid,balance))
        self.conn.commit()
        # self.cursor.close()
        # self.conn.close()  
    
    def insertChatHistory(self,params):
        # (userId,role,model,promptTokens,complettionTokens,totalTokens,created,GptContent,prompt,sessionid)
        self.cursor.execute("INSERT INTO chatHistory (SessionId ,UserId,Role ,Model ,PromptTokens ,CompletionTokens ,TotalTokens,Created ,GptContent , Prompt,chargeStatus ) VALUES (?, ?,?,?,?, ?,?,?,?, ?,?)", params)
        self.conn.commit()
        self.cursor.close()
        self.conn.close()
    
    def insertTtsHistory(self,params):
        # (userId,role,model,promptTokens,complettionTokens,totalTokens,created,GptContent,prompt,sessionid)
        self.cursor.execute("INSERT INTO ttsHistory (UserId ,Model ,PromptTokens ,CompletionTokens ,TotalTokens,Created,chargeStatus  ) VALUES (?, ?,?,?,?, ?,?)", params)
        self.conn.commit()
        self.cursor.close()
        self.conn.close()
    def insertTranscriptionHistory(self,params):
        # (userId,role,model,promptTokens,complettionTokens,totalTokens,created,GptContent,prompt,sessionid)
        self.cursor.execute("INSERT INTO transcriptionHistory (UserId ,Model ,Duration,Created,chargeStatus  ) VALUES (?, ?,?,?,?)", params)
        self.conn.commit()
        self.cursor.close()
        self.conn.close()

    def insertImageHistory(self,params):
        # (userId,role,model,promptTokens,complettionTokens,totalTokens,created,GptContent,prompt,sessionid)
        self.cursor.execute("INSERT INTO imageHistory (SessionId ,UserId,Created ,revisedPrompt  ,urls,model, Prompt,quality,resolution,chargeStatus ) VALUES (?, ?,?,?,?, ?,?,?,?,?)", params)
        self.conn.commit()
        self.cursor.close()
        self.conn.close()


    def query(self,query,params):
        self.cursor.execute(query,params)
        rows = self.cursor.fetchall()
        # 将查询结果转换为字典列表
        result = [dict(row) for row in rows]

        # self.cursor.close()
        # self.conn.close()
        return result
    
     
    def insertBarCode(self,params):
        # (userId,role,model,promptTokens,complettionTokens,totalTokens,created,GptContent,prompt,sessionid)
        self.cursor.execute("INSERT INTO barCode (userid,barcode ,statuskey,loadAmount ,created ) VALUES (?, ?,?,?,?)", params)
        self.conn.commit()
        self.cursor.close()
        self.conn.close()
    

    def insertFundTransaction(self,params):
        self.cursor.execute("INSERT INTO fundTransaction (userid,out_trade_no ,buyer_logon_id,trade_status ,total_amount,send_pay_date,trade_no,created ) VALUES (?, ?,?,?,?,?,?,?)", params)

    def insertEmailFailure(self,params):
        self.cursor.execute("INSERT INTO emailFailure (email,type,error ) VALUES (?, ?,?)", params)
        self.conn.commit()


    def updateBarCodeStatuskey(self,params):
        self.cursor.execute("update barCode set statuskey=3 where barcode in ({})".format(','.join('?'*len(params))) ,params)

    def updatePassword(self,email,password):
        expirationdate = datetime.datetime.now() +datetime.timedelta(hours=-1)    
        self.cursor.execute("update user set password=?, confirmationExpiration=? where email in (?)",(password,expirationdate,email))
        self.conn.commit()


    def updateCustomerBalance(self,loadAmount,userid):
        self.cursor.execute("update customer set balance=balance+{} where userid in ({})".format(loadAmount,userid))                 
        # self.conn.commit()
    
    def activateUser(self,userid):
        self.cursor.execute("update user set activate=1 where id in ({})".format(userid))                 
        self.conn.commit()

# CREATE TABLE fundTransaction(
#  Id INTEGER PRIMARY KEY AUTOINCREMENT,
#     UserId INTEGER,
#     out_trade_no TEXT,
#     buyer_logon_id  VARCHAR(100) ,
#     trade_status TVARCHAR(30),
#     total_amount REAL,
#     send_pay_date DATETIME,
#     trade_no TEXT
#     created TIMESTAMP
# );

