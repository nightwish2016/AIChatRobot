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



CREATE TABLE FundTransaction_bank (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    checkout_id VARCHAR(100),
    order_id VARCHAR(100),
    product_id VARCHAR(100),
    merchant_trans_no VARCHAR(100),
    customer_id VARCHAR(100),
    status VARCHAR(20),
    send_pay_date DATETIME,
    amount REAL,
    amount_paid REAL,
    tax_amount REAL,
    trans_type VARCHAR(30),
    channel VARCHAR(20),
    currency VARCHAR(20),
    create_date DATETIME,
    description VARCHAR(100),
    mode VARCHAR(20)
);


select * from fundTransaction;