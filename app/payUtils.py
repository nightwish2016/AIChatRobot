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
    
    def InsertBankCardTransaction(self, transaction_data, user_email, amount):
        """
        处理银行卡交易：插入交易记录并更新用户余额
        包含幂等性检查，防止重复处理
        """
        try:
            # 获取checkout_id（transaction_data的第一个元素）
            checkout_id = transaction_data[0]
            
            # 检查交易是否已经处理过（基于checkout_id）
            if self.db.checkTransactionExists(checkout_id):
                return {"success": False, "error": "duplicate_transaction", "message": f"交易已存在: {checkout_id}"}
            
            self.db.cursor.execute("BEGIN;")
            
            # 根据邮箱获取用户ID
            user_result = self.db.getUserIdByEmail(user_email)
            if not user_result:
                raise Exception(f"用户不存在: {user_email}")
            
            userid = user_result[0]['id']
            
            # 插入银行卡交易记录
            self.db.insertFundTransactionBank(transaction_data)
            
            # 更新用户余额
            self.db.updateCustomerBalance(amount, userid)
            
            self.db.conn.commit()
            return {"success": True, "user_id": userid}
        except sqlite3.Error as e:
            print('sqlite3.Error occurred:', e.args[0])
            self.db.conn.rollback()
            return {"success": False, "error": str(e)}
        except Exception as e:
            print('Error occurred:', str(e))
            self.db.conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            # 关闭游标和连接
            self.db.cursor.close()
            self.db.conn.close()

