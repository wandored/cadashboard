# R365 Dashboard

Flask web-app dashboard used to display Odata from R365.

- REQUIRED: Odata credentials

## Local Files

- /etc/config.json - environment data and keys

- /usr/local/share/export.csv - R365 Menu Items download (updated weekly)
- /usr/local/share/Menu Price Analysis.csv - Report updated weekly for recipes costs

- /usr/local/share/labor_categories.json - converts job names to labor categories
- /usr/local/share/major_categories.json - converts menu categories to major categories

## datarefresh.py

- datarefresh updates sales and labor data. It is run from a cron job

## masssalesupdate.py

- updates sales and labor data for the past 7 days

## transactionupdate.py

- transactionupdate updates the daily purchases and inventory data. Periodically run from cron job

## masstransupdate.py

- updates daily transactions for the current week LAST YEAR.

## recipelinks.py

- updates recipe costs (necessary until they add recipes to odata)
