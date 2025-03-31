drop table if exists barCode;
CREATE TABLE barCode (
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    userid INTEGER,   
    barcode TEXT NOT NULL,
    statuskey int,
    loadAmount REAL,
    created TIMESTAMP
);


select * from barCode;


drop table if exists fundTransaction;
CREATE TABLE fundTransaction(
 Id INTEGER PRIMARY KEY AUTOINCREMENT,
    userId INTEGER,
    out_trade_no TEXT,
    buyer_logon_id  VARCHAR(100) ,
    trade_status TVARCHAR(30),
    total_amount REAL,
    send_pay_date DATETIME,
    trade_no TEXT,
    created TIMESTAMP
);

select * from fundTransaction;