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
         userInfo=u.getUserInfo(session['user_id'])
         balance = userInfo['balance']
         return render_template('chat.html', user_name=session['user_name'],balance=round(balance,2))   
    else:
        return render_template('chat.html')

@chatview_bp.route('/')
def index():      
    if  'user_name' in session:
        u=UserUtils()
        userInfo=u.getUserInfo(session['user_id'])
        balance = userInfo['balance']
        return render_template('chat.html', user_name=session['user_name'],balance=round(balance,2))   
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

