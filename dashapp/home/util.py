"""
CentraArchy Dashboard by wandored
"""
import json
import csv
import requests
import pandas as pd
import numpy as np
from dashapp.config import Config
from datetime import datetime
from dashapp.authentication.models import (
    Calendar,
    Sales,
    Labor,
    Restaurants,
    db,
    Menuitems,
    Potatoes,
    Unitsofmeasure,
)
from sqlalchemy import or_, func


pd.option_context(
    "display.max_rows",
    None,
    "display.max_columns",
    None,
    "display.precision",
    3,
)


def refresh_data(start, end):
    """
    When new date submitted, the data for that date will be replaced with new data from R365
    We check if there are infact sales for that day, if not, it resets to yesterday, if
    there are sales, then labor is polled
    """
    # delete current days data from database and replace with fresh data
    Sales.query.filter_by(date=start).delete()
    Labor.query.filter_by(date=start).delete()
    Menuitems.query.filter_by(date=start).delete()
    Potatoes.query.filter_by(date=start).delete()
    db.session.commit()

    # refres the sales data and check to make sure there are sales for that day
    baddates = sales_employee(start, end)
    if baddates == 1:
        return 1

    # refresh labor
    labor_detail(start, end)
    # refresh categories and menuitems
    sales_detail(start, end)
    potato_sales(start)
    return 0


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


def get_lastyear(date):
    target = Calendar.query.filter_by(date=date)
    dt_date = datetime.now

    for i in target:
        lst_year = str(int(i.year) - 1)
        period = i.period
        week = i.week
        day = i.day
        ly_target = Calendar.query.filter_by(
            year=lst_year, period=period, week=week, day=day
        )
        for x in ly_target:
            dt_date = x.date
    return dt_date


def get_period(startdate):
    # startdate = datetime.strptime(date, "%Y-%m-%d")
    start = startdate.strftime("%Y-%m-%d")
    target = Calendar.query.filter_by(date=start)

    return target


def removeSpecial(df):
    """Removes specialty items from the menuitems dataframe"""
    file = open("../../specialty.txt")
    specialty_list = file.read().split("\n")
    file.close
    for item in specialty_list:
        df = df.drop(df[df.menuitem == item].index)
    return df


def sales_employee(start, end):

    url_filter = "$filter=date ge {}T00:00:00Z and date le {}T00:00:00Z".format(
        start, end
    )
    query = "$select=dayPart,netSales,numberofGuests,location&{}".format(url_filter)
    url = "{}/SalesEmployee?{}".format(Config.SRVC_ROOT, query)
    print(url)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    if df.empty:
        return 1

    data = db.session.query(Restaurants).all()
    df_loc = pd.DataFrame(
        [(x.name, x.location) for x in data], columns=["name", "location"]
    )
    df_merge = df_loc.merge(df, on="location")
    df_merge.rename(columns={"netSales": "sales", "dayPart": "daypart"}, inplace=True)

    # pivot data and write to database
    df_pivot = df_merge.pivot_table(
        index=["name", "daypart"], values=["sales"], aggfunc=np.sum
    )
    df_pivot.loc[:, "date"] = start
    df_pivot.to_sql("Sales", con=db.engine, if_exists="append")
    return 0


def labor_detail(start, end):

    url_filter = (
        "$filter=dateWorked ge {}T00:00:00Z and dateWorked le {}T00:00:00Z".format(
            start, end
        )
    )
    query = "$select=jobTitle,hours,total,location_ID&{}".format(url_filter)
    url = "{}/LaborDetail?{}".format(Config.SRVC_ROOT, query)
    print(url)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    if df.empty:
        return 1

    with open("/usr/local/share/labor_categories.json") as labor_file:
        labor_cats = json.load(labor_file)
    df_cats = pd.DataFrame(list(labor_cats.items()), columns=["job", "category"])

    data = db.session.query(Restaurants).all()
    df_loc = pd.DataFrame(
        [(x.name, x.location) for x in data], columns=["name", "location"]
    )
    df_merge = df_loc.merge(df, left_on="location", right_on="location_ID")
    df_merge.rename(columns={"jobTitle": "job", "total": "dollars"}, inplace=True)
    df_merge = df_merge.merge(df_cats, on="job")
    df_pivot = df_merge.pivot_table(
        index=["name", "category", "job"], values=["hours", "dollars"], aggfunc=np.sum
    )
    df_pivot.loc[:, "date"] = start
    df_pivot.to_sql("Labor", con=db.engine, if_exists="append")
    return 0


def sales_detail(start, end):

    url_filter = "$filter=date ge {}T00:00:00Z and date le {}T00:00:00Z".format(
        start, end
    )
    query = "$select=menuitem,amount,date,quantity,category,location&{}".format(
        url_filter
    )
    url = "{}/SalesDetail?{}".format(Config.SRVC_ROOT, query)
    print(url)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    if df.empty:
        return 1

    with open("/usr/local/share/major_categories.json") as file:
        major_cats = json.load(file)
    df_cats = pd.DataFrame(
        list(major_cats.items()), columns=["menu_category", "category"]
    )

    # the data needs to be cleaned before it can be used

    data = db.session.query(Restaurants).all()
    df_loc = pd.DataFrame(
        [(x.name, x.location) for x in data], columns=["name", "location"]
    )
    df_merge = df_loc.merge(df, on="location")
    df_merge.drop(columns=["location"], inplace=True)

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
    #    menuitems = removeSpecial(df_clean)  ### fix the file location before making this active
    # Write the daily menu items to Menuitems table
    menu_pivot = df_clean.pivot_table(
        index=["name", "menuitem", "category", "menu_category"],
        values=["amount", "quantity"],
        aggfunc=np.sum,
    )
    menu_pivot.loc[:, "date"] = start
    menu_pivot.to_sql("Menuitems", con=db.engine, if_exists="append")

    return 0


def get_daily_sales(start, end, store, cat):

    if cat == "GIFT CARDS":
        data = (
            db.session.query(
                Menuitems.date, func.sum(Menuitems.amount).label("total_sales")
            )
            .filter(
                Menuitems.date.between(start, end),
                Menuitems.name == store,
                Menuitems.menuitem.regexp_match("(?i)GIFT CARD*"),
            )
            .group_by(Menuitems.date)
            .all()
        )
    else:
        data = (
            db.session.query(
                Menuitems.date, func.sum(Menuitems.amount).label("total_sales")
            )
            .filter(
                Menuitems.date.between(start, end),
                Menuitems.name == store,
                Menuitems.category == cat,
            )
            .group_by(Menuitems.date)
            .all()
        )
    df = pd.DataFrame([(x.date, x.total_sales) for x in data], columns=["date", cat])
    return df


def get_daily_labor(start, end, store, cat):

    data = (
        db.session.query(
            Labor.date,
            func.sum(Labor.dollars).label("total_dollars"),
        )
        .filter(
            Labor.date.between(start, end), Labor.name == store, Labor.category == cat
        )
        .group_by(Labor.date)
        .all()
    )
    df = pd.DataFrame([(x.date, x.total_dollars) for x in data], columns=["date", cat])
    return df


def potato_sales(start):

    df_pot = pd.DataFrame()
    with open("/usr/local/share/potatochart.csv") as f:
        times = csv.reader(f)
        next(times)
        for i in times:
            url_filter = "$filter=date ge {}T{}Z and date le {}T{}Z".format(
                start, i[2], start, i[3]
            )
            query = "$select=menuitem,date,quantity,location&{}".format(url_filter)
            url = "{}/SalesDetail?{}".format(Config.SRVC_ROOT, query)
            rqst = make_HTTP_request(url)
            df = make_dataframe(rqst)
            if df.empty:
                print("empty dataframe")
                continue

            data = db.session.query(Restaurants).all()
            df_loc = pd.DataFrame(
                [(x.name, x.location) for x in data], columns=["name", "location"]
            )
            df_merge = df_loc.merge(df, on="location")
            if df_merge.empty:
                print(f"no sales at {i[0]}")
                if df_pot.empty:
                    continue
                df_pot.loc[i[0]] = [0]
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
            df.loc[:, "time"] = i[0]
            df.loc[:, "in_time"] = i[1]
            df.loc[:, "out_time"] = i[4]
            df_pot = df_pot.append(df)

        # Write the daily menu items to Menuitems table
        menu_pivot = df_pot.pivot_table(
            index=["time", "name", "in_time", "out_time"],
            values=["quantity"],
            aggfunc=np.sum,
        )
    menu_pivot.loc[:, "date"] = start
    menu_pivot.to_sql("Potatoes", con=db.engine, if_exists="append")

    return 0


def convert_uofm(unit):
    # convert the unit uofm to base quantity
    pack_size = (
        db.session.query(Unitsofmeasure)
        .filter(Unitsofmeasure.name == unit.UofM)
        .first()
    )
    if pack_size:
        return pack_size.base_qty, pack_size.base_uofm
    else:
        return 0, 0
