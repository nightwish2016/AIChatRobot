drop table if exists imageHistory;
drop table if exists chatHistory;
CREATE TABLE imageHistory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sessionid VARCHAR(36) NOT NULL,
    userid TEXT NOT NULL,
    created TEXT NOT NULL,
    revisedPrompt TEXT ,
    urls TEXT NOT NULL,
 Model VARCHAR(50) ,
Prompt TEXT 
);


CREATE TABLE chatHistory(
 Id INTEGER PRIMARY KEY AUTOINCREMENT,
    UserId INTEGER,
       Role TEXT,
    Model VARCHAR(50),
    PromptTokens INTEGER,
    CompletionTokens INTEGER,
    TotalTokens INTEGER,
    Created TIMESTAMP,
    GptContent TEXT,
    Prompt TEXT,
    SessionId VARCHAR(36)
);






ALTER TABLE imageHistory ADD COLUMN quality VARCHAR(32) DEFAULT NULL;
ALTER TABLE imageHistory ADD COLUMN resolution VARCHAR(32) DEFAULT NULL;
ALTER TABLE imageHistory ADD COLUMN chargeStatus INTEGER DEFAULT NULL;
ALTER TABLE chatHistory ADD COLUMN chargeStatus INTEGER DEFAULT NULL;





CREATE TABLE ttsHistory(
 Id INTEGER PRIMARY KEY AUTOINCREMENT,
    UserId INTEGER,      
    Model VARCHAR(50),
    PromptTokens INTEGER,
    CompletionTokens INTEGER,
    TotalTokens INTEGER,
    Created TIMESTAMP,
    chargeStatus
   
);



