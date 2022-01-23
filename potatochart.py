'''
potatochart.py will request the potato sales per 20 minutes
and write it to the database.  This is for multi-day building
'''
import json
import csv
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


def get_sales(date):

    df_pot = pd.DataFrame()
    with open('/usr/local/share/potatochart.csv') as f:
        times = csv.reader(f)
        next(times)
        for i in times:
            url_filter = "$filter=date ge {}T{}Z and date le {}T{}Z".format(
                date, i[2], date, i[3]
            )
            query = "$select=menuitem,date,quantity,location&{}".format(url_filter)
            url = "{}/SalesDetail?{}".format(Config.SRVC_ROOT, query)
            rqst = make_HTTP_request(url)
            df = make_dataframe(rqst)
            if df.empty:
                print('empty dataframe')
                continue
            cur.execute('select * from "Restaurants"')
            unit = cur.fetchall()
            df_loc = pd.DataFrame.from_records(unit, columns=['id', 'location', 'name'])
            df_merge = df_loc.merge(df, on="location")
            if df_merge.empty:
                print(f'no sales at {i[0]}')
                if df_pot.empty:
                    continue
                df_pot.loc[i[0]] = [0]
                continue
            df_merge.drop(columns=['location'], inplace=True)
            df_merge.loc[:, "menuitem"] = df_merge["menuitem"].str.replace(r"CHOPHOUSE - NOLA", "CHOPHOUSE-NOLA", regex=True)
            df_merge.loc[:, "menuitem"] = df_merge["menuitem"].str.replace(r"CAFÉ", "CAFE", regex=True)
            df_merge.loc[:, "menuitem"] = df_merge["menuitem"].str.replace(r"^(?:.*?( -)){2}", "-", regex=True)
            df_merge.loc[:, "menuitem"] = df_merge["menuitem"].str.strip()
            dafilter = df_merge["menuitem"].str.contains("VOID")
            df_clean = df_merge[~dafilter]
            df_clean[["x", "menuitem"]] = df_clean["menuitem"].str.split(" - ", expand=True)
            pot_list = ['BAKED POTATO',
                        'BAKED POTATO N/C',
                        'POTATO',
                        'POT',
                        'BAKED POTATO A SIDE',
                        'BAKED POTATO SIDE',
                        'KID SUB POT',
                        'POT-A',
                        'S-BAKED POTATO',
                        'SUB BAKED POTATO IN KIDS',
                        'SUB KID POT']
            df = df_clean[df_clean['menuitem'].isin(pot_list)]
            if df.empty:
                continue
            df['time'] = i[0]
            df['in_time'] = i[1]
            df['out_time'] = i[4]
            df_pot = df_pot.append(df)

        pot_pivot = df_pot.pivot_table(
            index=["time", "name", "in_time", "out_time"], values=["quantity"], aggfunc=np.sum
        )
    pot_pivot['date'] = date
    pot_pivot.to_sql('Potatoes', engine, if_exists='append')
    conn.commit()

    return


if __name__ == "__main__":

    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    conn = psycopg2.connect(
        host='localhost',
        database='dashboard',
        user=Config.PSYCOPG2_USER,
        password=Config.PSYCOPG2_PASS,
    )
    cur = conn.cursor()

    pot_df = pd.DataFrame()
    TODAY = datetime.date(datetime.now())
    for i in range(1, 29):
        target = TODAY - timedelta(days=i)
        start_date = target.strftime('%Y-%m-%d')
        cur.execute('DELETE FROM "Potatoes" WHERE date = %s', (start_date,))
        conn.commit()
        get_sales(start_date)
        print(f'wrote {start_date}')

    conn.close()
