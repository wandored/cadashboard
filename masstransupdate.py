"""
transactionupdate imports the previous 7 days data and
uploads it to the local database.  This is run
from a cron job
"""
import json
from sqlalchemy.engine.create import create_engine
from datetime import date, timedelta
import requests
import pandas as pd
import psycopg2
from dashapp import Config


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


def get_glaccount():
    query = "$select=glAccountId,name"
    url = "{}/GlAccount?{}".format(Config.SRVC_ROOT, query)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    df.rename(columns={"name": "account"}, inplace=True)

    return df


def transaction(id_list):

    rqst_list = []
    for i in id_list:
        url_filter = "$filter=transactionId eq {}".format(i)
        query = "$select=date,name,type,locationId,transactionId,companyId&{}".format(
            url_filter
        )
        url = "{}/Transaction?{}".format(Config.SRVC_ROOT, query)
        rqst = make_HTTP_request(url)
        try:
            rqst_list.append(rqst[0])
        except IndexError:
            pass

    df = make_dataframe(rqst_list)
    if df.empty:
        print("empty dataframe")
        return

    df["date"] = df["date"].dt.strftime(
        "%Y-%m-%d"
    )  # convert datetime to string and format
    cur.execute(rest_query)
    data = cur.fetchall()
    df_loc = pd.DataFrame.from_records(data, columns=["id", "location", "name"])
    df_merge = df_loc.merge(df, left_on="location", right_on="locationId")
    df_merge.rename(columns={"name_x": "name", "name_y": "item"}, inplace=True)
    df_merge.drop(columns=["location", "locationId"], inplace=True)

    query = "$select=companyId,name"
    url = "{}/Company?{}".format(Config.SRVC_ROOT, query)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    df.rename(columns={"name": "company"}, inplace=True)
    df_merge = df_merge.merge(df, on="companyId", how="left")

    return df_merge


def Items():

    query = "$select=itemId,name,category1,category2,category3"
    url = "{}/Item?{}".format(Config.SRVC_ROOT, query)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    if df.empty:
        print("empty dataframe")
        return
    df.rename(columns={"name": "item"}, inplace=True)

    return df


def transactionDetails(start, end):

    url_filter = (
        "$filter=modifiedOn ge {}T00:00:00Z and modifiedOn le {}T00:00:00Z".format(
            start, end
        )
    )
    query = "$select=locationId,itemId,credit,debit,amount,quantity,unitOfMeasureName,modifiedOn,transactionId,glAccountId&{}".format(
        url_filter
    )
    url = "{}/TransactionDetail?{}".format(Config.SRVC_ROOT, query)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    if df.empty:
        print("empty dataframe")
        return

    cur.execute(rest_query)
    data = cur.fetchall()
    df_loc = pd.DataFrame.from_records(data, columns=["id", "location", "name"])
    df_merge = df_loc.merge(df, left_on="location", right_on="locationId")
    df_merge[["modified", "m"]] = df_merge["modifiedOn"].str.split("T", expand=True)
    df_merge.drop(columns=["location", "locationId", "m", "modifiedOn"], inplace=True)

    return df_merge


def write_to_database(df1, df2, df3):

    gl = get_glaccount()
    df = df3.merge(gl, on="glAccountId")
    df = df.merge(df2, how="left", on=["itemId"])
    df = df.merge(df1, on=["transactionId", "id", "name"])
    df.rename(
        columns={
            "id": "store_id",
            "item_x": "item",
            "unitOfMeasureName": "UofM",
            "transactionId": "trans_id",
            "companyId": "companyid",
        },
        inplace=True,
    )
    df.drop(columns=["itemId", "item_y"], inplace=True)
    df = df[
        [
            "date",
            "trans_id",
            "store_id",
            "name",
            "item",
            "category1",
            "category2",
            "category3",
            "quantity",
            "UofM",
            "credit",
            "debit",
            "amount",
            "type",
            "modified",
            "companyid",
            "company",
            "account",
        ]
    ]
    df = df[
        df["type"].isin(
            [
                "Stock Count",
                "AP Invoice",
                "AP Credit Memo",
                "Waste Log",
                "Item Transfer",
            ]
        )
    ]
    df = df[df["account"] != "Accounts Payable"]
    df.to_sql("Transactions", engine, if_exists="append", index=False)
    conn.commit()


if __name__ == "__main__":

    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    conn = psycopg2.connect(
        host="localhost",
        database="dashboard",
        user=Config.PSYCOPG2_USER,
        password=Config.PSYCOPG2_PASS,
    )
    cur = conn.cursor()
    rest_query = 'select * from "Restaurants"'

    TODAY = date.today()
    for d in range(1, 28):
        dt = TODAY - timedelta(days=d)
        print(f"date {dt}")
        tmrw = dt + timedelta(days=1)
        start_date = dt.strftime("%Y-%m-%d")
        end_date = tmrw.strftime("%Y-%m-%d")

        df_items = Items()
        df_trans = transactionDetails(start_date, end_date)
        id_list = df_trans["transactionId"].tolist()
        id_list = list(dict.fromkeys(id_list))
        print(f"transaction total: {len(id_list)}")
        # index = len(id_list) - 1
        if df_trans["itemId"].any():
            for x in id_list:
                cur.execute('DELETE FROM "Transactions" WHERE trans_id = %s', (x,))
                conn.commit()
            df_type = transaction(id_list)
            # call function only if there are AP items
            write_to_database(df_type, df_items, df_trans)
            print(f"{dt} completed")

    conn.close()
