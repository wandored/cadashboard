"""
Datarefresh imports the previous days data and
uploads it to the local database.  This is run
hourly from a cron job
"""
import json
import csv
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


def removeSpecial(df):
    """Removes specialty items from the menuitems dataframe"""
    file = open("/usr/local/share/specialty.txt")
    specialty_list = file.read().split("\n")
    file.close
    for item in specialty_list:
        df = df.drop(df[df.menuitem == item].index)
    return df


def sales_detail(start, end):

    url_filter = "$filter=date ge {}T00:00:00Z and date le {}T00:00:00Z".format(
        start, end
    )
    query = "$select=menuitem,amount,date,quantity,category,location&{}".format(
        url_filter
    )
    url = "{}/SalesDetail?{}".format(Config.SRVC_ROOT, query)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    if df.empty:
        return

    cur.execute(rest_query)
    data = cur.fetchall()
    df_loc = pd.DataFrame.from_records(data, columns=["id", "location", "name"])
    df_merge = df_loc.merge(df, on="location")
    df_merge.drop(columns=["location"], inplace=True)

    with open("/usr/local/share/major_categories.json") as file:
        major_cats = json.load(file)
    df_cats = pd.DataFrame(
        list(major_cats.items()), columns=["menu_category", "category"]
    )

    # the data needs to be cleaned before it can be used
    df_menu = df_merge.merge(df_cats, left_on="category", right_on="menu_category")
    df_menu.loc[:, "menuitem"] = df_menu["menuitem"].str.replace(
        r"CHOPHOUSE - NOLA", "CHOPHOUSE-NOLA", regex=True
    )
    df_menu.loc[:, "menuitem"] = df_menu["menuitem"].str.replace(
        r"CAFÉ", "CAFE", regex=True
    )
    df_menu.loc[:, "menuitem"] = df_menu["menuitem"].str.replace(
        r"^(?:.*?( -)){2}", "-", regex=True
    )
    df_menu.loc[:, "menuitem"] = df_menu["menuitem"].str.strip()
    dafilter = df_menu["menuitem"].str.contains("VOID")
    df_clean = df_menu[~dafilter]
    df_clean[["x", "menuitem"]] = df_clean["menuitem"].str.split(" - ", expand=True)
    df_clean.drop(columns=["category_x", "x"], inplace=True)
    df_clean.rename(columns={"category_y": "category"}, inplace=True)
    # menuitems = removeSpecial(df_clean)
    # Write the daily menu items to Menuitems table
    menu_pivot = df_clean.pivot_table(
        index=["name", "menuitem", "category", "menu_category"],
        values=["amount", "quantity"],
        aggfunc=np.sum,
    )
    menu_pivot.loc[:, "date"] = start
    menu_pivot.to_sql("Menuitems", engine, if_exists="append")
    conn.commit()

    return


def sales_employee(start, end):

    url_filter = "$filter=date ge {}T00:00:00Z and date le {}T00:00:00Z".format(
        start, end
    )
    query = "$select=dayPart,netSales,numberofGuests,location&{}".format(url_filter)
    url = "{}/SalesEmployee?{}".format(Config.SRVC_ROOT, query)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    if df.empty:
        return
    cur.execute(rest_query)
    data = cur.fetchall()
    df_loc = pd.DataFrame.from_records(data, columns=["id", "location", "name"])
    df_merge = df_loc.merge(df, on="location")
    df_merge.rename(
        columns={"netSales": "sales", "numberofGuests": "guests", "dayPart": "daypart"},
        inplace=True,
    )

    # pivot data and write to database
    df_pivot = df_merge.pivot_table(
        index=["name", "daypart"], values=["sales", "guests"], aggfunc=np.sum
    )
    df_pivot.loc[:, "date"] = start
    df_pivot.to_sql("Sales", engine, if_exists="append")
    conn.commit()

    return


def labor_datail(start, end):

    url_filter = (
        "$filter=dateWorked ge {}T00:00:00Z and dateWorked le {}T00:00:00Z".format(
            start, end
        )
    )
    query = "$select=jobTitle,hours,total,location_ID&{}".format(url_filter)
    url = "{}/LaborDetail?{}".format(Config.SRVC_ROOT, query)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    if df.empty:
        return

    with open("/usr/local/share/labor_categories.json") as labor_file:
        labor_cats = json.load(labor_file)
    df_cats = pd.DataFrame(list(labor_cats.items()), columns=["job", "category"])

    cur.execute(rest_query)
    data = cur.fetchall()
    df_location = pd.DataFrame.from_records(data, columns=["id", "location", "name"])
    df_merge = df_location.merge(df, left_on="location", right_on="location_ID")
    df_merge.rename(columns={"jobTitle": "job", "total": "dollars"}, inplace=True)
    df_merge = df_merge.merge(df_cats, on="job")

    # pivot data and write to database
    df_pivot = df_merge.pivot_table(
        index=["name", "category", "job"], values=["hours", "dollars"], aggfunc=np.sum
    )
    df_pivot.loc[:, "date"] = start
    df_pivot.to_sql("Labor", engine, if_exists="append")
    conn.commit()

    return


def potato_sales(start):

    df_pot = pd.DataFrame()
    with open("/usr/local/share/potatochart.csv") as f:
        times = csv.reader(f)
        next(times)
        for t in times:
            url_filter = "$filter=date ge {}T{}Z and date le {}T{}Z".format(
                start, t[2], start, t[3]
            )
            query = "$select=menuitem,date,quantity,location&{}".format(url_filter)
            url = "{}/SalesDetail?{}".format(Config.SRVC_ROOT, query)
            rqst = make_HTTP_request(url)
            df = make_dataframe(rqst)
            if df.empty:
                continue

            cur.execute(rest_query)
            data = cur.fetchall()
            df_loc = pd.DataFrame.from_records(data, columns=["id", "location", "name"])
            df_merge = df_loc.merge(df, on="location")
            if df_merge.empty:
                if df_pot.empty:
                    continue
                df_pot.loc[t[0]] = [0]
                continue
            df_merge.drop(columns=["location"], inplace=True)
            df_menu = df_merge
            df_menu.loc[:, "menuitem"] = df_menu["menuitem"].str.replace(
                r"CHOPHOUSE - NOLA", "CHOPHOUSE-NOLA", regex=True
            )
            df_menu.loc[:, "menuitem"] = df_menu["menuitem"].str.replace(
                r"CAFÉ", "CAFE", regex=True
            )
            df_menu.loc[:, "menuitem"] = df_menu["menuitem"].str.replace(
                r"^(?:.*?( -)){2}", "-", regex=True
            )
            df_menu.loc[:, "menuitem"] = df_menu["menuitem"].str.strip()
            dafilter = df_menu["menuitem"].str.contains("VOID")
            df_clean = df_menu[~dafilter]
            df_clean[["x", "menuitem"]] = df_clean["menuitem"].str.split(
                " - ", expand=True
            )
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
            ]
            df = df_clean[df_clean["menuitem"].isin(pot_list)]
            if df.empty:
                continue
            df.loc[:, "time"] = t[0]
            df.loc[:, "in_time"] = t[1]
            df.loc[:, "out_time"] = t[4]
            df_pot = df_pot.append(df)

        # Write the daily menu items to Menuitems table
        menu_pivot = df_pot.pivot_table(
            index=["time", "name", "in_time", "out_time"],
            values=["quantity"],
            aggfunc=np.sum,
        )
    menu_pivot.loc[:, "date"] = start
    menu_pivot.to_sql("Potatoes", engine, if_exists="append")
    conn.commit()

    return


def sales_payments(start, end):

    url_filter = "$filter=date ge {}T00:00:00Z and date le {}T00:00:00Z".format(
        start, end
    )
    query = "$select=amount,date,location,paymenttype&{}".format(url_filter)
    url = "{}/SalesPayment?{}".format(Config.SRVC_ROOT, query)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    if df.empty:
        return
    cur.execute(rest_query)
    data = cur.fetchall()
    df_loc = pd.DataFrame.from_records(
        data, columns=["restaurant_id", "location", "name"]
    )
    df_merge = df_loc.merge(df, on="location")

    # pivot data and write to database
    df_pivot = df_merge.pivot_table(
        index=["restaurant_id", "location", "paymenttype"],
        values="amount",
        aggfunc=np.sum,
    )
    df_pivot.loc[:, "date"] = start
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

    TODAY = datetime.date(datetime.now())
    YSTDAY = TODAY - timedelta(days=1)
    start_date = YSTDAY.strftime("%Y-%m-%d")
    end_date = TODAY.strftime("%Y-%m-%d")

    cur.execute('DELETE FROM "Payments" WHERE date = %s', (start_date,))
    cur.execute('DELETE FROM "Sales" WHERE date = %s', (start_date,))
    cur.execute('DELETE FROM "Labor" WHERE date = %s', (start_date,))
    cur.execute('DELETE FROM "Menuitems" WHERE date = %s', (start_date,))
    cur.execute('DELETE FROM "Potatoes" WHERE date = %s', (start_date,))
    conn.commit()

    sales_payments(start_date, end_date)
    sales_detail(start_date, end_date)
    sales_employee(start_date, end_date)
    labor_datail(start_date, end_date)
    potato_sales(start_date)

    conn.close()
