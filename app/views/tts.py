from flask import Blueprint, render_template,session
# from flask import Flask, request,session
from ..UserUtils import UserUtils


ttsview_bp = Blueprint('tts', __name__)

@ttsview_bp.route('/tts')
def ttsPage():
    available_voices = [
        {'name': 'Kore', 'display_name': 'Kore (默认)'},
        {'name': 'achernar', 'display_name': 'achernar'},
        {'name': 'Aero', 'display_name': 'Aero'},
        {'name': 'Cyrus', 'display_name': 'Cyrus'},
        {'name': 'Cirrus', 'display_name': 'Cirrus'},
        # You can add more voices if they become available or you find others
    ]
    if  'user_name' in session:
        u=UserUtils()
        userInfo=u.getUserInfo(session['user_id'])
        balance = userInfo['balance']
        return render_template('tts.html', user_name=session['user_name'],balance=round(balance,2),voices=available_voices)
    else:  
        return render_template('tts.html',voices=available_voices)