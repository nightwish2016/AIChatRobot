from flask import Blueprint, render_template,session
# from flask import Flask, request,session
from ..UserUtils import UserUtils

imageview_bp = Blueprint('image', __name__)

@imageview_bp.route('/image')
def imagePage():
    if  'user_name' in session:
        u=UserUtils()
        userInfo=u.getUserInfo(session['user_id'])
        balance = userInfo['balance']
        return render_template('image.html', user_name=session['user_name'],balance=round(balance,2))
    else:  
        return render_template('image.html')