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


def build_query(start, end):

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


def query_sales(start, end):

    # calculate date last year
    startdate = datetime.strptime(start, "%Y-%m-%d")
    enddate = datetime.strptime(end, "%Y-%m-%d")
    start_dt =  startdate - timedelta(days=365)
    end_dt =  enddate - timedelta(days=365)
    start_ly = start_dt.strftime('%Y-%m-%d')
    end_ly = end_dt.strftime('%Y-%m-%d')

    thisyear = build_query(start, end)
    lastYear = build_query(start_ly, end_ly)
    totals = thisyear.merge(lastYear, how='outer', on='LocationName', sort=True)

    return totals


def get_period(startdate):
    #startdate = datetime.strptime(date, "%Y-%m-%d")
    start = startdate.strftime('%m/%d/%Y')
    target = Calendar.query.filter_by(date=start)

    return target
