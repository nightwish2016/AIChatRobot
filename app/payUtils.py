from app.DB.SqlLiteUtil import SqlLiteUtil
import sqlite3
from app.currency_utils import get_currency_converter
import logging

logger = logging.getLogger('log')

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
    
    def InsertBankCardTransaction(self, transaction_data, user_email, amount_usd):
        """
        处理银行卡交易：插入交易记录并更新用户余额
        包含幂等性检查，防止重复处理
        银行卡支付是美元，需要转换为人民币存储到余额中
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
            
            # 银行卡支付金额是美元，需要转换为人民币
            converter = get_currency_converter()
            amount_cny = converter.usd_to_cny(amount_usd)
            
            logger.info(f"银行卡支付转换: {amount_usd} USD = {amount_cny} CNY")
            
            # 插入银行卡交易记录（保留原始美元金额）
            self.db.insertFundTransactionBank(transaction_data)
            
            # 更新用户余额（用转换后的人民币金额）
            self.db.updateCustomerBalance(amount_cny, userid)
            
            self.db.conn.commit()
            return {
                "success": True, 
                "user_id": userid,
                "amount_usd": amount_usd,
                "amount_cny": amount_cny,
                "exchange_rate": converter.get_exchange_rate("CNY", "USD")
            }
        except sqlite3.Error as e:
            logger.error(f'银行卡交易sqlite3错误: {e.args[0]}')
            self.db.conn.rollback()
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f'银行卡交易处理错误: {str(e)}')
            self.db.conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            # 关闭游标和连接
            self.db.cursor.close()
            self.db.conn.close()

