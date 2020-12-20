drop database if exists depopscraper;
create database if not exists depopscraper;
use depopscraper;


drop table if exists seen;
CREATE TABLE seen(
    href VARCHAR(200) NOT NULL,
    PRIMARY KEY (href)
);

drop table if exists todaysfinds;
CREATE TABLE todaysfinds(
    href VARCHAR(200) NOT NULL,
	size VARCHAR(50),
	price VARCHAR(50),
	shipping VARCHAR(50),
	description VARCHAR(50),
    category VARCHAR(50),
    dateupdated VARCHAR(50),
    PRIMARY KEY (href),
	FOREIGN KEY (href) REFERENCES seen(href)
);

drop table if exists todaysfindspictures;
CREATE TABLE todaysfindspictures(
    href VARCHAR(200) NOT NULL,
	picture VARCHAR(300) NOT NULL,
    PRIMARY KEY (href, picture),
	FOREIGN KEY (href) REFERENCES todaysfinds(href)
);