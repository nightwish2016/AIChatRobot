from app.DB.SqlLiteUtil import SqlLiteUtil

class chatHistoryUtils:
    def __init__(self):
        self.db = SqlLiteUtil()

    #  userid, role, model,promptTokens ,CompletionTokens ,TotalTokens,Created,GptContent,Prompt,SessionId 
    def insertChatHistory(self ,pars   ):
        self.db.insertChatHistory(pars)

    def insertImageHistory(self ,pars   ):
        self.db.insertImageHistory(pars)

