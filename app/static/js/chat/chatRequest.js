async function ChatReuqest(prompt,model,guid) {                		
    console.log("******")
    cleanInputPromptText()
    console.log(guid)
    //user input
    const userInput = document.createElement('div');
    userInput.className = 'user-input';
    
    if( prompt.indexOf("\n")!== -1)
    {
        userInput.innerText = 'You: \n' + prompt
        // userInput.innerHTML=userInput.innerHTML.replace(/\n/g, '<br>');
    }
    else{
        userInput.innerText = 'You: ' + prompt
    }
    historyField.appendChild(userInput);
    historyField.scrollTop = historyField.scrollHeight;

    
    //add  chatgpt response  to history div if user didn't login
    const dataCheckLogin = await checkLoginStatus();     
    let loginStatus=dataCheckLogin.logged_in
    // console.log(dataCheckLogin)  
    // console.log("***"+loginStatus)   
    if(loginStatus==false)
    {                
        console.log('Is logged in:', loginStatus);    
        const chatgptOutput = document.createElement('div');
        chatgptOutput.className = 'chatgpt-output';        
        chatgptOutput.innerHTML ='Chatgpt:Please login first';
        historyField.appendChild(chatgptOutput);
        return ;

    }

    //chatgpt response
    const processingOutput = document.createElement('div');       
    let processingInterval=chatgptisprocessing(processingOutput,historyField)
    historyField.scrollTop = historyField.scrollHeight;

    //fetch data
    let error=""
    let response=""
    

                  
    const chatgptOutput = document.createElement('div');    
    chatgptOutput.className = 'chatgpt-output';
    // console.log(message)
    //chatgptOutput.innerText +='ChagGPT: '
    
    // let s="ChagGPT: "
    let s=" "
    const url = '/chatStream';
    
    // 获取当前选中的附件ID列表
    const attachmentIds = typeof getSelectedAttachmentIds === 'function' ? getSelectedAttachmentIds() : [];
    console.log('发送聊天请求，附件IDs:', attachmentIds);
    
    const data = {
        model: model,  // 这里设置 model 参数
        prompt: prompt,
        conversationid: guid,   // 这里设置 prompt 参数
        attachment_ids: attachmentIds  // 新增：附件ID列表
    };
    
    console.log('发送的数据:', data);
    
    // 不预先添加响应元素，等有内容时再添加
    
    fetch(url,{
        method: 'POST',           // 指定使用 POST 方法
        headers: {
            'Content-Type': 'application/json'  // 设置请求头，说明请求体是 JSON 格式
        },
        body: JSON.stringify(data)  // 将 JavaScript 对象转换成 JSON 字符串
    }).then(response => {
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let processingCleared = false; // 标记是否已清理处理中的提示
        let responseBoxAdded = false; // 标记响应框是否已添加到DOM
     
        function processStream() {
            reader.read().then(({ done, value }) => {
                if (done) {
                    console.log('Stream complete');
                    return;
                }
                const text = decoder.decode(value, { stream: true });
                // console.log('Received text', text);
                // 更新页面内容
                //container.textContent += text;

                // 只在第一次接收到数据时清理处理中的提示并添加响应框
                if (!processingCleared) {
                    clearInterval(processingInterval); // 停止显示处理中的点
                    processingOutput.remove(); // 删除处理中的提示
                    processingCleared = true;
                }

                s+=text;
               // console.log('Received s', s);
                //chatgptOutput.innerHTML+=text;
                //document.getElementById('prompt').value;
                let text2=marked.parse(s);
                //console.log('Received text2:', text2)

                // 只在第一次有实际内容时添加响应框到DOM
                if (!responseBoxAdded && s.trim().length > 0) {
                    historyField.appendChild(chatgptOutput);
                    responseBoxAdded = true;
                }

                // 只更新内容，不重复添加到DOM
                chatgptOutput.innerHTML=text2
                hljs.highlightAll();
                
                // 确保页面滚动到底部
                historyField.scrollTop = historyField.scrollHeight;
                
                // 递归调用以继续读取数据
                processStream();
            }).catch(error => {
                console.error('Error reading stream', error);
            });
        }

        processStream();
    }).catch(error => {
        console.error('Fetch error:', error);
    });
    // let text3=marked.parse(s);
    // console.log('Received s3:', s)
    // console.log('Received text3:', text3)
    // chatgptOutput.innerHTML=text3
    // add chat result to history div
    // const result = await response.json();  							
   /*
    if(response.status!=200)
    {

        message = response.status+"-"+result.error+":"+result.message
        addChatHistory(message,chatgptOutput,historyField)
        responseDisplayByChar(message,chatgptOutput,historyField)
        // console.log(result)
        // chatgptOutput.innerHtml ='ChagGPT: '
        historyField.appendChild(chatgptOutput);

        return ;
    }*/

    //message = result.message
    // addChatHistory(message,chatgptOutput,historyField)
  

    // responseDisplayByChar(message,chatgptOutput,historyField)

}


function sendToChatGPT()
{
    
    let guid=document.getElementById("guidDisplay").textContent
    console.log("guid:"+guid)
    const prompt = document.getElementById('prompt').value;           
    const model = document.getElementById('model-select').value;
    ChatReuqest(prompt,model,guid)
}