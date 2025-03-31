
drop table if exists emailFailure;
CREATE TABLE emailFailure(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
   email varchar(50),
type integer,
error varchar(100)
);