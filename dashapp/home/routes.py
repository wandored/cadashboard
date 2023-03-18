# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from datetime import datetime, timedelta
import json
import re

from flask import flash, redirect, render_template, request, session, url_for
from flask.helpers import url_for
from flask.wrappers import Response
from flask_security.core import current_user
from flask_security.decorators import login_required, roles_accepted
from fpdf import FPDF
import pandas as pd
from pandas.core.algorithms import isin
from sqlalchemy import and_, func, or_

from dashapp.authentication.forms import *
from dashapp.authentication.models import *
from dashapp.config import Config
from dashapp.home import blueprint
from dashapp.home.util import *


@blueprint.route("/", methods=["GET", "POST"])
@blueprint.route("/index/", methods=["GET", "POST"])
@login_required
def index():
    TODAY = datetime.date(datetime.now())
    # CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
    # YSTDAY = TODAY - timedelta(days=1)

    if not "token" in session:
        session["token"] = TODAY.strftime("%Y-%m-%d")
        return redirect(url_for("home_blueprint.index"))

    if not "store_list" in session:
        closed_stores = [1, 2, 7, 8]
        session["store_list"] = tuple(
            [
                store.id
                for store in Restaurants.query.filter(Restaurants.id.notin_(closed_stores))
                .order_by(Restaurants.name)
                .all()
            ]
        )
        return redirect(url_for("home_blueprint.index"))

    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))
    # List of stores to add ID so i can pass to other templates
    data = Restaurants.query.all()
    store_df = pd.DataFrame([x.as_dict() for x in data])

    # Check for no sales
    if not Sales.query.filter_by(date=fiscal_dates["start_day"]).first():
        session["token"] = find_day_with_sales(day=fiscal_dates["start_day"])
        return redirect(url_for("home_blueprint.index"))

    # Get Data
    form1 = DateForm()
    form3 = StoreForm()
    form4 = PotatoForm()
    form5 = LobsterForm()
    form6 = StoneForm()

    if form1.submit1.data and form1.validate():
        """
        Change token
        """
        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
        session["token"] = new_day
        return redirect(url_for("home_blueprint.index"))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        data = form3.stores.data
        session["store_list"] = tuple([x.id for x in data])
        return redirect(url_for("home_blueprint.index"))

    if form4.submit4.data and form4.validate():
        store_id = form4.store.data.id
        return redirect(url_for("home_blueprint.potato", store_id=store_id))

    if form5.submit5.data and form5.validate():
        store_id = form5.store.data.id
        return redirect(url_for("home_blueprint.lobster", store_id=store_id))

    if form6.submit6.data and form6.validate():
        store_id = form6.store.data.id
        return redirect(url_for("home_blueprint.stone", store_id=store_id))

    # Sales Chart
    def get_chart_values(start, end, time):
        chart = (
            db.session.query(func.sum(Sales.sales).label("total_sales"))
            .select_from(Sales)
            .join(Calendar, Calendar.date == Sales.date)
            .group_by(time)
            .order_by(time)
            .filter(Sales.date.between(start, end))
        )
        value = []
        for v in chart:
            value.append(v.total_sales)

        return value

    daily_sales_list = get_chart_values(fiscal_dates["start_week"], fiscal_dates["start_day"], Calendar.date)
    weekly_sales = sum(daily_sales_list)

    daily_sales_list_ly = get_chart_values(fiscal_dates["start_week_ly"], fiscal_dates["end_week_ly"], Calendar.date)
    weekly_sales_ly = sum(daily_sales_list_ly)

    week_to_date_sales_ly = get_chart_values(fiscal_dates["start_week_ly"], fiscal_dates["start_day_ly"], Calendar.date)
    wtd_sales_ly = sum(week_to_date_sales_ly)

    weekly_sales_list = get_chart_values(fiscal_dates["start_period"], fiscal_dates["start_day"], Calendar.week)
    period_sales = sum(weekly_sales_list)

    weekly_sales_list_ly = get_chart_values(
        fiscal_dates["start_period_ly"], fiscal_dates["end_period_ly"], Calendar.week
    )
    period_sales_ly = sum(weekly_sales_list_ly)

    period_to_date_sales_ly = get_chart_values(
        fiscal_dates["start_period_ly"], fiscal_dates["start_day_ly"], Calendar.week
    )
    ptd_sales_ly = sum(period_to_date_sales_ly)

    period_sales_list = get_chart_values(fiscal_dates["start_year"], fiscal_dates["start_day"], Calendar.period)
    yearly_sales = sum(period_sales_list)

    period_sales_list_ly = get_chart_values(fiscal_dates["start_year_ly"], fiscal_dates["end_year_ly"], Calendar.period)
    yearly_sales_ly = sum(period_sales_list_ly)

    year_to_date_sales_ly = get_chart_values(
        fiscal_dates["start_year_ly"], fiscal_dates["start_day_ly"], Calendar.period
    )
    ytd_sales_ly = sum(year_to_date_sales_ly)

    budget_chart = (
        db.session.query(func.sum(Budgets.total_sales).label("total_sales"))
        .select_from(Budgets)
        .group_by(Budgets.period)
        .order_by(Budgets.period)
        .filter(Budgets.year == fiscal_dates["year"])
    )
    budgets3 = []
    for v in budget_chart:
        budgets3.append(v.total_sales)

    def build_sales_table(start, end, start_ly, end_ly, time_frame):
        sales = (
            db.session.query(
                Sales.name,
                func.sum(Sales.sales).label("total_sales"),
                func.sum(Sales.guests).label("total_guests"),
            )
            .filter(Sales.date.between(start, end))
            .group_by(Sales.name)
            .all()
        )

        sales_ly = (
            db.session.query(
                Sales.name,
                func.sum(Sales.sales).label("total_sales_ly"),
                func.sum(Sales.guests).label("total_guests_ly"),
            )
            .filter(Sales.date.between(start_ly, end_ly))
            .group_by(Sales.name)
            .all()
        )
        # Get the top sales for each store
        store_list = store_df["name"]
        top_sales_list = []
        for sl in store_list:
            query = sales_record(sl, time_frame)
            if query != None:
                row = [sl, query]
                top_sales_list.append(row)

        top_sales = pd.DataFrame.from_records(top_sales_list, columns=["name", "top_sales"])

        df = pd.DataFrame.from_records(sales, columns=["name", "sales", "guests"])
        df_ly = pd.DataFrame.from_records(sales_ly, columns=["name", "sales_ly", "guests_ly"])
        sales_table = df.merge(df_ly, how="outer", sort=True)
        sales_table = sales_table.merge(top_sales, how="left")

        labor = (
            db.session.query(
                Labor.name,
                func.sum(Labor.hours).label("total_hours"),
                func.sum(Labor.dollars).label("total_dollars"),
            )
            .filter(Labor.date.between(start, end))
            .group_by(Labor.name)
            .all()
        )

        labor_ly = (
            db.session.query(
                Labor.name,
                func.sum(Labor.hours).label("total_hours_ly"),
                func.sum(Labor.dollars).label("total_dollars_ly"),
            )
            .filter(Labor.date.between(start_ly, end_ly))
            .group_by(Labor.name)
            .all()
        )

        df_labor = pd.DataFrame.from_records(labor, columns=["name", "hours", "dollars"])
        df_labor_ly = pd.DataFrame.from_records(labor_ly, columns=["name", "hours_ly", "dollars_ly"])
        labor_table = df_labor.merge(df_labor_ly, how="outer", sort=True)

        table = sales_table.merge(labor_table, how="outer", sort=True)
        table = table.merge(store_df, how="left")
        table = table.set_index("name")

        # Grab top sales over last year before we add totals
        table = table.fillna(0)
        table["doly"] = table.sales - table.sales_ly
        table["poly"] = (table.sales - table.sales_ly) / table.sales_ly * 100
        top = table[["doly", "poly"]]
        top = top.nlargest(5, "poly", keep="all")
        table["guest_check_avg"] = table["sales"] / table["guests"].astype(float)
        table["guest_check_avg_ly"] = table["sales_ly"] / table["guests_ly"].astype(float)
        table["labor_pct"] = table.dollars / table.sales
        table["labor_pct_ly"] = table.dollars_ly / table.sales_ly
        totals = table.sum()

        return totals, table, top

    daily_totals, daily_table, daily_top = build_sales_table(
        fiscal_dates["start_day"],
        fiscal_dates["start_day"],
        fiscal_dates["start_day_ly"],
        fiscal_dates["start_day_ly"],
        "daily",
    )

    weekly_totals, weekly_table, weekly_top = build_sales_table(
        fiscal_dates["start_week"],
        fiscal_dates["week_to_date"],
        fiscal_dates["start_week_ly"],
        fiscal_dates["week_to_date_ly"],
        "weekly",
    )

    period_totals, period_table, period_top = build_sales_table(
        fiscal_dates["start_period"],
        fiscal_dates["period_to_date"],
        fiscal_dates["start_period_ly"],
        fiscal_dates["period_to_date_ly"],
        "period",
    )

    yearly_totals, yearly_table, yearly_top = build_sales_table(
        fiscal_dates["start_year"],
        fiscal_dates["year_to_date"],
        fiscal_dates["start_year_ly"],
        fiscal_dates["year_to_date_ly"],
        "year",
    )

    return render_template(
        "home/index.html",
        title=Config.COMPANY_NAME,
        company_name=Config.COMPANY_NAME,
        segment="index",
        roles=current_user.roles,
        **locals(),
    )


@blueprint.route("/<int:store_id>/store/", methods=["GET", "POST"])
@login_required
def store(store_id):
    TODAY = datetime.date(datetime.now())
    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
    # YSTDAY = TODAY - timedelta(days=1)

    store = Restaurants.query.filter_by(id=store_id).first()

    if not "token" in session:
        session["token"] = TODAY.strftime("%Y-%m-%d")
        return redirect(url_for("home_blueprint.store", store_id=store.id))

    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))

    data = Restaurants.query.all()
    store_df = pd.DataFrame([x.as_dict() for x in data])

    if not Sales.query.filter_by(date=fiscal_dates["start_day"], name=store.name).first():
        session["token"] = find_day_with_sales(day=fiscal_dates["start_day"], store=store.name)
        return redirect(url_for("home_blueprint.store", store_id=store.id))

    # Get Data
    form1 = DateForm()
    form3 = StoreForm()
    form4 = PotatoForm()
    form5 = LobsterForm()
    form6 = StoneForm()

    if form1.submit1.data and form1.validate():
        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
        session["token"] = new_day
        return redirect(url_for("home_blueprint.store", store_id=store.id))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        data = form3.stores.data
        for x in data:
            # select only 1 store for store page
            store_id = x.id
            break
        session["store_list"] = tuple([x.id for x in data])
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    if form4.submit4.data and form4.validate():
        store_id = form4.store.data.id
        return redirect(url_for("home_blueprint.potato", store_id=store_id))

    if form5.submit5.data and form5.validate():
        store_id = form5.store.data.id
        return redirect(url_for("home_blueprint.lobster", store_id=store_id))

    if form6.submit6.data and form6.validate():
        store_id = form6.store.data.id
        return redirect(url_for("home_blueprint.stone", store_id=store_id))

    # Sales Charts
    def get_chart_values(start, end, time):
        chart = (
            db.session.query(func.sum(Sales.sales).label("total_sales"))
            .select_from(Sales)
            .join(Calendar, Calendar.date == Sales.date)
            .group_by(time)
            .order_by(time)
            .filter(Sales.date.between(start, end), Sales.name == store.name)
        )
        value = []
        for v in chart:
            value.append(v.total_sales)

        return value

    daily_sales_list = get_chart_values(fiscal_dates["start_week"], fiscal_dates["start_day"], Calendar.date)
    weekly_sales = sum(daily_sales_list)

    daily_sales_list_ly = get_chart_values(fiscal_dates["start_week_ly"], fiscal_dates["end_week_ly"], Calendar.date)
    weekly_sales_ly = sum(daily_sales_list_ly)

    week_to_date_sales_ly = get_chart_values(fiscal_dates["start_week_ly"], fiscal_dates["start_day_ly"], Calendar.date)
    wtd_sales_ly = sum(week_to_date_sales_ly)

    weekly_sales_list = get_chart_values(fiscal_dates["start_period"], fiscal_dates["start_day"], Calendar.week)
    period_sales = sum(weekly_sales_list)

    weekly_sales_list_ly = get_chart_values(
        fiscal_dates["start_period_ly"], fiscal_dates["end_period_ly"], Calendar.week
    )
    period_sales_ly = sum(weekly_sales_list_ly)

    period_to_date_sales_ly = get_chart_values(
        fiscal_dates["start_period_ly"], fiscal_dates["start_day_ly"], Calendar.week
    )
    ptd_sales_ly = sum(period_to_date_sales_ly)

    period_sales_list = get_chart_values(fiscal_dates["start_year"], fiscal_dates["start_day"], Calendar.period)
    yearly_sales = sum(period_sales_list)

    period_sales_list_ly = get_chart_values(fiscal_dates["start_year_ly"], fiscal_dates["end_year_ly"], Calendar.period)
    yearly_sales_ly = sum(period_sales_list_ly)

    year_to_date_sales_ly = get_chart_values(
        fiscal_dates["start_year_ly"], fiscal_dates["start_day_ly"], Calendar.period
    )
    ytd_sales_ly = sum(year_to_date_sales_ly)

    #  TODO need to use Menuitems to get category sales
    def build_category_sales_table(start, end, start_ly, end_ly, time_unit):
        # query Calendar and merge with table
        query = (
            db.session.query(
                Calendar.date,
                Calendar.dow,
                Calendar.day,
                Calendar.week,
                Calendar.period,
                Calendar.quarter,
                Calendar.year,
            )
            .filter(Calendar.date.between(start_ly, end))
            .all()
        )
        calendar = pd.DataFrame.from_records(query, columns=["date", "dow", "day", "week", "period", "quarter", "year"])

        lunch_sales = get_daypart_sales(start, end, store.name, "Lunch")
        ls = pd.DataFrame.from_records(lunch_sales, columns=["date", "category", "amount"])
        dinner_sales = get_daypart_sales(start, end, store.name, "Dinner")
        ds = pd.DataFrame.from_records(dinner_sales, columns=["date", "category", "amount"])
        lunch_guests = get_daypart_guest(start, end, store.name, "Lunch")
        lg = pd.DataFrame.from_records(lunch_guests, columns=["date", "category", "amount"])
        lg["category"] = lg["category"].str.replace("Lunch", "Lunch Guests")
        dinner_guests = get_daypart_guest(start, end, store.name, "Dinner")
        dg = pd.DataFrame.from_records(dinner_guests, columns=["date", "category", "amount"])
        dg["category"] = dg["category"].str.replace("Dinner", "Dinner Guests")

        # lunch_sales_ly = get_daypart_sales(start, end, store.name, "Lunch")
        # ls_ly = pd.DataFrame.from_records(lunch_sales, columns=["date", "category", "amount"])
        # dinner_sales_ly = get_daypart_sales(start, end, store.name, "Dinner")
        # ds_ly = pd.DataFrame.from_records(dinner_sales, columns=["date", "category", "amount"])
        # lunch_guests_ly = get_daypart_guest(start, end, store.name, "Lunch")
        # lg_ly = pd.DataFrame.from_records(lunch_guests, columns=["date", "category", "amount"])
        # lg_ly["category"] = lg_ly["category"].str.replace("Lunch", "Lunch Guests")
        # dinner_guests_ly = get_daypart_guest(start, end, store.name, "Dinner")
        # dg_ly = pd.DataFrame.from_records(dinner_guests, columns=["date", "category", "amount"])
        # dg_ly["category"] = dg_ly["category"].str.replace("Dinner", "Dinner Guests")

        # lunch_sales = ls.merge(ls_ly, how="outer", sort=True)
        # dinner_sales = ds.merge(ds_ly, how="outer", sort=True)
        # lunch_guests = lg.merge(lg_ly, how="outer", sort=True)
        # dinner_guests = dg.merge(dg_ly, how="outer", sort=True)

        sales_guests = ls.merge(ds, how="outer", sort=True)
        sales_guests = sales_guests.merge(lg, how="outer", sort=True)
        sales_guests = sales_guests.merge(dg, how="outer", sort=True)
        sales_guests = sales_guests.merge(calendar, how="left", sort=True)
        sales_guests = sales_guests.set_index("date")

        menuitems = (
            db.session.query(
                Menuitems.date,
                Menuitems.category,
                func.sum(Menuitems.amount).label("sales"),
            )
            .filter(Menuitems.date.between(start, end), Menuitems.name == store.name)
            .group_by(Menuitems.date, Menuitems.category)
            .all()
        )

        # menuitems_ly = (
        #    db.session.query(
        #        Menuitems.date,
        #        Menuitems.category,
        #        func.sum(Menuitems.amount).label("sales"),
        #    )
        #    .filter(Menuitems.date.between(start_ly, end_ly), Menuitems.name == store.name)
        #    .group_by(Menuitems.date, Menuitems.category)
        #    .all()
        # )
        menuitems_table = pd.DataFrame.from_records(menuitems, columns=["date", "category", "amount"])
        # df_ly = pd.DataFrame.from_records(menuitems_ly, columns=["date", "category", "amount"])
        # menuitems_table = df.merge(df_ly, how="outer", sort=True)
        menuitems_table = menuitems_table.merge(calendar, how="left", sort=True)
        menuitems_table = menuitems_table.set_index("date")

        labor = (
            db.session.query(
                Labor.date,
                Labor.category,
                func.sum(Labor.dollars).label("total_dollars"),
            )
            .filter(Labor.date.between(start, end), Labor.name == store.name)
            .group_by(Labor.date, Labor.category)
            .all()
        )

        # labor_ly = (
        #    db.session.query(
        #        Labor.date,
        #        Labor.category,
        #        func.sum(Labor.dollars).label("total_dollars"),
        #    )
        #    .filter(Labor.date.between(start_ly, end_ly), Labor.name == store.name)
        #    .group_by(Labor.date, Labor.category)
        #    .all()
        # )
        labor_table = pd.DataFrame.from_records(labor, columns=["date", "category", "amount"])
        # df_labor_ly = pd.DataFrame.from_records(labor_ly, columns=["date", "category", "amount"])
        # labor_table = df_labor.merge(df_labor_ly, how="outer", sort=True)
        labor_table = labor_table.merge(calendar, how="left", sort=True)
        labor_table = labor_table.set_index("date")

        # concat sales and labor
        # table = pd.concat([sales_guests, menuitems_table, labor_table])

        # Grab top sales over last year before we add totals
        # table = table.fillna(0)
        # table["labor_pct"] = table.dollars / table.sales
        # table["labor_pct_ly"] = table.dollars_ly / table.sales_ly
        # table = table.groupby(["category", time_unit]).sum()
        # table["Total Guests"] = table["Lunch Guests"] + table["Dinner Guests"]
        # table["Total Sales"] = table["Lunch"] + table["Dinner"]
        # table["Alcohol Sales"] = table["BEER"] + table["WINE"] + table["LIQUOR"]
        # table["Hourly Labor"] = (
        #    table["Bar"]
        #    + table["Kitchen"]
        #    + table["Restaurant"]
        #    + table["Catering"]
        #    + table["Maintenance"]
        #    + table["Training"]
        # )
        sales = pd.pivot_table(
            sales_guests,
            values=["amount"],
            index=["category"],
            columns=[time_unit],
            aggfunc=np.sum,
            fill_value=0,
        )
        sales.columns = sales.columns.droplevel(0)
        sales.loc["Total Guests"] = sales.loc["Lunch Guests"] + sales.loc["Dinner Guests"]
        sales.loc["Total Sales"] = sales.loc["Lunch"] + sales.loc["Dinner"]
        sales = sales.reindex(
            [
                "Lunch Guests",
                "Dinner Guests",
                "Total Guests",
                "Lunch",
                "Dinner",
                "Total Sales",
            ]
        )
        # Add Row for Total Guests
        sales = sales.fillna(0)
        sales["Totals"] = sales.sum(axis=1)

        labor = pd.pivot_table(
            labor_table,
            values=["amount"],
            index=["category"],
            columns=[time_unit],
            aggfunc=np.sum,
            fill_value=0,
        )
        labor.columns = labor.columns.droplevel(0)
        labor.loc["Total Hourly"] = labor.sum()
        labor = labor.reindex(
            [
                "Bar",
                "Host",
                "Restaurant",
                "Kitchen",
                "Catering",
                "Training",
                "Maintenance",
                "Total Hourly",
            ]
        )
        labor = labor.fillna(0)
        labor["Totals"] = labor.sum(axis=1)

        return sales, labor

    daily_table, daily_labor = build_category_sales_table(
        fiscal_dates["start_day"],
        fiscal_dates["start_day"],
        fiscal_dates["start_day_ly"],
        fiscal_dates["start_day_ly"],
        "date",
    )

    weekly_table, weekly_labor = build_category_sales_table(
        fiscal_dates["start_week"],
        fiscal_dates["week_to_date"],
        fiscal_dates["start_week_ly"],
        fiscal_dates["week_to_date_ly"],
        "dow",
    )

    # replace dow with day names 1 = "Wednesday"
    weekly_table = weekly_table.rename(
        columns={
            1: "Wednesday",
            2: "Thursday",
            3: "Friday",
            4: "Saturday",
            5: "Sunday",
            6: "Monday",
            7: "Tuesday",
        }
    )
    weekly_labor = weekly_labor.rename(
        columns={
            1: "Wednesday",
            2: "Thursday",
            3: "Friday",
            4: "Saturday",
            5: "Sunday",
            6: "Monday",
            7: "Tuesday",
        }
    )

    period_table, period_labor = build_category_sales_table(
        fiscal_dates["start_period"],
        fiscal_dates["period_to_date"],
        fiscal_dates["start_period_ly"],
        fiscal_dates["period_to_date_ly"],
        "week",
    )

    quarterly_table, quarterly_labor = build_category_sales_table(
        fiscal_dates["start_quarter"],
        fiscal_dates["quarter_to_date"],
        fiscal_dates["start_quarter_ly"],
        fiscal_dates["quarter_to_date_ly"],
        "period",
    )

    yearly_table, yearly_labor = build_category_sales_table(
        fiscal_dates["start_year"],
        fiscal_dates["year_to_date"],
        fiscal_dates["start_year_ly"],
        fiscal_dates["year_to_date_ly"],
        "quarter",
    )

    daily_sales = daily_sales_list[-1]
    daily_sales_ly = daily_sales_list_ly[-1]

    budget_chart = (
        db.session.query(func.sum(Budgets.total_sales).label("total_sales"))
        .select_from(Budgets)
        .group_by(Budgets.period)
        .order_by(Budgets.period)
        .filter(Budgets.year == fiscal_dates["year"], Budgets.name == store.name)
    )
    budgets3 = []
    for v in budget_chart:
        budgets3.append(v.total_sales)

    return render_template(
        "home/store.html",
        title=store.name,
        company_name=Config.COMPANY_NAME,
        segment="store.name",
        roles=current_user.roles,
        **locals(),
    )


@blueprint.route("/marketing/", methods=["GET", "POST"])
@login_required
def marketing():
    TODAY = datetime.date(datetime.now())
    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
    YSTDAY = TODAY - timedelta(days=1)

    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))
    form1 = DateForm()
    form4 = PotatoForm()
    form5 = LobsterForm()
    form6 = StoneForm()
    if form1.submit1.data and form1.validate():
        """ """
        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
        session["token"] = new_day
        return redirect(url_for("home_blueprint.marketing"))

    form3 = StoreForm()
    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        data = form3.store.data
        session["store_list"] = tuple([x.id for x in data])
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    if form4.submit4.data and form4.validate():
        store_id = form4.store.data.id
        return redirect(url_for("home_blueprint.potato", store_id=store_id))

    if form5.submit5.data and form5.validate():
        store_id = form5.store.data.id
        return redirect(url_for("home_blueprint.lobster", store_id=store_id))

    if form6.submit6.data and form6.validate():
        store_id = form6.store.data.id
        return redirect(url_for("home_blueprint.stone", store_id=store_id))

    # Gift Card Sales

    def get_giftcard_sales(start, end, epoch):
        chart = (
            db.session.query(func.sum(Menuitems.amount).label("sales"), Calendar.period)
            .select_from(Menuitems)
            .join(Calendar, Calendar.date == Menuitems.date)
            .group_by(epoch)
            .order_by(epoch)
            .filter(
                Menuitems.date.between(start, end),
                Menuitems.menuitem.regexp_match("(?i)GIFT CARD*"),
            )
        )
        value = []
        for p in period_order:
            for v in chart:
                if v.period == p:
                    value.append(int(v.sales))

        return value

    def get_giftcard_payments(start, end, epoch):
        chart = (
            db.session.query(func.sum(Payments.amount).label("sales"), Calendar.period)
            .select_from(Payments)
            .join(Calendar, Calendar.date == Payments.date)
            .group_by(epoch)
            .order_by(epoch)
            .filter(
                Payments.date.between(start, end),
                Payments.paymenttype.regexp_match("(?i)GIFT CARD*"),
            )
        )
        value = []
        for p in period_order:
            for v in chart:
                if v.period == p:
                    value.append(int(v.sales))

        return value

    # list of last 13 periods
    period_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
    slice1 = period_list[fiscal_dates["period"] :]
    slice2 = period_list[: fiscal_dates["period"]]
    period_order = slice1 + slice2

    giftcard_sales = get_giftcard_sales(fiscal_dates["last_threesixtyfive"], fiscal_dates["start_day"], Calendar.period)
    giftcard_payments = get_giftcard_payments(
        fiscal_dates["last_threesixtyfive"], fiscal_dates["start_day"], Calendar.period
    )

    # TODO set to trailing year beginning in 2023
    giftcard_diff = []
    dif = 0
    for ii in range(len(giftcard_sales)):
        dif = (giftcard_sales[ii] - giftcard_payments[ii]) + dif
        giftcard_diff.append(dif)
    giftcard_payments[:] = [-abs(x) for x in giftcard_payments]

    def get_giftcard_sales_per_store(start, end):
        query = (
            db.session.query(
                Menuitems.name,
                func.sum(Menuitems.amount).label("sales"),
                func.sum(Menuitems.quantity).label("count"),
            )
            .filter(
                Menuitems.date.between(start, end),
                Menuitems.menuitem.regexp_match("(?i)GIFT CARD*"),
            )
            .group_by(Menuitems.name)
        ).all()
        sales = pd.DataFrame.from_records(query, columns=["store", "amount", "quantity"])
        sales.sort_values(by=["amount"], ascending=False, inplace=True)
        sales.loc["TOTALS"] = sales.sum(numeric_only=True)
        return sales

    def get_giftcard_payments_per_store(start, end):
        data = Restaurants.query.all()
        df_loc = pd.DataFrame([x.as_dict() for x in data])
        df_loc.rename(
            columns={
                "id": "restaurant_id",
            },
            inplace=True,
        )

        query = (
            db.session.query(
                Payments.restaurant_id,
                func.sum(Payments.amount).label("payment"),
            )
            .filter(
                Payments.date.between(start, end),
                Payments.paymenttype.regexp_match("GIFT CARD"),
            )
            .group_by(Payments.restaurant_id)
        ).all()

        payments = pd.DataFrame.from_records(query, columns=["restaurant_id", "payment"])
        payments.sort_values(by=["payment"], ascending=False, inplace=True)
        payments = df_loc.merge(payments, on="restaurant_id")

        payments.loc["TOTALS"] = payments.sum(numeric_only=True)
        return payments

    gift_card_sales = get_giftcard_sales_per_store(fiscal_dates["start_year"], fiscal_dates["end_year"])
    gift_card_payments = get_giftcard_payments_per_store(fiscal_dates["start_year"], fiscal_dates["end_year"])
    gift_card_sales = gift_card_sales.merge(gift_card_payments, left_on="store", right_on="name")
    gift_card_sales["diff"] = gift_card_sales["amount"] - gift_card_sales["payment"]
    gift_card_sales.sort_values(by=["diff"], ascending=False, inplace=True)

    return render_template(
        "home/marketing.html",
        title="Marketing",
        company_name=Config.COMPANY_NAME,
        segment="marketing",
        fiscal_dates=fiscal_dates,
        form1=form1,
        form3=form3,
        current_user=current_user,
        roles=current_user.roles,
        gift_card_sales=gift_card_sales,
        giftcard_sales=giftcard_sales,
        giftcard_payments=giftcard_payments,
        giftcard_diff=giftcard_diff,
        period_order=period_order,
    )


@blueprint.route("/support/", methods=["GET", "POST"])
@login_required
@roles_accepted("admin")
def support():
    TODAY = datetime.date(datetime.now())
    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
    YSTDAY = TODAY - timedelta(days=1)

    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))

    form1 = DateForm()
    form2 = UpdateForm()
    form3 = StoreForm()
    form4 = PotatoForm()
    form5 = LobsterForm()
    form6 = StoneForm()
    uofm_form = UofMForm()
    form9 = RecipeForm()

    if form1.submit1.data and form1.validate():
        """ """
        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
        session["token"] = new_day
        return redirect(url_for("home_blueprint.support"))

    if form2.submit2.data and form2.validate():
        """ """
        new_start_day = form2.selectdate.data.strftime("%Y-%m-%d")
        day_end = form2.selectdate.data + timedelta(days=1)
        new_end_day = day_end.strftime("%Y-%m-%d")

        baddates = refresh_data(new_start_day, new_end_day)
        if baddates == 1:
            flash(
                f"I cannot find sales for the day you selected.  Please select another date!",
                "warning",
            )
        session["token"] = new_start_day
        return redirect(url_for("home_blueprint.support"))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        data = form3.store.data
        session["store_list"] = tuple([x.id for x in data])

        return redirect(url_for("home_blueprint.store", store_id=store_id))

    if form4.submit4.data and form4.validate():
        store_id = form4.store.data.id
        return redirect(url_for("home_blueprint.potato", store_id=store_id))

    if form5.submit5.data and form5.validate():
        store_id = form5.store.data.id
        return redirect(url_for("home_blueprint.lobster", store_id=store_id))

    if form6.submit6.data and form6.validate():
        store_id = form6.store.data.id
        return redirect(url_for("home_blueprint.stone", store_id=store_id))

    if uofm_form.submit_uofm.data and uofm_form.validate():
        file = request.files["file"]
        uofm_update(file)
        session["token"] = fiscal_dates["start_day"]
        return redirect(url_for("home_blueprint.support"))

    if form9.submit9.data and form9.validate():
        file = request.files["file"]
        receiving_by_purchased_item(file)
        session["token"] = fiscal_dates["start_day"]
        return redirect(url_for("home_blueprint.support"))

    query = (
        db.session.query(
            Menuitems.name,
            Menuitems.menuitem,
            Menuitems.category,
            func.sum(Menuitems.amount).label("sales"),
            func.sum(Menuitems.quantity).label("count"),
        )
        .filter(
            Menuitems.date == fiscal_dates["start_day"],
            or_(
                Menuitems.menuitem == "Unassigned",
                Menuitems.category == "Unassigned",
            ),
        )
        .group_by(Menuitems.name, Menuitems.menuitem, Menuitems.category)
    ).all()
    unassigned_sales = pd.DataFrame.from_records(query, columns=["store", "menuitem", "category", "amount", "quantity"])
    unassigned_sales.sort_values(by=["amount"], ascending=False, inplace=True)

    query = (
        db.session.query(Transactions.name, Transactions.item)
        .filter(
            Transactions.date >= fiscal_dates["start_week"],
            Transactions.item.regexp_match("^DO NOT USE*"),
        )
        .group_by(Transactions.name, Transactions.item)
    ).all()
    do_not_use = pd.DataFrame.from_records(query, columns=["store", "menuitem"])
    do_not_use.sort_values(by=["store"], inplace=True)

    return render_template(
        "home/support.html",
        title="Support",
        company_name=Config.COMPANY_NAME,
        segment="support",
        **locals(),
    )


@blueprint.route("/profile/", methods=["GET", "POST"])
@login_required
def profile():
    TODAY = datetime.date(datetime.now())
    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
    YSTDAY = TODAY - timedelta(days=1)

    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))
    form1 = DateForm()
    form3 = StoreForm()
    form4 = PotatoForm()
    form5 = LobsterForm()
    form6 = StoneForm()

    if form1.submit1.data and form1.validate():
        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
        session["token"] = new_day
        return redirect(url_for("home_blueprint.profile"))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        data = form3.store.data
        session["store_list"] = tuple([x.id for x in data])
        return redirect(url_for("home_blueprint.profile"))

    if form4.submit4.data and form4.validate():
        store_id = form4.store.data.id
        return redirect(url_for("home_blueprint.potato", store_id=store_id))

    if form5.submit5.data and form5.validate():
        store_id = form5.store.data.id
        return redirect(url_for("home_blueprint.lobster", store_id=store_id))

    if form6.submit6.data and form6.validate():
        store_id = form6.store.data.id
        return redirect(url_for("home_blueprint.stone", store_id=store_id))

    return render_template(
        "home/profile.html",
        title="Profile",
        company_name=Config.COMPANY_NAME,
        segment="profile",
        **locals(),
    )


@blueprint.route("/<int:store_id>/potato/", methods=["GET", "POST"])
@login_required
def potato(store_id):
    # TODO need to fix store ID
    TODAY = datetime.date(datetime.now())
    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
    YSTDAY = TODAY - timedelta(days=1)

    store = Restaurants.query.filter_by(id=store_id).first()

    pot_df = pd.read_csv("/usr/local/share/potatochart.csv", usecols=["time"])

    for i in [28, 21, 14, 7]:
        target = TODAY - timedelta(days=i)
        start = target.strftime("%Y-%m-%d")
        # TODO switch queries to "with_entities"
        query = (
            Potatoes.query.with_entities(Potatoes.time, Potatoes.quantity).filter(
                Potatoes.date == start, Potatoes.name == store.name
            )
        ).all()
        df = pd.DataFrame.from_records(query, columns=["time", i])
        pot_df = pot_df.merge(df, on="time", how="outer")

    pot_df.fillna(0, inplace=True)
    pot_df.loc[:, "AVG"] = pot_df.mean(numeric_only=True, axis=1)
    pot_df.loc[:, "MEDIAN"] = pot_df.median(numeric_only=True, axis=1)
    pot_df.loc[:, "MAX"] = pot_df.max(numeric_only=True, axis=1)
    out_times = pd.read_csv("/usr/local/share/potatochart.csv", usecols=["time", "in_time", "out_time"])
    rotation = pot_df.merge(out_times, on="time", how="left")
    rotation.loc["TOTALS"] = rotation.sum()

    # format pdf page
    pdf_date = TODAY.strftime("%A, %B-%d")
    pdf = FPDF()
    pdf.add_page()
    page_width = pdf.w - 2 * pdf.l_margin
    pdf.set_font("Times", "B", 14.0)
    pdf.cell(page_width, 0.0, "POTATO LOADING CHART", align="C")
    pdf.ln(5)
    pdf.cell(page_width, 0.0, store.name, align="C")
    pdf.ln(5)
    pdf.cell(page_width, 0.0, pdf_date, align="C")
    pdf.ln(5)

    pdf.set_font("Courier", "", 12)
    col_width = page_width / 8
    notes_width = page_width / 3
    pdf.ln(1)
    th = pdf.font_size + 1

    pdf.cell(col_width, th, str("LUNCH"), border=1)
    pdf.ln(th)
    pdf.cell(col_width, th, str("IN TIME"), border=1)
    pdf.cell(col_width, th, str("Average"), border=1)
    pdf.cell(col_width, th, str("Median"), border=1)
    pdf.cell(col_width, th, str("Max"), border=1)
    pdf.cell(col_width, th, str("OUT TIME"), border=1)
    pdf.cell(notes_width, th, str("NOTES"), border=1)
    pdf.ln(th)
    for k, v in rotation.iterrows():
        if v["time"] == "15:00":
            pdf.ln(th)
            pdf.cell(col_width, th, str("DINNER"), border=1)
            pdf.ln(th)
            pdf.cell(col_width, th, str("IN TIME"), border=1)
            pdf.cell(col_width, th, str("Average"), border=1)
            pdf.cell(col_width, th, str("Median"), border=1)
            pdf.cell(col_width, th, str("Max"), border=1)
            pdf.cell(col_width, th, str("OUT TIME"), border=1)
            pdf.cell(notes_width, th, str("NOTES"), border=1)
            pdf.ln(th)
        if k == "TOTALS":
            pdf.ln(th)
            pdf.cell(col_width, th, str("TOTALS"), border=1)
            pdf.ln(th)
            pdf.cell(col_width, th, "", border=1)
            pdf.cell(col_width, th, str(round(v["AVG"])), border=1)
            pdf.cell(col_width, th, str(round(v["MEDIAN"])), border=1)
            pdf.cell(col_width, th, str(round(v["MAX"])), border=1)
            pdf.cell(col_width, th, "", border=1)
            pdf.cell(notes_width, th, "", border=1)
            pdf.ln(th)
            continue
        pdf.cell(col_width, th, str(v["in_time"]), border=1)
        pdf.cell(col_width, th, str(round(v["AVG"])), border=1)
        pdf.cell(col_width, th, str(round(v["MEDIAN"])), border=1)
        pdf.cell(col_width, th, str(round(v["MAX"])), border=1)
        pdf.cell(col_width, th, str(v["out_time"]), border=1)
        pdf.cell(notes_width, th, "", border=1)
        pdf.ln(th)

    pdf.ln(5)
    pdf.set_font("Times", "", 10.0)
    pdf.cell(page_width, 0.0, "* Calculated from previous 4 weeks same day sales", align="L")
    pdf.ln(5)
    pdf.cell(page_width, 0.0, "- end of report -", align="C")

    return Response(
        pdf.output(dest="S").encode("latin-1"),
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment;filename=potato_loading.pdf"},
    )


@blueprint.route("/<int:store_id>/lobster/", methods=["GET", "POST"])
@login_required
def lobster(store_id):
    TODAY = datetime.date(datetime.now())
    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))

    store = Restaurants.query.filter_by(id=store_id).first()

    live_lobster_avg_cost = get_item_avg_cost(
        "SEAFOOD Lobster Live*",
        fiscal_dates["last_seven"],
        fiscal_dates["start_day"],
        store_id,
    )
    with open("./lobster_items.json") as file:
        lobster_items = json.load(file)

    # format pdf page
    pdf_date = TODAY.strftime("%A, %B-%d")
    pdf = FPDF()
    pdf.add_page()
    page_width = pdf.w - 2 * pdf.l_margin
    pdf.set_font("Times", "B", 14.0)
    pdf.cell(page_width, 0.0, "LOBSTER PRICE CHART", align="C")
    pdf.ln(5)
    pdf.cell(page_width, 0.0, store.name, align="C")
    pdf.ln(5)
    pdf.cell(page_width, 0.0, pdf_date, align="C")
    pdf.ln(5)

    pdf.set_font("Courier", "", 12)
    col_width = page_width / 5
    size_width = page_width / 3
    pdf.ln(1)
    th = pdf.font_size + 1

    pdf.cell(col_width, th, str("Avg Cost/lb"), border=1)
    pdf.cell(col_width, th, "${:,.2f}".format(round(live_lobster_avg_cost, 2)), align="R", border=1)
    pdf.ln(2 * th)
    pdf.cell(size_width, th, str("Size"), border=1)
    pdf.cell(col_width, th, str("Cost"), border=1)
    pdf.cell(col_width, th, str("Price @40%"), border=1)
    pdf.ln(th)

    for v in lobster_items["lobster_sizes"]:
        pdf.cell(size_width, th, str(v["item"]), border=1)
        pdf.cell(col_width, th, "${:,.2f}".format(round(live_lobster_avg_cost * v["factor"], 2)), align="R", border=1)
        pdf.cell(
            col_width, th, "${:,.2f}".format(round(live_lobster_avg_cost * v["factor"] / 0.4)), align="R", border=1
        )
        pdf.ln(th)

    pdf.ln(5)
    pdf.set_font("Times", "", 10.0)
    pdf.cell(page_width, 0.0, "* Calculated from previous 7 days purchases", align="L")
    pdf.ln(5)
    pdf.cell(page_width, 0.0, "- end of report -", align="C")

    return Response(
        pdf.output(dest="S").encode("latin-1"),
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment;filename=lobster_prices.pdf"},
    )


@blueprint.route("/<int:store_id>/stone/", methods=["GET", "POST"])
@login_required
def stone(store_id):
    TODAY = datetime.date(datetime.now())
    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))

    store = Restaurants.query.filter_by(id=store_id).first()

    stone_claw_avg_cost = get_item_avg_cost(
        "^(SEAFOOD Crab Stone Claw)",
        fiscal_dates["last_seven"],
        fiscal_dates["start_day"],
        store_id,
    )
    with open("./stone_claw_items.json") as file:
        stone_items = json.load(file)

    # format pdf page
    pdf_date = TODAY.strftime("%A, %B-%d")
    pdf = FPDF()
    pdf.add_page()
    page_width = pdf.w - 2 * pdf.l_margin
    pdf.set_font("Times", "B", 14.0)
    pdf.cell(page_width, 0.0, "STONE CLAW PRICE CHART", align="C")
    pdf.ln(5)
    pdf.cell(page_width, 0.0, store.name, align="C")
    pdf.ln(5)
    pdf.cell(page_width, 0.0, pdf_date, align="C")
    pdf.ln(5)

    pdf.set_font("Courier", "", 12)
    col_width = page_width / 5
    size_width = page_width / 3
    pdf.ln(1)
    th = pdf.font_size + 1

    pdf.cell(col_width, th, str("Avg Cost/lb"), border=1)
    pdf.cell(col_width, th, "${:,.2f}".format(round(stone_claw_avg_cost, 2)), align="R", border=1)
    pdf.ln(2 * th)
    pdf.cell(size_width, th, str("Size"), border=1)
    pdf.cell(col_width, th, str("Cost"), border=1)
    pdf.cell(col_width, th, str("Price @40%"), border=1)
    pdf.ln(th)

    for v in stone_items["stone_sizes"]:
        pdf.cell(size_width, th, str(v["item"]), border=1)
        pdf.cell(col_width, th, "${:,.2f}".format(round(stone_claw_avg_cost * v["factor"], 2)), align="R", border=1)
        pdf.cell(col_width, th, "${:,.2f}".format(round(stone_claw_avg_cost * v["factor"] / 0.4)), align="R", border=1)
        pdf.ln(th)

    pdf.ln(5)
    pdf.set_font("Times", "", 10.0)
    pdf.cell(page_width, 0.0, "* Calculated from previous 7 days purchases", align="L")
    pdf.ln(5)
    pdf.cell(page_width, 0.0, "- end of report -", align="C")

    return Response(
        pdf.output(dest="S").encode("latin-1"),
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment;filename=stone_claw_prices.pdf"},
    )
