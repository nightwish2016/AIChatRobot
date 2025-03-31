
function closeLargeImage(largeImageContainer,chatcontainer) {
    largeImageContainer.style.display = 'none';
    
   // document.querySelector('.chat-container').style.width = '70%';
    chatcontainer.style.width = '100%';
}



document.addEventListener('DOMContentLoaded', function() {
    var button = document.getElementById('close-button');
    button.onclick = function() {
     
      closeLargeImage(largeImageContainer,chatcontainer)
    };
  });


  


  

  async function generateImage(prompt,model,pixl) {
    console.log("model",model)
    console.log("pixl",pixl)
    console.log("prompt",prompt)
          
    //user input
    const userInput = document.createElement('div');
    const responseElement = document.getElementById('output');        
    userInput.className = 'user-input';
    userInput.textContent = 'You: ' + prompt;
    historyField.appendChild(userInput);
    historyField.scrollTop = historyField.scrollHeight;

    
//add  chatgpt response  to history div if user didn't login
const dataCheckLogin = await checkLoginStatus();     
let loginStatus=dataCheckLogin.logged_in       
if(loginStatus==false)
{                
console.log('Is logged in:', loginStatus);    
const chatgptOutput = document.createElement('div');
chatgptOutput.className = 'chatgpt-output';        
chatgptOutput.innerHTML ='Chatgpt:Please login first';
historyField.appendChild(chatgptOutput);
return ;

}
// add chat result to history div
const processingOutput = document.createElement('div');   
cleanInputPromptText()
let processingInterval=chatgptisprocessing(processingOutput,historyField)        
    //
    let error=""
    let response=""
     try {
         response = await fetch('/api/v1/image', {
           method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt, model,pixl })
        });						

       
    }
    catch (error) {
     processingOutput.remove();  // 确保即使发生错误也停止动态点
       console.error('Error:', error);
        responseElement.textContent = 'Error calling the API.';
    }

    const result = await response.json();
       
        
        
    
    
         clearInterval(processingInterval); // 停止显示处理中的点
         processingOutput.remove(); // 删除处理中的提示								
        const chatgptOutput = document.createElement('div');
        chatgptOutput.className = 'chatgpt-output';		
        // error handling
        if(response.status!=200)
        {

          message = response.status+"-"+result.error+":"+result.message
          addChatHistory(message,chatgptOutput,historyField)
          responseDisplayByChar(message,chatgptOutput,historyField)
          // console.log(result)
          // chatgptOutput.innerHtml ='ChagGPT: '
          historyField.appendChild(chatgptOutput);

          return ;
        }
        console.log(result)
        var imageUrl = result.url
        console.log("***")
        console.log(imageUrl)
        
         // After text, add an image
        const img = document.createElement('img');
        img.src = imageUrl; // URL of the image
        img.alt = 'Image description';

        img.onclick = function () {
        largeImage.src = imageUrl;       
        largeImageContainer.style.display = 'flex';
        document.querySelector('.chat-container').style.width = '30%';
        };

        chatgptOutput.appendChild(img);								
        historyField.appendChild(chatgptOutput);

}




