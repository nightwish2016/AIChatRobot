import requests
import json
import logging
import redis
from datetime import datetime
from .config import creem_config, app_config

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
        
        # 初始化Redis缓存
        try:
            self.redis_client = redis.StrictRedis(
                host=app_config.REDIS_HOST,
                port=app_config.REDIS_PORT,
                db=app_config.REDIS_DB,
                decode_responses=True  # 自动解码返回的字符串
            )
            # 测试Redis连接
            self.redis_client.ping()
            self.cache_enabled = True
            logger.info("[INFO] Redis缓存已启用")
        except Exception as e:
            self.cache_enabled = False
            logger.warning(f"[WARNING] Redis连接失败，产品缓存功能禁用: {str(e)}")
        
        # 记录当前使用的环境
        env_info = creem_config.get_environment_info()
        logger.info(f"[INFO] Creem环境配置: {env_info['environment'].upper()}")
        logger.info(f"[INFO] API基础URL: {self.base_url}")
    
    def get_cache_key(self, amount):
        """生成缓存键"""
        env = creem_config.environment
        return f"creem:product:{env}:{amount}"
    
    def get_cached_product_id(self, amount):
        """从缓存获取产品ID"""
        if not self.cache_enabled:
            return None
        
        try:
            cache_key = self.get_cache_key(amount)
            product_id = self.redis_client.get(cache_key)
            if product_id:
                logger.info(f"[CACHE HIT] 从缓存获取产品ID: {product_id} (金额: {amount})")
                return product_id
            else:
                logger.info(f"[CACHE MISS] 缓存中未找到金额 {amount} 对应的产品ID")
                return None
        except Exception as e:
            logger.error(f"[CACHE ERROR] 获取缓存失败: {str(e)}")
            return None
    
    def cache_product_id(self, amount, product_id, expire_time=7200):
        """缓存产品ID，默认缓存2小时"""
        if not self.cache_enabled:
            return False
        
        try:
            cache_key = self.get_cache_key(amount)
            self.redis_client.setex(cache_key, expire_time, product_id)
            logger.info(f"[CACHE SET] 缓存产品ID: {product_id} (金额: {amount}, 过期时间: {expire_time}秒)")
            return True
        except Exception as e:
            logger.error(f"[CACHE ERROR] 设置缓存失败: {str(e)}")
            return False
    
    def clear_product_cache(self, amount=None):
        """清除产品缓存"""
        if not self.cache_enabled:
            return False
        
        try:
            if amount:
                # 清除特定金额的缓存
                cache_key = self.get_cache_key(amount)
                result = self.redis_client.delete(cache_key)
                logger.info(f"[CACHE CLEAR] 清除金额 {amount} 的缓存，结果: {result}")
                return result > 0
            else:
                # 清除所有产品缓存
                env = creem_config.environment
                pattern = f"creem:product:{env}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    result = self.redis_client.delete(*keys)
                    logger.info(f"[CACHE CLEAR] 清除所有产品缓存，共清除 {result} 个键")
                    return result > 0
                return True
        except Exception as e:
            logger.error(f"[CACHE ERROR] 清除缓存失败: {str(e)}")
            return False
    
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
        """处理银行卡支付流程（优化版本 - 使用缓存）"""
        try:
            start_time = datetime.now()
            logger.info(f"[PAYMENT START] 开始处理银行卡支付，金额: {amount}")
            
            # 1. 首先尝试从缓存获取产品ID
            product_id = self.get_cached_product_id(amount)
            
            if product_id:
                # 缓存命中，直接使用缓存的产品ID
                logger.info(f"[CACHE OPTIMIZATION] 使用缓存产品ID，跳过API搜索: {product_id}")
            else:
                # 缓存未命中，需要搜索或创建产品
                logger.info(f"[CACHE MISS] 缓存未命中，开始搜索/创建产品")
                
                # 2. 搜索是否有相同金额的产品
                search_result = self.search_products(amount)
                if not search_result["success"]:
                    return search_result
                
                products = search_result["products"]
                
                # 3. 如果没有找到相同金额的产品，创建一个新的
                if not products:
                    logger.info(f"没有找到金额为{amount}的产品，创建新产品")
                    product_name = f"充值{amount}元"
                    create_result = self.create_product(product_name, amount)
                    if not create_result["success"]:
                        return create_result
                    product_id = create_result["product"]["id"]
                    logger.info(f"新产品创建成功: {product_id}")
                else:
                    # 使用第一个找到的产品
                    product_id = products[0]["id"]
                    logger.info(f"找到现有产品: {product_id}")
                
                # 4. 将产品ID缓存起来
                self.cache_product_id(amount, product_id)
            
            # 5. 创建checkout（传入用户邮箱）
            checkout_result = self.create_checkout(product_id, user_email, success_url, cancel_url)
            if not checkout_result["success"]:
                return checkout_result
            
            checkout = checkout_result["checkout"]
            checkout_url = checkout.get("checkout_url")
            
            # 记录总执行时间
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"[PAYMENT COMPLETE] 银行卡支付流程完成，总耗时: {duration:.2f}秒")
            logger.info(f"[PAYMENT COMPLETE] Checkout URL: {checkout_url}")
            
            return {
                "success": True,
                "checkout_url": checkout_url,
                "checkout_id": checkout.get("id"),
                "product_id": product_id,
                "cache_hit": self.get_cached_product_id(amount) is not None,
                "duration": duration
            }
            
        except Exception as e:
            logger.error(f"银行卡支付流程异常: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def preload_common_products(self, amounts=None):
        """预加载常用金额的产品到缓存"""
        if amounts is None:
            amounts = [10, 20, 50, 100, 200, 500]  # 默认常用金额
        
        logger.info(f"[PRELOAD] 开始预加载产品，金额列表: {amounts}")
        results = {}
        
        for amount in amounts:
            try:
                # 检查缓存是否已存在
                cached_id = self.get_cached_product_id(amount)
                if cached_id:
                    logger.info(f"[PRELOAD] 金额 {amount} 已在缓存中: {cached_id}")
                    results[amount] = {"status": "cached", "product_id": cached_id}
                    continue
                
                # 搜索现有产品
                search_result = self.search_products(amount)
                if search_result["success"] and search_result["products"]:
                    product_id = search_result["products"][0]["id"]
                    self.cache_product_id(amount, product_id)
                    logger.info(f"[PRELOAD] 找到并缓存现有产品，金额: {amount}, ID: {product_id}")
                    results[amount] = {"status": "found_and_cached", "product_id": product_id}
                else:
                    # 创建新产品
                    product_name = f"充值{amount}元"
                    create_result = self.create_product(product_name, amount)
                    if create_result["success"]:
                        product_id = create_result["product"]["id"]
                        self.cache_product_id(amount, product_id)
                        logger.info(f"[PRELOAD] 创建并缓存新产品，金额: {amount}, ID: {product_id}")
                        results[amount] = {"status": "created_and_cached", "product_id": product_id}
                    else:
                        logger.error(f"[PRELOAD] 创建产品失败，金额: {amount}, 错误: {create_result.get('error')}")
                        results[amount] = {"status": "failed", "error": create_result.get("error")}
                        
            except Exception as e:
                logger.error(f"[PRELOAD] 处理金额 {amount} 时发生异常: {str(e)}")
                results[amount] = {"status": "error", "error": str(e)}
        
        logger.info(f"[PRELOAD] 预加载完成，结果: {results}")
        return results
    
    def get_cache_stats(self):
        """获取缓存统计信息"""
        if not self.cache_enabled:
            return {"cache_enabled": False, "message": "缓存未启用"}
        
        try:
            env = creem_config.environment
            pattern = f"creem:product:{env}:*"
            keys = self.redis_client.keys(pattern)
            
            cache_info = {"cache_enabled": True, "total_cached": len(keys), "cached_amounts": []}
            
            for key in keys:
                # 从键中提取金额
                amount = key.split(":")[-1]
                product_id = self.redis_client.get(key)
                ttl = self.redis_client.ttl(key)
                cache_info["cached_amounts"].append({
                    "amount": amount,
                    "product_id": product_id,
                    "ttl": ttl
                })
            
            return cache_info
            
        except Exception as e:
            logger.error(f"[CACHE STATS] 获取缓存统计失败: {str(e)}")
            return {"cache_enabled": True, "error": str(e)} 