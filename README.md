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
from src import accounts 

token = accounts.QuestradeAccount('refresh_token.json.')  # arg is filepath/name to refresh token data .json file

token.positions()  # dataframe of current positions portfolio
```