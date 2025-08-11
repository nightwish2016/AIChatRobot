from flask import Blueprint, render_template, session, request
from ..UserUtils import UserUtils

legal_bp = Blueprint('legal', __name__)

@legal_bp.route('/contact')
def contact():
    """联系我们页面"""
    if 'user_name' in session:
        u = UserUtils()
        currency_preference = request.args.get('currency', 'CNY')
        userInfo = u.getUserInfoWithCurrency(session['user_id'], currency_preference)
        
        return render_template('contact.html', 
                             user_name=session['user_name'],
                             balance=round(userInfo['balance'], 2),
                             balance_display=userInfo['balance_display'],
                             balance_secondary=userInfo['balance_secondary'],
                             currency_info=userInfo['currency_info'],
                             currency_preference=currency_preference,
                             user_email=session.get('user_email', ''))   
    else:
        return render_template('contact.html')

@legal_bp.route('/privacy')
def privacy():
    """隐私政策页面"""
    if 'user_name' in session:
        u = UserUtils()
        currency_preference = request.args.get('currency', 'CNY')
        userInfo = u.getUserInfoWithCurrency(session['user_id'], currency_preference)
        
        return render_template('privacy.html', 
                             user_name=session['user_name'],
                             balance=round(userInfo['balance'], 2),
                             balance_display=userInfo['balance_display'],
                             balance_secondary=userInfo['balance_secondary'],
                             currency_info=userInfo['currency_info'],
                             currency_preference=currency_preference,
                             user_email=session.get('user_email', ''))   
    else:
        return render_template('privacy.html')

@legal_bp.route('/terms')
def terms():
    """服务条款页面"""
    if 'user_name' in session:
        u = UserUtils()
        currency_preference = request.args.get('currency', 'CNY')
        userInfo = u.getUserInfoWithCurrency(session['user_id'], currency_preference)
        
        return render_template('terms.html', 
                             user_name=session['user_name'],
                             balance=round(userInfo['balance'], 2),
                             balance_display=userInfo['balance_display'],
                             balance_secondary=userInfo['balance_secondary'],
                             currency_info=userInfo['currency_info'],
                             currency_preference=currency_preference,
                             user_email=session.get('user_email', ''))   
    else:
        return render_template('terms.html')