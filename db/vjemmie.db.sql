BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "pfm_memes" (
	"topic"	TEXT,
	"title"	TEXT,
	"description"	TEXT,
	"content"	TEXT,
	"media_type"	TEXT
);
CREATE TABLE IF NOT EXISTS "gm" (
	"id"	INTEGER,
	"occurences"	INTEGER
);
CREATE TABLE IF NOT EXISTS "tidstyver" (
	"id"	INTEGER UNIQUE,
	"time"	REAL,
	PRIMARY KEY("id")
);
CREATE TABLE IF NOT EXISTS "skribbl" (
	"word"	TEXT,
	"submitterID"	INTEGER,
	"submittedAt"	REAL,
	PRIMARY KEY("word")
);
CREATE TABLE IF NOT EXISTS "groups" (
	"group"	TEXT NOT NULL UNIQUE,
	"submitterID"	INTEGER,
	"submittedAt"	INTEGER,
	PRIMARY KEY("group")
);
CREATE TABLE IF NOT EXISTS "twitter" (
	"username"	TEXT NOT NULL UNIQUE,
	"submitterID"	INTEGER NOT NULL,
	"submittedAt"	INTEGER,
	PRIMARY KEY("username")
);
CREATE TABLE IF NOT EXISTS "tweets" (
	"tweetID"	INTEGER NOT NULL UNIQUE,
	"userID"	INTEGER,
	"username"	TEXT,
	"url"	TEXT,
	"time"	INTEGER,
	"text"	TEXT,
	"replies"	INTEGER,
	"retweets"	INTEGER,
	"likes"	REAL,
	PRIMARY KEY("tweetID"),
	FOREIGN KEY("username") REFERENCES "twitter"("username")
);
CREATE TABLE IF NOT EXISTS "bag" (
	"guild_id"	INTEGER NOT NULL UNIQUE,
	"channel_id"	INTEGER,
	"role_id"	INTEGER,
	PRIMARY KEY("guild_id")
);
COMMIT;
