'''
potatochart.py will calculate the average sales per 20 minutes
and create a potatchart for the current day
'''
import json
import csv
from sqlalchemy.engine.create import create_engine
from datetime import datetime, timedelta
import requests
import pandas as pd
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


def get_sales(date, store_id):
    pot_chart = pd.DataFrame()

    with open('./potatochart.csv') as f:
        times = csv.reader(f)
        next(times)
        for i in times:
            url_filter = "$filter=date ge {}T{}Z and date le {}T{}Z".format(
                date, i[1], date, i[2]
            )
            query = "$select=menuitem,quantity,location&{}".format(url_filter)
            url = "{}/SalesDetail?{}".format(Config.SRVC_ROOT, query)
            rqst = make_HTTP_request(url)
            df = make_dataframe(rqst)
            if df.empty:
                print('empty dataframe')
                break
            cur.execute('select * from "Restaurants" WHERE id = %s', (store_id,))
            unit = cur.fetchall()
            df_loc = pd.DataFrame.from_records(unit, columns=['id', 'location', 'name'])
            df_merge = df_loc.merge(df, on="location")
            if df_merge.empty:
                print(f'no sales at {i[0]}')
                if pot_chart.empty:
                    break
                pot_chart.loc[i[0]] = [0]
                break
            df_merge.drop(columns=['location'], inplace=True)
            df_merge.loc[:, "menuitem"] = df_merge["menuitem"].str.replace(r"CHOPHOUSE - NOLA", "CHOPHOUSE-NOLA", regex=True)
            df_merge.loc[:, "menuitem"] = df_merge["menuitem"].str.replace(r"CAFÉ", "CAFE", regex=True)
            df_merge.loc[:, "menuitem"] = df_merge["menuitem"].str.replace(r"^(?:.*?( -)){2}", "-", regex=True)
            df_merge.loc[:, "menuitem"] = df_merge["menuitem"].str.strip()
            dafilter = df_merge["menuitem"].str.contains("VOID")
            df_clean = df_merge[~dafilter]
            df_clean[["x", "menuitem"]] = df_clean["menuitem"].str.split(" - ", expand=True)
            df = df_clean.loc[df_clean['menuitem'].isin(['BAKED POTATO', 'BAKED POTATO N/C', 'POTATO', 'POT'])]
            df.drop(columns=['x', 'id', 'name', 'menuitem'], inplace=True)
            df.loc[i[0]] = df.sum(numeric_only=True)
            r = (len(df)-1)
            pot_chart = pot_chart.append(df.iloc[[r]])


        pot_chart.rename(columns={'quantity': date}, inplace=True)

    return pot_chart


if __name__ == "__main__":

    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    conn = psycopg2.connect(
        host='localhost',
        database='dashboard',
        user=Config.PSYCOPG2_USER,
        password=Config.PSYCOPG2_PASS,
    )
    cur = conn.cursor()
    store_id = input('enter store number ')

    pot_df = pd.DataFrame()
    TODAY = datetime.date(datetime.now())
    for i in [28, 21, 14, 7]:
        target = TODAY - timedelta(days=i)
        start_date = target.strftime('%Y-%m-%d')
        df = get_sales(start_date, store_id)
        pot_df = pot_df.merge(df, left_index=True, right_index=True, how='outer')

    pot_df.fillna(0, inplace=True)
    pot_df['AVG'] = round(pot_df.mean(axis=1))
    pot_df['MEDIAN'] = round(pot_df.median(axis=1))
    pot_df['MAX'] = pot_df.max(axis=1)
    out_times = pd.read_csv('./potatochart.csv', index_col='in')
    rotation = pot_df.merge(out_times, left_index=True, right_on='in', how='left')
    rotation.drop(columns=['start_time', 'stop_time'], inplace=True)
    print(rotation)

    conn.close()
