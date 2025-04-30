# Price Breaker

## Clone and prepare

```bash
git clone 
pipenv install
```

## Configure

Save a .env file with the following contents:

```bash
sender="<email address>"
recipient="<email address>"
subject="Idealo Scraper"
password="▉▉▉▉▉▉▉▉▉▉▉▉"
smtp_server="smtp.gmail.com"
smtp_port=465
save_screenshots="False"
```

`sender` will be used together with `password` to login to `smtp_server` on port `smtp_port`.
An email with subject `subject` is sent to `recipient`.
If you want the script to save screenshots of relevant scraping stages, set `save_screenshots` to `"True"`.

## Run

```bash
pipenv run python scraper.py
```

