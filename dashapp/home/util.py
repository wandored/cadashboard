'''
CentraArchy Dashboard by wandored
'''
import json
import requests
import pandas as pd
import numpy as np
from flask import redirect, url_for, flash, session
from dashapp.home import blueprint
from datetime import datetime
from sqlalchemy.engine.create import create_engine
from dashapp import Config, db
from dashapp.authentication.models import Calendar, Sales, Labor


#def query_sales(start, end):
#
#    current_sales = sales_employee(start, end)
##
##    totals = current_sales.merge(lastYear, how='outer', on='name', sort=True)
#
#    return current_sales
#
#
#def query_labor(start, end):
#
#    current_labor = labor_detail(start, end)
#
##    start_ly = get_lastyear(start)
##    end_ly = get_lastyear(end)
##    lastYear = labor_detail(start_ly, end_ly)
##
##    totals = current_labor.merge(lastYear, how='outer', on='name', sort=True)
#
#    return current_labor


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
    target = Calendar.query.filter_by(date=date)
    dt_date = datetime.now

    for i in target:
        lst_year = str(int(i.year) - 1)
        period = i.period
        week = i.week
        day = i.day
        ly_target = Calendar.query.filter_by(year=lst_year, period=period, week=week, day=day)
        for x in ly_target:
            dt_date = x.date
    return dt_date


def get_period(startdate):
    #startdate = datetime.strptime(date, "%Y-%m-%d")
    start = startdate.strftime('%Y-%m-%d')
    target = Calendar.query.filter_by(date=start)

    return target


def sales_employee(start, end):

    df_loc = pd.read_csv('/home/wandored/Projects/Dashboard/locations.csv')
    url_filter = '$filter=date ge {}T00:00:00Z and date le {}T00:00:00Z'.format(start, end)
    query = '$select=dayPart,netSales,numberofGuests,location&{}'.format(url_filter)
    url = '{}/SalesEmployee?{}'.format(Config.SRVC_ROOT, query)
    print(url)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    if df.empty:
        return 1

    df_merge = df_loc.merge(df, on='location')
    df_merge.rename(columns={'netSales': 'sales', 'numberofGuests': 'guests'}, inplace=True)

    # pivot data and write to database
    df_pivot = df_merge.pivot_table(
        index=['name',
               'dayPart'],
        values=['sales',
                'guests'],
        aggfunc=np.sum
    )
    df_pivot['date'] = start
    df_pivot.to_sql('Sales', con=db.engine, if_exists='append')
    return 0


def labor_detail(start, end):

    df_loc = pd.read_csv('/home/wandored/Projects/Dashboard/locations.csv')
    url_filter = '$filter=dateWorked ge {}T00:00:00Z and dateWorked le {}T00:00:00Z'.format(start, end)
    query = '$select=jobTitle,hours,total,location_ID&{}'.format(url_filter)
    url = '{}/LaborDetail?{}'.format(Config.SRVC_ROOT, query)
    print(url)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    if df.empty:
        return 1

    df_merge = df_loc.merge(df, left_on='location', right_on='location_ID')
    df_merge.rename(columns={'jobTitle': 'job', 'total': 'dollars'}, inplace=True)
    df_pivot = df_merge.pivot_table(
        index=['name',
               'job'],
        values=['hours',
                'dollars'],
        aggfunc=np.sum
    )
    df_pivot['date'] = start
    df_pivot.to_sql('Labor', con=db.engine, if_exists='append')
    return 0
