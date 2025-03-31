	 
		function cleanInputPromptText()
        {
        // 清空输入框并保持焦点
                 document.getElementById('prompt').value = '';
                 document.getElementById('prompt').focus();
        }                 
                
        function chatgptisprocessing(processingOutput,historyField)
        {
              // 添加正在处理的提示
              
              processingOutput.className = 'chatgpt-processing';
              processingOutput.textContent = 'ChatGPT is processing';
              historyField.appendChild(processingOutput);
                  // 动态显示处理中的点
             let dots = 0;
             const processingInterval = setInterval(() => {
                 processingOutput.textContent = `ChatGPT is processing${'.'.repeat(dots % 4)}`;
                 dots++;
             }, 500); // 每500毫秒更新一次
             return  processingInterval
             
        }


        function addChatHistory(message,chatgptOutput,historyField)
        {
            
            chatgptOutput.className = 'chatgpt-output';
            console.log(message)
            chatgptOutput.innerText ='ChagGPT: '
            historyField.appendChild(chatgptOutput);


           
        }
        
       

        function responseDisplayByChar(message,chatgptOutput,historyField)
        {
        	 // 逐字显示消息，处理换行
					let index = 0;
					function typeWriter() {
						if (index < message.length) {
							const char = message.charAt(index);
							
							if (char === '\n') {
								chatgptOutput.innerHTML += '<br>';
							}						
							else {
								chatgptOutput.innerHTML += char;
							}							
							index++;
							setTimeout(typeWriter, 30); // 调整速度
							
                historyField.scrollTop = historyField.scrollHeight;
						}
					}
					typeWriter();
        }
            
            
        function sendRequestByEnter(elmentId,keyevent)
        {
             // 添加回车键发送消息的功能
            
                document.getElementById(elmentId).addEventListener(keyevent, function(event) {
                    if (event.key === 'Enter' && !event.shiftKey) {
                        event.preventDefault();  // 阻止默认行为，即不插入换行符
                        sendToChatGPT();
                      }
            });
        }

      
        // function chatgptResponseUpdate(processingOutput,historyField)
        // {
        //     console.log("chatgptResponseUpdate********")
        //     cleanInputPromptText()
        //     chatgptisprocessing(processingOutput,historyField)
        // }
                 
               
         
                 
           
         