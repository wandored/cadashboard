import json
import csv
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


def potato_sales(start):
    df_pot = pd.DataFrame()
    with open("/usr/local/share/potatochart.csv") as f:
        times = csv.reader(f)
        next(times)
        for t in times:
            url_filter = "$filter=date ge {}T{}Z and date le {}T{}Z".format(start, t[2], start, t[3])
            query = "$select=menuitem,date,quantity,location&{}".format(url_filter)
            url = "{}/SalesDetail?{}".format(Config.SRVC_ROOT, query)
            rqst = make_HTTP_request(url)
            df = make_dataframe(rqst)
            if df.empty:
                continue

            cur.execute(rest_query)
            data = cur.fetchall()
            restaurants = pd.DataFrame.from_records(data, columns=["id", "location", "name"])
            restaurants["location"] = restaurants["location"].astype("category")
            df = restaurants.merge(df, on="location")
            if df.empty:
                if df_pot.empty:
                    continue
                df_pot.loc[t[0]] = [0]
                continue
            df = df.drop(columns=["location"])
            df = df.copy()
            df.loc[:, "menuitem"] = df["menuitem"].str.replace(r"CHOPHOUSE - NOLA", "CHOPHOUSE-NOLA", regex=True)
            df.loc[:, "menuitem"] = df["menuitem"].str.replace(r"CAFÉ", "CAFE", regex=True)
            df.loc[:, "menuitem"] = df["menuitem"].str.replace(r"^(?:.*?( -)){2}", "-", regex=True)
            df.loc[:, "menuitem"] = df["menuitem"].str.strip()
            dafilter = df["menuitem"].str.contains("VOID")
            df = df[~dafilter]
            df[["x", "menuitem"]] = df["menuitem"].str.split(" - ", expand=True)
            pot_list = [
                "BAKED POTATO",
                "BAKED POTATO N/C",
                "POTATO",
                "POT",
                "BAKED POTATO A SIDE",
                "BAKED POTATO SIDE",
                "KID SUB POT",
                "POT-A",
                "S-BAKED POTATO",
                "SUB BAKED POTATO IN KIDS",
                "SUB KID POT",
                "Baked Potato",
                "Baked Potato (After 4:00 PM)",
                "Kid Baked Potato",
                "Kid Baked Potato (After 4:00 PM)",
                "Loaded Baked Potato",
            ]
            df = df[df["menuitem"].isin(pot_list)]
            if df.empty:
                continue
            df.loc[:, "time"] = t[0]
            df.loc[:, "in_time"] = t[1]
            df.loc[:, "out_time"] = t[4]
            df["date"] = convert_datetime_to_string(df["date"])
            df_pot = pd.concat([df_pot, df], ignore_index=True)

        # Write the daily menu items to Menuitems table
        menu_pivot = df_pot.pivot_table(
            index=["date", "name", "time", "in_time", "out_time"],
            values=["quantity"],
            aggfunc=np.sum,
        )
    for index, row in menu_pivot.iterrows():
        cur.execute(
            'DELETE FROM "Potatoes" WHERE date = %s AND name = %s AND time = %s',
            (
                index[0],
                index[1],
                index[2],
            ),
        )
        conn.commit()

    menu_pivot.to_sql("Potatoes", engine, if_exists="append")
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
        yesterday = YSTDAY.strftime("%Y-%m-%d")

        start_time = time.time()
        potato_sales(yesterday)
        end_time = time.time()
        print(f"Potato Sales took {end_time - start_time} seconds")
        current_date = current_date + timedelta(days=1)

    conn.close()
