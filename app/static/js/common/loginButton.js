// 检查登录状态
async   function checkLoginStatus() {
    // return sessionStorage.getItem('loggedIn') === 'true';
                    try {
            const response = await fetch('/check-login');
            const data = await response.json();           

            if (data.logged_in==true) {
                console.log("user already login");
               
            } else {
                console.log("user doesn't login");
              
            }
            return data;
        } catch (error) {
            console.error("Error checking login status:", error);
            return data;  // 在出错时返回 false 或其他适当的错误处理
        }
}



// 根据登录状态显示登录按钮或已登录图标
async  function                                                                                                                         displayLoginStatus() {
    const dataCheckLogin = await checkLoginStatus(); 
    let loginStatus=dataCheckLogin.logged_in
    // console.log(dataCheckLogin)  
    // console.log(loginStatus)
     if (loginStatus) {
        document.getElementById('loginButton').style.display = 'none';
        document.getElementById('loggedInIcon').style.display = 'block';
        document.getElementById('balance').style.display = 'block';
       
       
    } else {
      
        document.getElementById('loginButton').style.display = 'block';
         document.getElementById('loggedInIcon').style.display = 'none';
         document.getElementById('welcome').style.display = 'none';
         document.getElementById('balance').style.display = 'none';
    }
}

function loginButtonDisplayProcess() {
    window.onload = function() {
        displayLoginStatus();
    };

    document.getElementById('loginButton').onclick = function() {
      
        displayLoginStatus();
    };

    document.getElementById('loggedInIcon').onclick = function() {
        document.getElementById('popup').style.display = 'block';
    };

    document.getElementById('logoutButton').onclick = function() {              
        displayLoginStatus();
        document.getElementById('popup').style.display = 'none';
    };
}