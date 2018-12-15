CREATE TABLE IF NOT EXISTS mercatool.ratings
(
	season VARCHAR(9) NOT NULL,
	day INTEGER NOT NULL,
	player TEXT NOT NULL,
	position TEXT NOT NULL,
	team TEXT NOT NULL,
	rating INTEGER NOT NULL
);
