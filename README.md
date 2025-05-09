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
product="<product name>"
size="44"
limit=70
url="https://www.idealo.de/preisvergleich/OffersOfProduct/200671888_-elite-flex-corriedale-78803-ccl-grey-skechers.html"
```

`sender` will be used together with `password` to login to `smtp_server` on port `smtp_port`.
An email with subject `subject` is sent to `recipient`.
If you want the script to save screenshots of relevant scraping stages, set `save_screenshots` to `"True"`.

The name of `product` will be used in the mail sent to `recipient`, if the prize drops below `limit`.
`size` is the requested size of the product, e.g. "44" for a pair of shoes.

`url` points to the web page with the overview of the product.

## Run

```bash
pipenv run python scraper.py
```

