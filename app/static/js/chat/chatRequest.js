let currentSessionId = null;
const sessionTitleState = new Map();
let titleGenerationEventsBound = false;

function getSessionTitleState(sessionId) {
    if (!sessionId) {
        return null;
    }
    if (!sessionTitleState.has(sessionId)) {
        sessionTitleState.set(sessionId, {
            userMessageCount: 0,
            idleTimerId: null,
            requestInFlight: false,
            titleGenerated: false,
        });
    }
    return sessionTitleState.get(sessionId);
}

function clearTitleGenerationTimer(state) {
    if (state && state.idleTimerId) {
        clearTimeout(state.idleTimerId);
        state.idleTimerId = null;
    }
}

function maybeScheduleSessionTitleGeneration(sessionId) {
    const state = getSessionTitleState(sessionId);
    if (!state) {
        return;
    }
    if (state.titleGenerated || state.requestInFlight) {
        return;
    }
    if (state.userMessageCount < 2) {
        clearTitleGenerationTimer(state);
        return;
    }
    clearTitleGenerationTimer(state);
    state.idleTimerId = setTimeout(() => {
        triggerSessionTitleGeneration(sessionId, 'idle_timeout');
    }, 10000);
}

async function triggerSessionTitleGeneration(sessionId, reason = 'manual') {
    const state = getSessionTitleState(sessionId);
    if (!state) {
        return;
    }
    if (state.titleGenerated || state.requestInFlight || state.userMessageCount < 2) {
        return;
    }
    state.requestInFlight = true;
    clearTitleGenerationTimer(state);
    try {
        const response = await fetch(`/api/v1/chat/sessions/${encodeURIComponent(sessionId)}/title`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reason }),
        });
        const data = await response.json().catch(() => null);
        if (!response.ok) {
            if (data && data.reason === 'session_not_found') {
                state.titleGenerated = true;
            }
            return;
        }
        if (!data) {
            return;
        }
        const alreadyExists = data.reason === 'already_exists';
        if (data.generated || alreadyExists) {
            state.titleGenerated = true;
            if (data.generated) {
                refreshConversationListForCurrentSession();
            }
        }
    } catch (error) {
        console.error('Failed to generate session title:', error);
    } finally {
        state.requestInFlight = false;
        if (!state.titleGenerated && state.userMessageCount >= 2) {
            maybeScheduleSessionTitleGeneration(sessionId);
        }
    }
}

function handleUserMessageForTitle(sessionId) {
    const state = getSessionTitleState(sessionId);
    if (!state) {
        return;
    }
    state.userMessageCount += 1;
    maybeScheduleSessionTitleGeneration(sessionId);
}

function syncSessionTitleStateFromHistory(sessionId, messages = []) {
    const state = getSessionTitleState(sessionId);
    if (!state) {
        return;
    }
    const userMessages = messages.filter(
        (item) => (item.role || '').toLowerCase() === 'user' && (item.content || '').trim().length > 0,
    );
    state.userMessageCount = userMessages.length;
    if (state.userMessageCount < 2) {
        clearTitleGenerationTimer(state);
    }
}

function ensureTitleGenerationEventBindings() {
    if (titleGenerationEventsBound) {
        return;
    }
    document.addEventListener('visibilitychange', () => {
        if (document.hidden && currentSessionId) {
            triggerSessionTitleGeneration(currentSessionId, 'visibility_change');
        }
    });
    window.addEventListener('blur', () => {
        if (currentSessionId) {
            triggerSessionTitleGeneration(currentSessionId, 'window_blur');
        }
    });
    titleGenerationEventsBound = true;
}

function getHistoryContainer() {
    return document.getElementById('history');
}

function updateGuidDisplay(sessionId) {
    const guidDisplay = document.getElementById('guidDisplay');
    if (guidDisplay) {
        guidDisplay.textContent = sessionId || '';
    }
}

function highlightActiveConversation(sessionId) {
    const conversationItems = document.querySelectorAll('.conversation-item');
    conversationItems.forEach((item) => {
        if (sessionId && item.dataset.sessionId === sessionId) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
}

function setCurrentSessionId(sessionId) {
    currentSessionId = sessionId || null;
    if (currentSessionId) {
        getSessionTitleState(currentSessionId);
    }
    updateGuidDisplay(currentSessionId);
    highlightActiveConversation(currentSessionId);
}

function ensureSessionId() {
    if (currentSessionId) {
        return currentSessionId;
    }
    const guidDisplay = document.getElementById('guidDisplay');
    if (guidDisplay && guidDisplay.textContent.trim().length > 0) {
        currentSessionId = guidDisplay.textContent.trim();
        return currentSessionId;
    }
    const guid = typeof generateGUID === 'function'
        ? generateGUID()
        : Math.random().toString(36).slice(2);
    setCurrentSessionId(guid);
    return guid;
}

function appendHistoryMessage(role, content) {
    const historyContainer = getHistoryContainer();
    if (!historyContainer) {
        return;
    }

    const normalizedRole = (role || '').toLowerCase();
    const safeContent = content || '';
    const messageElement = document.createElement('div');

    if (normalizedRole === 'user') {
        messageElement.className = 'user-input';
        if (safeContent.indexOf('\n') !== -1) {
            messageElement.innerText = 'You: \n' + safeContent;
        } else {
            messageElement.innerText = 'You: ' + safeContent;
        }
    } else {
        messageElement.className = 'chatgpt-output';
        messageElement.innerHTML = marked.parse(safeContent);
    }

    historyContainer.appendChild(messageElement);
}

function clearHistoryContainer() {
    const historyContainer = getHistoryContainer();
    if (historyContainer) {
        historyContainer.innerHTML = '';
    }
}

function formatSessionTime(isoString) {
    if (!isoString) {
        return '';
    }
    try {
        const date = new Date(isoString);
        if (Number.isNaN(date.getTime())) {
            return '';
        }
        return date.toLocaleString();
    } catch (error) {
        return '';
    }
}

function buildConversationItem(session) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'conversation-item';
    button.dataset.sessionId = session.session_id;

    const titleDiv = document.createElement('div');
    titleDiv.className = 'conversation-title';
    titleDiv.textContent = session.title || '新的对话';

    const timeDiv = document.createElement('div');
    timeDiv.className = 'conversation-time';
    timeDiv.textContent = formatSessionTime(session.last_created_iso);

    button.appendChild(titleDiv);
    button.appendChild(timeDiv);

    button.addEventListener('click', async () => {
        const previousSessionId = currentSessionId;
        await loadChatHistory(session.session_id);
        if (previousSessionId && previousSessionId !== session.session_id) {
            triggerSessionTitleGeneration(previousSessionId, 'conversation_switch');
        }
        highlightActiveConversation(session.session_id);
    });

    return button;
}

async function loadChatHistory(sessionId = null) {
    const historyContainer = getHistoryContainer();
    if (!historyContainer) {
        return;
    }

    const params = new URLSearchParams();
    params.set('limit', '100');
    if (sessionId) {
        params.set('session_id', sessionId);
    }

    try {
        const response = await fetch(`/api/v1/chat/history?${params.toString()}`);
        if (!response.ok) {
            if (response.status !== 401 && response.status !== 404) {
                console.warn('Failed to load chat history', response.status);
            }
            return;
        }

        const data = await response.json();
        if (!data || !Array.isArray(data.messages)) {
            return;
        }

        const resolvedSessionId = data.session_id || sessionId || ensureSessionId();
        setCurrentSessionId(resolvedSessionId);
        syncSessionTitleStateFromHistory(resolvedSessionId, data.messages);

        historyContainer.innerHTML = '';
        data.messages.forEach((item) => {
            appendHistoryMessage(item.role, item.content);
        });

        hljs.highlightAll();
        historyContainer.scrollTop = historyContainer.scrollHeight;
    } catch (error) {
        console.error('Failed to load chat history:', error);
    }
}

async function loadConversationSessions(options = {}) {
    const listContainer = document.getElementById('conversation-list');
    const emptyState = document.getElementById('conversation-empty');
    if (!listContainer) {
        return;
    }

    try {
        const response = await fetch('/api/v1/chat/sessions?limit=50');
        if (!response.ok) {
            if (response.status === 401) {
                listContainer.innerHTML = '';
                if (emptyState) {
                    emptyState.style.display = 'block';
                }
            } else {
                console.warn('Failed to load conversation list', response.status);
            }
            return;
        }

        const data = await response.json();
        const sessions = Array.isArray(data.sessions) ? data.sessions : [];

        listContainer.innerHTML = '';
        if (sessions.length === 0) {
            if (emptyState) {
                emptyState.style.display = 'block';
            }
            if (!options.skipHistoryLoad) {
                startNewConversation();
            }
            return;
        }

        if (emptyState) {
            emptyState.style.display = 'none';
        }

        sessions.forEach((session) => {
            const item = buildConversationItem(session);
            listContainer.appendChild(item);
        });

        if (options.skipHistoryLoad) {
            highlightActiveConversation(currentSessionId);
            return;
        }

        let targetSessionId = options.selectSession || currentSessionId;
        if (!targetSessionId && options.selectLatest !== false) {
            targetSessionId = sessions[0]?.session_id;
        }

        if (targetSessionId) {
            await loadChatHistory(targetSessionId);
        } else if (sessions.length > 0) {
            await loadChatHistory(sessions[0].session_id);
        }
    } catch (error) {
        console.error('Failed to load conversation list:', error);
    }
}

function startNewConversation() {
    const historyContainer = getHistoryContainer();
    if (historyContainer) {
        historyContainer.innerHTML = '';
    }

    const guid = typeof generateGUID === 'function'
        ? generateGUID()
        : Math.random().toString(36).slice(2);
    setCurrentSessionId(guid);

    const listContainer = document.getElementById('conversation-list');
    if (listContainer) {
        listContainer.querySelectorAll('.conversation-item').forEach((item) => item.classList.remove('active'));
    }
    const emptyState = document.getElementById('conversation-empty');
    if (emptyState) {
        const hasSessions = listContainer && listContainer.childElementCount > 0;
        emptyState.style.display = hasSessions ? 'none' : 'block';
    }

    return guid;
}

function refreshConversationListForCurrentSession() {
    loadConversationSessions({
        selectSession: currentSessionId,
        skipHistoryLoad: true,
    });
}

document.addEventListener('DOMContentLoaded', async () => {
    ensureTitleGenerationEventBindings();
    const newChatButton = document.getElementById('new-chat-button');
    if (newChatButton) {
        newChatButton.addEventListener('click', () => {
            const previousSessionId = currentSessionId;
            startNewConversation();
            if (previousSessionId) {
                triggerSessionTitleGeneration(previousSessionId, 'new_chat');
            }
            highlightActiveConversation(null);
        });
    }

    startNewConversation();

    try {
        const loginInfo = await checkLoginStatus();
        if (loginInfo && loginInfo.logged_in) {
            await loadConversationSessions({ selectLatest: false, skipHistoryLoad: true });
        }
    } catch (error) {
        console.error('Chat history initialization failed:', error);
    }
});

async function ChatReuqest(prompt,model,guid) {                		
    console.log("******")
    cleanInputPromptText()

    const sessionId = ensureSessionId();
    setCurrentSessionId(sessionId);
    console.log(sessionId)

    appendHistoryMessage('user', prompt);
    handleUserMessageForTitle(sessionId);
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
        conversationid: sessionId,   // 这里设置 prompt 参数
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
                    refreshConversationListForCurrentSession();
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
        refreshConversationListForCurrentSession();
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
