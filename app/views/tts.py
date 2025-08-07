from flask import Blueprint, render_template,session,request
# from flask import Flask, request,session
from ..UserUtils import UserUtils


ttsview_bp = Blueprint('tts', __name__)

@ttsview_bp.route('/tts')
def ttsPage():
    available_voices = [
        {'name': 'Kore', 'display_name': 'Kore (默认)'},
        {'name': 'Zephyr', 'display_name': 'Zephyr'},
        {'name': 'Puck', 'display_name': 'Puck'},
        {'name': 'Charon', 'display_name': 'Charon'},
        {'name': 'Fenrir', 'display_name': 'Fenrir'},
        {'name': 'Leda', 'display_name': 'Leda'},
        {'name': 'Orus', 'display_name': 'Orus'},
        {'name': 'Aoede', 'display_name': 'Aoede'},
        {'name': 'Callirrhoe', 'display_name': 'Callirrhoe'},
        {'name': 'Autonoe', 'display_name': 'Autonoe'},
        {'name': 'Enceladus', 'display_name': 'Enceladus'},
        {'name': 'Iapetus', 'display_name': 'Iapetus'},
        {'name': 'Umbriel', 'display_name': 'Umbriel'},

        # You can add more voices if they become available or you find others
    ]
    if  'user_name' in session:
        u=UserUtils()
        # 获取用户的货币偏好，默认显示人民币，但同时提供美元等值
        currency_preference = request.args.get('currency', 'CNY')
        userInfo = u.getUserInfoWithCurrency(session['user_id'], currency_preference)
        
        return render_template('tts.html', 
                             user_name=session['user_name'],
                             balance=round(userInfo['balance'],2),
                             balance_display=userInfo['balance_display'],
                             balance_secondary=userInfo['balance_secondary'],
                             currency_info=userInfo['currency_info'],
                             currency_preference=currency_preference,
                             user_email=session.get('user_email', ''),
                             voices=available_voices)
    else:  
        return render_template('tts.html',voices=available_voices)