CREATE TABLE accounts (
account_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
number INT NOT NULL UNIQUE,
name TEXT NOT NULL,
type TEXT NOT NULL UNIQUE
);

CREATE TABLE dates (
date_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
date DATE NOT NULL UNIQUE
);

CREATE TABLE symbols (symbol_id INTEGER PRIMARY KEY AUTOINCREMENT,
symbol TEXT NOT NULL UNIQUE,
name TEXT
);

CREATE TABLE transfers (
transfer_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
account_id INT NOT NULL, 
date_id INT NOT NULL, 
deposit NUMERIC NOT NULL, 
FOREIGN KEY(account_id) REFERENCES accounts(account_id), 
FOREIGN KEY(date_id) REFERENCES dates(date_id) 
);

CREATE TABLE trades (
trade_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
account_id INT NOT NULL, 
symbol_id INT NOT NULL, 
date_id INT NOT NULL, 
quantity INT NOT NULL, 
value NUMERIC NOT NULL, 
FOREIGN KEY(account_id) REFERENCES accounts(account_id), 
FOREIGN KEY(symbol_id) REFERENCES symbols(symbol_id), 
FOREIGN KEY(date_id) REFERENCES dates(date_id) 
);

CREATE TABLE positions (
position_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
account_id INT NOT NULL, 
symbol_id INT NOT NULL, 
date_id INT NOT NULL, 
quantity INT,
value NUMERIC NOT NULL,
FOREIGN KEY(account_id) REFERENCES accounts(account_id), 
FOREIGN KEY(symbol_id) REFERENCES symbols(symbol_id), 
FOREIGN KEY(date_id) REFERENCES dates(date_id)
);

CREATE TABLE exchange_rate (
ex_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
date_id INT NOT NULL, 
cad_usd NUMERIC,
FOREIGN KEY(date_id) REFERENCES dates(date_id)
);
