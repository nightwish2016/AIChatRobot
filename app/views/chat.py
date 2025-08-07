from flask import Blueprint, render_template,session,request
import redis
import json
from ..UserUtils import UserUtils
# from flask import Flask, request,session

chatview_bp = Blueprint('chat', __name__)


@chatview_bp.route('/chat')
def chatpage():      
    if  'user_name' in session:
        u=UserUtils()
        # 获取用户的货币偏好，默认显示人民币，但同时提供美元等值
        currency_preference = request.args.get('currency', 'CNY')
        userInfo = u.getUserInfoWithCurrency(session['user_id'], currency_preference)
        
        return render_template('chat.html', 
                             user_name=session['user_name'],
                             balance=round(userInfo['balance'],2),
                             balance_display=userInfo['balance_display'],
                             balance_secondary=userInfo['balance_secondary'],
                             currency_info=userInfo['currency_info'],
                             currency_preference=currency_preference,
                             user_email=session.get('user_email', ''))   
    else:
        return render_template('chat.html')

@chatview_bp.route('/')
def index():      
    if  'user_name' in session:
        u=UserUtils()
        # 获取用户的货币偏好，默认显示人民币，但同时提供美元等值
        currency_preference = request.args.get('currency', 'CNY')
        userInfo = u.getUserInfoWithCurrency(session['user_id'], currency_preference)
        
        return render_template('chat.html', 
                             user_name=session['user_name'],
                             balance=round(userInfo['balance'],2),
                             balance_display=userInfo['balance_display'],
                             balance_secondary=userInfo['balance_secondary'],
                             currency_info=userInfo['currency_info'],
                             currency_preference=currency_preference,
                             user_email=session.get('user_email', ''))   
    else:
        return render_template('chat.html')


@chatview_bp.route('/confirm', methods=['GET'])
def activeAccount():
    token = request.args.get('token')
    email = request.args.get('email')
    #check toke and update toke ,acitve
    u=UserUtils()
    result=u.activateUser(token,email)
    if result==True:       
        return render_template('activate_success.html')
    else:
        return render_template('activate_failure.html')

