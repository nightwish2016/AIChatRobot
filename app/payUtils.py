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
    
    def InsertFundTransaction(self,paramTrans,barcodekey,userid,loadAmount_cny):
        """
        处理支付宝交易：插入交易记录并更新用户余额
        支付宝支付是人民币，需要转换为美元存储到余额中
        """
        try:
            self.db.cursor.execute("BEGIN;")
            
            # 支付宝支付金额是人民币，需要转换为美元存储
            converter = get_currency_converter()
            loadAmount_usd = converter.cny_to_usd(loadAmount_cny)
            
            logger.info(f"支付宝支付转换: {loadAmount_cny} CNY = {loadAmount_usd} USD")
            
            self.db.insertFundTransaction(paramTrans)
            barcodekey=barcodekey+","
            self.db.updateBarCodeStatuskey(barcodekey.split(','))
            
            # 更新用户余额（用转换后的美元金额）
            self.db.updateCustomerBalance(loadAmount_usd,userid)
            self.db.conn.commit()
            
            return {
                "success": True,
                "amount_cny": loadAmount_cny,
                "amount_usd": loadAmount_usd,
                "exchange_rate": converter.get_exchange_rate("CNY", "USD")
            }
            
        except sqlite3.Error as e:
            logger.error(f'支付宝交易sqlite3错误: {e.args[0]}')
            self.db.conn.rollback()
            raise e
        except Exception as e:
            logger.error(f'支付宝交易处理错误: {str(e)}')
            self.db.conn.rollback()
            raise e
        finally:
            # 关闭游标和连接
            self.db.cursor.close()
            self.db.conn.close()
    
    def InsertBankCardTransaction(self, transaction_data, user_email, amount_usd):
        """
        处理银行卡交易：插入交易记录并更新用户余额
        包含幂等性检查，防止重复处理
        银行卡支付是美元，直接存储到余额中
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
            
            logger.info(f"银行卡支付: {amount_usd} USD 直接存储到余额")
            
            # 插入银行卡交易记录
            self.db.insertFundTransactionBank(transaction_data)
            
            # 更新用户余额（直接使用美元金额）
            self.db.updateCustomerBalance(amount_usd, userid)
            
            self.db.conn.commit()
            return {
                "success": True, 
                "user_id": userid,
                "amount_usd": amount_usd
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

