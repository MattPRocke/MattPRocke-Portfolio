 DROP TABLE IF EXISTS projects;

DROP TABLE IF EXISTS projects;

CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    url TEXT NOT NULL,
    is_public INTEGER DEFAULT 0,
    thumbnail TEXT  -- New column for image filenames
);


DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);
