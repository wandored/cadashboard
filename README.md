# R365 Dashboard

Flask web-app dashboard used to display Odata from R365.

* REQUIRED: Odata credentials

## Local Files
* /usr/local/share/labor_categories.json - converts job names to labor categories
* /usr/local/share/major_categories.json - converts menu categories to major categories
* /usr/local/share/uofm.json - converts case sizes to pound

## datarefresh.py
datarefresh updates sales and labor data.  It is run from a cron job

## transactionupdate.py
transactionupdate updates the daily purchases and inventory data.  Periodically run from cron job
