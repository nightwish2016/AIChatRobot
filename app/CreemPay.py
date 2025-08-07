import requests
import json
import logging
from datetime import datetime
from .config import creem_config

logger = logging.getLogger('log')

class CreemPay:
    def __init__(self, api_key=None, base_url=None):
        # 如果没有传入参数，使用配置文件中的值
        self.api_key = api_key or creem_config.get_api_key()
        self.base_url = base_url or creem_config.get_base_url()
        
        if not self.api_key:
            raise ValueError("Creem API密钥未配置，请检查.env文件中的配置")
        
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # 记录当前使用的环境
        env_info = creem_config.get_environment_info()
        logger.info(f"[INFO] Creem环境配置: {env_info['environment'].upper()}")
        logger.info(f"[INFO] API基础URL: {self.base_url}")
    
    def search_products(self, amount=None):
        """搜索产品列表"""
        try:
            logger.info(f"搜索产品列表...")
            response = requests.get(
                f"{self.base_url}/products/search",
                headers=self.headers
            )
            logger.info(f"产品列表API响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                
                # 过滤出status为active且billing_type为onetime的产品
                filtered_products = []
                for product in items:
                    if (product.get("status") == "active" and 
                        product.get("billing_type") == "onetime"):
                        # 如果指定了金额，还要匹配价格
                        # Creem的价格是以分为单位，需要转换为元进行比较
                        product_price_yuan = product.get("price", 0) / 100
                        if amount is None or abs(product_price_yuan - amount) < 0.01:  # 允许0.01元的误差
                            filtered_products.append(product)
                
                logger.info(f"找到 {len(filtered_products)} 个符合条件的产品")
                return {"success": True, "products": filtered_products}
            else:
                logger.error(f"产品搜索失败: {response.text}")
                return {"success": False, "error": response.text}
        except Exception as e:
            logger.error(f"产品搜索异常: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def create_product(self, name, price, description=None):
        """创建产品"""
        try:
            # 将价格从元转换为分（Creem API期望的价格单位）
            price_in_cents = int(price * 100)
            
            product_data = {
                "name": name,
                "description": description or f"充值{price}元",
                "price": price_in_cents,  # 以分为单位
                "currency": "USD",
                "billing_type": "onetime",
                "tax_mode": "inclusive",
                "tax_category": "saas"
            }
            
            logger.info(f"创建产品请求数据: {product_data}")
            response = requests.post(
                f"{self.base_url}/products",
                headers=self.headers,
                json=product_data
            )
            logger.info(f"创建产品API响应状态码: {response.status_code}")
            logger.info(f"创建产品API响应内容: {response.text}")
            
            if response.status_code == 200:
                product = response.json()
                logger.info(f"产品创建成功: {product.get('id')}")
                return {"success": True, "product": product}
            else:
                logger.error(f"产品创建失败: {response.text}")
                return {"success": False, "error": response.text}
        except Exception as e:
            logger.error(f"产品创建异常: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def create_checkout(self, product_id, customer_email=None, success_url=None, cancel_url=None):
        """创建checkout"""
        try:
            checkout_data = {
                "product_id": product_id
            }
            
            # 添加customer信息
            if customer_email:
                checkout_data["customer"] = {
                    "email": customer_email
                }
            
            if success_url:
                checkout_data["success_url"] = success_url
            # if cancel_url:
            #     checkout_data["cancel_url"] = cancel_url
            
            logger.info(f"创建checkout请求数据: {checkout_data}")
            response = requests.post(
                f"{self.base_url}/checkouts",
                headers=self.headers,
                json=checkout_data
            )
            logger.info(f"Checkout API响应状态码: {response.status_code}")
            logger.info(f"Checkout API响应内容: {response.text}")
            
            if response.status_code == 200:
                checkout = response.json()
                logger.info(f"Checkout创建成功: {checkout.get('id')}")
                return {"success": True, "checkout": checkout}
            else:
                logger.error(f"Checkout创建失败: {response.text}")
                return {"success": False, "error": response.text}
        except Exception as e:
            logger.error(f"Checkout创建异常: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def process_bankcard_payment(self, amount, user_email, success_url=None, cancel_url=None):
        """处理银行卡支付流程"""
        try:
            # 1. 搜索是否有相同金额的产品
            search_result = self.search_products(amount)
            if not search_result["success"]:
                return search_result
            
            products = search_result["products"]
            product_id = None
            
            # 2. 如果没有找到相同金额的产品，创建一个新的
            if not products:
                logger.info(f"没有找到金额为{amount}的产品，创建新产品")
                product_name = f"充值{amount}元"
                create_result = self.create_product(product_name, amount)
                if not create_result["success"]:
                    return create_result
                product_id = create_result["product"]["id"]
            else:
                # 使用第一个找到的产品
                product_id = products[0]["id"]
                logger.info(f"找到现有产品: {product_id}")
            
            # 3. 创建checkout（传入用户邮箱）
            checkout_result = self.create_checkout(product_id, user_email, success_url, cancel_url)
            if not checkout_result["success"]:
                return checkout_result
            
            checkout = checkout_result["checkout"]
            checkout_url = checkout.get("checkout_url")  
            
            logger.info(f"银行卡支付流程完成,checkout URL: {checkout_url}")
            return {
                "success": True,
                "checkout_url": checkout_url,
                "checkout_id": checkout.get("id"),
                "product_id": product_id
            }
            
        except Exception as e:
            logger.error(f"银行卡支付流程异常: {str(e)}")
            return {"success": False, "error": str(e)} 