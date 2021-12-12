"""
CentraArchy Dashboard by wandored
"""
import json
import requests
import pandas as pd
import numpy as np
from flask import redirect, url_for, flash, session
from dashapp.home import blueprint
from dashapp.config import Config
from datetime import datetime
from sqlalchemy.engine.create import create_engine
from dashapp.authentication.models import Calendar, Sales, Labor, Restaurants, db, Categories, Menuitems


pd.option_context('display.max_rows', None,
                   'display.max_columns', None,
                   'display.precision', 3,
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
        Categories.query.filter_by(date=start).delete()
        Menuitems.query.filter_by(date=start).delete()
        db.session.commit()

        # refres the sales data and check to make sure there are sales for that day
        baddates = sales_employee(start, end)
        if baddates == 1:
            return 1

        # refresh labor
        labor_detail(start, end)
        # refresh categories and menuitems
        sales_detail(start, end)
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
    file = open("/usr/local/share/specialty.txt")
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
    df_merge.rename(
        columns={"netSales": "sales", "dayPart": "daypart"}, inplace=True
    )

    # pivot data and write to database
    df_pivot = df_merge.pivot_table(
        index=["name", "daypart"], values=["sales"], aggfunc=np.sum
    )
    df_pivot["date"] = start
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

    data = db.session.query(Restaurants).all()
    df_loc = pd.DataFrame(
        [(x.name, x.location) for x in data], columns=["name", "location"]
    )
    df_merge = df_loc.merge(df, left_on="location", right_on="location_ID")
    df_merge.rename(columns={"jobTitle": "job", "total": "dollars"}, inplace=True)
    df_pivot = df_merge.pivot_table(
        index=["name", "job"], values=["hours", "dollars"], aggfunc=np.sum
    )
    df_pivot["date"] = start
    df_pivot.to_sql("Labor", con=db.engine, if_exists="append")
    return 0


def sales_detail(start, end):

    url_filter = "$filter=date ge {}T00:00:00Z and date le {}T00:00:00Z".format(
        start, end
    )
    query = "$select=menuitem,amount,date,quantity,category,location&{}".format(url_filter)
    url = "{}/SalesDetail?{}".format(Config.SRVC_ROOT, query)
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
    df_merge.drop(columns=['location'], inplace=True)
#    print(df_merge)

    # Write the daily cateory data to Categories table
    df_cats = df_merge.loc[df_merge['category'].isin(['FOOD', 'BEER', 'WINE', 'LIQUOR', 'GIFT CARDS', 'GIFT CARD', 'G.C.SALES', 'GC SALES'])]
    df_pivot = df_cats.pivot_table(
        index=["name", "category"], values=["amount"], aggfunc=np.sum
    )
    df_pivot["date"] = start
    df_pivot.to_sql("Categories", con=db.engine, if_exists="append")

    # the data needs to be cleaned before it can be used
    df_menu = df_merge.loc[df_merge['category'].isin(['FOOD', 'BEER', 'WINE', 'LIQUOR', 'GIFT CARDS', 'GIFT CARD', 'G.C.SALES', 'GC SALES'])]
    df_menu.loc[:, 'menuitem'] = df_menu['menuitem'].str.replace(r'CHOPHOUSE - NOLA', 'CHOPHOUSE-NOLA', regex=True)
    df_menu.loc[:, 'menuitem'] = df_menu['menuitem'].str.replace(r'CAFÉ', 'CAFE', regex=True)
    df_menu.loc[:, 'menuitem'] = df_menu['menuitem'].str.strip()
    dafilter = df_menu['menuitem'].str.contains('VOID')
    df_clean = df_menu[~dafilter]
    df_clean[['x', 'menuitem']] = df_clean['menuitem'].str.split(' - ', expand=True)
    menuitems = removeSpecial(df_clean)
#    print(df_clean.info())
    # Write the daily menu items to Menuitems table
    menu_pivot = menuitems.pivot_table(
        index=['name', 'menuitem'], values=['amount', 'quantity'], aggfunc=np.sum
    )
    menu_pivot["date"] = start
    menu_pivot.to_sql("Menuitems", con=db.engine, if_exists="append")

    # This prints all the current categories
    df_test = df_merge.pivot_table(
        index=["category"], values=["amount"], aggfunc=np.sum
    )
    df_test["date"] = start
#    print(df_test)

    return 0
