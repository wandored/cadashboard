"""
Dashboard by wandored
"""
from functools import lru_cache
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dashapp.authentication.models import *
from sqlalchemy import func


def get_lastyear(date):
    target = calendar.query.filter_by(date=date)
    dt_date = date

    for i in target:
        lst_year = str(int(i.year) - 1)
        period = i.period
        week = i.week
        day = i.day
        ly_target = calendar.query.filter_by(year=lst_year, period=period, week=week, day=day)
        for x in ly_target:
            dt_date = x.date
    return dt_date


def set_dates(startdate):

    target = calendar.query.filter_by(date=startdate)
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


def convert_uofm(unit):
    # convert the unit uofm to base quantity
    pack_size = db.session.query(Unitsofmeasure).filter(Unitsofmeasure.name == unit.UofM).first()
    if pack_size:
        return pack_size.base_qty, pack_size.base_uofm
    else:
        return 0, 0


def get_vendors(regex, days):
    query = (
        Transactions.query.with_entities(Transactions.company)
        .filter(
            Transactions.item.regexp_match(regex),
            Transactions.company != "None",
            Transactions.date >= days,
        )
        .group_by(Transactions.company)
    ).all()
    return query


@lru_cache
def get_cost_per_vendor(regex, start, end, stores):

    query = (
        db.session.query(
            Transactions.company,
            Transactions.UofM,
            func.sum(Transactions.quantity).label("quantity"),
            func.sum(Transactions.amount).label("cost"),
        )
        .filter(
            Transactions.item.regexp_match(regex),
            Transactions.date.between(start, end),
            Transactions.store_id.in_(stores),
            Transactions.type == "AP Invoice",
        )
        .group_by(
            Transactions.company,
            Transactions.UofM,
        )
    ).all()
    item_list = []
    for q in query:
        qty, uofm = convert_uofm(q)
        row_dict = dict(q)
        row_dict["base_qty"] = qty
        row_dict["base_uofm"] = uofm
        item_list.append(row_dict)
    df = pd.DataFrame(item_list)
    sorted_units = (
        df.groupby(["UofM"]).mean(["quantity", "cost"]).sort_values(by=["quantity"], ascending=False).reset_index()
    )
    report = sorted_units.iloc[0]
    df = df.groupby(["company"]).sum(["quantity", "cost"]).reset_index()

    if not df.empty:
        df["unit_cost"] = ((df["cost"] / df["quantity"]) / df["base_qty"]) * report["base_qty"]
        df["unit_qty"] = (df["quantity"] * df["base_qty"]) / report["base_qty"]
        df["report_unit"] = report.UofM

        #df["base_cost"] = (df["cost"] / df["quantity"]) / df["base_qty"]
        ## df["unit_qty"] = (df["quantity"] * df["base_qty"])
        #df["unit_cost"] = df["base_cost"] * df["base_qty"]
        #df["report_unit"] = report.UofM
        # calculate the unit cost based on base_uofm value
        # df["unit_cost"] = np.where(
        #   df["base_uofm"] == "OZ-wt",
        #   ((df["cost"] / df["quantity"]) / df["base_qty"] * 16).astype(float),
        #   np.where(
        #       df["base_uofm"] == "OZ-fl",
        #       ((df["cost"] / df["quantity"]) / df["base_qty"] * 128).astype(float),
        #       ((df["cost"] / df["quantity"]) / df["base_qty"] * 1).astype(float),
        #   ),
        # )
        # df["unit_qty"] = np.where(
        #   df["base_uofm"] == "OZ-wt",
        #   (df["quantity"] * df["base_qty"] / 16).astype(float),
        #   np.where(
        #       df["base_uofm"] == "OZ-fl",
        #       (df["quantity"] * df["base_qty"] / 128).astype(float),
        #       (df["quantity"] * df["base_qty"]).astype(float),
        #   ),
        # )
        # df["report_unit"] = np.where(
        #   df["base_uofm"] == "OZ-wt",
        #   "Pound",
        #   np.where(
        #       df["base_uofm"] == "OZ-fl",
        #       "Gallon",
        #       "Each",
        #   ),
        # )

        df.drop(columns=["quantity", "cost", "base_qty"], inplace=True)
        table = pd.pivot_table(
            df,
            values=["unit_cost", "unit_qty"],
            index=["company", "report_unit"],
            aggfunc={"unit_cost": np.mean, "unit_qty": np.sum},
        )
        if not table.empty:
            table.sort_values(by=["unit_cost"], inplace=True)
            return table
    df = pd.DataFrame()
    return df


@lru_cache
def get_cost_per_store(regex, start, end, stores):

    query = (
        db.session.query(
            Transactions.name,
            Transactions.UofM,
            func.sum(Transactions.quantity).label("quantity"),
            func.sum(Transactions.amount).label("cost"),
        )
        .filter(
            Transactions.item.regexp_match(regex),
            Transactions.date.between(start, end),
            Transactions.store_id.in_(stores),
            Transactions.type == "AP Invoice",
        )
        .group_by(
            Transactions.name,
            Transactions.UofM,
        )
    ).all()
    item_list = []
    for q in query:
        qty, uofm = convert_uofm(q)
        row_dict = dict(q)
        row_dict["base_qty"] = qty
        row_dict["base_uofm"] = uofm
        item_list.append(row_dict)
    df = pd.DataFrame(item_list)
    sorted_units = (
        df.groupby(["UofM"]).mean(["quantity", "cost"]).sort_values(by=["quantity"], ascending=False).reset_index()
    )
    report = sorted_units.iloc[0]
    df = df.groupby(["name"]).sum(["quantity", "cost"]).reset_index()

    if not df.empty:
        df["unit_cost"] = ((df["cost"] / df["quantity"]) / df["base_qty"]) * report["base_qty"]
        df["unit_qty"] = (df["quantity"] * df["base_qty"]) / report["base_qty"]
        df["report_unit"] = report.UofM

        # calculate the unit cost based on base_uofm value
        # df["unit_cost"] = np.where(
        #    df["base_uofm"] == "OZ-wt",
        #    ((df["cost"] / df["count"]) / df["base_qty"] * report.count).astype(float),
        #    np.where(
        #        df["base_uofm"] == "OZ-fl",
        #        ((df["cost"] / df["count"]) / df["base_qty"] * report.count).astype(float),
        #        ((df["cost"] / df["count"]) / df["base_qty"] * report.count).astype(float),
        #    ),
        # )
        # df["unit_qty"] = np.where(
        #    df["base_uofm"] == "OZ-wt",
        #    (df["count"] * df["base_qty"] / report.cost).astype(float),
        #    np.where(
        #        df["base_uofm"] == "OZ-fl",
        #        (df["count"] * df["base_qty"] / report.cost).astype(float),
        #        (df["count"] * df["base_qty"] / report.cost).astype(float),
        #    ),
        # )
        # df["report_unit"] = np.where(
        #    df["base_uofm"] == "OZ-wt",
        #    report.UofM,
        #    np.where(
        #        df["base_uofm"] == "OZ-fl",
        #        report.UofM,
        #        report.UofM,
        #    ),
        # )
        df.drop(columns=["quantity", "cost", "base_qty"], inplace=True)
        table = pd.pivot_table(
            df,
            values=["unit_cost", "unit_qty"],
            index=["name", "report_unit"],
            aggfunc={"unit_cost": np.mean, "unit_qty": np.sum},
        )
        if not table.empty:
            table.sort_values(by=["unit_cost"], inplace=True)
            return table
    df = pd.DataFrame()
    return df


@lru_cache
def period_purchases(regex, start, end, stores):
    # generate list of purchase costs per period for charts
    calendar = calendar.query.with_entities(calendar.date, calendar.week, calendar.period, calendar.year).all()
    cal_df = pd.DataFrame(calendar, columns=["date", "week", "period", "year"])

    query = (
        db.session.query(
            Transactions.date,
            Transactions.company,
            Transactions.name,
            Transactions.UofM,
            func.sum(Transactions.quantity).label("count"),
            func.sum(Transactions.amount).label("cost"),
        )
        .filter(
            Transactions.item.regexp_match(regex),
            Transactions.date.between(start, end),
            Transactions.store_id.in_(stores),
            Transactions.type == "AP Invoice",
        )
        .group_by(
            Transactions.date,
            Transactions.company,
            Transactions.name,
            Transactions.UofM,
        )
    ).all()

    item_list = []
    for q in query:
        if not q.UofM:
            continue
        qty, uofm = convert_uofm(q)
        row_dict = dict(q)
        row_dict["base_qty"] = qty
        row_dict["base_uofm"] = uofm

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
            Transactions.account,
            func.sum(Transactions.credit).label("credits"),
            func.sum(Transactions.debit).label("costs"),
        )
        .filter(
            Transactions.account.in_(regex),
            Transactions.date.between(start, end),
            Transactions.store_id.in_(stores),
            Transactions.type == "AP Invoice",
        )
        .group_by(Transactions.account)
        .order_by(func.sum(Transactions.debit).desc())
    ).all()
    results = pd.DataFrame(query, columns=["Account", "Credits", "Costs"])
    results["Totals"] = results["Costs"] - results["Credits"]
    return results


def get_category_topten(regex, start, end, stores):

    query = (
        db.session.query(
            Transactions.item,
            func.sum(Transactions.debit).label("cost"),
        )
        .filter(
            Transactions.account.in_(regex),
            Transactions.date.between(start, end),
            Transactions.store_id.in_(stores),
            Transactions.type == "AP Invoice",
        )
        .group_by(Transactions.item)
        .order_by(func.sum(Transactions.debit).desc())
    ).limit(10)
    df = pd.DataFrame(query, columns=["Item", "Cost"])

    return df


def get_restaurant_topten(regex, start, end, stores):

    query = (
        db.session.query(
            Transactions.name,
            func.sum(Transactions.debit).label("cost"),
        )
        .filter(
            Transactions.account.in_(regex),
            Transactions.date.between(start, end),
            Transactions.store_id.in_(stores),
            Transactions.type == "AP Invoice",
        )
        .group_by(Transactions.name)
        .order_by(func.sum(Transactions.debit).desc())
    ).all()
    dframe = pd.DataFrame(query, columns=["Restaurant", "Cost"])

    return dframe


def get_vendor_topten(regex, start, end, stores):

    query = (
        db.session.query(
            Transactions.company,
            func.sum(Transactions.debit).label("cost"),
        )
        .filter(
            Transactions.account.in_(regex),
            Transactions.date.between(start, end),
            Transactions.store_id.in_(stores),
            Transactions.type == "AP Invoice",
        )
        .group_by(Transactions.company)
        .order_by(func.sum(Transactions.debit).desc())
    ).limit(10)
    dframe = pd.DataFrame(query, columns=["Vendor", "Cost"])

    return dframe


def get_item_topten(regex, start, end, stores):

    query = (
        db.session.query(
            Transactions.item,
            func.sum(Transactions.debit).label("cost"),
        )
        .filter(
            Transactions.item.regexp_match(regex),
            Transactions.date.between(start, end),
            Transactions.store_id.in_(stores),
            Transactions.type == "AP Invoice",
        )
        .group_by(Transactions.item)
        .order_by(func.sum(Transactions.debit).desc())
    ).limit(10)
    dframe = pd.DataFrame(query, columns=["Item", "Cost"])

    return dframe
