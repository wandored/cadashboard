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

# pd.options.mode.chained_assignment = None


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


def sales_detail(start, end):

    url_filter = "$filter=modifiedOn ge {}T00:00:00Z and modifiedOn le {}T00:00:00Z".format(start, end)
    query = "$select=menuitem,amount,date,quantity,category,location&{}".format(url_filter)
    url = "{}/SalesDetail?{}".format(Config.SRVC_ROOT, query)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    df["location"] = df["location"].astype("category")
    df["amount"] = df["amount"].astype("float16")
    df["quantity"] = df["quantity"].astype("float16")
    if df.empty:
        return

    cur.execute(rest_query)
    data = cur.fetchall()
    restaurants = pd.DataFrame.from_records(data, columns=["id", "location", "name"])
    restaurants["location"] = restaurants["location"].astype("category")
    df = restaurants.merge(df, on="location")
    df = df.drop(columns=["location"])

    with open("/usr/local/share/major_categories.json") as file:
        major_cats = json.load(file)
    sales_categories = pd.DataFrame(list(major_cats.items()), columns=["menu_category", "category"])

    # the data needs to be cleaned before it can be used
    df = df.merge(sales_categories, left_on="category", right_on="menu_category")
    df.loc[:, "menuitem"] = df["menuitem"].str.replace(r"CHOPHOUSE - NOLA", "CHOPHOUSE-NOLA", regex=True)
    df.loc[:, "menuitem"] = df["menuitem"].str.replace(r"CAFÉ", "CAFE", regex=True)
    df.loc[:, "menuitem"] = df["menuitem"].str.replace(r"^(?:.*?( -)){2}", "-", regex=True)
    df.loc[:, "menuitem"] = df["menuitem"].str.strip()
    dafilter = df["menuitem"].str.contains("VOID")
    df = df[~dafilter]
    df[["x", "menuitem"]] = df["menuitem"].str.split(" - ", expand=True)
    df = df.drop(columns=["category_x", "x"])
    df = df.rename(columns={"category_y": "category"})
    df["date"] = convert_datetime_to_string(df["date"])
    menu_pivot = df.pivot_table(
        index=["date", "name", "menuitem", "category", "menu_category"],
        values=["amount", "quantity"],
        aggfunc=np.sum,
    )
    for index, row in menu_pivot.iterrows():
        # delete row if date = index[0] and name = index[1] and daypart = index[2]
        cur.execute(
            'DELETE FROM "Menuitems" WHERE date = %s AND name = %s AND menuitem = %s AND category = %s AND menu_category = %s',
            (index[0], index[1], index[2], index[3], index[4]),
        )
        conn.commit()

    menu_pivot.to_sql("Menuitems", engine, if_exists="append")
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
        start_date = datetime.strptime(args.date, "%Y-%m-%d")
    else:
        start_date = datetime.date(datetime.now())

    TMRDAY = start_date + timedelta(days=1)
    today = start_date.strftime("%Y-%m-%d")
    tonight = TMRDAY.strftime("%Y-%m-%d")
    print(f"Date is {today}")

    start_time = time.time()
    sales_detail(today, tonight)
    end_time = time.time()
    print(f"Sales Detail took {end_time - start_time} seconds")

    conn.close()
