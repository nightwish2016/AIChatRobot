// 检查登录状态
async function checkLoginStatus() {
    try {
        const response = await fetch('/check-login');
        const data = await response.json();           

        if (data.logged_in == true) {
            console.log("user already login");
        } else {
            console.log("user doesn't login");
        }
        return data;
    } catch (error) {
        console.error("Error checking login status:", error);
        // 在出错时返回默认的未登录状态
        return { logged_in: false };
    }
}



// 根据登录状态显示登录按钮或已登录图标
async  function                                                                                                                         displayLoginStatus() {
    const dataCheckLogin = await checkLoginStatus(); 
    let loginStatus=dataCheckLogin.logged_in
    // console.log(dataCheckLogin)  
    // console.log(loginStatus)
             if (loginStatus) {
        const loginButton = document.getElementById('loginButton');
        const loggedInIcon = document.getElementById('loggedInIcon');
        const balance = document.getElementById('balance');
        const welcome = document.getElementById('welcome') || document.getElementById('welcome-text');
        
        if (loginButton) loginButton.style.display = 'none';
        if (loggedInIcon) loggedInIcon.style.display = 'inline-block';
        if (balance) balance.style.display = 'block';
        if (welcome) welcome.style.display = 'inline';
       
    } else {
        const loginButton = document.getElementById('loginButton');
        const loggedInIcon = document.getElementById('loggedInIcon');
        const balance = document.getElementById('balance');
        const welcome = document.getElementById('welcome') || document.getElementById('welcome-text');
        
        if (loginButton) loginButton.style.display = 'inline-block';
        if (loggedInIcon) loggedInIcon.style.display = 'none';
        if (welcome) welcome.style.display = 'none';
        if (balance) balance.style.display = 'none';
    }
}

// 检测是否为触摸设备
function isTouchDevice() {
    return (('ontouchstart' in window) ||
            (navigator.maxTouchPoints > 0) ||
            (navigator.msMaxTouchPoints > 0));
}

// 显示弹窗
function showPopup() {
    document.getElementById('popup').style.display = 'block';
}

// 隐藏弹窗
function hidePopup() {
    document.getElementById('popup').style.display = 'none';
}

// 切换弹窗显示状态
function togglePopup() {
    const popup = document.getElementById('popup');
    if (popup.style.display === 'block') {
        hidePopup();
    } else {
        showPopup();
    }
}

function loginButtonDisplayProcess() {
    // 确保在DOM加载完成后初始化
    function initializeLoginProcess() {
        console.log('初始化登录按钮处理流程'); // 调试日志
        displayLoginStatus();
        
        const loginButton = document.getElementById('loginButton');
        const loggedInIcon = document.getElementById('loggedInIcon');
        const popup = document.getElementById('popup');
        const logoutButton = document.getElementById('logoutButton');

        if (!loggedInIcon || !popup) {
            console.error('找不到登录图标或弹窗元素');
            return;
        }

        console.log('设备类型:', isTouchDevice() ? '触摸设备' : '桌面设备'); // 调试日志

        if (loginButton) {
            loginButton.onclick = function() {
                console.log('登录按钮被点击');
                // 跳转到登录页面
                window.location.href = '/loginPage?origin=' + encodeURIComponent(window.location.pathname);
            };
        }

        if (isTouchDevice()) {
            console.log('设置移动端事件监听器'); // 调试日志
            
            // 移动端：使用点击事件
            loggedInIcon.onclick = function(e) {
                console.log('点击登录图标'); // 调试日志
                e.stopPropagation(); // 阻止事件冒泡
                togglePopup();
            };

            // 点击页面其他区域时关闭弹窗
            document.addEventListener('click', function(e) {
                console.log('页面点击事件，目标元素:', e.target); // 调试日志
                if (!popup.contains(e.target) && !loggedInIcon.contains(e.target)) {
                    console.log('点击外部区域，隐藏弹窗'); // 调试日志
                    hidePopup();
                }
            });

            // 防止在弹窗内点击时关闭弹窗
            popup.onclick = function(e) {
                console.log('点击弹窗内部'); // 调试日志
                e.stopPropagation();
            };
        } else {
            console.log('设置桌面端事件监听器'); // 调试日志
            
            // 桌面端：保持原有的悬停行为
            loggedInIcon.onmouseenter = function() {
                showPopup();
            };

            popup.onmouseleave = function() {
                hidePopup();
            };
        }

        if (logoutButton) {
            logoutButton.onclick = function() {
                displayLoginStatus();
                hidePopup();
            };
        }
    }

    // 使用多种方式确保初始化函数被调用
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeLoginProcess);
    } else {
        // DOM已经加载完成
        initializeLoginProcess();
    }
}

// 全局点击处理器 - 简化版本
(function() {
    'use strict';
    
    let isInitialized = false;
    
    function setupGlobalClickHandler() {
        if (isInitialized) return;
        isInitialized = true;
        
        console.log('设置全局点击处理器');
        
        // 全局点击事件处理
        document.addEventListener('click', function(e) {
            const popup = document.getElementById('popup');
            const loggedInIcon = document.getElementById('loggedInIcon');
            
            if (!popup || !loggedInIcon) return;
            
            // 检查是否为触摸设备
            const isMobile = (('ontouchstart' in window) || (navigator.maxTouchPoints > 0));
            
            if (isMobile) {
                // 如果点击的是登录图标
                if (loggedInIcon.contains(e.target)) {
                    e.stopPropagation();
                    if (popup.style.display === 'block') {
                        popup.style.display = 'none';
                        console.log('隐藏弹窗');
                    } else {
                        popup.style.display = 'block';
                        console.log('显示弹窗');
                    }
                    return;
                }
                
                // 如果点击的是弹窗内部，不做任何操作
                if (popup.contains(e.target)) {
                    e.stopPropagation();
                    return;
                }
                
                // 其他任何地方的点击都隐藏弹窗
                if (popup.style.display === 'block') {
                    popup.style.display = 'none';
                    console.log('点击外部区域，隐藏弹窗');
                }
            }
        }, true); // 使用捕获阶段确保优先执行
    }
    
    // 多种方式确保初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupGlobalClickHandler);
    } else {
        setTimeout(setupGlobalClickHandler, 100);
    }
    
    window.addEventListener('load', setupGlobalClickHandler);
})();