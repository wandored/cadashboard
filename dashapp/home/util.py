"""
home/util.py
Dashboard by wandored
"""
import json
import requests
from flask import send_file
import pandas as pd
import numpy as np
from io import StringIO, BytesIO
from dashapp.config import Config
from datetime import timedelta
from dashapp.authentication.models import *
from sqlalchemy import func


def get_daypart_sales(start, end, store, day_part):
    query = (
        db.session.query(
            SalesDaypart.date,
            SalesDaypart.dow,
            SalesDaypart.week,
            SalesDaypart.period,
            SalesDaypart.year,
            SalesDaypart.daypart,
            SalesDaypart.net_sales,
            SalesDaypart.guest_count,
        )
        .filter(SalesDaypart.date.between(start, end),
                SalesDaypart.daypart == (day_part),
                SalesDaypart.store == store)
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
    """
    when a date is submitted on the dashboard, we first check if the date
    has sales, if not it goes back one and checks until if finds a day with sales
    """
    if "store" in kwargs:
        while not SalesTotals.query.filter_by(date=kwargs["day"], name=kwargs["store"]).first():
            #date = datetime.strptime(kwargs["day"], "%Y-%m-%d")
            next_day = kwargs['day'] - timedelta(days=1)
            print(next_day)
            kwargs["day"] = next_day
    else:
        while not SalesTotals.query.filter_by(date=kwargs["day"]).first():
            #date = datetime.date(kwargs["day"])
            next_day = kwargs['day'] - timedelta(days=1)
            print(next_day)
            kwargs["day"] = next_day
    return next_day


#def refresh_data(start, end):
#    """
#    When new date submitted, the data for that date will be replaced with new data from R365
#    We check if there are infact sales for that day, if not, it resets to yesterday, if
#    there are sales, then labor is polled
#    """
#    # delete current days data from database and replace with fresh data
#    Sales.query.filter_by(date=start).delete()
#    Labor.query.filter_by(date=start).delete()
#    Menuitems.query.filter_by(date=start).delete()
#    Potatoes.query.filter_by(date=start).delete()
#    db.session.commit()
#
#    # refres the sales data and check to make sure there are sales for that day
#    baddates = sales_employee(start, end)
#    if baddates == 1:
#        return 1
#
#    # refresh labor
#    labor_detail(start)
#    # refresh categories and menuitems
#    # TODO add sales_payments
#    sales_detail(start, end)
##    potato_sales(start)
#    return 0


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
    """
    returns the period integer for the current startdate
    """
    target = Calendar.query.filter_by(date=startdate)

    return target


#def removeSpecial(df):
#    """Removes specialty items from the menuitems dataframe"""
#    file = open("../../specialty.txt")
#    specialty_list = file.read().split("\n")
#    file.close
#    for item in specialty_list:
#        df = df.drop(df[df.menuitem == item].index)
#    return df
#
#
#def sales_employee(start, end):
#    url_filter = "$filter=date ge {}T00:00:00Z and date le {}T00:00:00Z".format(start, end)
#    query = "$select=dayPart,netSales,numberofGuests,location&{}".format(url_filter)
#    url = "{}/SalesEmployee?{}".format(Config.SRVC_ROOT, query)
#    rqst = make_HTTP_request(url)
#    df = make_dataframe(rqst)
#    if df.empty:
#        return 1
#
#    data = db.session.query(Restaurants).all()
#    df_loc = pd.DataFrame([(x.name, x.location) for x in data], columns=["name", "location"])
#    df_merge = df_loc.merge(df, on="location")
#    df_merge = df_merge.rename(columns={"netSales": "sales", "numberofGuests": "guests", "dayPart": "daypart"})
#
#    # pivot data and write to database
#    df_pivot = df_merge.pivot_table(index=["name", "daypart"], values=["sales", "guests"], aggfunc=np.sum)
#    df_pivot.loc[:, "date"] = start
#    df_pivot.to_sql("Sales", con=db.engine, if_exists="append")
#    return 0
#
#
#def labor_detail(start):
#    url_filter = "$filter=dateWorked eq {}T00:00:00Z".format(start)
#    query = "$select=jobTitle,hours,total,location_ID&{}".format(url_filter)
#    url = "{}/LaborDetail?{}".format(Config.SRVC_ROOT, query)
#    rqst = make_HTTP_request(url)
#    df = make_dataframe(rqst)
#    if df.empty:
#        return 1
#
#    with open("/usr/local/share/labor_categories.json") as labor_file:
#        labor_cats = json.load(labor_file)
#    df_cats = pd.DataFrame(list(labor_cats.items()), columns=["job", "category"])
#
#    data = db.session.query(Restaurants).all()
#    df_loc = pd.DataFrame([(x.name, x.location) for x in data], columns=["name", "location"])
#    df_merge = df_loc.merge(df, left_on="location", right_on="location_ID")
#    df_merge = df_merge.rename(columns={"jobTitle": "job", "total": "dollars"})
#    df_merge = df_merge.merge(df_cats, on="job")
#    df_pivot = df_merge.pivot_table(index=["name", "category", "job"], values=["hours", "dollars"], aggfunc=np.sum)
#    df_pivot.loc[:, "date"] = start
#    df_pivot.to_sql("Labor", con=db.engine, if_exists="append")
#    return 0
#
#
#def sales_detail(start, end):
#    url_filter = "$filter=date ge {}T00:00:00Z and date le {}T00:00:00Z".format(start, end)
#    query = "$select=menuitem,amount,date,quantity,category,location&{}".format(url_filter)
#    url = "{}/SalesDetail?{}".format(Config.SRVC_ROOT, query)
#    rqst = make_HTTP_request(url)
#    df = make_dataframe(rqst)
#    if df.empty:
#        return 1
#
#    with open("/usr/local/share/major_categories.json") as file:
#        major_cats = json.load(file)
#    df_cats = pd.DataFrame(list(major_cats.items()), columns=["menu_category", "category"])
#
#    data = db.session.query(Restaurants).all()
#    df_loc = pd.DataFrame([(x.name, x.location) for x in data], columns=["name", "location"])
#    df_merge = df_loc.merge(df, on="location")
#    df_merge = df_merge.drop(columns=["location"])
#
#    df_menu = df_merge.merge(df_cats, left_on="category", right_on="menu_category")
#
#    df_menu.loc[:, "menuitem"] = df_menu["menuitem"].str.replace(r"CHOPHOUSE - NOLA", "CHOPHOUSE-NOLA", regex=True)
#    df_menu.loc[:, "menuitem"] = df_menu["menuitem"].str.replace(r"CAFÉ", "CAFE", regex=True)
#    df_menu.loc[:, "menuitem"] = df_menu["menuitem"].str.replace(r"^(?:.*?( -)){2}", "-", regex=True)
#    df_menu.loc[:, "menuitem"] = df_menu["menuitem"].str.strip()
#    dafilter = df_menu["menuitem"].str.contains("VOID")
#    df_clean = df_menu[~dafilter]
#    df_temp = df_clean.copy()
#    df_temp[["x", "menuitem"]] = df_clean["menuitem"].str.split(" - ", expand=True)
#    df_clean = df_temp.drop(columns=["category_x", "x"])
#    df_clean = df_clean.rename(columns={"category_y": "category"})
#    #    menuitems = removeSpecial(df_clean)  ### fix the file location before making this active
#    # Write the daily menu items to Menuitems table
#    menu_pivot = df_clean.pivot_table(
#        index=["name", "menuitem", "category", "menu_category"],
#        values=["amount", "quantity"],
#        aggfunc=np.sum,
#    )
#    menu_pivot.loc[:, "date"] = start
#    menu_pivot.to_sql("Menuitems", con=db.engine, if_exists="append")
#
#    return 0


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


#def get_glaccount_costs(start, end, acct, store, epoch):
#    # Return list of sales
#    query = (
#        db.session.query(
#            func.sum(Transactions.credit).label("credits"),
#            func.sum(Transactions.debit).label("costs"),
#        )
#        .select_from(Transactions)
#        .join(Calendar, Calendar.date == Transactions.date)
#        .group_by(epoch)
#        .order_by(epoch)
#        .filter(
#            Transactions.date.between(start, end),
#            Transactions.account == acct,
#            Transactions.name == store,
#        )
#    )
#    results = []
#    for q in query:
#        amount = q.costs - q.credits
#        results.append(amount)
#    return results


def get_item_avg_cost(regex, start, end, id):
    # Return average cost for purchase item

    avg_cost = 0
    query = db.session.query(
        func.sum(Purchases.debit).label("cost"),
        func.sum(Purchases.quantity).label("count"),
    ).filter(
        Purchases.item.regexp_match(regex),
        Purchases.date.between(start, end),
        Purchases.id == id,
    ).all()
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


def convert_uofm(unit):
    # convert the unit uofm to base quantity
    pack_size = db.session.query(unitsofmeasure).filter(unitsofmeasure.name == unit.UofM).first()
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
    # upsert data to Unitsofmeasure table
    try:
        df.to_sql("unitsofmeasure", db.engine, if_exists="replace", index=False)
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
    target = Calendar.query.filter_by(date=startdate)
    d = {}

    for i in target:

        day_end = i.date + timedelta(days=1)
        seven = i.date - timedelta(days=7)
        thirty = i.date - timedelta(days=30)
        threesixtyfive = i.date - timedelta(days=365)

        d["dow"] = i.dow
        d["day"] = i.day
        d["week"] = i.week
        d["period"] = i.period
        d["year"] = i.year
        d["quarter"] = i.quarter
        d["date"] = i.date.strftime("%A, %B %d %Y")
        d["start_day"] = i.date
        d["end_day"] = i.date + timedelta(days=1)
        d['start_week'] = i.week_start
        d["end_week"] = i.week_end
        d["week_to_date"] = i.date
        d["last_seven"] = i.date - timedelta(days=7)
        d["start_period"] = i.period_start
        d["end_period"] = i.period_end
        d["period_to_date"] = i.date
        d["last_thirty"] = i.date - timedelta(days=30)
        d["start_quarter"] = i.quarter_start
        d["end_quarter"] = i.quarter_end
        d["quarter_to_date"] = i.date
        d["start_year"] = i.year_start
        d["end_year"] = i.year_end
        d["year_to_date"] = i.date
        d["last_threesixtyfive"] = i.date - timedelta(days=365) 
        d["start_day_ly"] = get_lastyear(i.date)
        d["end_day_ly"] = get_lastyear(d["end_day"])
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
        d["start_previous_week"] = i.week_start - timedelta(days=7)
        d["end_previous_week"] = i.week_end - timedelta(days=7)

    return d
