"""
Dashboard by wandored
"""
import json
import csv
import requests
from flask import send_file
import pandas as pd
import numpy as np
from io import StringIO, BytesIO
from dashapp.config import Config
from datetime import datetime, timedelta
from dashapp.authentication.models import *
from sqlalchemy import func


# TODO weekly and period sales records
def sales_record(store, time_frame):
    if time_frame == "daily":
        query = (
            db.session.query(func.sum(Sales.sales).label("top_sales"))
            .filter(Sales.name == store)
            .group_by(Sales.date)
            .order_by(func.sum(Sales.sales).desc())
            .first()
        )
    elif time_frame == "weekly":
        query = (
            db.session.query(func.sum(Sales.sales).label("top_sales"))
            .filter(Sales.name == store)
            .join(Calendar, Calendar.date == Sales.date)
            .group_by(Calendar.week, Calendar.period, Calendar.year)
            .order_by(func.sum(Sales.sales).desc())
            .first()
        )
    elif time_frame == "period":
        query = (
            db.session.query(func.sum(Sales.sales).label("top_sales"))
            .filter(Sales.name == store)
            .join(Calendar, Calendar.date == Sales.date)
            .group_by(Calendar.period, Calendar.year)
            .order_by(func.sum(Sales.sales).desc())
            .first()
        )
    elif time_frame == "year":
        query = (
            db.session.query(func.sum(Sales.sales).label("top_sales"))
            .filter(Sales.name == store)
            .join(Calendar, Calendar.date == Sales.date)
            .group_by(Calendar.year)
            .order_by(func.sum(Sales.sales).desc())
            .first()
        )
    if query:
        return query[0]


def get_daypart_sales(start, end, store, day_part):
    query = (
        db.session.query(
            Sales.date,
            Sales.daypart,
            Sales.sales,
        )
        .filter(Sales.date.between(start, end), Sales.daypart == (day_part), Sales.name == store)
        .all()
    )
    return query


def get_daypart_guest(start, end, store, day_part):
    query = (
        db.session.query(
            Sales.date,
            Sales.daypart,
            Sales.guests,
        )
        .filter(Sales.date.between(start, end), Sales.daypart == (day_part), Sales.name == store)
        .all()
    )
    return query


def find_day_with_sales(**kwargs):
    if "store" in kwargs:
        while not Sales.query.filter_by(date=kwargs["day"], name=kwargs["store"]).first():
            date = datetime.strptime(kwargs["day"], "%Y-%m-%d")
            next_day = date - timedelta(days=1)
            kwargs["day"] = next_day.strftime("%Y-%m-%d")
    else:
        while not Sales.query.filter_by(date=kwargs["day"]).first():
            date = datetime.strptime(kwargs["day"], "%Y-%m-%d")
            next_day = date - timedelta(days=1)
            kwargs["day"] = next_day.strftime("%Y-%m-%d")
    return kwargs["day"]


def refresh_data(start, end):
    """
    When new date submitted, the data for that date will be replaced with new data from R365
    We check if there are infact sales for that day, if not, it resets to yesterday, if
    there are sales, then labor is polled
    """
    # delete current days data from database and replace with fresh data
    Sales.query.filter_by(date=start).delete()
    Labor.query.filter_by(date=start).delete()
    Menuitems.query.filter_by(date=start).delete()
    Potatoes.query.filter_by(date=start).delete()
    db.session.commit()

    # refres the sales data and check to make sure there are sales for that day
    baddates = sales_employee(start, end)
    if baddates == 1:
        return 1

    # refresh labor
    labor_detail(start)
    # refresh categories and menuitems
    # TODO add sales_payments
    sales_detail(start, end)
    potato_sales(start)
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
    dt_date = date

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
    start = startdate.strftime("%Y-%m-%d")
    target = Calendar.query.filter_by(date=start)

    return target


def removeSpecial(df):
    """Removes specialty items from the menuitems dataframe"""
    file = open("../../specialty.txt")
    specialty_list = file.read().split("\n")
    file.close
    for item in specialty_list:
        df = df.drop(df[df.menuitem == item].index)
    return df


def sales_employee(start, end):
    url_filter = "$filter=date ge {}T00:00:00Z and date le {}T00:00:00Z".format(start, end)
    query = "$select=dayPart,netSales,numberofGuests,location&{}".format(url_filter)
    url = "{}/SalesEmployee?{}".format(Config.SRVC_ROOT, query)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    if df.empty:
        return 1

    data = db.session.query(Restaurants).all()
    df_loc = pd.DataFrame([(x.name, x.location) for x in data], columns=["name", "location"])
    df_merge = df_loc.merge(df, on="location")
    df_merge = df_merge.rename(columns={"netSales": "sales", "numberofGuests": "guests", "dayPart": "daypart"})

    # pivot data and write to database
    df_pivot = df_merge.pivot_table(index=["name", "daypart"], values=["sales", "guests"], aggfunc=np.sum)
    df_pivot.loc[:, "date"] = start
    df_pivot.to_sql("Sales", con=db.engine, if_exists="append")
    return 0


def labor_detail(start):
    url_filter = "$filter=dateWorked eq {}T00:00:00Z".format(start)
    query = "$select=jobTitle,hours,total,location_ID&{}".format(url_filter)
    url = "{}/LaborDetail?{}".format(Config.SRVC_ROOT, query)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    if df.empty:
        return 1

    with open("/usr/local/share/labor_categories.json") as labor_file:
        labor_cats = json.load(labor_file)
    df_cats = pd.DataFrame(list(labor_cats.items()), columns=["job", "category"])

    data = db.session.query(Restaurants).all()
    df_loc = pd.DataFrame([(x.name, x.location) for x in data], columns=["name", "location"])
    df_merge = df_loc.merge(df, left_on="location", right_on="location_ID")
    df_merge = df_merge.rename(columns={"jobTitle": "job", "total": "dollars"})
    df_merge = df_merge.merge(df_cats, on="job")
    df_pivot = df_merge.pivot_table(index=["name", "category", "job"], values=["hours", "dollars"], aggfunc=np.sum)
    df_pivot.loc[:, "date"] = start
    df_pivot.to_sql("Labor", con=db.engine, if_exists="append")
    return 0


def sales_detail(start, end):
    url_filter = "$filter=date ge {}T00:00:00Z and date le {}T00:00:00Z".format(start, end)
    query = "$select=menuitem,amount,date,quantity,category,location&{}".format(url_filter)
    url = "{}/SalesDetail?{}".format(Config.SRVC_ROOT, query)
    rqst = make_HTTP_request(url)
    df = make_dataframe(rqst)
    if df.empty:
        return 1

    with open("/usr/local/share/major_categories.json") as file:
        major_cats = json.load(file)
    df_cats = pd.DataFrame(list(major_cats.items()), columns=["menu_category", "category"])

    data = db.session.query(Restaurants).all()
    df_loc = pd.DataFrame([(x.name, x.location) for x in data], columns=["name", "location"])
    df_merge = df_loc.merge(df, on="location")
    df_merge = df_merge.drop(columns=["location"])

    df_menu = df_merge.merge(df_cats, left_on="category", right_on="menu_category")

    df_menu.loc[:, "menuitem"] = df_menu["menuitem"].str.replace(r"CHOPHOUSE - NOLA", "CHOPHOUSE-NOLA", regex=True)
    df_menu.loc[:, "menuitem"] = df_menu["menuitem"].str.replace(r"CAFÉ", "CAFE", regex=True)
    df_menu.loc[:, "menuitem"] = df_menu["menuitem"].str.replace(r"^(?:.*?( -)){2}", "-", regex=True)
    df_menu.loc[:, "menuitem"] = df_menu["menuitem"].str.strip()
    dafilter = df_menu["menuitem"].str.contains("VOID")
    df_clean = df_menu[~dafilter]
    df_temp = df_clean.copy()
    df_temp[["x", "menuitem"]] = df_clean["menuitem"].str.split(" - ", expand=True)
    df_clean = df_temp.drop(columns=["category_x", "x"])
    df_clean = df_clean.rename(columns={"category_y": "category"})
    #    menuitems = removeSpecial(df_clean)  ### fix the file location before making this active
    # Write the daily menu items to Menuitems table
    menu_pivot = df_clean.pivot_table(
        index=["name", "menuitem", "category", "menu_category"],
        values=["amount", "quantity"],
        aggfunc=np.sum,
    )
    menu_pivot.loc[:, "date"] = start
    menu_pivot.to_sql("Menuitems", con=db.engine, if_exists="append")

    return 0


def get_category_sales(start, end, store, cat):
    # dataframe of sales per category per period

    if cat == "GIFT CARDS":
        data = (
            db.session.query(Menuitems.date, func.sum(Menuitems.amount).label("total_sales"))
            .filter(
                Menuitems.date.between(start, end),
                Menuitems.name == store,
                Menuitems.menuitem.regexp_match("(?i)GIFT CARD*"),
            )
            .group_by(Menuitems.date)
            .all()
        )
    else:
        data = (
            db.session.query(Menuitems.date, func.sum(Menuitems.amount).label("total_sales"))
            .filter(
                Menuitems.date.between(start, end),
                Menuitems.name == store,
                Menuitems.category == cat,
            )
            .group_by(Menuitems.date)
            .all()
        )
    df = pd.DataFrame([(x.date, x.total_sales) for x in data], columns=["date", cat])
    return df


def get_glaccount_costs(start, end, acct, store, epoch):
    # Return list of sales
    query = (
        db.session.query(
            func.sum(Transactions.credit).label("credits"),
            func.sum(Transactions.debit).label("costs"),
        )
        .select_from(Transactions)
        .join(Calendar, Calendar.date == Transactions.date)
        .group_by(epoch)
        .order_by(epoch)
        .filter(
            Transactions.date.between(start, end),
            Transactions.account == acct,
            Transactions.name == store,
        )
    )
    results = []
    for q in query:
        amount = q.costs - q.credits
        results.append(amount)
    return results


# def get_category_costs(start, end, sales, cat):
#    # List of costs per category per period
#    query = (
#        db.session.query(
#            func.sum(Transactions.credit).label("credits"),
#            func.sum(Transactions.debit).label("costs"),
#        )
#        .select_from(Transactions)
#        .join(Calendar, Calendar.date == Transactions.date)
#        .group_by(Calendar.period)
#        .order_by(Calendar.period)
#        .filter(
#            Transactions.date.between(start, end),
#            Transactions.category2.in_(cat),
#            Transactions.name == store.name,
#        )
#    )
#    dol_lst = []
#    pct_lst = []
#    for v in query:
#        amount = v.costs - v.credits
#        dol_lst.append(amount)
#    add_items = len(sales) - len(dol_lst)
#    for i in range(0, add_items):
#        dol_lst.append(0)
#    for i in range(0, len(sales)):
#        pct_lst.append(dol_lst[i] / sales[i])
#    return dol_lst, pct_lst


def get_item_avg_cost(regex, start, end, id):
    # Return average cost for purchase item

    query = db.session.query(
        func.sum(Transactions.debit).label("cost"),
        func.sum(Transactions.quantity).label("count"),
    ).filter(
        Transactions.item.regexp_match(regex),
        Transactions.date.between(start, end),
        Transactions.store_id == id,
        Transactions.type == "AP Invoice",
    )
    for q in query:
        try:
            avg_cost = q["cost"] / q["count"]
        except:
            avg_cost = 0

    return avg_cost


def get_category_labor(start, end, store, cat):
    data = (
        db.session.query(
            Labor.date,
            func.sum(Labor.dollars).label("total_dollars"),
        )
        .filter(Labor.date.between(start, end), Labor.name == store, Labor.category == cat)
        .group_by(Labor.date)
        .all()
    )
    df = pd.DataFrame([(x.date, x.total_dollars) for x in data], columns=["date", cat])
    return df


def potato_sales(start):
    df_pot = pd.DataFrame()
    with open("/usr/local/share/potatochart.csv") as f:
        times = csv.reader(f)
        next(times)
        for i in times:
            url_filter = "$filter=date ge {}T{}Z and date le {}T{}Z".format(start, i[2], start, i[3])
            query = "$select=menuitem,date,quantity,location&{}".format(url_filter)
            url = "{}/SalesDetail?{}".format(Config.SRVC_ROOT, query)
            rqst = make_HTTP_request(url)
            df = make_dataframe(rqst)
            if df.empty:
                print("empty dataframe")
                continue

            data = db.session.query(Restaurants).all()
            df_loc = pd.DataFrame([(x.name, x.location) for x in data], columns=["name", "location"])
            df_merge = df_loc.merge(df, on="location")
            if df_merge.empty:
                print(f"no sales at {i[0]}")
                if df_pot.empty:
                    continue
                df_pot.loc[i[0]] = [0]
                continue
            df_merge = df_merge.drop(columns=["location"])
            df_menu = df_merge
            df_menu.loc[:, "menuitem"] = df_menu["menuitem"].str.replace(
                r"CHOPHOUSE - NOLA", "CHOPHOUSE-NOLA", regex=True
            )
            df_menu.loc[:, "menuitem"] = df_menu["menuitem"].str.replace(r"CAFÉ", "CAFE", regex=True)
            df_menu.loc[:, "menuitem"] = df_menu["menuitem"].str.replace(r"^(?:.*?( -)){2}", "-", regex=True)
            df_menu.loc[:, "menuitem"] = df_menu["menuitem"].str.strip()
            dafilter = df_menu["menuitem"].str.contains("VOID")
            df_clean = df_menu[~dafilter]
            df_temp = df_clean.copy()
            df_temp[["x", "menuitem"]] = df_clean["menuitem"].str.split(" - ", expand=True)
            pot_list = [
                "BAKED POTATO",
                "BAKED POTATO N/C",
                "POTATO",
                "POT",
                "BAKED POTATO A SIDE",
                "BAKED POTATO SIDE",
                "KID SUB POT",
                "POT-A",
                "S-BAKED POTATO",
                "SUB BAKED POTATO IN KIDS",
                "SUB KID POT",
                "Baked Potato",
                "Baked Potato (After 4:00 PM)",
                "Kid Baked Potato",
                "Kid Baked Potato (After 4:00 PM)",
                "Loaded Baked Potato",
            ]
            df = df_temp[df_temp["menuitem"].isin(pot_list)]
            if df.empty:
                continue
            df.loc[:, "time"] = i[0]
            df.loc[:, "in_time"] = i[1]
            df.loc[:, "out_time"] = i[4]
            df_pot = pd.concat([df_pot, df], ignore_index=True)
            # df_pot = df_pot.append(df)

        # Write the daily menu items to Menuitems table
        menu_pivot = df_pot.pivot_table(
            index=["time", "name", "in_time", "out_time"],
            values=["quantity"],
            aggfunc=np.sum,
        )
    menu_pivot.loc[:, "date"] = start
    menu_pivot.to_sql("Potatoes", con=db.engine, if_exists="append")

    return 0


def convert_uofm(unit):
    # convert the unit uofm to base quantity
    pack_size = db.session.query(Unitsofmeasure).filter(Unitsofmeasure.name == unit.UofM).first()
    if pack_size:
        return pack_size.base_qty, pack_size.base_uofm
    else:
        return 0, 0


def download_file(filename):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    df.to_excel(writer, sheet_name="Sheet1")
    writer.save()
    output.seek(0)

    # Send the Excel file as a response
    response = make_response(output.read())
    response.headres.set("Content-Disposition", "attachment", filename=filename)
    response.headres.set("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    return response


def receiving_by_purchased_item(file):
    def make_pivot(table):
        vendor = pd.pivot_table(
            table,
            values=["totalQuantity", "ExtCost"],
            index=["ItemName", "VendorName", "unit"],
            aggfunc=np.sum,
        )
        vendor = vendor.reset_index().sort_values(["ItemName", "VendorName"]).set_index("VendorName")
        vendor.loc["Totals"] = vendor.sum(numeric_only=True)
        vendor["CostPerUnit"] = vendor["ExtCost"] / vendor["totalQuantity"]

        restaurant = pd.pivot_table(
            table,
            values=["totalQuantity", "ExtCost"],
            index=["ItemName", "LocationName", "unit"],
            aggfunc=np.sum,
        )
        restaurant = restaurant.reset_index().sort_values(["ItemName", "LocationName"]).set_index("LocationName")
        restaurant.loc["Totals"] = restaurant.sum(numeric_only=True)
        restaurant["CostPerUnit"] = restaurant["ExtCost"] / restaurant["totalQuantity"]
        restaurant.style.format(
            {
                "ExtCost": "${:,.2f}",
                "totalQuantity": "{:,.0f}",
                "CostPerUnit": "${:,.2f}",
            }
        )
        return [vendor, restaurant]

    try:
        file_contents = file.stream.read().decode("utf-8")  # read the file's contents into memory
        df = pd.read_csv(
            StringIO(file_contents),
            skiprows=3,
            usecols=[
                "ItemName",
                "LocationName",
                "TransactionNumber",
                "VendorName",
                "Textbox11",
                "TransactionDate",
                "PurchaseUnit",
                "Quantity",
                "AmountEach",
                "ExtPrice2",
            ],
        )
    except:
        print("No file selected or file error")
        return 1

    try:
        filter = df.Quantity.str.match(r"\((.+)\)")
        df = df[~filter]
    except:
        pass

    item_list = [df.ItemName.unique()]
    item_list = [item for sublist in item_list for item in sublist]
    item_list.sort()

    # TODO merge the UofM table with the df
    with open("/usr/local/share/UofM.json") as file:
        uofm = json.load(file)
    units = pd.DataFrame(uofm)
    df = df.merge(units, left_on="PurchaseUnit", right_on="Name", how="left")
    df.rename(columns={"Textbox11": "VendorNumber"}, inplace=True)
    try:
        df["BaseQty"] = df["BaseQty"].str.replace(",", "").astype(float)
    except:
        df["BaseQty"] = df["BaseQty"].astype(float)
    df["Quantity"] = df["Quantity"].astype(float)
    try:
        df["AmountEach"] = df["AmountEach"].str.replace(",", "").astype(float)
    except:
        df["AmountEach"] = df["AmountEach"].astype(float)
    try:
        df["ExtPrice2"] = df["ExtPrice2"].astype(str).str.replace(",", "").astype(float)
    except:
        df["ExtPrice2"] = df["ExtPrice2"].astype(float)
    # rename df["ExtPrice2"] to df["ExtPrice"] to match other reports
    df.rename(columns={"ExtPrice2": "ExtCost"}, inplace=True)
    # df.loc["Totals"] = df.sum(numeric_only=True)
    sorted_units = (
        df.groupby(["Name"]).mean(numeric_only=True).sort_values(by=["Quantity"], ascending=False).reset_index()
    )
    df_sorted = pd.DataFrame()
    for item in item_list:
        df_temp = df[df.ItemName == item]
        sorted_units = (
            df_temp.groupby(["Name"])
            .mean(numeric_only=True)
            .sort_values(by=["Quantity"], ascending=False)
            .reset_index()
        )
        report_unit = df_temp.iloc[0]["Name"]
        base_factor = df_temp.iloc[0]["BaseQty"]
        df_temp["reportUnit"] = report_unit
        df_temp["base_factor"] = base_factor
        df_temp["totalQuantity"] = df["Quantity"] * df["BaseQty"] / base_factor
        df_temp["unit"] = report_unit
        df_sorted = pd.concat([df_sorted, df_temp], ignore_index=True)

    vendor, restaurant = make_pivot(df_sorted)

    output = BytesIO()
    with pd.ExcelWriter(output) as writer:
        vendor.to_excel(writer, sheet_name="Vendor")
        restaurant.to_excel(writer, sheet_name="Restaurant")
        df_sorted.to_excel(writer, sheet_name="Detail", index=False)

    output.seek(0)

    # Send the Excel file as a response
    return send_file(
        output,
        as_attachment=True,
        download_name="receiving_by_purchased_item.xlsx",
    )


def uofm_update(file):
    try:
        file_contents = file.stream.read().decode("utf-8")  # read the file's contents into memory
        df = pd.read_csv(
            StringIO(file_contents),
            usecols=[
                "Name",
                "EquivalentQty",
                "EquivalentUofM",
                "MeasureType",
                "BaseQty",
                "BaseUofM",
                "UnitOfMeasureId",
            ],
        )
    except Exception as e:
        print("Error reading file:", e)
        return 1

    df.rename(
        columns={
            "Name": "name",
            "EquivalentQty": "equivalent_qty",
            "EquivalentUofM": "equivalent_uofm",
            "MeasureType": "measure_type",
            "BaseQty": "base_qty",
            "BaseUofM": "base_uofm",
            "UnitOfMeasureId": "uofm_id",
        },
        inplace=True,
    )
    print(df)
    # upsert data to Unitsofmeasure table
    try:
        df.to_sql("Unitsofmeasure", db.engine, if_exists="replace", index=False)
    except Exception as e:
        print("Error writing to database:", e)
        return 1

    return 0


def update_recipe_costs():
    """
    write current recipe costs to database
    imported from downloaded report
    """

    df = pd.read_csv("/usr/local/share/export.csv", sep=",")
    df.loc[:, "Name"] = df["Name"].str.replace(r"CHOPHOUSE - NOLA", "CHOPHOUSE-NOLA", regex=True)
    df.loc[:, "Name"] = df["Name"].str.replace(r"CAFÉ", "CAFE", regex=True)
    df.loc[:, "Name"] = df["Name"].str.replace(r"^(?:.*?( -)){2}", "-", regex=True)
    df[["name", "menuitem"]] = df["Name"].str.split(" - ", expand=True)
    df = df.drop(columns=["Name", "__count", "Barcode"])
    df = df.rename(
        columns={
            "RecipeId": "recipeid",
            "Recipe": "recipe",
            "Category1": "category1",
            "Category2": "category2",
            "POSID": "posid",
            "MenuItemId": "menuitemid",
        }
    )
    df = df[
        [
            "name",
            "menuitem",
            "recipe",
            "category1",
            "category2",
            "posid",
            "recipeid",
            "menuitemid",
        ]
    ]

    df_cost = pd.read_csv("/usr/local/share/Menu Price Analysis.csv", skiprows=3, sep=",", thousands=",")
    df_cost.loc[:, "MenuItemName"] = df_cost["MenuItemName"].str.replace(
        r"CHOPHOUSE - NOLA", "CHOPHOUSE-NOLA", regex=True
    )
    df_cost.loc[:, "MenuItemName"] = df_cost["MenuItemName"].str.replace(r"CAFÉ", "CAFE", regex=True)
    df_cost.loc[:, "MenuItemName"] = df_cost["MenuItemName"].str.replace(r"^(?:.*?( -)){2}", "-", regex=True)
    df_cost[["name", "menuitem"]] = df_cost["MenuItemName"].str.split(" - ", expand=True)
    df_cost = df_cost.drop(
        columns=[
            "AvgPrice1",
            "Profit1",
            "Textbox35",
            "TargetMargin1",
            "Textbox43",
            "PriceNeeded1",
            "Location",
            "Cost1",
            "AvgPrice",
            "Profit",
            "ProfitPercent",
            "TargetMargin",
            "Variance",
            "PriceNeeded",
            "MenuItemName",
        ]
    )
    df_cost = df_cost.rename(columns={"Cost": "cost"})
    df_cost = df_cost[["name", "menuitem", "cost"]]

    recipes = pd.merge(df_cost, df, on=["name", "menuitem"], how="left")
    # Need to fix names to match the database
    recipes.loc[:, "name"] = recipes["name"].str.replace(r"'47", "47", regex=True)
    recipes.loc[:, "name"] = recipes["name"].str.replace(r"NEW YORK PRIME-BOCA", "NYP-BOCA", regex=True)
    recipes.loc[:, "name"] = recipes["name"].str.replace(r"NEW YORK PRIME-MYRTLE BEACH", "NYP-MYRTLE BEACH", regex=True)
    recipes.loc[:, "name"] = recipes["name"].str.replace(r"NEW YORK PRIME-ATLANTA", "NYP-ATLANTA", regex=True)

    # TODO may need to delete by recipID if duplicates show up
    recipes.to_sql("Recipes", con=db.engine, if_exists="replace", index_label="id")
    return 0


def set_dates(startdate):
    start = startdate.strftime("%Y-%m-%d")
    target = Calendar.query.filter_by(date=start)

    for i in target:
        day_start = datetime.strptime(i.date, "%Y-%m-%d")
        day_end = day_start + timedelta(days=1)
        seven = day_start - timedelta(days=7)
        thirty = day_start - timedelta(days=30)
        threesixtyfive = day_start - timedelta(days=365)
        week_start = datetime.strptime(i.week_start, "%Y-%m-%d")
        lws = week_start - timedelta(days=7)
        week_end = datetime.strptime(i.week_end, "%Y-%m-%d")
        lwe = week_end - timedelta(days=7)

        d = dict()
        d["day"] = i.day
        d["week"] = i.week
        d["period"] = i.period
        d["year"] = i.year
        d["quarter"] = i.quarter
        d["date"] = day_start.strftime("%A, %B %d %Y")
        d["start_day"] = i.date
        d["end_day"] = day_end.strftime("%Y-%m-%d")
        d["start_week"] = i.week_start
        d["end_week"] = i.week_end
        d["week_to_date"] = i.date
        d["last_seven"] = seven.strftime("%Y-%m-%d")
        d["start_period"] = i.period_start
        d["end_period"] = i.period_end
        d["period_to_date"] = i.date
        d["last_thirty"] = thirty.strftime("%Y-%m-%d")
        d["start_quarter"] = i.quarter_start
        d["end_quarter"] = i.quarter_end
        d["quarter_to_date"] = i.date
        d["start_year"] = i.year_start
        d["end_year"] = i.year_end
        d["year_to_date"] = i.date
        d["last_threesixtyfive"] = threesixtyfive.strftime("%Y-%m-%d")
        d["start_day_ly"] = get_lastyear(i.date)
        d["end_day_ly"] = get_lastyear(day_end.strftime("%Y-%m-%d"))
        d["start_week_ly"] = get_lastyear(i.week_start)
        d["end_week_ly"] = get_lastyear(i.week_end)
        d["week_to_date_ly"] = get_lastyear(i.date)
        d["start_period_ly"] = get_lastyear(i.period_start)
        d["end_period_ly"] = get_lastyear(i.period_end)
        d["period_to_date_ly"] = get_lastyear(i.date)
        d["start_quarter_ly"] = get_lastyear(i.quarter_start)
        d["end_quarter_ly"] = get_lastyear(i.quarter_end)
        d["quarter_to_date_ly"] = get_lastyear(i.date)
        d["start_year_ly"] = get_lastyear(i.year_start)
        d["end_year_ly"] = get_lastyear(i.year_end)
        d["year_to_date_ly"] = get_lastyear(i.date)
        d["start_previous_week"] = lws.strftime("%Y-%m-%d")
        d["end_previous_week"] = lwe.strftime("%Y-%m-%d")

    return d

def get_user_list():
    query = (
            db.session.query(
                Users.id,
                Users.email,
                Users.active,
                Users.confirmed_at,
                Users.last_login_at,
                Users.login_count,
                )
            .order_by(Users.last_login_at.desc()
            ).all()
    )
    #user_table = pd.DataFrame.from_records(
    #        query,
    #        columns=
    #              [
    #                  "id",
    #                  "email",
    #                  "active",
    #                  "confirmed_at",
    #                  "last_login_at",
    #                  "login_count"
    #                  ]
    #              )
    return query
