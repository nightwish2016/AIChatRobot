from flask import Blueprint, render_template,session,request,make_response,jsonify,Response,current_app,url_for,redirect
from app.alifacepay import AliFacePay
from threading import Lock
import qrcode
from PIL import Image
import time
from app.payUtils import payUtils
import datetime

import redis
import json
import logging 
from ..UserUtils import UserUtils
orderCreationview_bp = Blueprint('orderCreation', __name__)


logger = logging.getLogger('log')
@orderCreationview_bp.route('/orderPreCreate')
def orderPreCreate():     
    user_email=session['user_email']  
    balance=0       
    u=UserUtils()
    userInfo=u.getUserInfo(session['user_id'])
    balance = userInfo['balance']
    return render_template('orderPreCreate.html',user_email=user_email,balance=round(balance,2))




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
   


@orderCreationview_bp.route('/create_trade')
def  create_trade():  
    # email=request.args.get('user_email')
    amount=request.args.get('amount')
    otherAmount=request.args.get('otherAmount')
    if otherAmount!="":
        amount=otherAmount
    out_trade_no = AliFacePay.gen_trade_no('yqhs')
    ali_face_pay=current_app.ali_face_pay
    amount=float(amount)
    qr_code = ali_face_pay.precreate(out_trade_no,amount, "AIChat")

    #add barcode data to barcode table
    u=payUtils()
    current_time=datetime.datetime.now()
    timestamp=int(current_time.timestamp())
    userId=session['user_id']  
    param=(userId,out_trade_no,1,amount,timestamp)
    u.inseBarCode(param)


    # 为订单加锁
     
    

    # if out_trade_no not in locks:
    #     # l = Lock()
    #     # l.acquire()       
    #     # locks[out_trade_no] = l
    #     payment_status = None
    #     status_lock = threading.Lock()
    

    qr_generate(qr_code,out_trade_no)
    qr_image_path = url_for('static', filename=f'QR/{out_trade_no}.png')
    # return render_template('template.html', qr_image_path=qr_image_path)
    return render_template('show_qrcode.html', qrcode_url=qr_code, out_trade_no=out_trade_no,qr_image_path=qr_image_path)



@orderCreationview_bp.route('/alipay_nofity', methods=['POST'])
def alipay_nofity():
    data = request.form.to_dict()
    logger.info("notify******")
    logger.info(data)
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
    # out_trade_no = request.args['out_trade_no']
    # # 这里请求在支付成功之前都会阻塞
    # locks[out_trade_no].acquire()
    # # acquired!
    # locks[out_trade_no].release()
    # del locks[out_trade_no]
    # return Response()
    redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
    result_fundtrans=(redis_client.get(f'fundTrans:{out_trade_no}')    )
    
    payment_status=False
    if result_fundtrans!=None:
        result=json.loads(result_fundtrans)
        payment_status=result['pay_success']
        details=json.loads(result['detail'])
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
              
  
    return jsonify({
        'pay_success': payment_status  # 假设status可以是 "success", "pending", "failed"
    })



@orderCreationview_bp.route('/pay_success')
def pay_success():
    return render_template('pay_success.html')


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

