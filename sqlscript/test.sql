select u.id,u.user,u.email,c.balance from user as u
join Customer  as c on c.userid=u.id;


select u.user,u.email,ctd.model,ctd.transactionAmount,ctd.transactionStatus,ctd.consumeTransactionDetailTypekey,
datetime(ctd.created, 'unixepoch')
from ConsumeTransactionDetail as ctd
join user as u on u.id=ctd.userId
where ctd.transactionStatus=1;

select u.user,ct.transactionAmount,datetime(ct.created, 'unixepoch') from ConsumeTransaction as ct
join user as u on u.id=ct.userId;


select  u.user,u.email,ch.model,ch.totaltokens,
datetime(ch.created,'unixepoch') from chatHistory as ch
join user as u on u.id=ch.userId
where chargestatus=1;





select  u.user,u.email,ch.model,ch.quality,ch.resolution,
datetime(ch.created,'unixepoch') from imageHistory as ch
join user as u on u.id=ch.userId
where ch.chargestatus=1;


