import logging 
# from app import logger
from flask import session,Blueprint,make_response,jsonify,redirect, url_for,request,render_template
from app.UserUtils import UserUtils
from werkzeug.security import generate_password_hash,check_password_hash
import redis
import secrets
from app.SendMail import SendMail
from app.DB.SqlLiteUtil import SqlLiteUtil
from app import limiter 
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address



userAPI_bp = Blueprint('userapi', __name__)
logger = logging.getLogger('log')
def ip_key_func():
    return get_remote_address()

@userAPI_bp.route('/check-login')
def check_login():
    is_logged_in = 'user_email' in session
    logger.info('logged_in:'+str(is_logged_in))
    
    statusCode=200
    if is_logged_in==False:
        statusCode=401
    
    result = {           
        "logged_in": is_logged_in
    }
    
    # 如果已登录，添加用户名信息
    if is_logged_in:
        user_email = session.get('user_email', '')
        user_id = session.get('user_id')
        
        # 从数据库查询真正的用户名
        if user_id:
            try:
                from app.DB.SqlLiteUtil import SqlLiteUtil
                db = SqlLiteUtil()
                query = "SELECT user FROM user WHERE id = ?"
                rows = db.query(query, (user_id,))
                db.cursor.close()
                db.conn.close()
                
                if rows and len(rows) > 0:
                    user_name = rows[0]['user']
                else:
                    user_name = 'User'  # 默认用户名
            except Exception as e:
                logger.error(f'查询用户名失败: {e}')
                user_name = 'User'  # 出错时使用默认用户名
        else:
            user_name = 'User'  # 没有用户ID时使用默认用户名
            
        result["user_name"] = user_name
        result["user_email"] = user_email
     
    response = make_response(jsonify(result), statusCode)
    return response




@userAPI_bp.route('/logout')
def logout():
    userid=session['user_id']
    session.pop('user_email', None)
    session.pop('user_name', None)
    session.pop('user_id', None)
    session.pop('chatHistory', None)        
    session.pop('user_level', None) 
    redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
   
    redis_client.delete(f'useid:{userid}')  
    return redirect(url_for('chat.index'))




@userAPI_bp.route('/api/v1/login', methods=['POST'])
def emailLoginapi():
    status="failure"
    error=""
    # password = request.form['password']
    # email = request.form['email']
    data = request.json
    email = data['email']  
    password = data['password']   
    # confirmPassword = data['confirmPassword']  
    userUtils=UserUtils()   
    rows=userUtils.userQuery(email)
    logger.info(rows)
    # origin = request.form.get('origin')  
    # origin = request.args.get('origin', '/')  
    if len(rows)>0:
        stored_password_hash=rows[0]["password"]
        user_email=rows[0]["email"]
        user_name=rows[0]["user"]
        user_id=rows[0]["id"]
        level=rows[0]["level"]
        logger.info("level:"+str(level))
        response=""
        statusCode=200
        if stored_password_hash and check_password_hash(stored_password_hash, password):
            logger.info("Password matched")
            status="success"
           
            # access_token = create_access_token(identity=user_email)
            # print("access_token:",access_token)
            # session['api_token'] = access_token
           
            # return redirect(url_for('chatpage'))   
            if level in [3,2,1,0]:      
                session['user_email'] = user_email  
                session['user_name'] = user_name  
                session['user_id']=user_id
                session['user_level']=level
                session["chatHistory"]=None 
                # return redirect(origin)  
                response = make_response(jsonify({"UserName":user_name}), statusCode)
            else:
                result={"error": "Unauthorized", "message": "Find loginUser,But No permission to accesss,Please contact with kzhou2017@outloook.com"}
                statusCode=401
                response = make_response(jsonify(result), statusCode)
            #    return jsonify({"error": "Unauthorized", "message": "Find loginUser,But No permission to accesss,Please contact with kzhou2017@outloook.com"}), 401       
        else:
            logger.info("Password not matched")
            # return jsonify({"error": "Unauthorized", "message": "User or password is invalid"}), 401
            result={"error": "Unauthorized", "message": "User or password is invalid"}
            statusCode=401
            response = make_response(jsonify(result), statusCode)
            
    else:
        result={"error": "Unauthorized", "message": "Not found user"}
        statusCode=401
        response = make_response(jsonify(result), statusCode)
            
    return response
   


@userAPI_bp.route('/api/v1/check-email-register', methods=['POST'])
def check_email_register():
    
    # return jsonify({'logged_in': is_logged_in})   
    emailExist=False
    userUtils=UserUtils()
    data = request.json
    email = data['email'] 
    rows=userUtils.userQuery(email)
    if len(rows)>0:
            emailExist=True
    statusCode=200    
    result = {           
                "emailExist": emailExist
            }     
    response = make_response(jsonify(result), statusCode)
    return response


@userAPI_bp.route('/register', methods=['POST'])
@limiter.limit("1 per minute,2 per hour,2 per day", key_func=ip_key_func)
def registerapi():
    # data = request.json
    user=request.form['user']
    email = request.form['email']
    password = request.form['password']
    confirmPassword = request.form['confirm_password'] 
    logger.info(password)
    logger.info(confirmPassword)



    hashed_password = generate_password_hash(password)

    # if password != confirmPassword:
    #     password_error = 'Passwords do not match.'
    #     return 

    # encrypte password
    # insert into db
    userUtils=UserUtils()
    # rows=userUtils.userQuery(email)
    # if len(rows)>0:
    #     return jsonify({"error": "Unauthorized", "message": "Email already exists,Please use another email to register"}), 401
    # confirmation_link = f"https://www.example.com/confirm?token={token}"
    
    token = secrets.token_urlsafe(16)    
    userUtils.register(user,email,hashed_password,0,token)
    # generate confiramtion url
    confirmation_link =request.url_root+ f"confirm?email={email}&token={token}"
    body='Please click the link to activate your account:'+confirmation_link+'<br>'
    
    logger.info(confirmation_link)

    recipients = [email]
    m=SendMail()
    subject="Please activate your account!"
    body=f'{user},Please click the link to activate your account:<a href="{confirmation_link}" >点击这里确认</a>'
    
    result=m.sendMail(recipients,"",subject,body)
    if result==False:
        # email send failure:
        s=SqlLiteUtil()
        s.insertEmailFailure((recipients[0]["email"],1,result['text']))
    # return redirect(url_for('chat.index'))
    return render_template('verifyEmail.html')
