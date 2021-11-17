'''
CentraArchy Dashboard by wandored
'''
import json
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dashapp import Config, db
from dashapp.authentication.models import Calendar


def query_sales(start, end):

    current_sales = sales_employee(start, end)

    start_ly = get_lastyear(start)
    end_ly = get_lastyear(end)
    lastYear = sales_employee(start_ly, end_ly)

    totals = current_sales.merge(lastYear, how='outer', on='LocationName', sort=True)

    return totals


def query_labor(start, end):

    current_labor = labor_detail(start, end)

    start_ly = get_lastyear(start)
    end_ly = get_lastyear(end)
    lastYear = labor_detail(start_ly, end_ly)

    totals = current_labor.merge(lastYear, how='outer', on='LocationName', sort=True)

    return totals


def make_HTTP_request(url):
    all_records = []
    while True:
        if not url:
            break
        r = requests.get(
            url, auth=(Config.SRVC_USER, Config.SRVC_PSWRD)
        )
        if r.status_code == 200:
            json_data = json.loads(r.text)
            all_records = all_records + json_data['value']
            if '@odata.nextLink' in json_data:
                url = json_data['@odata.nextLink']
            else:
                break
    return all_records


def make_dataframe(sales):
    jStr = json.dumps(sales)
    df = pd.read_json(jStr)
    return df


def get_lastyear(date):
    date_dt = datetime.strptime(date, "%Y-%m-%d")
#    year_ly = date_dt - timedelta(days=365)
    date_str = date_dt.strftime('%m/%d/%Y')
    target = Calendar.query.filter_by(date=date_str)
#    start_ly = end_ly = datetime.now
    dt_date = datetime.now

    for i in target:
        print(i.date, i.year, i.period, i.week, i.day)
        lst_year = str(int(i.year) - 1)
        period = i.period
        week = i.week
        day = i.day
        ly_target = Calendar.query.filter_by(year=lst_year, period=period, week=week, day=day)
        for x in ly_target:
            print(x.date, x.year, x.period, x.week, x.day)
            print("-")
            string_date = datetime.strptime(x.date, "%m/%d/%Y")
            dt_date = string_date.strftime("%Y-%m-%d")
    return dt_date


def get_period(startdate):
    #startdate = datetime.strptime(date, "%Y-%m-%d")
    start = startdate.strftime('%m/%d/%Y')
    target = Calendar.query.filter_by(date=start)

    return target


def sales_employee(start, end):

    df_loc = pd.read_csv('/home/wandored/Projects/Dashboard/locations.csv')
    url_filter = '$filter=date ge {}T00:00:00Z and date le {}T00:00:00Z'.format(start, end)
    query = '$select=netSales,numberofGuests,location&{}'.format(url_filter)
    url = '{}/SalesEmployee?{}'.format(Config.SRVC_ROOT, query)
    print(url)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    df_merge = df_loc.merge(df, on='location')
    df_pivot = df_merge.pivot_table(
        index=['LocationName'],
        values=['netSales',
                'numberofGuests'],
        aggfunc=np.sum
    )
    df_pivot.loc['Totals'] = df_pivot.sum()
    return df_pivot


def labor_detail(start, end):

    df_loc = pd.read_csv('/home/wandored/Projects/Dashboard/locations.csv')
    url_filter = '$filter=dateWorked ge {}T00:00:00Z and dateWorked le {}T00:00:00Z'.format(start, end)
    query = '$select=hours,total,location_ID&{}'.format(url_filter)
    url = '{}/LaborDetail?{}'.format(Config.SRVC_ROOT, query)
    print(url)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    df_merge = df_loc.merge(df, left_on='location', right_on='location_ID')
    df_pivot = df_merge.pivot_table(
        index=['LocationName'],
        values=['hours',
                'total'],
        aggfunc=np.sum
    )
    df_pivot.loc['Totals'] = df_pivot.sum()
    return df_pivot
