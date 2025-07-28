drop table if exists imagePrice;
drop table if exists chatPrice;
CREATE TABLE chatPrice (
    id INTEGER PRIMARY KEY  AUTOINCREMENT,       -- 定义 id 为整数类型的主键，自动增长
    model varchar(32) NOT NULL,          -- 定义 model 为文本类型，不允许为空
    inputPrice REAL,              -- 定义 inputPrice 为实数类型，允许存储小数
    outputPrice REAL              -- 定义 outputPrice 为实数类型，允许存储小数
);

CREATE TABLE imagePrice (
    id INTEGER PRIMARY KEY AUTOINCREMENT,           -- 定义 id 为整数类型的主键，自动增长
    model varchar(32) NOT NULL,                        -- 定义 mode 为文本类型
    inputPrice REAL,              -- 定义 quality 为长度最大为32的字符类型
    outputPrice REAL           -- 定义 resolution 为长度最大为32的字符类型                       -- 定义 price 为实数类型，允许存储小数
);


CREATE TABLE ttsPrice (
  id INTEGER PRIMARY KEY  AUTOINCREMENT,       -- 定义 id 为整数类型的主键，自动增长
    model varchar(32) NOT NULL,          -- 定义 model 为文本类型，不允许为空
    inputPrice REAL,              -- 定义 inputPrice 为实数类型，允许存储小数
    outputPrice REAL                -- 定义 price 为实数类型，允许存储小数
);




insert into chatPrice(model,inputPrice,outputPrice) values('deepseek-chat',0.50/7,1.15);
insert into chatPrice(model,inputPrice,outputPrice) values('gpt-3.5-turbo-0125',0.50,1.50);
insert into chatPrice(model,inputPrice,outputPrice) values('gpt-3.5-turbo-instruct',1.50,2.00);
insert into chatPrice(model,inputPrice,outputPrice) values('gpt-4',30,60);
insert into chatPrice(model,inputPrice,outputPrice) values('gpt-4-32k',60,120);
insert into chatPrice(model,inputPrice,outputPrice) values('gpt-4-turbo-2024-04-09',10,30);
insert into chatPrice(model,inputPrice,outputPrice) values('gpt-4o-2024-05-13',5,15);
insert into chatPrice(model,inputPrice,outputPrice) values('gpt-4o-2024-08-06',2.5,10);
insert into chatPrice(model,inputPrice,outputPrice) values('gpt-4o-mini-2024-07-18',0.15,0.6);

insert into imagePrice(model,quality,resolution,price) values('dall-e-3','Standard','1024x1024',0.04);
insert into imagePrice(model,quality,resolution,price)  values('dall-e-3','Standard','1024x1079',0.08);
insert into imagePrice(model,quality,resolution,price)  values('dall-e-3','Standard','1079x1024',0.08);

insert into imagePrice(model,quality,resolution,price)  values('dall-e-3','HD','1024x1024',0.08);
insert into imagePrice(model,quality,resolution,price)  values('dall-e-3','HD','1024x1079',0.12);
insert into imagePrice(model,quality,resolution,price)  values('dall-e-3','HD','1079x1024',0.12);



insert into imagePrice(model,quality,resolution,price)  values('dall-e-2','Standard','1024x1024',0.02);
insert into imagePrice(model,quality,resolution,price)  values('dall-e-2','Standard','512x512',0.018);
insert into imagePrice(model,quality,resolution,price)  values('dall-e-2','Standard','256x256',0.016);

insert into ttsPrice(model,inputPrice,outputPrice) values('gemini-2.5-flash-preview-tts',0.5,1.110);

select * from  chatPrice;
select * from imagePrice;

select * from ttsPrice;
