"""
货币转换工具模块
提供人民币和美元之间的汇率转换功能
"""

import requests
import redis
import json
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger('log')

class CurrencyConverter:
    """货币转换器"""
    
    def __init__(self):
        self.redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
        self.cache_key = "exchange_rate:CNY_USD"
        self.cache_duration = 3600  # 缓存1小时
        
    def get_exchange_rate(self, from_currency="CNY", to_currency="USD"):
        """
        获取汇率，优先从缓存获取，如果缓存不存在则从API获取
        
        Args:
            from_currency: 源货币代码，默认CNY
            to_currency: 目标货币代码，默认USD
            
        Returns:
            float: 汇率值，如果获取失败返回默认汇率0.14
        """
        try:
            # 尝试从Redis缓存获取汇率
            cached_rate = self.redis_client.get(self.cache_key)
            if cached_rate:
                rate_data = json.loads(cached_rate)
                logger.info(f"从缓存获取汇率: {rate_data['rate']}")
                return rate_data['rate']
            
            # 缓存不存在，从API获取
            rate = self._fetch_exchange_rate_from_api(from_currency, to_currency)
            
            if rate:
                # 缓存汇率
                rate_data = {
                    "rate": rate,
                    "timestamp": datetime.now().isoformat(),
                    "from": from_currency,
                    "to": to_currency
                }
                self.redis_client.set(self.cache_key, json.dumps(rate_data), ex=self.cache_duration)
                logger.info(f"从API获取汇率并缓存: {rate}")
                return rate
            else:
                # API获取失败，使用默认汇率
                default_rate = 0.14  # 1 CNY ≈ 0.14 USD
                logger.warning(f"汇率API获取失败，使用默认汇率: {default_rate}")
                return default_rate
                
        except Exception as e:
            logger.error(f"获取汇率异常: {str(e)}")
            return 0.14  # 默认汇率
    
    def _fetch_exchange_rate_from_api(self, from_currency, to_currency):
        """
        从免费API获取实时汇率
        
        Returns:
            float: 汇率值，获取失败返回None
        """
        try:
            # 使用免费的汇率API - exchangerate-api.com
            # 注意：免费版本有请求限制，生产环境建议使用付费版本
            url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                rate = data.get('rates', {}).get(to_currency)
                if rate:
                    logger.info(f"成功从API获取汇率: 1 {from_currency} = {rate} {to_currency}")
                    return float(rate)
            
            logger.warning(f"汇率API响应异常: {response.status_code}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"汇率API请求失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"解析汇率API响应失败: {str(e)}")
            return None
    
    def cny_to_usd(self, cny_amount):
        """
        将人民币转换为美元
        
        Args:
            cny_amount: 人民币金额（可以是字符串或数字）
            
        Returns:
            float: 美元金额，保留2位小数
        """
        try:
            # 确保输入是数字类型
            cny_amount = float(cny_amount)
        except (ValueError, TypeError) as e:
            logger.error(f"人民币金额格式错误: {cny_amount}, 错误: {str(e)}")
            raise ValueError(f"无效的人民币金额: {cny_amount}")
            
        rate = self.get_exchange_rate("CNY", "USD")
        usd_amount = cny_amount * rate
        return round(usd_amount, 2)
    
    def usd_to_cny(self, usd_amount):
        """
        将美元转换为人民币
        
        Args:
            usd_amount: 美元金额（可以是字符串或数字）
            
        Returns:
            float: 人民币金额，保留2位小数
        """
        try:
            # 确保输入是数字类型
            usd_amount = float(usd_amount)
        except (ValueError, TypeError) as e:
            logger.error(f"美元金额格式错误: {usd_amount}, 错误: {str(e)}")
            raise ValueError(f"无效的美元金额: {usd_amount}")
            
        rate = self.get_exchange_rate("CNY", "USD")
        cny_amount = usd_amount / rate
        return round(cny_amount, 2)
    
    def format_currency(self, amount, currency="CNY"):
        """
        格式化货币显示
        
        Args:
            amount: 金额
            currency: 货币类型 CNY/USD
            
        Returns:
            str: 格式化后的货币字符串
        """
        if currency == "CNY":
            return f"¥{amount:.2f}"
        elif currency == "USD":
            return f"${amount:.2f}"
        else:
            return f"{amount:.2f} {currency}"
    
    def get_dual_currency_display(self, cny_amount):
        """
        获取双货币显示（人民币 + 美元等值）
        
        Args:
            cny_amount: 人民币金额
            
        Returns:
            dict: 包含两种货币格式的字典
        """
        usd_amount = self.cny_to_usd(cny_amount)
        
        return {
            "cny": {
                "amount": cny_amount,
                "formatted": self.format_currency(cny_amount, "CNY")
            },
            "usd": {
                "amount": usd_amount,
                "formatted": self.format_currency(usd_amount, "USD")
            },
            "display": f"¥{cny_amount:.2f} (${usd_amount:.2f})"
        }

# 全局实例
currency_converter = CurrencyConverter()

def get_currency_converter():
    """获取货币转换器实例"""
    return currency_converter