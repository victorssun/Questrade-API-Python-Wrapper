# Questrade API Wrapper
Python wrapper for Questrade API. Requires Questrade refresh token

Save token as .JSON file
```
{
    "refresh_token": "REFRSH_TOKEN_HERE",
    "expiry_date": "YYYY-MM-DD"
}
```

Example of generating instance of QT wrapper:
```
from src import questrade 

token = questrade.QuestradeToken(<FILEPATH TO TOKEN .JSON>, <ACCOUNT_INDEX>)

token.get_accounts()  # list of dict of accounts data
```

Example of generating instance of QT accounts wrapper:
```
from src import accounts 

token = accounts.QuestradeAccount(<FILEPATH TO TOKEN .JSON>, <ACCOUNT_INDEX>)

token.positions()  # dataframe of current positions portfolio
```

Example of grabbing `account_index`
```
from src import accounts

token = accounts.QuestradeAccount(<FILEPATH TO TOKEN .JSON>)
token.get_accounts()  # then identify specific index of wanted account
token.initialize(<ACCOUNT_INDEX>)  # reinitialize with correct account
```

## Procedure to update questrade sqlite db
`questrade.db` must exist
1. Execute `uses/questrade_db/questrade_script.py`

## Procedure to generating questrade sqlite db from old account .pkl file
`account_data.pickle` must exist
1. Create new sqlite database file
2. Execute `generate_questrade_db_sql.sql`
3. Execute `account2questrade.py`

## Procedure to update account .pkl and sqlite db [DEFUNC]
`account_data.pickle` must exist
1. Execute `account_daily.py`
2. Execute `account_daily_sql.py`

## TODO
- Separate `questrade_db` dependency on accounts
- Test queries when multiple account exist