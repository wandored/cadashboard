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
from dashapp.authentication.models import (
    LaborTotals,
    PotatoChart,  # noqa: F401
    PotatoLoadTimes,  # noqa: F401
    PotatoSales,
    Restaurants,
    SalesCategory,
    SalesCarryout,
    SalesRecordsDay,  # noqa: F401
    SalesRecordsPeriod,  # noqa: F401
    SalesRecordsWeek,  # noqa: F401
    SalesRecordsYear,  # noqa: F401
    SalesTotals,
    SalesDaypart,
    StockCount,
    TableTurns,
    Users,
    db,
    Calendar,  # noqa: F401
    GiftCardSales,
    GiftCardRedeem,
)
from sqlalchemy import func

from icecream import ic


def get_sales_charts(start, end, time, store_list):
    chart = (
        db.session.query(func.sum(SalesTotals.net_sales).label("total_sales"))
        .select_from(SalesTotals)
        .group_by(time)
        .order_by(time)
        .filter(SalesTotals.date.between(start, end), SalesTotals.id.in_(store_list))
    )
    value = [v.total_sales for v in chart]
    return value


# daypart sales
def get_daypart_sales(start, end, store_list):
    cal_query = Calendar.query.with_entities(
        Calendar.date, Calendar.dow, Calendar.week, Calendar.period, Calendar.year
    ).filter(Calendar.date.between(start, end))
    cal_df = pd.DataFrame(cal_query, columns=["date", "dow", "week", "period", "year"])
    query = (
        db.session.query(
            SalesDaypart.date,
            SalesDaypart.daypart,
            SalesDaypart.dow,
            SalesDaypart.week,
            SalesDaypart.period,
            SalesDaypart.year,
            func.sum(SalesDaypart.net_sales).label("sales"),
            func.sum(SalesDaypart.guest_count).label("guests"),
        )
        .filter(
            SalesDaypart.date.between(start, end),
            SalesDaypart.id.in_(store_list),
        )
        .group_by(
            SalesDaypart.date,
            SalesDaypart.daypart,
            SalesDaypart.dow,
            SalesDaypart.week,
            SalesDaypart.period,
            SalesDaypart.year,
        )
        .order_by(SalesDaypart.date)
        .all()
    )
    df = pd.DataFrame.from_records(
        query,
        columns=[
            "date",
            "daypart",
            "dow",
            "week",
            "period",
            "year",
            "sales",
            "guests",
        ],
    )
    df_lunch = df[df["daypart"] == "Lunch"]
    df_lunch = df_lunch.merge(
        cal_df, how="outer", on=["date", "dow", "week", "period", "year"]
    )
    df_lunch["daypart"] = df_lunch["daypart"].fillna("Lunch")
    df_dinner = df[df["daypart"] == "Dinner"]
    df_dinner = df_dinner.merge(
        cal_df, how="outer", on=["date", "dow", "week", "period", "year"]
    )
    df_dinner["daypart"] = df_dinner["daypart"].fillna("Dinner")
    df_lunch = df_lunch.sort_values(by=["date"])
    df_dinner = df_dinner.sort_values(by=["date"])
    df_lunch = df_lunch.fillna(0)
    df_dinner = df_dinner.fillna(0)
    print(df_lunch)
    print(df_dinner)
    return df_lunch, df_dinner


def get_giftcard_sales(start, end, store_list):
    cal_query = Calendar.query.with_entities(
        Calendar.date, Calendar.dow, Calendar.week, Calendar.period, Calendar.year
    ).filter(Calendar.date.between(start, end))
    cal_df = pd.DataFrame(cal_query, columns=["date", "dow", "week", "period", "year"])
    query = (
        db.session.query(
            GiftCardSales.date,
            GiftCardSales.dow,
            GiftCardSales.week,
            GiftCardSales.period,
            GiftCardSales.year,
            func.sum(GiftCardSales.amount).label("sales"),
            func.sum(GiftCardSales.quantity).label("count"),
        )
        .select_from(GiftCardSales)
        .filter(
            GiftCardSales.date.between(start, end), GiftCardSales.id.in_(store_list)
        )
        .group_by(
            GiftCardSales.date,
            GiftCardSales.dow,
            GiftCardSales.week,
            GiftCardSales.period,
            GiftCardSales.year,
        )
        .order_by(GiftCardSales.date)
        .all()
    )
    df = pd.DataFrame.from_records(
        query, columns=["date", "dow", "week", "period", "year", "sales", "count"]
    )
    df = df.merge(cal_df, how="outer", on=["date", "dow", "week", "period", "year"])
    df = df.fillna(0)
    df = df.sort_values(by=["date"])
    return df


def get_giftcard_redeem(start, end, store_list):
    cal_query = Calendar.query.with_entities(
        Calendar.date, Calendar.dow, Calendar.week, Calendar.period, Calendar.year
    ).filter(Calendar.date.between(start, end))
    cal_df = pd.DataFrame(cal_query, columns=["date", "dow", "week", "period", "year"])
    query = (
        db.session.query(
            GiftCardRedeem.date,
            GiftCardRedeem.dow,
            GiftCardRedeem.week,
            GiftCardRedeem.period,
            GiftCardRedeem.year,
            func.sum(GiftCardRedeem.amount).label("sales"),
        )
        .select_from(GiftCardRedeem)
        .filter(
            GiftCardRedeem.date.between(start, end), GiftCardRedeem.id.in_(store_list)
        )
        .group_by(
            GiftCardRedeem.date,
            GiftCardRedeem.dow,
            GiftCardRedeem.week,
            GiftCardRedeem.period,
            GiftCardRedeem.year,
        )
        .order_by(GiftCardRedeem.date)
        .all()
    )
    df = pd.DataFrame.from_records(
        query, columns=["date", "dow", "week", "period", "year", "sales"]
    )
    df = df.merge(cal_df, how="outer", on=["date", "dow", "week", "period", "year"])
    df = df.fillna(0)
    df = df.sort_values(by=["date"])
    return df


def get_category_sales(start, end, categories, store_list):
    cal_query = Calendar.query.with_entities(
        Calendar.date, Calendar.dow, Calendar.week, Calendar.period, Calendar.year
    ).filter(Calendar.date.between(start, end))
    cal_df = pd.DataFrame(cal_query, columns=["date", "dow", "week", "period", "year"])
    query = (
        db.session.query(
            SalesCategory.date,
            SalesCategory.dow,
            SalesCategory.week,
            SalesCategory.period,
            SalesCategory.year,
            func.sum(SalesCategory.amount).label("sales"),
            func.sum(SalesCategory.quantity).label("count"),
        )
        .select_from(SalesCategory)
        .filter(
            SalesCategory.date.between(start, end),
            SalesCategory.id.in_(store_list),
            SalesCategory.category.in_(categories),
        )
        .group_by(
            SalesCategory.date,
            SalesCategory.dow,
            SalesCategory.week,
            SalesCategory.period,
            SalesCategory.year,
        )
        .order_by(SalesCategory.date)
        .all()
    )
    df = pd.DataFrame.from_records(
        query, columns=["date", "dow", "week", "period", "year", "sales", "count"]
    )
    df = df.merge(cal_df, how="outer", on=["date", "dow", "week", "period", "year"])
    df = df.fillna(0)
    df = df.sort_values(by=["date"])
    return df


def get_togo_sales(start, end, store_list):
    cal_query = Calendar.query.with_entities(
        Calendar.date, Calendar.dow, Calendar.week, Calendar.period, Calendar.year
    ).filter(Calendar.date.between(start, end))
    cal_df = pd.DataFrame(cal_query, columns=["date", "dow", "week", "period", "year"])
    query = (
        db.session.query(
            SalesCarryout.date,
            SalesCarryout.dow,
            SalesCarryout.week,
            SalesCarryout.period,
            SalesCarryout.year,
            func.sum(SalesCarryout.amount).label("sales"),
            func.sum(SalesCarryout.quantity).label("count"),
        )
        .select_from(SalesCarryout)
        .filter(
            SalesCarryout.date.between(start, end),
            SalesCarryout.id.in_(store_list),
        )
        .group_by(
            SalesCarryout.date,
            SalesCarryout.dow,
            SalesCarryout.week,
            SalesCarryout.period,
            SalesCarryout.year,
        )
        .order_by(SalesCarryout.date)
        .all()
    )
    df = pd.DataFrame.from_records(
        query, columns=["date", "dow", "week", "period", "year", "sales", "count"]
    )
    df = df.merge(cal_df, how="outer", on=["date", "dow", "week", "period", "year"])
    df = df.fillna(0)
    df = df.sort_values(by=["date"])
    return df


def find_day_with_sales(**kwargs):
    """
    when a date is submitted on the dashboard, we first check if the date
    has sales, if not it goes back one and checks until if finds a day with sales
    """
    if "store" in kwargs:
        while not SalesTotals.query.filter_by(
            date=kwargs["day"], store=kwargs["store"]
        ).first():
            # date = datetime.strptime(kwargs["day"], "%Y-%m-%d")
            next_day = kwargs["day"] - timedelta(days=1)
            kwargs["day"] = next_day
    else:
        while not SalesTotals.query.filter_by(date=kwargs["day"]).first():
            # date = datetime.date(kwargs["day"])
            next_day = kwargs["day"] - timedelta(days=1)
            kwargs["day"] = next_day
    return next_day


def get_timeing_data(start, end, store_list):
    results = (
        db.session.query(TableTurns)
        .filter(TableTurns.date.between(start, end), TableTurns.id.in_(store_list))
        .all()
    )
    # convert results to list of dictionaries
    data = [
        {
            "store": row.store,
            "date": row.date,
            "dow": row.dow,
            "week": row.week,
            "period": row.period,
            "year": row.year,
            "bar": row.bar,
            "dining_room": row.dining_room,
            "handheld": row.handheld,
            "patio": row.patio,
            "online_ordering": row.online_ordering,
        }
        for row in results
    ]

    df = pd.DataFrame(data)
    columns_to_convert = [
        "bar",
        "dining_room",
        "handheld",
        "patio",
        "online_ordering",
    ]
    if not df.empty:
        for column in columns_to_convert:
            # if df[column] == 'nan' change to 0
            df[column] = df[column].fillna(0)
            df[column] = (
                pd.to_timedelta(df[column].astype(str)).dt.total_seconds().astype(int)
            )
        return df
    else:
        # return empty dataframe
        cal_query = Calendar.query.with_entities(
            Calendar.date, Calendar.dow, Calendar.week, Calendar.period, Calendar.year
        ).filter(Calendar.date.between(start, end))
        df = pd.DataFrame(cal_query, columns=["date", "dow", "week", "period", "year"])
        df["store"] = results.name
        df["bar"] = 0
        df["dining_room"] = 0
        df["handheld"] = 0
        df["patio"] = 0
        df["online_ordering"] = 0
        return df


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
        ly_target = Calendar.query.filter_by(
            year=lst_year, period=period, week=week, day=day
        )
        for x in ly_target:
            dt_date = x.date
    return dt_date


def get_period(startdate):
    """
    returns the period integer for the current startdate
    """
    target = Calendar.query.filter_by(date=startdate)

    return target


def get_item_avg_cost(regex, start, end, id):
    # Return average cost for purchase item

    avg_cost = 0
    query = (
        db.session.query(
            func.sum(Purchases.amount).label("cost"),
            func.sum(Purchases.quantity).label("count"),
        )
        .filter(
            Purchases.item.regexp_match(regex),
            Purchases.date.between(start, end),
            Purchases.id == id,
        )
        .all()
    )
    for q in query:
        try:
            avg_cost = q[0] / q[1]
        except:
            avg_cost = 0

    return avg_cost


def convert_uofm(unit):
    # convert the unit uofm to base quantity
    pack_size = (
        db.session.query(UnitsOfMeasure)
        .filter(UnitsOfMeasure.name == unit.UofM)
        .first()
    )
    if pack_size:
        return pack_size.base_qty, pack_size.base_uofm
    else:
        return 0, 0


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
        d["start_week"] = i.week_start
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
