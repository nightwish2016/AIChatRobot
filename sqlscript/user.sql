
drop table if exists user;
drop table if exists customer;
CREATE TABLE user(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
   user varchar(50),
email  varchar(50) UNIQUE,
password TEXT,
level INTEGER 

);

CREATE TABLE customer (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  
    userid INTEGER,        
    balance REAL
);


ALTER TABLE user ADD COLUMN confirmationToken VARCHAR(120) DEFAULT NULL;
ALTER TABLE user ADD COLUMN confirmationExpiration datetime DEFAULT NULL;
ALTER TABLE user ADD COLUMN activate INTEGER DEFAULT 0;
ALTER TABLE user ADD COLUMN created datetime DEFAULT NULL;

--ALTER TABLE user DROP COLUMN activate;

select * from user;

select * from user where confirmationToken='hhumucQL4FK2zjNlrI1ccA'; 


select u.id,u.user,u.email,u.activate,u.level,c.balance from user as u
join Customer  as c on c.userid=u.id;
