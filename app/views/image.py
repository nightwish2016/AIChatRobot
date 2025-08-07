from flask import Blueprint, render_template,session,request
# from flask import Flask, request,session
from ..UserUtils import UserUtils

imageview_bp = Blueprint('image', __name__)

@imageview_bp.route('/image')
def imagePage():
    if  'user_name' in session:
        u=UserUtils()
        # 获取用户的货币偏好，默认显示人民币，但同时提供美元等值
        currency_preference = request.args.get('currency', 'CNY')
        userInfo = u.getUserInfoWithCurrency(session['user_id'], currency_preference)
        
        return render_template('image.html', 
                             user_name=session['user_name'],
                             balance=round(userInfo['balance'],2),
                             balance_display=userInfo['balance_display'],
                             balance_secondary=userInfo['balance_secondary'],
                             currency_info=userInfo['currency_info'],
                             currency_preference=currency_preference,
                             user_email=session.get('user_email', ''))
    else:  
        return render_template('image.html')