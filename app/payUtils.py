from app.DB.SqlLiteUtil import SqlLiteUtil
import sqlite3

class payUtils:
    def __init__(self):
        self.db = SqlLiteUtil()

    
    def inseBarCode(self ,pars   ):
        self.db.insertBarCode(pars)
    
    def InsertFundTransaction(self,paramTrans,barcodekey,userid,loadAmount):
        try:
            self.db.cursor.execute("BEGIN;")
            self.db.insertFundTransaction(paramTrans)
            barcodekey=barcodekey+","
            self.db.updateBarCodeStatuskey(barcodekey.split(','))
            param=(loadAmount,userid)
            self.db.updateCustomerBalance(loadAmount,userid)
            self.db.conn.commit()
        except sqlite3.Error as e:
            print('sqlite3.Error occurred:', e.args[0])
            self.db.conn.rollback()
        finally:
            # 关闭游标和连接
            self.db.cursor.close()
            self.db.conn.close()

