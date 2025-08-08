from flask import Blueprint, render_template,session,request,make_response,jsonify,Response,current_app,url_for,redirect,abort
from app.alifacepay import AliFacePay
from threading import Lock
import qrcode
from PIL import Image
import time
from app.payUtils import payUtils
import datetime
import os

import redis
import json
import logging 
from ..UserUtils import UserUtils
from dataclasses import dataclass, asdict
orderCreationview_bp = Blueprint('orderCreation', __name__)


logger = logging.getLogger('log')
@orderCreationview_bp.route('/orderPreCreate')
def orderPreCreate():     
    user_email=session['user_email']  
    u=UserUtils()
    # 获取用户的货币偏好，默认显示人民币，但同时提供美元等值
    currency_preference = request.args.get('currency', 'CNY')
    userInfo = u.getUserInfoWithCurrency(session['user_id'], currency_preference)
    
    return render_template('orderPreCreate.html',
                          user_email=user_email,
                          balance=round(userInfo['balance'],2),
                          balance_display=userInfo['balance_display'],
                          balance_secondary=userInfo['balance_secondary'],
                          currency_info=userInfo['currency_info'],
                          currency_preference=currency_preference)

@orderCreationview_bp.route('/payment_method')
def payment_method():
    user_email = request.args.get('user_email')
    
    # 如果没有提供用户邮箱，从session获取
    if not user_email:
        user_email = session.get('user_email', '')
    
    return render_template('payment_method.html', 
                         user_email=user_email)

@orderCreationview_bp.route('/amount_input')
def amount_input():
    user_email = request.args.get('user_email')
    payment_method = request.args.get('payment_method')
    
    # 如果没有提供用户邮箱，从session获取
    if not user_email:
        user_email = session.get('user_email', '')
    
    # 验证支付方式
    if payment_method not in ['alipay', 'bankcard']:
        return redirect('/payment_method')
    
    return render_template('amount_input.html', 
                         user_email=user_email,
                         payment_method=payment_method)

@orderCreationview_bp.route('/bankcard_payment')
def bankcard_payment():
    """银行卡支付页面"""
    amount = request.args.get('amount', '10')
    error = request.args.get('error', '')
    
    return render_template('bankcard_payment.html', 
                         amount=amount, 
                         error=error)




'''
{
    "code": "10000",
    "msg": "Success",
    "buyer_logon_id": "137******65",
    "buyer_pay_amount": "1.00",
    "buyer_user_id": "2088802495048314",
    "fund_bill_list": [
        {
            "amount": "1.00",
            "fund_channel": "ALIPAYACCOUNT"
        }
    ],
    "invoice_amount": "1.00",
    "out_trade_no": "yqhs_202405261802204375809916",
    "point_amount": "0.00",
    "receipt_amount": "1.00",
    "send_pay_date": "2024-05-26 18:02:35",
    "total_amount": "1.00",
    "trade_no": "2024052622001448311433423981",
    "trade_status": "TRADE_SUCCESS"
}
'''
@orderCreationview_bp.route('/query_order', methods=['GET'])
def query_order():        
    out_trade_no = request.args.get('out_trade_no')
    ali_face_pay=current_app.ali_face_pay
    result = ali_face_pay.query(out_trade_no)
    response = make_response(jsonify(result), 200)
    return response
    # 为订单加锁

    # return render_template('template.html', qr_image_path=qr_image_path)
   

@orderCreationview_bp.route("/payment_success")
def payment_success():
    order_id = request.args.get("order_id", "")
    return render_template("payment_success.html", order_id=order_id)

@orderCreationview_bp.route('/create_trade')
def  create_trade():  
    # email=request.args.get('user_email')
    amount=request.args.get('amount')
    otherAmount=request.args.get('otherAmount')
    payment_method=request.args.get('payment_method', 'alipay')
    
    if otherAmount and otherAmount != "" and otherAmount != "None":
        amount=otherAmount
    
    amount=float(amount)
    
    # 根据支付方式选择不同的处理逻辑
    if payment_method == 'bankcard':
        # 银行卡支付逻辑
        return handle_bankcard_payment(amount)
    else:
        # 支付宝支付逻辑（原有逻辑）
        return handle_alipay_payment(amount)

def handle_bankcard_payment(amount):
    """处理银行卡支付"""
    try:
        # 获取用户邮箱
        user_email = session.get('user_email', '')
        
        # 设置成功和取消URL（必须是完整的外链地址）
        from ..config import app_config
        base_url = app_config.BASE_URL.rstrip('/')
        success_url = f"{base_url}/payment_success"
        cancel_url = f"{base_url}/payment_method"
        
        # 调用Creem支付服务
        creem_pay = current_app.creem_pay
        result = creem_pay.process_bankcard_payment(
            amount=amount,
            user_email=user_email,
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        if result["success"]:
            checkout_url = result["checkout_url"]
            checkout_id = result["checkout_id"]
            product_id = result["product_id"]
            cache_hit = result.get("cache_hit", False)
            duration = result.get("duration", 0)
            
            # 记录性能信息
            cache_status = "缓存命中" if cache_hit else "缓存未命中"
            logger.info(f"银行卡支付性能统计 - {cache_status}, 耗时: {duration:.2f}秒, 产品ID: {product_id}")
            
            # 记录支付信息到数据库
           # u = payUtils()
            current_time = datetime.datetime.now()
            timestamp = int(current_time.timestamp())
            userId = session['user_id']
            
            # 使用checkout_id作为订单号
            out_trade_no = f"creem_{checkout_id}"
          #  param = (userId, out_trade_no, 1, amount, timestamp)
            # u.inseBarCode(param)
            
            logger.info(f"银行卡支付创建成功，跳转到: {checkout_url}")
            return redirect(checkout_url)
        else:
            logger.error(f"银行卡支付创建失败: {result.get('error')}")
            return render_template('bankcard_payment.html', 
                                amount=amount, 
                                error=result.get('error', '支付创建失败'))
    
    except Exception as e:
        logger.error(f"银行卡支付异常: {str(e)}")
        return render_template('bankcard_payment.html', 
                            amount=amount, 
                            error=f"支付处理异常: {str(e)}")

def handle_alipay_payment(amount):
    """处理支付宝支付"""
    out_trade_no = AliFacePay.gen_trade_no('yqhs')
    ali_face_pay = current_app.ali_face_pay
    qr_code = ali_face_pay.precreate(out_trade_no, amount, "AIChat")

    # add barcode data to barcode table
    # 支付宝支付金额是人民币，需要转换为美元存储
    from app.currency_utils import get_currency_converter
    converter = get_currency_converter()
    amount_usd = converter.cny_to_usd(amount)
    
    logger.info(f"支付宝二维码生成 - 用户支付: ¥{amount}, 存储金额: ${amount_usd}")
    
    u = payUtils()
    current_time = datetime.datetime.now()
    timestamp = int(current_time.timestamp())
    userId = session['user_id']  
    # 存储转换后的美元金额到barCode表
    param = (userId, out_trade_no, 1, amount_usd, timestamp)
    u.inseBarCode(param)

    qr_generate(qr_code, out_trade_no)
    qr_image_path = url_for('static', filename=f'QR/{out_trade_no}.png')
    return render_template('show_qrcode.html', 
                         qrcode_url=qr_code, 
                         out_trade_no=out_trade_no,
                         qr_image_path=qr_image_path)



@orderCreationview_bp.route('/alipay_nofity', methods=['POST'])
def alipay_nofity():
    data = request.form.to_dict()
    logger.info("=== 支付宝回调开始 ===")
    logger.info(f"收到支付宝回调数据: {data}")
    
    # 记录关键信息
    out_trade_no = data.get('out_trade_no', 'UNKNOWN')
    trade_status = data.get('trade_status', 'UNKNOWN')
    total_amount = data.get('total_amount', 'UNKNOWN')
    logger.info(f"订单号: {out_trade_no}, 状态: {trade_status}, 金额: {total_amount}")
    ali_face_pay=current_app.ali_face_pay
    result={}
    if ali_face_pay.verify_params_sign(data):
        # 通知参数说明 https://docs.open.alipay.com/194/103296#s5
        result['notify_time'] = data['notify_time']           # 通知发出的时间
        result['notify_type'] = data['notify_type']           # 通知类型
        result['trade_status'] = data['trade_status']         # 订单状态
        result['out_trade_no']= data['out_trade_no']         # 订单号
        result['buyer_logon_id'] = data['buyer_logon_id']     # 买家支付宝账号
        result['total_amount'] = data['total_amount']         # 订单金额
        result['subject'] = data['subject']                   # 订单标题
        result['gmt_payment']=data['gmt_payment']
        result['trade_no']=data['trade_no']
        out_trade_no= result['out_trade_no']

        # 异步通知默认只会收到TRADE_SUCCESS或者TRADE_FINISHED
        # 沙盒下测试居然收到了WAIT_BUYER_PAY，不过实际环境收不到
        if result['notify_type']  == 'trade_status_sync':
            logger.info(result['trade_status'])
            pay_success = False
            trade_status=result['trade_status']
            if trade_status == 'TRADE_SUCCESS' or trade_status == 'TRADE_FINISHED':
                pay_success = True
            if pay_success:
                # 支付成功解锁
                # locks[out_trade_no].release()
                trans={}
                trans["out_trade_no"]= result['out_trade_no']
                trans["pay_success"]=True
                trans["detail"]= json.dumps(result)
                redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
                redis_client.set(f'fundTrans:{out_trade_no}',  json.dumps(trans),ex=600)
                
                logger.info(f"支付成功！已保存到Redis: fundTrans:{out_trade_no}")
                logger.info(f"保存的数据: {json.dumps(trans)}")
                
                result={"Message": "Notification send successfully",}
                statusCode= 200
             
            #   result=redis_client.get(f'useid:{userid}')        
    else:        
        logger.info('验证签名失败')
        result={"error": "Not FOUND",}
        statusCode= 404
    response = make_response(jsonify(result), statusCode)
    return response

@orderCreationview_bp.route('/wait_pay/<out_trade_no>', methods=['GET'])
def wait_pay(out_trade_no):
    logger.info(f"等待支付轮询 - 订单号: {out_trade_no}")
    
    redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
    result_fundtrans = redis_client.get(f'fundTrans:{out_trade_no}')
    
    logger.info(f"Redis查询结果: {result_fundtrans}")
    
    payment_status = False
    if result_fundtrans != None:
        result = json.loads(result_fundtrans)
        payment_status = result['pay_success']
        details = json.loads(result['detail'])
        logger.info(f"支付状态: {payment_status}, 详情: {details}")
    else:
        logger.info(f"Redis中未找到订单 {out_trade_no} 的支付信息")
    
    if payment_status:
                
            # update barcode,add fundTrans
                u=payUtils()               
                current_time=datetime.datetime.now()
                timestamp=int(current_time.timestamp())
                userId=session['user_id'] 
                # userId=3
                send_pay_date=details['gmt_payment']
                buyer_logon_id=details['buyer_logon_id']
                trade_status=details['trade_status']
                total_amount=details['total_amount']
                trade_no=details['trade_no']
                buyer_logon_id=details['buyer_logon_id']
                paramTrans=(userId,out_trade_no,buyer_logon_id,trade_status,total_amount,send_pay_date,trade_no,timestamp)
                u.InsertFundTransaction(paramTrans,out_trade_no,userId,total_amount)  

                redis_client.delete(f'useid:{userId}')  
              
  
    logger.info(f"返回支付状态: {payment_status}")
    return jsonify({
        'pay_success': payment_status  # 假设status可以是 "success", "pending", "failed"
    })



@orderCreationview_bp.route('/pay_success')
def pay_success():
    return render_template('pay_success.html')



@orderCreationview_bp.route('/creem_webhook', methods=['POST'])
def creem_webhook():
    """处理Creem支付回调"""
    try:
        import hmac
        import hashlib
        
        # 获取webhook密钥
        from ..config import creem_config
        webhook_secret = creem_config.get_webhook_secret()
        
        if not webhook_secret:
            logger.error("[ERROR] Webhook密钥未配置，请检查.env文件中的配置")
            abort(500, "Webhook secret not configured")
        
        # 验证签名
        payload = request.get_data()
        received_sig = request.headers.get("creem-signature", "")
        computed_sig = hmac.new(
            key=webhook_secret.encode('utf-8'),
            msg=payload,
            digestmod=hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(computed_sig, received_sig):
            logger.error("[ERROR] Creem webhook签名验证失败！")
            abort(401, "Invalid signature")
        
        logger.info("Creem webhook签名验证成功！")
        
        # 解析webhook数据
        webhook_data = json.loads(payload.decode('utf-8'))
        event_type = webhook_data.get("eventType")
        event_data = DictToObj(webhook_data.get("object", {}))

        
        logger.info(f"收到Creem webhook事件: {event_type}")
        
        if event_type == "checkout.completed":
            # 处理支付成功事件
            checkout_id = event_data.id
            product_id = event_data.order.product
            amount = event_data.order.amount / 100  # Creem的金额是以分为单位
            currency = event_data.order.currency
            customer_id = event_data.order.customer
            order_id = event_data.order.id
            status = event_data.order.status
            # payment_time = event_data.completed_at 
            amount=event_data.order.amount / 100  # 转换为美元
            amount_paid=event_data.order.amount / 100  # 转换为美元
            tax_amount=event_data.order.tax_amount / 100  # 转换为美元
            trans_type=event_data.order.type
            channel="bankcard"
            description=f"AI Chat充值 - {amount}元"
            mode=getattr(event_data.order, 'mode', 'production')

            customer_email = event_data.customer.email
            
            logger.info(f"  Creem支付成功!")
            logger.info(f"   Checkout ID: {checkout_id}")
            logger.info(f"   Product ID: {product_id}")
            logger.info(f"   金额: {amount} {currency}")
            logger.info(f"   客户邮箱: {customer_email}")
            
            # 处理支付成功逻辑
            out_trade_no = f"creem_{checkout_id}"
            
            # 更新支付状态
            u = payUtils()
            trans = {
                "out_trade_no": out_trade_no,
                "pay_success": True,
                "detail": json.dumps(webhook_data.get("object", {}))
            }
            
            # 存储到Redis
            redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
            redis_client.set(f'fundTrans:{out_trade_no}', json.dumps(trans), ex=600)
            
            # 处理银行卡交易记录和余额更新
            try:
                
                
                # 获取支付时间，如果没有则使用当前时间
                payment_time = webhook_data.get('completed_at') or datetime.datetime.now().isoformat()
                
                # 准备银行卡交易数据
                transaction_data = (
                    checkout_id,                        # checkout_id (新增字段，用于幂等性检查)
                    order_id,                           # order_id
                    product_id,                         # product_id  
                    f"merchant_{checkout_id}",          # merchant_trans_no
                    customer_id,                        # customer_id
                    status,                             # status
                    payment_time,                       # send_pay_date
                    amount,                             # amount (转换为元)
                    amount_paid,                        # amount_paid (转换为元)
                    tax_amount,                         # tax_amount
                    trans_type,                         # trans_type
                    channel,                            # channel
                    currency.upper(),                   # currency
                    datetime.datetime.now().isoformat(), # create_date
                    description,                        # description
                    mode                                # mode
                )
                
                # 插入银行卡交易记录并更新用户余额
                result = u.InsertBankCardTransaction(transaction_data, customer_email, amount_paid)
                
                if result["success"]:
                    logger.info(f"[SUCCESS] 银行卡交易记录已保存，用户余额已更新")
                    logger.info(f"   用户ID: {result['user_id']}, 充值金额: {amount_paid}元")
                    
                    # 清除用户余额缓存，让下次查询从数据库获取最新余额
                    redis_key = f'useid:{result["user_id"]}'
                    redis_client.delete(redis_key)
                    logger.info(f"[SUCCESS] 已清除用户余额缓存: {redis_key}")
                elif result.get("error") == "duplicate_transaction":
                    logger.warning(f"[WARNING] 重复交易被忽略: {result.get('message', '')}")
                    logger.info(f"   这是正常的webhook重试，无需处理")
                else:
                    logger.error(f"[ERROR] 银行卡交易处理失败: {result['error']}")
                    
            except Exception as bank_error:
                logger.error(f"[ERROR] 银行卡交易处理异常: {str(bank_error)}")
            
            # 这里可以添加更多业务逻辑，比如发送确认邮件等
            
        elif event_type == "checkout.failed":
            # 处理支付失败事件
            checkout_id = event_data.id
            failure_reason = event_data.failure_reason
            logger.error(f"[ERROR] Creem支付失败！Checkout ID: {checkout_id}, 原因: {failure_reason}")
            
        elif event_type == "checkout.expired":
            # 处理支付过期事件
            checkout_id = event_data.id
            logger.warning(f"[WARNING] Creem支付过期！Checkout ID: {checkout_id}")
            
        else:
            logger.info(f"[INFO] 未处理的Creem事件类型: {event_type}")
            
    except Exception as e:
        logger.error(f"[ERROR] Creem webhook处理异常: {str(e)}")
        return {"status": "error", "message": str(e)}, 500
    
    return {"status": "ok"}


@orderCreationview_bp.route('/creem_webhook_prod_test', methods=['POST'])
def creem_webhook_prodTest():
    """处理Creem支付回调"""
    try:
        import hmac
        import hashlib
        
        # 获取webhook密钥
        from ..config import creem_config
        webhook_secret = creem_config.get_webhook_secret()
        
        if not webhook_secret:
            logger.error("[ERROR] Webhook密钥未配置，请检查.env文件中的配置")
            abort(500, "Webhook secret not configured")
        
        # 验证签名
        payload = request.get_data()
        received_sig = request.headers.get("creem-signature", "")
        computed_sig = hmac.new(
            key=webhook_secret.encode('utf-8'),
            msg=payload,
            digestmod=hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(computed_sig, received_sig):
            logger.error("[ERROR] Creem webhook签名验证失败！")
            abort(401, "Invalid signature")
        
        logger.info("Creem webhook签名验证成功！")
        
        # 解析webhook数据
        webhook_data = json.loads(payload.decode('utf-8'))
        event_type = webhook_data.get("eventType")
        event_data = DictToObj(webhook_data.get("object", {}))

        
        logger.info(f"收到Creem webhook事件: {event_type}")
        
        if event_type == "checkout.completed":
            # 处理支付成功事件
            checkout_id = event_data.id
            product_id = event_data.order.product
            amount = event_data.order.amount / 100  # Creem的金额是以分为单位
            currency = event_data.order.currency
            customer_id = event_data.order.customer
            order_id = event_data.order.id
            status = event_data.order.status
            # payment_time = event_data.completed_at 
            amount=event_data.order.amount / 100  # 转换为美元
            amount_paid=event_data.order.amount / 100  # 转换为美元
            tax_amount=event_data.order.tax_amount / 100  # 转换为美元
            trans_type=event_data.order.type
            channel="bankcard"
            description=f"AI Chat充值 - {amount}元"
            mode=getattr(event_data.order, 'mode', 'production')

            customer_email = event_data.customer.email
            
            logger.info(f"  Creem支付成功!")
            logger.info(f"   Checkout ID: {checkout_id}")
            logger.info(f"   Product ID: {product_id}")
            logger.info(f"   金额: {amount} {currency}")
            logger.info(f"   客户邮箱: {customer_email}")
            
            # 处理支付成功逻辑
            out_trade_no = f"creem_{checkout_id}"
            
            # 更新支付状态
            u = payUtils()
            trans = {
                "out_trade_no": out_trade_no,
                "pay_success": True,
                "detail": json.dumps(webhook_data.get("object", {}))
            }
            
            # 存储到Redis
            redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
            redis_client.set(f'fundTrans:{out_trade_no}', json.dumps(trans), ex=600)
            
            # 处理银行卡交易记录和余额更新
            try:
                
                
                # 获取支付时间，如果没有则使用当前时间
                payment_time = webhook_data.get('completed_at') or datetime.datetime.now().isoformat()
                
                # 准备银行卡交易数据
                transaction_data = (
                    checkout_id,                        # checkout_id (新增字段，用于幂等性检查)
                    order_id,                           # order_id
                    product_id,                         # product_id  
                    f"merchant_{checkout_id}",          # merchant_trans_no
                    customer_id,                        # customer_id
                    status,                             # status
                    payment_time,                       # send_pay_date
                    amount,                             # amount (转换为元)
                    amount_paid,                        # amount_paid (转换为元)
                    tax_amount,                         # tax_amount
                    trans_type,                         # trans_type
                    channel,                            # channel
                    currency.upper(),                   # currency
                    datetime.datetime.now().isoformat(), # create_date
                    description,                        # description
                    mode                                # mode
                )
                
                # 插入银行卡交易记录并更新用户余额
                result = u.InsertBankCardTransaction(transaction_data, customer_email, amount_paid)
                
                if result["success"]:
                    logger.info(f"[SUCCESS] 银行卡交易记录已保存，用户余额已更新")
                    logger.info(f"   用户ID: {result['user_id']}, 充值金额: {amount_paid}元")
                    
                    # 清除用户余额缓存，让下次查询从数据库获取最新余额
                    redis_key = f'useid:{result["user_id"]}'
                    redis_client.delete(redis_key)
                    logger.info(f"[SUCCESS] 已清除用户余额缓存: {redis_key}")
                elif result.get("error") == "duplicate_transaction":
                    logger.warning(f"[WARNING] 重复交易被忽略: {result.get('message', '')}")
                    logger.info(f"   这是正常的webhook重试，无需处理")
                else:
                    logger.error(f"[ERROR] 银行卡交易处理失败: {result['error']}")
                    
            except Exception as bank_error:
                logger.error(f"[ERROR] 银行卡交易处理异常: {str(bank_error)}")
            
            # 这里可以添加更多业务逻辑，比如发送确认邮件等
            
        elif event_type == "checkout.failed":
            # 处理支付失败事件
            checkout_id = event_data.id
            failure_reason = event_data.failure_reason
            logger.error(f"[ERROR] Creem支付失败！Checkout ID: {checkout_id}, 原因: {failure_reason}")
            
        elif event_type == "checkout.expired":
            # 处理支付过期事件
            checkout_id = event_data.id
            logger.warning(f"[WARNING] Creem支付过期！Checkout ID: {checkout_id}")
            
        else:
            logger.info(f"[INFO] 未处理的Creem事件类型: {event_type}")
            
    except Exception as e:
        logger.error(f"[ERROR] Creem webhook处理异常: {str(e)}")
        return {"status": "error", "message": str(e)}, 500
    
    return {"status": "ok"}



def qr_generate(data,out_trade_no):
        
    # 创建QRCode对象
    qr = qrcode.QRCode(
        version=1,  # 控制二维码的大小，范围是1到40
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # 使用高等级的错误纠正（H）以保证夹带logo的二维码可扫描
        box_size=10,  # 控制二维码中的每个小格子的大小
        border=4,  # 控制边框的宽度（最小是4）
    )

    # 将数据添加到QRCode对象
    qr.add_data(data)
    qr.make(fit=True)

    # 生成图像
    img = qr.make_image(fill='black', back_color='white').convert('RGB')

    # 打开Logo图像
    logo = Image.open('./app/static/image/alipayLog.png')  # 确保这里是你支付宝logo的路径

    # 计算Logo的大小（这里让logo占据二维码的20%）
    logo_size = int(img.size[0] * 0.2), int(img.size[1] * 0.2)
    logo = logo.resize(logo_size, Image.LANCZOS)

    # 计算Logo在二维码中间的位置
    logo_pos = ((img.size[0] - logo.size[0]) // 2, (img.size[1] - logo.size[1]) // 2)

    # 将Logo粘贴到二维码图像上
    img.paste(logo, logo_pos, mask=logo)

    # 使用时间戳生成唯一的文件名    
    filename = f"{out_trade_no}.png"
    img.save('./app/static/QR/'+filename)

    logger.info(f"二维码已生成并保存为 {filename}")



class DictToObj:
    def __init__(self, data):
        for key, value in data.items():
            if isinstance(value, dict):
                value = DictToObj(value)  # 递归转换
            self.__dict__[key] = value