'''
transactionupdate imports the previous days data and
uploads it to the local database.  This is run
from a cron job
'''
import json
from sqlalchemy.engine.create import create_engine
from datetime import datetime, timedelta
import requests
import pandas as pd
import numpy as np
import psycopg2
from dashapp import Config


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


def removeSpecial(df):
    """Removes specialty items from the menuitems dataframe"""
    file = open("/usr/local/share/specialty.txt")
    specialty_list = file.read().split("\n")
    file.close
    for item in specialty_list:
        df = df.drop(df[df.menuitem == item].index)
    return df


def transaction(start, end):

    url_filter = "$filter=date ge {}T00:00:00Z and date le {}T00:00:00Z".format(
        start, end
    )
    query = "$select=date,name,type,locationName&{}".format(url_filter)
    url = "{}/Transaction?{}".format(Config.SRVC_ROOT, query)
    print(url)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    if df.empty:
        print('empty dataframe')
        return

    cur.execute(rest_query)
    data = cur.fetchall()
    df_loc = pd.DataFrame.from_records(data, columns=['id', 'location', 'name'])
    df_merge = df_loc.merge(df, left_on="name", right_on='locationName')
    df_merge.drop(columns=['location', 'locationName'], inplace=True)
    print(df_merge)


def Items():

    query = "$select=itemId,name,category1,category2,category3"
    url = "{}/Item?{}".format(Config.SRVC_ROOT, query)
    print(url)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    if df.empty:
        print('empty dataframe')
        return

    return df


def transactionDetails(start, end):

    url_filter = "$filter=createdOn ge {}T00:00:00Z and createdOn le {}T00:00:00Z".format(
        start, end
    )
    query = "$select=locationId,itemId,credit,debit,amount,quantity,unitOfMeasureName,createdOn&{}".format(url_filter)
    url = "{}/TransactionDetail?{}".format(Config.SRVC_ROOT, query)
    print(url)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    if df.empty:
        print('empty dataframe')
        return

    cur.execute(rest_query)
    data = cur.fetchall()
    df_loc = pd.DataFrame.from_records(data, columns=['id', 'location', 'name'])
    df_merge = df_loc.merge(df, left_on="location", right_on='locationId')
    df_merge.drop(columns=['location', 'locationId', 'createdOn'], inplace=True)
    df_merge['date'] = start

    return df_merge


def write_to_database(df1, df2):

    df = df1.merge(df2, on='itemId')
    df.drop(columns=['itemId'], inplace=True)
    df.rename(columns={'name_x': 'item', 'unitOfMeasureName': 'UofM', 'name_y': 'name', 'id': 'store_id'}, inplace=True)
    print(df)
    df.to_sql('Transactions', engine, if_exists='append', index=False)
    conn.commit()


if __name__ == "__main__":

    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    conn = psycopg2.connect(
        host='localhost',
        database='dashboard',
        user=Config.PSYCOPG2_USER,
        password=Config.PSYCOPG2_PASS,
    )
    cur = conn.cursor()
    rest_query = 'select * from "Restaurants"'

    TODAY = datetime.date(datetime.now())
    YSTDAY = TODAY - timedelta(days=1)
    start_date = YSTDAY.strftime('%Y-%m-%d')
    end_date = TODAY.strftime('%Y-%m-%d')

#    cur.execute('DELETE FROM "Sales" WHERE date = %s', (start_date,))
#    conn.commit()

    # transaction(start_date, end_date)
    df_items = Items()
    df_trans = transactionDetails(start_date, end_date)
    write_to_database(df_items, df_trans)

    conn.close()
