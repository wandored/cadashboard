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
                print(url)
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

    url_filter = "$filter=modifiedOn ge {}T00:00:00Z and modifiedOn le {}T00:00:00Z".format(
        start, end
    )
    query = "$select=date,modifiedOn,name,type,locationId,transactionId&{}".format(url_filter)
    url = "{}/Transaction?{}".format(Config.SRVC_ROOT, query)
    print(url)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    if df.empty:
        print('empty dataframe')
        return

    df['date'] = df['date'].dt.strftime('%Y-%m-%d') #convert datetime to string and format
    cur.execute(rest_query)
    data = cur.fetchall()
    df_loc = pd.DataFrame.from_records(data, columns=['id', 'location', 'name'])
    df_merge = df_loc.merge(df, left_on="location", right_on='locationId')
    df_merge.rename(columns={'name_x': 'name', 'name_y': 'item'}, inplace=True)
    df_merge[["modified", "m"]] = df_merge["modifiedOn"].str.split("T", expand=True)
    df_merge.drop(columns=['location', 'locationId', 'm', 'modifiedOn'], inplace=True)

    return  df_merge


def Items():

    query = "$select=itemId,name,category1,category2,category3"
    url = "{}/Item?{}".format(Config.SRVC_ROOT, query)
    print(url)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    if df.empty:
        print('empty dataframe')
        return
    df.rename(columns={'name': 'item'}, inplace=True)

    return df


def transactionDetails(start, end):

    url_filter = "$filter=modifiedOn ge {}T00:00:00Z and modifiedOn le {}T00:00:00Z".format(
        start, end
    )
    query = "$select=locationId,itemId,credit,debit,amount,quantity,unitOfMeasureName,modifiedOn,transactionId&{}".format(url_filter)
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
    df_merge[["modified", "m"]] = df_merge["modifiedOn"].str.split("T", expand=True)
    df_merge.drop(columns=['location', 'locationId', 'm', 'modifiedOn'], inplace=True)

    id_list = df_merge['transactionId'].tolist()
    id_list = list(dict.fromkeys(id_list))
    for x in id_list:
        cur.execute('DELETE FROM "Transactions" WHERE trans_id = %s', (x,))
        conn.commit()

    return df_merge


def write_to_database(df1, df2, df3):

    df = df3.merge(df1, on=['transactionId', 'modified'])
    df = df.merge(df2, on='itemId')
    df.rename(columns={'item_y': 'item', 'unitOfMeasureName': 'UofM', 'name_x': 'name', 'id_x': 'store_id', 'transactionId': 'trans_id'}, inplace=True)
    df.drop(columns=['itemId', 'name_y', 'id_y', 'item_x'], inplace=True)
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

    # This part is for multi-day loading of data
    df_cal = pd.read_csv('./scripts/calendar.csv')
#    select = ['2021-12-29', '2021-12-30', '2021-12-31', '2022-01-01', '2022-01-02', '2022-01-03', '2022-01-04', '2022-01-05']
#    select = df_cal.loc[1071:1108,'date']
#    for d in select:
#        dt = datetime.strptime(d, '%Y-%m-%d')
#        tmrw = dt + timedelta(days=1)
#        start_date = dt.strftime('%Y-%m-%d')
#        end_date = tmrw.strftime('%Y-%m-%d')
#        df_type = transaction(start_date, end_date)
#        df_items = Items()
#        df_trans = transactionDetails(start_date, end_date)
#        if df_trans['itemId'].any():
#            # call function only if there are AP items
#            write_to_database(df_type, df_items, df_trans)

    TODAY = datetime.date(datetime.now())
    YSTDAY = TODAY - timedelta(days=1)
    TOMROW = TODAY + timedelta(days=1)
    start_date = TODAY.strftime('%Y-%m-%d')
    end_date = TOMROW.strftime('%Y-%m-%d')

    df_type = transaction(start_date, end_date)
    df_items = Items()
    df_trans = transactionDetails(start_date, end_date)
    if df_trans['itemId'].any():
        # call function only if there are AP items
        write_to_database(df_type, df_items, df_trans)

    conn.close()
