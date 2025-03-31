drop table if exists ConsumeTransactionDetail;
drop table if exists ConsumeTransaction;

CREATE TABLE ConsumeTransactionDetail (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  
    userId INTEGER,
    HistoryId INTEGER,
    -- imageHistoryId INTEGER,
    model varchar(50),
    -- priceId INTEGER,
    transactionAmount REAL,
    transactionStatus int,
    Created TIMESTAMP
);


CREATE TABLE ConsumeTransaction (
    id INTEGER PRIMARY KEY,
    userId INTEGER,
    consumeTransactionDetailIds TEXT,
    transactionAmount REAL,
    created DATETIME
);


ALTER TABLE ConsumeTransactionDetail ADD COLUMN consumeTransactionDetailTypekey INTEGER  DEFAULT 1;

