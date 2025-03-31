from flask import Blueprint, render_template,session,request,make_response,jsonify,url_for,flash,redirect
from ..UserUtils import UserUtils
import secrets
from werkzeug.security import generate_password_hash,check_password_hash
# from app import logger
import datetime
import logging
from app.SendMail import SendMail
from app.DB.SqlLiteUtil import SqlLiteUtil


userview_bp = Blueprint('user', __name__)

logger = logging.getLogger('log')

@userview_bp.route('/loginPage', methods=['POST','GET'])
def loginPage():
    # return render_template('login.html')
   
   if request.method == 'POST':
        origin = request.args.get('origin', '/')
        return render_template('login.html',origin=origin)    
   else:
        return render_template('login.html',origin='/')    
   



@userview_bp.route('/register')
def register():
    return render_template('register.html')



@userview_bp.route('/new_password/<email>/<token>', methods=['GET', 'POST'])
def newPasword(email,token):
     u= UserUtils()
   

     if request.method == 'POST':    
          password = request.form['password']    
          hashed_password = generate_password_hash(password)
          rows=u.userQueryByTokenAndEmail(token,email)    
          if len(rows)!=1:
               flash('Invalid or expired token', 'danger')
               # return redirect(url_for('user.reset_password'))
               return  render_template('password_reset_Failure.html')
          else:
               expirationDate=datetime.datetime.strptime(rows[0]["confirmationExpiration"],"%Y-%m-%d %H:%M:%S.%f")
               if  expirationDate>datetime.datetime.now():               
                    # update password
                    u.updatePassword(email,hashed_password)
                    flash('Your password has been updated.', 'success')
                    # return redirect(url_for('user.loginPage'))
                    return  render_template('password_reset_Success.html',origin='/')    
               else:
                    flash('Invalid or expired token', 'danger')
                    # return redirect(url_for('user.reset_password'))
                    return  render_template('password_reset_Failure.html')
     return render_template('new_password.html', email=email,token=token)




@userview_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form['email']
        u=UserUtils()
        rows=u.userQuery(email)
        if len(rows)>0:           
          user=rows[0]["user"]
          token = secrets.token_urlsafe(16)              
          u.updateTokenForResetPassword(email,token)   
          restPasswordUrl =request.url_root+ f"new_password/{email}/{token}"    
          logger.info(f"Reset password url: {restPasswordUrl}")   

          recipients = [email]              
          m=SendMail()
          subject="Please reset your password!"
          body=f'{user},Please click the link to reset your password:<a href="{restPasswordUrl}" >Click here</a>'
          
          result=m.sendMail(recipients,"",subject,body)
          if result==False:
               # email send failure:
               s=SqlLiteUtil()
               s.insertEmailFailure((recipients[0]["email"],3,result['text']))    
          #   send_reset_email(email, token)
          # flash('A password reset link has been sent to your email.', 'info')
          # return render_template('email_sent.html',login=url_for('user.loginPage'))
          return render_template('email_sent.html')
        else:
            flash('Email not found', 'danger')
    return render_template('reset_password.html')


