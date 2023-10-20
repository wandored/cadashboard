"""
Datarefresh imports the previous days data and
uploads it to the local database.  This is run
hourly from a cron job
"""
import json
import argparse
import time
from sqlalchemy.engine.create import create_engine
from datetime import datetime, timedelta
import requests
import pandas as pd
import numpy as np
import psycopg2
from dashapp import Config

pd.options.mode.chained_assignment = None


def make_HTTP_request(url):
    all_records = []
    while True:
        if not url:
            break
        r = requests.get(url, auth=(Config.SRVC_USER, Config.SRVC_PSWRD))
        if r.status_code == 200:
            json_data = json.loads(r.text)
            all_records = all_records + json_data["value"]
            if "@odata.nextLink" in json_data:
                url = json_data["@odata.nextLink"]
            else:
                break
    return all_records


def make_dataframe(sales):
    jStr = json.dumps(sales)
    df = pd.read_json(jStr)
    return df


def convert_datetime_to_string(col):
    col = pd.to_datetime(col).dt.date
    col = col.astype(str)
    return col


def sales_employee(start, end):
    url_filter = "$filter=modifiedOn ge {}T00:00:00Z and modifiedOn le {}T00:00:00Z".format(start, end)
    query = "$select=date,dayPart,netSales,numberofGuests,location&{}".format(url_filter)
    url = "{}/SalesEmployee?{}".format(Config.SRVC_ROOT, query)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    if df.empty:
        return
    cur.execute(rest_query)
    data = cur.fetchall()
    restaurants = pd.DataFrame.from_records(data, columns=["id", "location", "name"])
    df = restaurants.merge(df, on="location")
    df = df.rename(columns={"netSales": "sales", "numberofGuests": "guests", "dayPart": "daypart"})
    df["date"] = convert_datetime_to_string(df["date"])
    df_pivot = df.pivot_table(index=["date", "name", "daypart"], values=["sales", "guests"], aggfunc=np.sum)
    for index, row in df_pivot.iterrows():
        # delete row if date = index[0] and name = index[1] and daypart = index[2]
        cur.execute(
            'DELETE FROM "Sales" WHERE date = %s AND name = %s AND daypart = %s',
            (
                index[0],
                index[1],
                index[2],
            ),
        )
        conn.commit()

    df_pivot.to_sql("Sales", engine, if_exists="append")
    conn.commit()

    return


def labor_datail(start, end):
    url_filter = "$filter=modifiedOn ge {}T00:00:00Z and modifiedOn le {}T00:00:00Z".format(start, end)
    query = "$select=dateWorked,jobTitle,hours,total,location_ID&{}".format(url_filter)
    url = "{}/LaborDetail?{}".format(Config.SRVC_ROOT, query)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    if df.empty:
        return

    with open("/usr/local/share/labor_categories.json") as labor_file:
        labor_cats = json.load(labor_file)
    labor_categories = pd.DataFrame(list(labor_cats.items()), columns=["job", "category"])

    cur.execute(rest_query)
    data = cur.fetchall()
    restaurantsation = pd.DataFrame.from_records(data, columns=["id", "location", "name"])
    df = restaurantsation.merge(df, left_on="location", right_on="location_ID")
    df = df.rename(columns={"jobTitle": "job", "total": "dollars"})
    df = df.merge(labor_categories, on="job")

    df["date"] = convert_datetime_to_string(df["dateWorked"])
    df_pivot = df.pivot_table(
        index=["date", "name", "category", "job"],
        values=["hours", "dollars"],
        aggfunc=np.sum,
    )
    for index, row in df_pivot.iterrows():
        # delete row if date = index[0] and name = index[1] and daypart = index[2]
        cur.execute(
            'DELETE FROM "Labor" WHERE date = %s AND name = %s AND category = %s AND job = %s',
            (
                index[0],
                index[1],
                index[2],
                index[3],
            ),
        )
        conn.commit()

    df_pivot.to_sql("Labor", engine, if_exists="append")
    conn.commit()

    return


def sales_payments(start, end):
    url_filter = "$filter=modifiedOn ge {}T00:00:00Z and modifiedOn le {}T00:00:00Z".format(start, end)
    query = "$select=amount,date,location,paymenttype&{}".format(url_filter)
    url = "{}/SalesPayment?{}".format(Config.SRVC_ROOT, query)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    if df.empty:
        return
    cur.execute(rest_query)
    data = cur.fetchall()
    restaurants = pd.DataFrame.from_records(data, columns=["restaurant_id", "location", "name"])
    df = restaurants.merge(df, on="location")

    df["date"] = convert_datetime_to_string(df["date"])
    df_pivot = df.pivot_table(
        index=["date", "restaurant_id", "location", "paymenttype"],
        values="amount",
        aggfunc=np.sum,
    )
    for index, row in df_pivot.iterrows():
        # delete row if date = index[0] and name = index[1] and daypart = index[2]
        cur.execute(
            'DELETE FROM "Payments" WHERE date = %s AND location = %s AND paymenttype = %s',
            (
                index[0],
                index[2],
                index[3],
            ),
        )
        conn.commit()

    df_pivot.to_sql("Payments", engine, if_exists="append")
    conn.commit()

    return


if __name__ == "__main__":
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    conn = psycopg2.connect(
        host="localhost",
        database="dashboard",
        user=Config.PSYCOPG2_USER,
        password=Config.PSYCOPG2_PASS,
    )
    cur = conn.cursor()
    rest_query = 'select * from "Restaurants"'

    # creat and argument parser object
    parser = argparse.ArgumentParser()

    # check for user provide argument
    parser.add_argument("-d", "--date", help="Date to run the script")
    args = parser.parse_args()

    # if user provide argument use it else use today's date
    if args.date:
        start_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        start_date = datetime.now().date()

    if start_date > datetime.now().date():
        print("Date cannot be in the future")
        exit()

    current_date = start_date
    while current_date <= datetime.now().date():
        YSTDAY = current_date - timedelta(days=1)
        TMRDAY = current_date + timedelta(days=1)
        today = current_date.strftime("%Y-%m-%d")
        tonight = TMRDAY.strftime("%Y-%m-%d")
        yesterday = YSTDAY.strftime("%Y-%m-%d")

        start_time = time.time()
        sales_payments(today, tonight)
        end_time = time.time()
        print(f"Sales Payments took {end_time - start_time} seconds")
        start_time = time.time()
        sales_employee(today, tonight)
        end_time = time.time()
        print(f"Sales Employee took {end_time - start_time} seconds")
        start_time = time.time()
        labor_datail(today, tonight)
        end_time = time.time()
        print(f"Labor Detail took {end_time - start_time} seconds")
        current_date = current_date + timedelta(days=1)

    conn.close()
