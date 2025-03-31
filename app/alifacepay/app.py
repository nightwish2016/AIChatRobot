#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import traceback
from random import randint
import time

# api文档 https://docs.open.alipay.com/194/105203
from alipay.aop.api.AlipayClientConfig import AlipayClientConfig
from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient

# alipay.trade.precreate
from alipay.aop.api.domain.AlipayTradePrecreateModel import AlipayTradePrecreateModel
from alipay.aop.api.request.AlipayTradePrecreateRequest import AlipayTradePrecreateRequest
from alipay.aop.api.response.AlipayTradePrecreateResponse import AlipayTradePrecreateResponse

# alipay.trade.query
from alipay.aop.api.domain.AlipayTradeQueryModel import AlipayTradeQueryModel
from alipay.aop.api.request.AlipayTradeQueryRequest import AlipayTradeQueryRequest
from alipay.aop.api.response.AlipayTradeQueryResponse import AlipayTradeQueryResponse

# alipay.trade.cancel
from alipay.aop.api.domain.AlipayTradeCancelModel import AlipayTradeCancelModel
from alipay.aop.api.request.AlipayTradeCancelRequest import AlipayTradeCancelRequest
from alipay.aop.api.response.AlipayTradeCancelResponse import AlipayTradeCancelResponse

# alipay.trade.close
from alipay.aop.api.domain.AlipayTradeCloseModel import AlipayTradeCloseModel
from alipay.aop.api.request.AlipayTradeCloseRequest import AlipayTradeCloseRequest
from alipay.aop.api.response.AlipayTradeCloseResponse import AlipayTradeCloseResponse

# alipay.trade.refund
from alipay.aop.api.domain.AlipayTradeRefundModel import AlipayTradeRefundModel
from alipay.aop.api.request.AlipayTradeRefundRequest import AlipayTradeRefundRequest
from alipay.aop.api.response.AlipayTradeRefundResponse import AlipayTradeRefundResponse

from alipay.aop.api.util.SignatureUtils import verify_with_rsa

logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        filemode='a', )

'''
1. 默认通过预下单接口生成的二维码有效时间为2小时，这里设置为5分钟 qr_code_timeout_express
2. 默认用户扫码后支付超时时间为15天，这里设置为5分钟 timeout_express
3. 可退款期限根据签约协议确定，一般为三个月或十二个月
4. 对于未支付的订单，请及时通过调用撤销接口关闭订单（注意：超过24小时的订单无法撤销）；
另外一种方法是为每笔订单设置超时时间，超过时间未支付的订单会自动关闭（当前采用这种方案，5分钟超时）。
'''


class AliFacePay:
    logger = logging.getLogger('')

    def __init__(self, app_id, app_private_key, alipay_public_key, notify_url=None, sandbox_debug=False):
        '''
        设置配置，包括支付宝网关地址、app_id、应用私钥、支付宝公钥等，其他配置值可以查看AlipayClientConfig的定义。
        '''
        alipay_client_config = AlipayClientConfig(sandbox_debug=sandbox_debug)
        alipay_client_config.app_id = app_id
        alipay_client_config.app_private_key = app_private_key
        alipay_client_config.alipay_public_key = alipay_public_key

        '''
        得到客户端对象。
        注意，一个alipay_client_config对象对应一个DefaultAlipayClient，定义DefaultAlipayClient对象后，alipay_client_config不得修改，如果想使用不同的配置，请定义不同的DefaultAlipayClient。
        logger参数用于打印日志，不传则不打印，建议传递。
        '''
        self.client = DefaultAlipayClient(alipay_client_config=alipay_client_config, logger=AliFacePay.logger)
        self.notify_url = notify_url
        self.alipay_public_key = alipay_public_key

    '''
    功能：生成支付二维码，生成二维码后，展示给用户，由用户扫描二维码创建支付订单
    
    参数：
    out_trade_no：订单号，不可重复，用来区分每一笔订单
    total_amount：订单金额，单位元，精确到小数点后2位
    subject：订单标题
    body：订单详细描述
    
    返回值：string 付款二维码链接，使用二维码生成工具生成二维码提供给用户付款
    '''
    def precreate(self, out_trade_no, total_amount, subject, body=None):
        '''
        系统接口示例：alipay.trade.precreate
        '''
        # 对照接口文档，构造请求对象
        precreate_model = AlipayTradePrecreateModel()
        precreate_model.out_trade_no = out_trade_no
        precreate_model.total_amount = total_amount
        precreate_model.subject = subject

        # 该笔订单允许的最晚付款时间，逾期将自动关闭交易(TRADE_CLOSED),时间从用户扫描付款二维码以后开始计算
        # 扫码后的最晚付款时间限制 默认交易超时时间为15天
        precreate_model.timeout_express = '5m'

        # 二维码有效期，从创建二维码开始直到用户扫码，默认2h，要求最小2m
        # （沙箱目前qr_code_timeout_express这个参数是不生效的，实际环境才有效果）
        # 到期二维码失效，不会影响订单状态，因为此时订单还没有创建
        # 二维码创建后的最晚扫码时间限制
        precreate_model.qr_code_timeout_express = '5m'

        # 花呗，默认支持吗？
        #precreate_model.enable_pay_channels = 'pcredit'
        # 花呗分期
        #precreate_model.enable_pay_channels = 'pcreditpayInstallment'

        if body:
            precreate_model.body = body

        precreate_request = AlipayTradePrecreateRequest(biz_model=precreate_model)
        precreate_request.notify_url = self.notify_url
        precreate_response_content = None
        qr_code = None
        try:
            precreate_response_content = self.client.execute(precreate_request)
        except Exception as e:
            print(traceback.format_exc())

        if not precreate_response_content:
            print("failed execute precreate")
        else:
            precreate_response = AlipayTradePrecreateResponse()
            # 解析响应结果
            precreate_response.parse_response_content(precreate_response_content)
            if precreate_response.is_success():
                # 如果业务成功，则通过respnse属性获取需要的值
                qr_code = precreate_response.qr_code
                # print("get response out_trade_no:" + precreate_response.out_trade_no)
                # print("get response qr_code:" + precreate_response.qr_code)
            else:
                # 如果业务失败，则从错误码中可以得知错误情况，具体错误码信息可以查看接口文档
                print(precreate_response.code + "," + precreate_response.msg + "," + precreate_response.sub_code + ","
                      + precreate_response.sub_msg)
        return qr_code

    '''
    功能：主动查询订单状态(只有用户扫描了二维码以后才会创建订单，用户扫描之前得到的结果会是 40004 交易不存在)

    参数：
    out_trade_no：订单号，不可重复，用来区分每一笔订单        

    返回值：dict
    out_trade_no：订单号
    buyer_logon_id：买家支付宝账号
    trade_status：交易状态：WAIT_BUYER_PAY（交易创建，等待买家付款）、TRADE_CLOSED（未付款交易超时关闭，或支付完成后全额退款）、TRADE_SUCCESS（交易支付成功）、TRADE_FINISHED（交易结束，不可退款）
    交易状态 TRADE_FINISHED 的通知触发条件是商户签约的产品不支持退款功能的前提下，买家付款成功；或者，商户签约的产品支持退款功能的前提下，交易已经成功并且已经超过可退款期限
    total_amount：交易金额
    '''
    def query(self, out_trade_no):
        '''
        系统接口示例：alipay.trade.query
        '''
        # 对照接口文档，构造请求对象
        query_model = AlipayTradeQueryModel()
        query_model.out_trade_no = out_trade_no

        query_request = AlipayTradeQueryRequest(biz_model=query_model)
        query_response_content = None
        ret_dict = {}
        try:
            query_response_content = self.client.execute(query_request)
        except Exception as e:
            print(traceback.format_exc())

        if not query_response_content:
            print("failed execute query")
        else:
            query_response = AlipayTradeQueryResponse()
            # 解析响应结果
            query_response.parse_response_content(query_response_content)
            if query_response.is_success():
                # 如果业务成功，则通过respnse属性获取需要的值
                ret_dict['out_trade_no'] = query_response.out_trade_no
                ret_dict['buyer_logon_id'] = query_response.buyer_logon_id
                ret_dict['trade_status'] = query_response.trade_status
                ret_dict['total_amount'] = query_response.total_amount
                ret_dict['send_pay_date'] = query_response.send_pay_date
                ret_dict['trade_no'] = query_response.send_pay_date
            else:
                # 如果业务失败，则从错误码中可以得知错误情况，具体错误码信息可以查看接口文档
                print(query_response.code + "," + query_response.msg + "," + query_response.sub_code + ","
                      + query_response.sub_msg)
        return ret_dict

    '''
    功能：支付交易返回失败或支付系统超时，调用该接口撤销交易。
    cancel和close的区别是，交易完成后不可以close，但是可以cancel，cancel会退款给用户
    生成二维码之后，扫描之前也可以cancel，但是不可以close

    参数：
    out_trade_no：订单号，不可重复，用来区分每一笔订单
        
    返回值：bool 是否执行成功
    '''
    def cancel(self, out_trade_no):
        '''
        系统接口示例：alipay.trade.cancel
        '''
        # 对照接口文档，构造请求对象
        cancel_model = AlipayTradeCancelModel()
        cancel_model.out_trade_no = out_trade_no

        cancel_request = AlipayTradeCancelRequest(biz_model=cancel_model)
        cancel_response_content = None
        ret = False
        try:
            cancel_response_content = self.client.execute(cancel_request)
        except Exception as e:
            print(traceback.format_exc())

        if not cancel_response_content:
            print("failed execute cancel")
        else:
            cancel_response = AlipayTradeCancelResponse()
            # 解析响应结果
            cancel_response.parse_response_content(cancel_response_content)
            if cancel_response.is_success():
                # 如果业务成功，则通过respnse属性获取需要的值
                ret = True
            else:
                # 如果业务失败，则从错误码中可以得知错误情况，具体错误码信息可以查看接口文档
                print(cancel_response.code + "," + cancel_response.msg + "," + cancel_response.sub_code + ","
                      + cancel_response.sub_msg)
        return ret

    '''
    功能：用于交易创建后，用户在一定时间内未进行支付，可调用该接口直接将未付款的交易进行关闭。
    也就是用户扫码创建了订单，用户支付之前我们可以close订单
    也就是说当且仅当订单状态为WAIT_BUYER_PAY时可以close

    参数：
    out_trade_no：订单号，不可重复，用来区分每一笔订单

    返回值：bool 是否执行成功
    '''
    def close(self, out_trade_no):
        '''
        系统接口示例：alipay.trade.cancel
        '''
        # 对照接口文档，构造请求对象
        close_model = AlipayTradeCloseModel()
        close_model.out_trade_no = out_trade_no

        close_request = AlipayTradeCloseRequest(biz_model=close_model)
        close_response_content = None
        ret = False
        try:
            close_response_content = self.client.execute(close_request)
        except Exception as e:
            print(traceback.format_exc())

        if not close_response_content:
            print("failed execute close")
        else:
            close_response = AlipayTradeCloseResponse()
            # 解析响应结果
            close_response.parse_response_content(close_response_content)
            if close_response.is_success():
                # 如果业务成功，则通过respnse属性获取需要的值
                ret = True
            else:
                # 如果业务失败，则从错误码中可以得知错误情况，具体错误码信息可以查看接口文档
                print(close_response.code + "," + close_response.msg + "," + close_response.sub_code + ","
                      + close_response.sub_msg)
        return ret

    '''
    功能：退款

    参数：
    out_trade_no：订单号，不可重复，用来区分每一笔订单

    返回值：bool 是否执行成功
    '''
    def refund(self, out_trade_no, refund_amount):
        '''
        系统接口示例：alipay.trade.refund
        '''
        # 对照接口文档，构造请求对象
        refund_model = AlipayTradeRefundModel()
        refund_model.out_trade_no = out_trade_no
        refund_model.refund_amount = refund_amount

        refund_request = AlipayTradeRefundRequest(biz_model=refund_model)
        refund_response_content = None
        ret = False
        try:
            refund_response_content = self.client.execute(refund_request)
        except Exception as e:
            print(traceback.format_exc())

        if not refund_response_content:
            print("failed execute refund")
        else:
            refund_response = AlipayTradeRefundResponse()
            # 解析响应结果
            refund_response.parse_response_content(refund_response_content)
            if refund_response.is_success():
                # 如果业务成功，则通过respnse属性获取需要的值
                ret = True
                # print("get response out_trade_no:" + refund_response.out_trade_no)
                # print("get response refund_fee:" + refund_response.refund_fee)
            else:
                # 如果业务失败，则从错误码中可以得知错误情况，具体错误码信息可以查看接口文档
                print(refund_response.code + "," + refund_response.msg + "," + refund_response.sub_code + ","
                      + refund_response.sub_msg)
        return ret

    '''
    功能：验证异步回调签名

    参数：
    params：回调通知参数字典，例如flask通知中使用request.form.to_dict()来构造参数（params = request.form.to_dict()）

    返回值：bool 是否验证成功
    '''

    def verify_params_sign(self, params):
        # 文档 https://docs.open.alipay.com/194/103296#s5
        sign = params.pop('sign', None)  # 取出sign参数
        params.pop('sign_type')  # 取出sign_type参数
        params = sorted(params.items(), key=lambda e: e[0], reverse=False)  # 取出字典元素按key的字母升序排序形成列表
        message = "&".join(u"{}={}".format(k, v) for k, v in params).encode()  # 将列表转为二进制参数字符串
        try:
            status = verify_with_rsa(self.alipay_public_key.encode('utf-8').decode('utf-8'), message,
                                     sign)  # 验证签名并获取结果
            return status  # 返回验证结果
        except Exception as e:  # 如果验证失败，返回假值。
            return False

    @classmethod
    def get_rand_string(cls, length=10):
        # 生成len长度的随机字符串
        s = ""
        for _ in range(length):
            s = s + str(randint(0, 9))
        return s

    @classmethod
    def gen_trade_no(cls, pre_string=None):
        timestamp = time.strftime("%Y%m%d%H%M%S", time.localtime(time.time()))
        trade_no = timestamp + cls.get_rand_string()
        if pre_string:
            trade_no = pre_string + '_' + trade_no
        return trade_no


'''
同步方式使用当面付接口
'''

if __name__ == "__main__":
    # 基础信息配置
    # 只需要三个关键信息 app_id，alipay_public_key，app_private_key
    sandbox = True
    if sandbox:
        app_id = '9021000137634851'
        alipay_public_key_string = '''-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAo3XUTdshfLg3a415orD2APguhRTdN/fLeVetJndYJYxhE33n7MHdR6zntHc/z4dBuekxBivUoQ5kkN+iFBSa3DFWz5qIsOqizdjUrvFf+xVvgcw3AteKx7MslCIhRACzKweLzMkGdPt+MRTuZIOE01KbeSu7yR5DaYuwIFSYJAmpzG0rN37TiaJz9dsQPF/JGvVnQ7XMNNp1se8Cb/PQN5RS6hoyOjilBFF162rZmunqNRtMZzKcwq88he6HGncu6gNB02TloLdSMhD29gO5kSrO10sBiGBtW8khQPE0mFsW+ps/8dJiH0D8eWFC2V6LzUvUfT+TMLMoInsM2495uQIDAQAB
-----END PUBLIC KEY-----'''
    else:
        app_id = '2019061665605123'
        alipay_public_key_string = 'MIIEowIBAAKCAQEAhHUCnphzIcEV7Al3NqgtXhReYbQ4X4smAAzMdTkbXMIP30FNqzLi8pXPPQJFmWoK2CXUlxTCEQtuFF5VHJligRbvjEwY5uwMJtAWBYFOA1wAXHUe7COSFlvhU/PPP0jue14ZRgzRC+Tj9F+05o0ZeWU/HL9zkRohFbzKNGWK5WdXZhZFQDiI1P2HOHKoIZVhtpA7qkiUzBnynmBML2bHJ8W0PZ5HKY7/mSF9v3wCP5pEfE8HJUKb6mznQm29I6mRES3vNWWGdxS4jHGwI8q56Bm/aKBDN6esC2+25goAoUaUprzv0jer37sMS5m8Et17W+/e5erXK6K641/soc+Y4QIDAQABAoIBAGDky47CjG4jteqdngRwkAdjNQuZ7ycNPjYJJsOVi8uV9lBlj/BtYBD+v8OsVsd8CATH37TJLZGUX+ksfGxYU/OEmKVzwT+jatw1mfZa+XuBoI4B6yXoe2Q5wCJOlst/iVzbn/dbRszBmnNYU5fXncvs4XchIeQCTjN9kBk2Mp3OpmNqTVoY8V4Zgy4r5RsGbz7MwgPEnD8wptSXb56J4YrC69iCh3sBmJynuylkulhiofMFrkR11F4gXh+yiuUBZ/T+QGyBYwTYow+YlYZw1sliCfAipqEpJ9d6McBXSz67cxshYO2CrzfDvPkLR0uqGVZVhZEYDkg7wvm2nmIqBNUCgYEAvPSdYsGZP+QxVI2rak0oSUVBlpp4y9Fzi6CnTrNmKNKEGCWTuournQrvdxCWPL20GxwTp023+J5UOBvRbuMtwmwJruawfwUAOCielab/331tYIKOxOOc5JVNxNex4bd6Z0/F5zj/BndOS2O+zqNlVmSwPAO7U1B8mKm4q/i1Cq8CgYEAs3R5kcpmLBghyMdUj3dwjIfc5+zWW8CoxerKkAm519MDg6EplFiXi2IJuLb2HO0f00xxukcXa3rDYMQg7fW+rHDfovq3h9u0gFiR7I21DfTJDLCn0XM7zKSjN8a1kjev2uuvEUbFHnCKrKRWEE4lcKgTHjn91gOgCX5dK/LBOW8CgYA9jZ37fr+SbZ6YQbI2Zb4a6EGuctGo66ktMf9uhshfwfwf9ZXDLh6QgPBzI+cdEFssfZ/1Xz7v8XvT71PxQHY2oIUjAak7J4Djym+mpokx36USzFT/1HnWiMCVwAIFWoS4ROdeJFYHYDQUIQEWRWoMk65JTpnmURDVlmw/MTygpwKBgHGZE7PUWeUjyY8dj0vaIebzwkUWSYN/a9cNj/iqD3it3RWgGYAMrLHQ97J0L0uUV4ccZwmyIwMojTFeNjIsU+047nhvGWrpC1QLvSPveGNDR1m/IhyWQ46B0chnA11x3uJIO2RGVlW0jDRJOynLLiwoWSHTN/oYBWC9GyHM48AFAoGBALVms3TZe6MAqf/cLnqpYn+8hmJAY+tWNQNYo/aqL8wMvlbz2cRgSa5g3CQ1YTuvmXiXaDOFE2RMfjnWR3AdCIYBc4m017PdcnhzdlEwRZkpdGyrx/7+AP2dogOCENPU1nMGcaNFk+Kqf6xbl+YTQY+SeoEQBfwCdpsfsYyVdww1'

    app_private_key_string ='''-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAhHUCnphzIcEV7Al3NqgtXhReYbQ4X4smAAzMdTkbXMIP30FNqzLi8pXPPQJFmWoK2CXUlxTCEQtuFF5VHJligRbvjEwY5uwMJtAWBYFOA1wAXHUe7COSFlvhU/PPP0jue14ZRgzRC+Tj9F+05o0ZeWU/HL9zkRohFbzKNGWK5WdXZhZFQDiI1P2HOHKoIZVhtpA7qkiUzBnynmBML2bHJ8W0PZ5HKY7/mSF9v3wCP5pEfE8HJUKb6mznQm29I6mRES3vNWWGdxS4jHGwI8q56Bm/aKBDN6esC2+25goAoUaUprzv0jer37sMS5m8Et17W+/e5erXK6K641/soc+Y4QIDAQABAoIBAGDky47CjG4jteqdngRwkAdjNQuZ7ycNPjYJJsOVi8uV9lBlj/BtYBD+v8OsVsd8CATH37TJLZGUX+ksfGxYU/OEmKVzwT+jatw1mfZa+XuBoI4B6yXoe2Q5wCJOlst/iVzbn/dbRszBmnNYU5fXncvs4XchIeQCTjN9kBk2Mp3OpmNqTVoY8V4Zgy4r5RsGbz7MwgPEnD8wptSXb56J4YrC69iCh3sBmJynuylkulhiofMFrkR11F4gXh+yiuUBZ/T+QGyBYwTYow+YlYZw1sliCfAipqEpJ9d6McBXSz67cxshYO2CrzfDvPkLR0uqGVZVhZEYDkg7wvm2nmIqBNUCgYEAvPSdYsGZP+QxVI2rak0oSUVBlpp4y9Fzi6CnTrNmKNKEGCWTuournQrvdxCWPL20GxwTp023+J5UOBvRbuMtwmwJruawfwUAOCielab/331tYIKOxOOc5JVNxNex4bd6Z0/F5zj/BndOS2O+zqNlVmSwPAO7U1B8mKm4q/i1Cq8CgYEAs3R5kcpmLBghyMdUj3dwjIfc5+zWW8CoxerKkAm519MDg6EplFiXi2IJuLb2HO0f00xxukcXa3rDYMQg7fW+rHDfovq3h9u0gFiR7I21DfTJDLCn0XM7zKSjN8a1kjev2uuvEUbFHnCKrKRWEE4lcKgTHjn91gOgCX5dK/LBOW8CgYA9jZ37fr+SbZ6YQbI2Zb4a6EGuctGo66ktMf9uhshfwfwf9ZXDLh6QgPBzI+cdEFssfZ/1Xz7v8XvT71PxQHY2oIUjAak7J4Djym+mpokx36USzFT/1HnWiMCVwAIFWoS4ROdeJFYHYDQUIQEWRWoMk65JTpnmURDVlmw/MTygpwKBgHGZE7PUWeUjyY8dj0vaIebzwkUWSYN/a9cNj/iqD3it3RWgGYAMrLHQ97J0L0uUV4ccZwmyIwMojTFeNjIsU+047nhvGWrpC1QLvSPveGNDR1m/IhyWQ46B0chnA11x3uJIO2RGVlW0jDRJOynLLiwoWSHTN/oYBWC9GyHM48AFAoGBALVms3TZe6MAqf/cLnqpYn+8hmJAY+tWNQNYo/aqL8wMvlbz2cRgSa5g3CQ1YTuvmXiXaDOFE2RMfjnWR3AdCIYBc4m017PdcnhzdlEwRZkpdGyrx/7+AP2dogOCENPU1nMGcaNFk+Kqf6xbl+YTQY+SeoEQBfwCdpsfsYyVdww1
-----END RSA PRIVATE KEY-----'''
    pay = AliFacePay(app_id, app_private_key_string, alipay_public_key_string, None, sandbox)

    #out_trade_no = 'out_trade_no20190616_13'
    out_trade_no = AliFacePay.gen_trade_no('yqhs')

    # print(pay.cancel(out_trade_no))
    # print(pay.close(out_trade_no))
    # print(pay.refund(out_trade_no, 1))
    # print(pay.query(out_trade_no))
    # exit()

    start = time.time()

    # 生成付款二维码，可以去这里生成qr_code的二维码图片 http://www.liantu.com/
    qr_code = pay.precreate(out_trade_no, 1, "测试")

    end = time.time()
    print(end - start)

    if qr_code:
        print(qr_code)
        # 查询订单状态
        paid = False
        for i in range(20):
            # 最佳实践：每隔3s轮询，总轮询60s，未付款则取消订单
            time.sleep(30)
            query_result = pay.query(out_trade_no)
            print(query_result.get("trade_status", ""))
            if query_result.get("trade_status", "") == "TRADE_SUCCESS":
                paid = True
                print("支付成功")
                break
            elif query_result.get("trade_status", "") == "WAIT_BUYER_PAY":
                print("等待用户支付")
            else:
                print("等待用户扫描付款二维码")

        if paid:
            print("退款")
            print(pay.refund(out_trade_no, 1))
        else:
            print("取消订单")
            pay.cancel(out_trade_no)

    else:
        print('付款二维码生成失败')


'''
异步方式使用当面付接口（以flask为例）
'''

'''
from flask import Flask
from flask import render_template, request, Response
from alifacepay import AliFacePay

app = Flask(__name__)

# 基础信息配置
# 只需要三个关键信息 app_id，alipay_public_key，app_private_key
sandbox = True
if sandbox:
    app_id = '2016092900626816'
    alipay_public_key_string = open("G:/python/alipay_key/alipay_public_key_sandbox.txt").read()
else:
    app_id = '2019061665605123'
    alipay_public_key_string = open("G:/python/alipay_key/alipay_public_key.txt").read()

app_private_key_string = open("G:/python/alipay_key/app_private_key.pem").read()

ali_face_pay = AliFacePay(app_id, app_private_key_string, alipay_public_key_string,
                 'http://pzcuni.natappfree.cc/alipay_nofity', sandbox)


@app.route('/')
def hello_world():
    out_trade_no = AliFacePay.gen_trade_no('yqhs')
    # 生成付款二维码，可以去这里生成qr_code的二维码图片 http://www.liantu.com/
    qr_code = ali_face_pay.precreate(out_trade_no, 1, "测试")
    return Response(qr_code)


@app.route('/alipay_nofity', methods=['POST'])
def alipay_nofity():
    data = request.form.to_dict()
    print(data)
    if ali_face_pay.verify_params_sign(data):
        # 通知参数说明 https://docs.open.alipay.com/194/103296#s5
        notify_time = data['notify_time']           # 通知发出的时间
        notify_type = data['notify_type']           # 通知类型
        trade_status = data['trade_status']         # 订单状态
        out_trade_no = data['out_trade_no']         # 订单号
        buyer_logon_id = data['buyer_logon_id']     # 买家支付宝账号
        total_amount = data['total_amount']         # 订单金额
        subject = data['subject']                   # 订单标题

        # 异步通知默认只会收到TRADE_SUCCESS或者TRADE_FINISHED
        # 沙盒下测试居然收到了WAIT_BUYER_PAY，不过实际环境收不到
        if notify_type == 'trade_status_sync':
            print(trade_status)
            pay_success = False
            if trade_status == 'TRADE_SUCCESS' or trade_status == 'TRADE_FINISHED':
                pay_success = True

        return Response('success')

    print('验证签名失败')
    return '404'


if __name__ == '__main__':
    app.run()

'''
