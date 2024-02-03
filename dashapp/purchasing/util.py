"""
Dashboard by wandored
"""
from datetime import timedelta
from functools import cache

import numpy as np
import pandas as pd
from icecream import ic
from sqlalchemy import func

from dashapp.authentication.models import (
    Calendar,
    Purchases,
    UnitsOfMeasure,
    db,
)


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


def set_dates(startdate):
    target = Calendar.query.filter_by(date=startdate)
    d = {}

    for i in target:
        day_end = i.date + timedelta(days=1)
        seven = i.date - timedelta(days=7)
        thirty = i.date - timedelta(days=30)
        threesixtyfive = i.date - timedelta(days=365)

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


def convert_uofm(unit):
    # convert the unit uofm to base quantity
    pack_size = (
        db.session.query(UnitsOfMeasure)
        .filter(UnitsOfMeasure.name == unit.uofm)
        .first()
    )
    if pack_size:
        return pack_size.base_qty, pack_size.base_uofm
    else:
        return 0, 0


def get_vendors(regex, days):
    query = (
        Purchases.query.with_entities(Purchases.company)
        .filter(
            Purchases.item.regexp_match(regex),
            Purchases.company != "None",
            Purchases.date >= days,
        )
        .group_by(Purchases.company)
    ).all()
    return query


@cache
def get_cost_per_vendor(regex, start, end, stores):
    query = (
        db.session.query(
            Purchases.company,
            Purchases.uofm,
            func.sum(Purchases.quantity).label("count"),
            func.sum(Purchases.amount).label("cost"),
        )
        .filter(
            Purchases.item.regexp_match(regex),
            Purchases.date.between(start, end),
            Purchases.id.in_(stores),
        )
        .group_by(
            Purchases.company,
            Purchases.uofm,
        )
    ).all()
    item_list = []
    for q in query:
        qty, uofm = convert_uofm(q)
        row_dict = {
            "company": q[0],
            "uofm": q[1],
            "count": q[2],
            "cost": q[3],
            "base_qty": qty,
            "base_uofm": uofm,
        }
        item_list.append(row_dict)
    df = pd.DataFrame(item_list)
    sorted_units = (
        df.groupby(["uofm"])
        .mean(["count", "cost"])
        .sort_values(by=["count"], ascending=False)
        .reset_index()
    )
    report = sorted_units.iloc[0]
    df = df.groupby(["company", "uofm"]).sum(["count", "cost"]).reset_index()

    if not df.empty:
        # get common unit to compare costs and sort
        df["base_cost"] = ((df["cost"] / df["count"]) / df["base_qty"]) * report[
            "base_qty"
        ]
        df["unit_cost"] = df["cost"] / df["count"]
        df = df[df.unit_cost.notna()]
        table = pd.pivot_table(
            df,
            values=["unit_cost", "count", "base_cost"],
            index=["company", "uofm"],
            aggfunc={"unit_cost": np.mean, "count": np.sum, "base_cost": np.mean},
        )
        if not table.empty:
            table.sort_values(by=["base_cost"], inplace=True)
            return table
    df = pd.DataFrame()
    return df


@cache
def get_cost_per_store(regex, start, end, stores):
    query = (
        db.session.query(
            Purchases.store,
            Purchases.uofm,
            func.sum(Purchases.quantity).label("count"),
            func.sum(Purchases.amount).label("cost"),
        )
        .filter(
            Purchases.item.regexp_match(regex),
            Purchases.date.between(start, end),
            Purchases.id.in_(stores),
        )
        .group_by(
            Purchases.store,
            Purchases.uofm,
        )
    ).all()
    item_list = []
    for q in query:
        qty, uofm = convert_uofm(q)
        row_dict = {
            "store": q[0],
            "uofm": q[1],
            "count": q[2],
            "cost": q[3],
            "base_qty": qty,
            "base_uofm": uofm,
        }
        item_list.append(row_dict)
    df = pd.DataFrame(item_list)
    sorted_units = (
        df.groupby(["uofm"])
        .mean(["count", "cost"])
        .sort_values(by=["count"], ascending=False)
        .reset_index()
    )
    report = sorted_units.iloc[0]
    df = df.groupby(["store", "uofm"]).sum(["count", "cost"]).reset_index()
    mask = df["uofm"] != report.uofm
    df.loc[mask, "uofm"] = report.uofm
    df.loc[mask, "count"] = (df.loc[mask, "base_qty"] / report["base_qty"]) * df.loc[
        mask, "count"
    ]
    df.loc[mask, "base_qty"] = report.base_qty

    if not df.empty:
        df["unit_cost"] = ((df["cost"] / df["count"]) / df["base_qty"]) * report[
            "base_qty"
        ]
        df["unit_qty"] = (df["count"] * df["base_qty"]) / report["base_qty"]
        df["report_unit"] = report.uofm

        df.drop(columns=["count", "cost", "base_qty"], inplace=True)
        df = df[df.unit_cost.notna()]
        table = pd.pivot_table(
            df,
            values=["unit_cost", "unit_qty"],
            index=["store", "report_unit"],
            aggfunc={"unit_cost": np.mean, "unit_qty": np.sum},
        )
        if not table.empty:
            table.sort_values(by=["unit_cost"], inplace=True)
            return table
    df = pd.DataFrame()
    return df


def period_purchases(regex, start, end, stores):
    # generate list of purchase costs per period for charts
    cal_query = Calendar.query.with_entities(
        Calendar.date, Calendar.week, Calendar.period, Calendar.year
    ).all()
    cal_df = pd.DataFrame(cal_query, columns=["date", "week", "period", "year"])

    query = (
        db.session.query(
            Purchases.date,
            Purchases.company,
            Purchases.store,
            Purchases.uofm,
            func.sum(Purchases.quantity).label("count"),
            func.sum(Purchases.amount).label("cost"),
        )
        .filter(
            Purchases.item.regexp_match(regex),
            Purchases.date.between(start, end),
            Purchases.id.in_(stores),
        )
        .group_by(
            Purchases.date,
            Purchases.company,
            Purchases.store,
            Purchases.uofm,
        )
    ).all()

    item_list = []
    for q in query:
        if not q.uofm:
            continue
        qty, uofm = convert_uofm(q)
        row_dict = {
            "date": q[0],
            "company": q[1],
            "store": q[2],
            "uofm": q[3],
            "count": q[4],
            "cost": q[5],
            "base_qty": qty,
            "base_uofm": uofm,
        }
        row_dict["unit_qty"] = np.where(
            row_dict["base_uofm"] == "OZ-wt",
            row_dict["count"] * row_dict["base_qty"] / 16,
            np.where(
                row_dict["base_uofm"] == "OZ-fl",
                row_dict["count"] * row_dict["base_qty"] / 128,
                row_dict["count"] * row_dict["base_qty"],
            ),
        )
        row_dict["unit_qty"] = np.single(row_dict["unit_qty"])
        item_list.append(row_dict)
    df = pd.DataFrame(item_list)

    if not df.empty:
        # fills in months with no purchases
        df = df.merge(cal_df, on="date", how="outer")
        df = df.sort_values("period")
        df = df.groupby(["period"]).sum(numeric_only=True)
        df["unit_cost"] = (df["cost"] / df["unit_qty"]).astype(float)
        df["unit_cost"] = df["unit_cost"].fillna(0)
        df_list = df["unit_cost"].tolist()
        return df_list
    else:
        return [0] * len(cal_df.period.unique().tolist())


def get_category_costs(regex, start, end, stores):
    # Return list of sales
    query = (
        db.session.query(
            Purchases.account,
            func.sum(Purchases.credit).label("credits"),
            func.sum(Purchases.debit).label("costs"),
        )
        .filter(
            Purchases.account.in_(regex),
            Purchases.date.between(start, end),
            Purchases.id.in_(stores),
        )
        .group_by(Purchases.account)
        .order_by(func.sum(Purchases.debit).desc())
    ).all()
    results = pd.DataFrame(query, columns=["Account", "Credits", "Costs"])
    results["Totals"] = results["Costs"] - results["Credits"]
    return results


def get_category_topten(regex, start, end, stores):
    query = (
        db.session.query(
            Purchases.item,
            func.sum(Purchases.debit).label("cost"),
        )
        .filter(
            Purchases.account.in_(regex),
            Purchases.date.between(start, end),
            Purchases.id.in_(stores),
        )
        .group_by(Purchases.item)
        .order_by(func.sum(Purchases.debit).desc())
    ).limit(10)
    df = pd.DataFrame(query, columns=["Item", "Cost"])

    return df


def get_restaurant_topten(regex, start, end, stores):
    query = (
        db.session.query(
            Purchases.store,
            func.sum(Purchases.debit).label("cost"),
        )
        .filter(
            Purchases.account.in_(regex),
            Purchases.date.between(start, end),
            Purchases.id.in_(stores),
        )
        .group_by(Purchases.store)
        .order_by(func.sum(Purchases.debit).desc())
    ).all()
    dframe = pd.DataFrame(query, columns=["Restaurant", "Cost"])

    return dframe


def get_vendor_topten(regex, start, end, stores):
    query = (
        db.session.query(
            Purchases.company,
            func.sum(Purchases.debit).label("cost"),
        )
        .filter(
            Purchases.account.in_(regex),
            Purchases.date.between(start, end),
            Purchases.id.in_(stores),
        )
        .group_by(Purchases.company)
        .order_by(func.sum(Purchases.debit).desc())
    ).limit(10)
    dframe = pd.DataFrame(query, columns=["Vendor", "Cost"])

    return dframe


def get_item_topten(regex, start, end, stores):
    query = (
        db.session.query(
            Purchases.item,
            func.sum(Purchases.debit).label("cost"),
        )
        .filter(
            Purchases.item.regexp_match(regex),
            Purchases.date.between(start, end),
            Purchases.id.in_(stores),
        )
        .group_by(Purchases.item)
        .order_by(func.sum(Purchases.debit).desc())
    ).limit(10)
    dframe = pd.DataFrame(query, columns=["Item", "Cost"])

    return dframe
