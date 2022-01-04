'''
Datarefresh imports the previous days data and
uploads it to the local database.  This is run
hourly from a cron job
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


def sales_detail(start, end):

#    df_loc = pd.read_csv('/home/wandored/Projects/Dashboard/scripts/locations.csv')
    url_filter = "$filter=date ge {}T00:00:00Z and date le {}T00:00:00Z".format(
        start, end
    )
    query = "$select=menuitem,amount,date,quantity,category,location&{}".format(url_filter)
    url = "{}/SalesDetail?{}".format(Config.SRVC_ROOT, query)
    print(url)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    if df.empty:
        print('empty dataframe')
        return

    cur.execute(rest_query)
    data = cur.fetchall()
    df_loc = pd.DataFrame.from_records(data, columns=['id', 'location', 'name'])
    df_merge = df_loc.merge(df, on="location")
    df_merge.drop(columns=['location'], inplace=True)

    # the data needs to be cleaned before it can be used
    df_menu = df_merge
    df_menu.loc[:, "menuitem"] = df_menu["menuitem"].str.replace(r"CHOPHOUSE - NOLA", "CHOPHOUSE-NOLA", regex=True)
    df_menu.loc[:, "menuitem"] = df_menu["menuitem"].str.replace(r"CAFÉ", "CAFE", regex=True)
    df_menu.loc[:, "menuitem"] = df_menu["menuitem"].str.replace(r"^(?:.*?( -)){2}", "-", regex=True)
    df_menu.loc[:, "menuitem"] = df_menu["menuitem"].str.strip()
    dafilter = df_menu["menuitem"].str.contains("VOID")
    df_clean = df_menu[~dafilter]
    df_clean[["x", "menuitem"]] = df_clean["menuitem"].str.split(" - ", expand=True)
    # menuitems = removeSpecial(df_clean)
    # Write the daily menu items to Menuitems table
    menu_pivot = df_clean.pivot_table(
        index=["name", "menuitem", "category"], values=["amount", "quantity"], aggfunc=np.sum
    )
    menu_pivot["date"] = start
    menu_pivot.to_sql("Menuitems", engine, if_exists="append")
    conn.commit()

    return

def sales_employee(start, end):

#    df_loc = pd.read_csv('/home/wandored/Projects/Dashboard/locations.csv')
    url_filter = '$filter=date ge {}T00:00:00Z and date le {}T00:00:00Z'.format(start, end)
    query = '$select=dayPart,netSales,numberofGuests,location&{}'.format(url_filter)
    url = '{}/SalesEmployee?{}'.format(Config.SRVC_ROOT, query)
    print(url)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    if df.empty:
        print('empty dataframe')
        return
    cur.execute(rest_query)
    data = cur.fetchall()
    df_loc = pd.DataFrame.from_records(data, columns=['id', 'location', 'name'])
    df_merge = df_loc.merge(df, on='location')
    df_merge.rename(columns={'netSales': 'sales', 'numberofGuests': 'guests', 'dayPart': 'daypart'}, inplace=True)

    # pivot data and write to database
    df_pivot = df_merge.pivot_table(
        index=['name',
               'daypart'],
        values=['sales',
                'guests'],
        aggfunc=np.sum
    )
    df_pivot['date'] = start
    df_pivot.to_sql('Sales', engine, if_exists='append')
    conn.commit()

    return

def labor_datail(start, end):

    url_filter = '$filter=dateWorked ge {}T00:00:00Z and dateWorked le {}T00:00:00Z'.format(start, end)
    query = '$select=jobTitle,hours,total,location_ID&{}'.format(url_filter)
    url = '{}/LaborDetail?{}'.format(Config.SRVC_ROOT, query)
    print(url)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    if df.empty:
        print('empty dataframe')
        return

    with open("./labor_categories.json") as labor_file:
        labor_cats = json.load(labor_file)
    df_cats = pd.DataFrame(list(labor_cats.items()), columns=['job', 'category'])

    cur.execute(rest_query)
    data = cur.fetchall()
    df_loc = pd.DataFrame.from_records(data, columns=['id', 'location', 'name'])
    df_merge = df_loc.merge(df, left_on='location', right_on='location_ID')
    df_merge.rename(columns={'jobTitle': 'job', 'total': 'dollars'}, inplace=True)
    df_merge = df_merge.merge(df_cats, on='job')

    # pivot data and write to database
    df_pivot = df_merge.pivot_table(
        index=['name',
               'category',
               'job'],
        values=['hours',
                'dollars'],
        aggfunc=np.sum
    )
    df_pivot['date'] = start
    df_pivot.to_sql('Labor', engine, if_exists='append')
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
    rest_query = 'select * from "Restaurants"'

    TODAY = datetime.date(datetime.now())
    YSTDAY = TODAY - timedelta(days=1)
    start_date = YSTDAY.strftime('%Y-%m-%d')
    end_date = TODAY.strftime('%Y-%m-%d')

    cur.execute('DELETE FROM "Sales" WHERE date = %s', (start_date,))
    cur.execute('DELETE FROM "Labor" WHERE date = %s', (start_date,))
    cur.execute('DELETE FROM "Menuitems" WHERE date = %s', (start_date,))
    conn.commit()

    sales_detail(start_date, end_date)
    sales_employee(start_date, end_date)
    labor_datail(start_date, end_date)

    conn.close()
