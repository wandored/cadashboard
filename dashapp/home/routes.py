# -*- encmding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import re
import json
import pandas as pd
from fpdf import FPDF
from flask.helpers import url_for
from flask_security.decorators import roles_accepted
from pandas.core.algorithms import isin
from flask import flash, render_template, session, redirect, url_for
from flask.wrappers import Response
from flask_security import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, func
from dashapp.config import Config
from dashapp.home import blueprint
from dashapp.home.util import *
from dashapp.authentication.forms import *
from dashapp.authentication.models import *


@blueprint.route("/", methods=["GET", "POST"])
@blueprint.route("/index/", methods=["GET", "POST"])
@login_required
def index():

    TODAY = datetime.date(datetime.now())
    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
    YSTDAY = TODAY - timedelta(days=1)

    if not "token" in session:
        session["token"] = TODAY.strftime("%Y-%m-%d")
        return redirect(url_for("home_blueprint.index"))

    if not "store_list" in session:
        session["store_list"] = (4, 9, 11, 16, 17, 3, 5, 6, 10, 12, 13, 14, 15, 18)
        return redirect(url_for("home_blueprint.index"))
    print(session['store_list'])

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
    if form1.submit1.data and form1.validate():
        """
        Change token
        """
        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
        session["token"] = new_day
        return redirect(url_for("home_blueprint.index"))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        data = (form3.stores.data)
        session["store_list"] = tuple([x.id for x in data])
        return redirect(url_for("home_blueprint.index"))

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

    daily_sales_list = get_chart_values(
        fiscal_dates["start_week"], fiscal_dates["start_day"], Calendar.date
    )
    # sum daily sales list
    weekly_sales = sum(daily_sales_list)
    daily_sales_list_ly = get_chart_values(
        fiscal_dates["start_week_ly"], fiscal_dates["end_week_ly"], Calendar.date
    )
    weekly_sales_ly = sum(daily_sales_list_ly)
    week_to_date_sales_ly = get_chart_values(
        fiscal_dates["start_week_ly"], fiscal_dates["start_day_ly"], Calendar.date
    )
    wtd_sales_ly = sum(week_to_date_sales_ly)

    weekly_sales_list = get_chart_values(
        fiscal_dates["start_period"], fiscal_dates["start_day"], Calendar.week
    )
    period_sales = sum(weekly_sales_list)
    weekly_sales_list_ly = get_chart_values(
        fiscal_dates["start_period_ly"], fiscal_dates["end_period_ly"], Calendar.week
    )
    period_sales_ly = sum(weekly_sales_list_ly)
    period_to_date_sales_ly = get_chart_values(
        fiscal_dates["start_period_ly"], fiscal_dates["start_day_ly"], Calendar.week
    )
    ptd_sales_ly = sum(period_to_date_sales_ly)

    period_sales_list = get_chart_values(
        fiscal_dates["start_year"], fiscal_dates["start_day"], Calendar.period
    )
    yearly_sales = sum(period_sales_list)
    period_sales_list_ly = get_chart_values(
        fiscal_dates["start_year_ly"], fiscal_dates["end_year_ly"], Calendar.period
    )
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

    # Daily Sales Table
    sales_day = (
        db.session.query(
            Sales.name,
            func.sum(Sales.sales).label("total_sales"),
            func.sum(Sales.guests).label("total_guests"),
        )
        .filter(Sales.date == fiscal_dates["start_day"])
        .group_by(Sales.name)
        .all()
    )

    sales_day_ly = (
        db.session.query(
            Sales.name,
            func.sum(Sales.sales).label("total_sales_ly"),
            func.sum(Sales.guests).label("total_guests_ly"),
        )
        .filter(Sales.date == fiscal_dates["start_day_ly"])
        .group_by(Sales.name)
        .all()
    )

    #entree_count = (
    #    db.session.query(
    #        Menuitems.name,
    #        func.sum(Menuitems.quantity).label("entree_count"),
    #    )
    #    .filter(
    #        Menuitems.date == fiscal_dates["start_day"],
    #        Menuitems.menu_category.regexp_match("ENTREE*"),
    #    )
    #    .group_by(Menuitems.name)
    #    .all()
    #)
    ## replace ly with guest check average
    #entree_count_ly = (
    #    db.session.query(
    #        Menuitems.name,
    #        func.sum(Menuitems.quantity).label("entree_count"),
    #    )
    #    .filter(
    #        Menuitems.date == fiscal_dates["start_day_ly"],
    #        Menuitems.menu_category.regexp_match("ENTREE*"),
    #    )
    #    .group_by(Menuitems.name)
    #    .all()
    #)

    # Get the top sales for each store
    store_list = store_df["name"]
    top_sales_list = []
    for sl in store_list:
        query = sales_record(sl)
        if query != None:
            row = [sl, query]
            top_sales_list.append(row)

    top_sales_df = pd.DataFrame.from_records(
        top_sales_list, columns=["name", "top_sales"]
    )

    df_sales_day = pd.DataFrame.from_records(
        sales_day, columns=["name", "sales", "guests"]
    )
    df_sales_day_ly = pd.DataFrame.from_records(
        sales_day_ly, columns=["name", "sales_ly", "guests_ly"]
    )
    #df_entree_count = pd.DataFrame.from_records(
    #    entree_count, columns=["name", "entree_count"]
    #)
    #df_entree_count_ly = pd.DataFrame.from_records(
    #    entree_count_ly, columns=["name", "entree_count_ly"]
    #)
    sales_table = df_sales_day.merge(df_sales_day_ly, how="outer", sort=True)
    #sales_table = sales_table.merge(df_entree_count, how="outer", sort=True)
    #sales_table = sales_table.merge(df_entree_count_ly, how="outer", sort=True)
    sales_table = sales_table.merge(top_sales_df, how="left")

    labor_day = (
        db.session.query(
            Labor.name,
            func.sum(Labor.hours).label("total_hours"),
            func.sum(Labor.dollars).label("total_dollars"),
        )
        .filter(Labor.date == fiscal_dates["start_day"])
        .group_by(Labor.name)
        .all()
    )

    labor_day_ly = (
        db.session.query(
            Labor.name,
            func.sum(Labor.hours).label("total_hours_ly"),
            func.sum(Labor.dollars).label("total_dollars_ly"),
        )
        .filter(Labor.date == fiscal_dates["start_day_ly"])
        .group_by(Labor.name)
        .all()
    )

    df_labor_day = pd.DataFrame.from_records(
        labor_day, columns=["name", "hours", "dollars"]
    )
    df_labor_day_ly = pd.DataFrame.from_records(
        labor_day_ly, columns=["name", "hours_ly", "dollars_ly"]
    )
    labor_table = df_labor_day.merge(df_labor_day_ly, how="outer", sort=True)

    daily_table = sales_table.merge(labor_table, how="outer", sort=True)

    daily_table = daily_table.merge(store_df, how="left")
    daily_table = daily_table.set_index("name")

    # Grab top sales over last year before we add totals
    daily_table = daily_table.fillna(0)
    daily_table["doly"] = daily_table.sales - daily_table.sales_ly
    daily_table["poly"] = (
        (daily_table.sales - daily_table.sales_ly) / daily_table.sales_ly * 100
    )
    daily_top = daily_table[["doly", "poly"]]
    daily_top = daily_top.nlargest(5, "poly", keep="all")

    # daily_table.loc["TOTALS"] = daily_table.sum(numeric_only=True)
    daily_table["guest_check_avg"] = daily_table["sales"] / daily_table[
        "guests"
    ].astype(float)
    #daily_table["entree_check_avg"] = daily_table["sales"] / daily_table[
    #    "entree_count"
    #].astype(float)
    daily_table["labor_pct"] = daily_table.dollars / daily_table.sales
    daily_table["labor_pct_ly"] = daily_table.dollars_ly / daily_table.sales_ly
    daily_table = daily_table.fillna(0)
    daily_totals = daily_table.sum()

    # Weekly Sales Table
    sales_week = (
        db.session.query(Sales.name, func.sum(Sales.sales).label("total_sales"))
        .filter(
            Sales.date.between(fiscal_dates["start_week"], fiscal_dates["end_week"])
        )
        .group_by(Sales.name)
        .all()
    )

    sales_week_ly = (
        db.session.query(Sales.name, func.sum(Sales.sales).label("total_sales_ly"))
        .filter(
            Sales.date.between(
                fiscal_dates["start_week_ly"], fiscal_dates["week_to_date"]
            )
        )
        .group_by(Sales.name)
        .all()
    )

    df_sales_week = pd.DataFrame.from_records(sales_week, columns=["name", "sales"])
    df_sales_week_ly = pd.DataFrame.from_records(
        sales_week_ly, columns=["name", "sales_ly"]
    )
    sales_table_wk = df_sales_week.merge(df_sales_week_ly, how="outer", sort=True)

    labor_week = (
        db.session.query(
            Labor.name,
            func.sum(Labor.hours).label("total_hours"),
            func.sum(Labor.dollars).label("total_dollars"),
        )
        .filter(
            Labor.date.between(fiscal_dates["start_week"], fiscal_dates["end_week"])
        )
        .group_by(Labor.name)
        .all()
    )

    labor_week_ly = (
        db.session.query(
            Labor.name,
            func.sum(Labor.hours).label("total_hours_ly"),
            func.sum(Labor.dollars).label("total_dollars_ly"),
        )
        .filter(
            Labor.date.between(
                fiscal_dates["start_week_ly"], fiscal_dates["week_to_date"]
            )
        )
        .group_by(Labor.name)
        .all()
    )

    df_labor_week = pd.DataFrame.from_records(
        labor_week, columns=["name", "hours", "dollars"]
    )
    df_labor_week_ly = pd.DataFrame.from_records(
        labor_week_ly, columns=["name", "hours_ly", "dollars_ly"]
    )
    labor_table_wk = df_labor_week.merge(df_labor_week_ly, how="outer", sort=True)

    weekly_table = sales_table_wk.merge(labor_table_wk, how="outer", sort=True)
    weekly_table = weekly_table.set_index("name")

    # Grab top sales over last year before we add totals
    weekly_table = weekly_table.fillna(0)
    weekly_table["doly"] = weekly_table.sales - weekly_table.sales_ly
    weekly_table["poly"] = (
        (weekly_table.sales - weekly_table.sales_ly) / weekly_table.sales_ly * 100
    )
    weekly_top = weekly_table[["doly", "poly"]]
    weekly_top = weekly_top.nlargest(5, "poly", keep="all")

    weekly_totals = weekly_table.sum()
    weekly_table["labor_pct"] = weekly_table.dollars / weekly_table.sales
    weekly_table["labor_pct_ly"] = weekly_table.dollars_ly / weekly_table.sales_ly

    # Period Sales Table
    sales_period = (
        db.session.query(Sales.name, func.sum(Sales.sales).label("total_sales"))
        .filter(
            Sales.date.between(fiscal_dates["start_period"], fiscal_dates["end_period"])
        )
        .group_by(Sales.name)
        .all()
    )

    sales_period_ly = (
        db.session.query(Sales.name, func.sum(Sales.sales).label("total_sales_ly"))
        .filter(
            Sales.date.between(
                fiscal_dates["start_period_ly"], fiscal_dates["period_to_date"]
            )
        )
        .group_by(Sales.name)
        .all()
    )

    df_sales_period = pd.DataFrame.from_records(sales_period, columns=["name", "sales"])
    df_sales_period_ly = pd.DataFrame.from_records(
        sales_period_ly, columns=["name", "sales_ly"]
    )
    sales_table_pd = df_sales_period.merge(df_sales_period_ly, how="outer", sort=True)

    labor_period = (
        db.session.query(
            Labor.name,
            func.sum(Labor.hours).label("total_hours"),
            func.sum(Labor.dollars).label("total_dollars"),
        )
        .filter(
            Labor.date.between(fiscal_dates["start_period"], fiscal_dates["end_period"])
        )
        .group_by(Labor.name)
        .all()
    )

    labor_period_ly = (
        db.session.query(
            Labor.name,
            func.sum(Labor.hours).label("total_hours_ly"),
            func.sum(Labor.dollars).label("total_dollars_ly"),
        )
        .filter(
            Labor.date.between(
                fiscal_dates["start_period_ly"], fiscal_dates["period_to_date"]
            )
        )
        .group_by(Labor.name)
        .all()
    )

    df_labor_period = pd.DataFrame.from_records(
        labor_period, columns=["name", "hours", "dollars"]
    )
    df_labor_period_ly = pd.DataFrame.from_records(
        labor_period_ly, columns=["name", "hours_ly", "dollars_ly"]
    )
    labor_table_pd = df_labor_period.merge(df_labor_period_ly, how="outer", sort=True)

    period_table = sales_table_pd.merge(labor_table_pd, how="outer", sort=True)
    period_table = period_table.set_index("name")

    # Grab top sales over last year before we add totals
    period_table = period_table.fillna(0)
    period_table["doly"] = period_table.sales - period_table.sales_ly
    period_table["poly"] = (
        (period_table.sales - period_table.sales_ly) / period_table.sales_ly * 100
    )
    period_top = period_table[["doly", "poly"]]
    period_top = period_top.nlargest(5, "poly", keep="all")

    period_totals = period_table.sum()
    period_table["labor_pct"] = period_table.dollars / period_table.sales
    period_table["labor_pct_ly"] = period_table.dollars_ly / period_table.sales_ly

    # Yearly Sales Table
    sales_yearly = (
        db.session.query(Sales.name, func.sum(Sales.sales).label("total_sales"))
        .filter(
            Sales.date.between(fiscal_dates["start_year"], fiscal_dates["end_year"])
        )
        .group_by(Sales.name)
        .all()
    )

    sales_yearly_ly = (
        db.session.query(Sales.name, func.sum(Sales.sales).label("total_sales_ly"))
        .filter(
            Sales.date.between(
                fiscal_dates["start_year_ly"], fiscal_dates["year_to_date"]
            )
        )
        .group_by(Sales.name)
        .all()
    )

    df_sales_yearly = pd.DataFrame.from_records(sales_yearly, columns=["name", "sales"])
    df_sales_yearly_ly = pd.DataFrame.from_records(
        sales_yearly_ly, columns=["name", "sales_ly"]
    )
    sales_table_yr = df_sales_yearly.merge(df_sales_yearly_ly, how="outer", sort=True)

    labor_yearly = (
        db.session.query(
            Labor.name,
            func.sum(Labor.hours).label("total_hours"),
            func.sum(Labor.dollars).label("total_dollars"),
        )
        .filter(
            Labor.date.between(fiscal_dates["start_year"], fiscal_dates["end_year"])
        )
        .group_by(Labor.name)
        .all()
    )

    labor_yearly_ly = (
        db.session.query(
            Labor.name,
            func.sum(Labor.hours).label("total_hours_ly"),
            func.sum(Labor.dollars).label("total_dollars_ly"),
        )
        .filter(
            Labor.date.between(
                fiscal_dates["start_year_ly"], fiscal_dates["year_to_date"]
            )
        )
        .group_by(Labor.name)
        .all()
    )

    df_labor_yearly = pd.DataFrame.from_records(
        labor_yearly, columns=["name", "hours", "dollars"]
    )
    df_labor_yearly_ly = pd.DataFrame.from_records(
        labor_yearly_ly, columns=["name", "hours_ly", "dollars_ly"]
    )
    labor_table_yr = df_labor_yearly.merge(df_labor_yearly_ly, how="outer", sort=True)

    yearly_table = sales_table_yr.merge(labor_table_yr, how="outer", sort=True)
    yearly_table = yearly_table.set_index("name")

    # Grab top sales over last year before we add totals
    yearly_table = yearly_table.fillna(0)
    yearly_table["doly"] = yearly_table.sales - yearly_table.sales_ly
    yearly_table["poly"] = (
        (yearly_table.sales - yearly_table.sales_ly) / yearly_table.sales_ly * 100
    )
    yearly_top = yearly_table[["doly", "poly"]]
    yearly_top = yearly_top.nlargest(5, "poly", keep="all")

    yearly_totals = yearly_table.sum()
    yearly_table["labor_pct"] = yearly_table.dollars / yearly_table.sales
    yearly_table["labor_pct_ly"] = yearly_table.dollars_ly / yearly_table.sales_ly

    return render_template(
        "home/index.html",
        title=Config.COMPANY_NAME,
        company_name=Config.COMPANY_NAME,
        # form1=form1,
        # form3=form3,
        segment="index",
        # current_user=current_user,
        roles=current_user.roles,
        **locals(),
    )


@blueprint.route("/<int:store_id>/store/", methods=["GET", "POST"])
@login_required
def store(store_id):

    TODAY = datetime.date(datetime.now())
    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
    YSTDAY = TODAY - timedelta(days=1)

    store = Restaurants.query.filter_by(id=store_id).first()

    if not "token" in session:
        session["token"] = TODAY.strftime("%Y-%m-%d")
        return redirect(url_for("home_blueprint.store", store_id=store.id))

    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))

    if store_id in [4, 9, 11, 17, 16]:
        concept = "steakhouse"
    else:
        concept = "casual"

    data = Restaurants.query.all()
    store_df = pd.DataFrame([x.as_dict() for x in data])

    if not Sales.query.filter_by(
        date=fiscal_dates["start_day"], name=store.name
    ).first():
        session["token"] = find_day_with_sales(
            day=fiscal_dates["start_day"], store=store.name
        )
        return redirect(url_for("home_blueprint.store", store_id=store.id))

    # Get Data
    form1 = DateForm()
    form3 = StoreForm()
    form4 = PotatoForm()
    if form1.submit1.data and form1.validate():
        """
        When new date submitted, the data for that date will be replaced with new data from R365
        We check if there are infact sales for that day, if not, it resets to yesterday, if
        there are sales, then labor is polled
        """
        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
        session["token"] = new_day
        return redirect(url_for("home_blueprint.store", store_id=store.id))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        data = (form3.store.data)
        session["store_list"] = tuple([x.id for x in data])
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    if form4.submit4.data and form4.validate():
        store_id = form4.store.data.id
        return redirect(url_for("home_blueprint.potato", store_id=store.id))

    # sales cards
    def get_sales(start, end, store):
        sales = []
        lst = (
            db.session.query(func.sum(Sales.sales).label("total_sales"))
            .filter(Sales.date.between(start, end), Sales.name == store)
            .all()
        )
        for i in lst:
            sales = i.total_sales
        return sales

    sales_day = get_sales(
        fiscal_dates["start_day"], fiscal_dates["start_day"], store.name
    )
    sales_day_ly = get_sales(
        fiscal_dates["start_day_ly"], fiscal_dates["start_day_ly"], store.name
    )
    sales_week = get_sales(
        fiscal_dates["start_week"], fiscal_dates["end_week"], store.name
    )
    sales_week_ly = get_sales(
        fiscal_dates["start_week_ly"], fiscal_dates["week_to_date"], store.name
    )
    sales_period = get_sales(
        fiscal_dates["start_period"], fiscal_dates["end_period"], store.name
    )
    sales_period_ly = get_sales(
        fiscal_dates["start_period_ly"], fiscal_dates["period_to_date"], store.name
    )
    sales_year = get_sales(
        fiscal_dates["start_year"], fiscal_dates["end_year"], store.name
    )
    sales_year_ly = get_sales(
        fiscal_dates["start_year_ly"], fiscal_dates["year_to_date"], store.name
    )

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

    daily_sales_list = get_chart_values(
        fiscal_dates["start_week"], fiscal_dates["end_week"], Calendar.date
    )
    daily_sales_list_ly = get_chart_values(
        fiscal_dates["start_week_ly"], fiscal_dates["end_week_ly"], Calendar.date
    )
    weekly_sales_list = get_chart_values(
        fiscal_dates["start_period"], fiscal_dates["end_period"], Calendar.week
    )
    weekly_sales_list_ly = get_chart_values(
        fiscal_dates["start_period_ly"], fiscal_dates["end_period_ly"], Calendar.week
    )
    period_sales_list = get_chart_values(
        fiscal_dates["start_year"], fiscal_dates["end_year"], Calendar.period
    )
    period_sales_list_ly = get_chart_values(
        fiscal_dates["start_year_ly"], fiscal_dates["end_year_ly"], Calendar.period
    )

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

    #    def sales_labor_table(start, end):
    #        # Build sales and labor stats for the time period given
    #
    #        food_sales = get_category_sales(start, end, store.name, "FOOD")
    #        beer_sales = get_category_sales(start, end, store.name, "BEER")
    #        liquor_sales = get_category_sales(start, end, store.name, "LIQUOR")
    #        wine_sales = get_category_sales(start, end, store.name, "WINE")
    #        gift_card_sales = get_category_sales(start, end, store.name, "GIFT CARDS")
    #
    #        sales_table = food_sales.merge(beer_sales)
    #        sales_table = sales_table.merge(liquor_sales)
    #        sales_table = sales_table.merge(wine_sales)
    #        sales_table = sales_table.merge(gift_card_sales, how="outer")
    #        sales_table.rename(
    #            columns={
    #                "FOOD": "food",
    #                "BEER": "beer",
    #                "LIQUOR": "liquor",
    #                "WINE": "wine",
    #                "GIFT CARDS": "gift_cards",
    #            },
    #            inplace=True,
    #        )
    #        sales_table.fillna(value=0, inplace=True)
    #        sales_table["alcohol_sales"] = (
    #            sales_table.beer + sales_table.liquor + sales_table.wine
    #        )
    #        sales_table["total_sales"] = sales_table.food + sales_table.alcohol_sales
    #        sales_table["net_sales"] = sales_table.total_sales + sales_table.gift_cards
    #
    #        # Labor
    #        bar_labor = get_category_labor(start, end, store.name, "Bar")
    #        host_labor = get_category_labor(start, end, store.name, "Host")
    #        restaurant_labor = get_category_labor(start, end, store.name, "Restaurant")
    #        kitchen_labor = get_category_labor(start, end, store.name, "Kitchen")
    #
    #        labor_table = bar_labor.merge(host_labor)
    #        labor_table = labor_table.merge(restaurant_labor)
    #        labor_table = labor_table.merge(kitchen_labor)
    #        labor_table.fillna(value=0, inplace=True)
    #
    #        labor_table["Total_Labor"] = (
    #            labor_table.Bar
    #            + labor_table.Host
    #            + labor_table.Restaurant
    #            + labor_table.Kitchen
    #        )
    #
    #        join_data = labor_table[
    #            [
    #                "Bar",
    #                "Host",
    #                "Restaurant",
    #                "Kitchen",
    #                "Total_Labor",
    #            ]
    #        ]
    #        _table = sales_table.join(join_data)
    #        _table["Labor_pct"] = _table.Total_Labor / _table.total_sales
    #        _table["Bar_pct"] = _table.Bar / (_table.alcohol_sales)
    #        _table["Host_pct"] = _table.Host / (_table.food)
    #        _table["Restaurant_pct"] = _table.Restaurant / (_table.food)
    #        _table["Kitchen_pct"] = _table.Kitchen / (_table.food)
    #        _table["name"] = store.name
    #
    #        _table = _table.merge(store_df, how="left")
    #        totals = _table.sum()
    #        return totals
    #
    #    weekly_totals = sales_labor_table(
    #        fiscal_dates["start_week"], fiscal_dates["end_week"]
    #    )
    #    period_totals = sales_labor_table(
    #        fiscal_dates["start_period"], fiscal_dates["end_period"]
    #    )

    stone_items = []
    sea_bass = []
    salmon = []
    feature = []

    # def get_shellfish(regex):

    #    lst = (
    #        db.session.query(Transactions.item)
    #        .filter(Transactions.item.regexp_match(regex))
    #        .group_by(Transactions.item)
    #    ).all()
    #    items = []
    #    for i in lst:
    #        cost = (
    #            db.session.query(
    #                Transactions.item,
    #                Transactions.date,
    #                Transactions.debit,
    #                Transactions.quantity,
    #            )
    #            .filter(
    #                Transactions.item == i.item,
    #                Transactions.store_id == store_id,
    #                Transactions.type == "AP Invoice",
    #            )
    #            .order_by(Transactions.date.desc())
    #        ).first()
    #        if cost:
    #            row_dict = dict(cost)
    #            ext = re.findall(r"\d*\.?\d", i.item)
    #            if not ext:
    #                ext = re.findall(r"\d{1,2}", i.item)
    #            size = float(ext[0])
    #            row_dict["size"] = size
    #            items.append(row_dict)
    #    return items

    def get_fish(regex):

        fish = (
            db.session.query(
                Transactions.item,
                Transactions.date,
                Transactions.UofM,
                func.sum(Transactions.amount).label("cost"),
                func.sum(Transactions.quantity).label("count"),
            )
            .filter(
                Transactions.item.regexp_match(regex),
                Transactions.store_id == store_id,
                Transactions.type == "AP Invoice",
            )
            .group_by(Transactions.item, Transactions.date, Transactions.UofM)
            .order_by(Transactions.date.desc())
            .limit(5)
            .all()
        )
        return fish

    live_lobster_avg_cost = get_item_avg_cost(
        "SEAFOOD Lobster Live*",
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
        store_id,
    )
    with open("./lobster_items.json") as file:
        lobster_items = json.load(file)

    stone_claw_avg_cost = get_item_avg_cost(
        "^(SEAFOOD Crab Stone Claw)",
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
        store_id,
    )
    with open("./stone_claw_items.json") as file:
        stone_items = json.load(file)

    if concept == "steakhouse":
        # lobster_items = get_shellfish("SEAFOOD Lobster Live*")
        # stone_items = get_shellfish("^(SEAFOOD Crab Stone Claw)")
        sea_bass = get_fish("SEAFOOD Sea Bass Chilean")
        salmon = get_fish("SEAFOOD Sea Bass Chilean")

    if concept == "casual":
        feature = get_fish("SEAFOOD Feature Fish")
        salmon = get_fish("^(SEAFOOD) (Salmon)$")

    # Chicken & Steak Order
    def get_purchases(regex, days):
        #
        item_list = []
        items = (
            Transactions.query.with_entities(
                Transactions.item,
            )
            .distinct(Transactions.item)
            .filter(
                Transactions.item.regexp_match(regex),
                Transactions.name == store.name,
                Transactions.date >= days,
                Transactions.type == "AP Invoice",
            )
            .order_by(
                Transactions.item,
            )
        ).all()
        [item_list.append(y) for x in items for y in x]
        return item_list

    def get_unit_values(start, end, time, regex, items):
        chart = (
            db.session.query(func.sum(Menuitems.amount).label("sales"))
            .select_from(Menuitems)
            .join(Calendar, Calendar.date == Menuitems.date)
            .group_by(time)
            .order_by(time)
            .filter(
                Menuitems.date.between(start, end),
                Menuitems.menuitem.regexp_match(regex),
                Menuitems.menuitem.in_(items),
            )
        )
        value = []
        for v in chart:
            value.append(int(v.sales))

        return value

    def get_unit_sales(start, end, list):
        query = (
            db.session.query(
                Menuitems.menuitem,
                func.sum(Menuitems.quantity).label("count"),
            )
            .filter(
                Menuitems.date.between(start, end),
                Menuitems.menuitem.in_(list),
                Menuitems.name == store.name,
            )
            .group_by(Menuitems.menuitem)
        ).all()
        sales = pd.DataFrame.from_records(query, columns=["menuitem", "quantity"])
        return sales

    def get_order_table(regex):
        """
        Get a list of items purchased in last 30 days
        check if used in any prep recipesselfself.
        Match each item with POS menuitem for last week
        and same week last year and calculate average
        """
        prep_item_list = []
        item_list = []
        # Get list of items purchased in last 30 days
        items = (
            Transactions.query.with_entities(
                Transactions.item,
            )
            .distinct(Transactions.item)
            .filter(
                Transactions.item.regexp_match(regex),
                Transactions.name == store.name,
                Transactions.date >= fiscal_dates["last_thirty"],
                Transactions.type == "AP Invoice",
            )
            .order_by(
                Transactions.item,
            )
        ).all()
        [item_list.append(y) for x in items for y in x]

        for i in item_list:
            # Get all recipes with ingredient i
            recipe_lst = (
                db.session.query(
                    Ingredients.item,
                    Ingredients.recipe,
                    Ingredients.qty,
                    Ingredients.uofm,
                ).filter(Ingredients.item == i)
            ).all()
            for x in recipe_lst:
                # account for recipes with prep items for ingredients
                if re.search(r"^PREP", x.recipe):
                    prep_lst = (
                        db.session.query(
                            Ingredients.item,
                            Ingredients.recipe,
                            Ingredients.qty,
                            Ingredients.uofm,
                        ).filter(Ingredients.item == x.recipe)
                    ).all()
                    if not prep_lst:
                        continue
                    # Replace the prep item with the original steak
                    row_dict = dict(prep_lst[0])
                    row_dict.update(item=i)
                    prep_item_list.append(row_dict)
                if re.search(r"^MENU", x.recipe):
                    prep_item_list.append(x)
        menu_list = []
        for p in prep_item_list:
            recipes = (
                db.session.query(Recipes)
                .filter(Recipes.recipe == p["recipe"], Recipes.name == store.name)
                .first()
            )
            if recipes:
                row_dict = dict(p)
                row_dict["menuitem"] = recipes.menuitem
                menu_list.append(row_dict)
        df = pd.DataFrame(menu_list)
        unit_list = df.loc[:, "menuitem"]
        unit_sales = get_unit_sales(
            fiscal_dates["start_previous_week"],
            fiscal_dates["end_previous_week"],
            unit_list,
        )
        df = df.merge(unit_sales, on="menuitem", how="outer")
        df["last_week"] = df["qty"] * df["quantity"].astype(float)
        unit_sales = get_unit_sales(
            fiscal_dates["start_week_ly"], fiscal_dates["end_week_ly"], unit_list
        )
        df = df.merge(unit_sales, on="menuitem", how="outer")
        df["last_year"] = df["qty"] * df["quantity_y"].astype(float)
        df.drop(["recipe", "qty"], axis=1, inplace=True)
        order = df.groupby(["item", "uofm"]).sum()

        return order

    steak_order = get_order_table("^(BEEF Steak)")
    # TODO multiple prep items does not work
    # chicken_order = get_order_table("^(PLTRY Chicken)")

    # Item price Change Analysis
    def get_transactions_by_category(cat, start, end, trans_type):
        query = (
            Transactions.query.with_entities(
                Transactions.item,
                Transactions.UofM,
                Transactions.quantity,
                Transactions.amount,
            )
            .distinct(Transactions.item)
            .filter(
                Transactions.category1 == cat,
                Transactions.date.between(start, end),
                Transactions.name == store.name,
                Transactions.type == trans_type,
            )
            .order_by(
                Transactions.item,
            )
        ).all()
        item_list = []
        if not query:
            row_dict = {
                "item": "Null",
                "UofM": "Null",
                "quantity": 0,
                "amount": 0,
                "base_qty": 1,
                "base_uofm": "Each",
            }
            item_list.append(row_dict)
        for q in query:
            qty, uofm = convert_uofm(q)
            row_dict = dict(q)
            row_dict["base_qty"] = qty
            row_dict["base_uofm"] = uofm
            item_list.append(row_dict)

        return item_list

    food_begin = get_transactions_by_category(
        "Food",
        fiscal_dates["end_previous_week"],
        fiscal_dates["end_previous_week"],
        "Stock Count",
    )
    df_begin = pd.DataFrame(food_begin)
    df_begin["inv_cost"] = df_begin["amount"] / (
        df_begin["base_qty"] * df_begin["quantity"]
    )
    df_begin.drop(columns=["quantity", "amount"], inplace=True)
    food_today = get_transactions_by_category(
        "Food", fiscal_dates["start_week"], CURRENT_DATE, "AP Invoice"
    )
    df_today = pd.DataFrame(food_today)
    df_today["current_cost"] = df_today["amount"] / (
        df_today["base_qty"] * df_today["quantity"]
    )
    df_today.drop(
        columns=["UofM", "quantity", "amount", "base_qty", "base_uofm"], inplace=True
    )
    df_merge = pd.merge(df_begin, df_today, on="item", how="left")
    df_merge["cost_diff"] = df_merge["current_cost"] - df_merge["inv_cost"]
    df_merge["pct_diff"] = (df_merge["cost_diff"] / df_merge["inv_cost"]) * 100
    df_merge.dropna(axis=0, how="any", subset=["cost_diff"], inplace=True)
    df_merge.sort_values(by=["pct_diff"], ascending=False, inplace=True)
    price_increase = df_merge.head(10)
    price_decrease = df_merge.tail(10).sort_values(by="pct_diff")

    # Costs charts
    def get_category_costs(start, end, sales, cat):
        query = (
            db.session.query(
                func.sum(Transactions.credit).label("credits"),
                func.sum(Transactions.debit).label("costs"),
            )
            .select_from(Transactions)
            .join(Calendar, Calendar.date == Transactions.date)
            .group_by(Calendar.period)
            .order_by(Calendar.period)
            .filter(
                Transactions.date.between(start, end),
                Transactions.account.in_(cat),
                Transactions.name == store.name,
            )
        )
        dol_lst = []
        for v in query:
            amount = v.costs - v.credits
            dol_lst.append(amount)
        add_items = len(sales) - len(dol_lst)
        for i in range(0, add_items):
            dol_lst.append(0)
        # for i in range(0, len(sales)):
        #    pct_lst.append(dol_lst[i] / sales[i])
        return dol_lst

    # Supplies cost chart
    supply_cost_dol = get_category_costs(
        fiscal_dates["start_year"],
        fiscal_dates["end_year"],
        period_sales_list,
        cat=[
            "Restaurant Supplies",
            "Kitchen Supplies",
            "Cleaning Supplies",
            "Office Supplies",
            "Bar Supplies",
        ],
    )
    supply_cost_dol_ly = get_category_costs(
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
        period_sales_list_ly,
        cat=[
            "Restaurant Supplies",
            "Kitchen Supplies",
            "Cleaning Supplies",
            "Office Supplies",
            "Bar Supplies",
        ],
    )
    query = (
        Budgets.query.with_entities(Budgets.total_supplies)
        .order_by(Budgets.period)
        .filter(Budgets.year == fiscal_dates["year"], Budgets.name == store.name)
    ).all()
    supply_budget = []
    for v in query:
        supply_budget.append(v.total_supplies)

    # Smallwares cost chart
    smallware_cost_dol = get_category_costs(
        fiscal_dates["start_year"],
        fiscal_dates["end_year"],
        period_sales_list,
        cat=["China", "Silverware", "Glassware", "Smallwares"],
    )
    smallware_cost_dol_ly = get_category_costs(
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
        period_sales_list_ly,
        cat=["China", "Silverware", "Glassware", "Smallwares"],
    )
    query = (
        Budgets.query.with_entities(Budgets.total_smallwares)
        .order_by(Budgets.period)
        .filter(Budgets.year == fiscal_dates["year"], Budgets.name == store.name)
    ).all()
    smallware_budget = []
    for v in query:
        smallware_budget.append(v.total_smallwares)

    # linen cost chart
    # linen_cost_dol = get_glaccount_costs(
    #    fiscal_dates["start_year"],
    #    fiscal_dates["end_year"],
    #    "Linen",
    #    store.name,
    #    Calendar.period,
    # )

    # linen_cost_dol_ly = get_glaccount_costs(
    #    fiscal_dates["start_year_ly"],
    #    fiscal_dates["end_year_ly"],
    #    "Linen",
    #    store.name,
    #    Calendar.period,
    # )

    # linen cost chart
    linen_cost_dol = get_category_costs(
        fiscal_dates["start_year"],
        fiscal_dates["end_year"],
        period_sales_list,
        cat=["Linen"],
    )
    linen_cost_dol_ly = get_category_costs(
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
        period_sales_list_ly,
        cat=["Linen"],
    )

    current_supply_cost = supply_cost_dol[fiscal_dates["period"] - 1]
    current_supply_budget = supply_budget[fiscal_dates["period"] - 1]
    current_smallware_cost = smallware_cost_dol[fiscal_dates["period"] - 1]
    current_smallware_budget = smallware_budget[fiscal_dates["period"] - 1]
    period_linen_cost = linen_cost_dol[fiscal_dates["period"] - 1]
    period_linen_cost_ly = linen_cost_dol_ly[fiscal_dates["period"] - 1]

    query = (
        Transactions.query.with_entities(Transactions.item).filter(
            Transactions.date >= fiscal_dates["start_week"],
            Transactions.name == store.name,
            Transactions.item.regexp_match("^DO NOT USE*"),
        )
    ).all()
    do_not_use = pd.DataFrame.from_records(query, columns=["menuitem"])

    return render_template(
        "home/store.html",
        title=store.name,
        company_name=Config.COMPANY_NAME,
        store_id=store.id,
        segment="store.name",
        concept=concept,
        form1=form1,
        form3=form3,
        form4=form4,
        current_user=current_user,
        roles=current_user.roles,
        fiscal_dates=fiscal_dates,
        sales_day=sales_day,
        sales_day_ly=sales_day_ly,
        sales_week=sales_week,
        sales_week_ly=sales_week_ly,
        sales_period=sales_period,
        sales_period_ly=sales_period_ly,
        sales_year=sales_year,
        sales_year_ly=sales_year_ly,
        daily_sales_list=daily_sales_list,
        daily_sales_list_ly=daily_sales_list_ly,
        weekly_sales_list=weekly_sales_list,
        weekly_sales_list_ly=weekly_sales_list_ly,
        period_sales_list=period_sales_list,
        period_sales_list_ly=period_sales_list_ly,
        budgets3=budgets3,
        supply_cost_dol=supply_cost_dol,
        supply_cost_dol_ly=supply_cost_dol_ly,
        supply_budget=supply_budget,
        smallware_cost_dol=smallware_cost_dol,
        smallware_cost_dol_ly=smallware_cost_dol_ly,
        smallware_budget=smallware_budget,
        current_supply_cost=current_supply_cost,
        current_supply_budget=current_supply_budget,
        current_smallware_cost=current_smallware_cost,
        current_smallware_budget=current_smallware_budget,
        linen_cost_dol=linen_cost_dol,
        linen_cost_dol_ly=linen_cost_dol_ly,
        period_linen_cost=period_linen_cost,
        period_linen_cost_ly=period_linen_cost_ly,
        # weekly_totals=weekly_totals,
        # period_totals=period_totals,
        lobster_items=lobster_items,
        live_lobster_avg_cost=live_lobster_avg_cost,
        stone_items=stone_items,
        stone_claw_avg_cost=stone_claw_avg_cost,
        sea_bass=sea_bass,
        salmon=salmon,
        feature=feature,
        steak_order=steak_order,
        # chicken_order=chicken_order,
        price_increase=price_increase,
        price_decrease=price_decrease,
        do_not_use=do_not_use,
    )


@blueprint.route("/marketing/", methods=["GET", "POST"])
@login_required
def marketing():

    TODAY = datetime.date(datetime.now())
    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
    YSTDAY = TODAY - timedelta(days=1)

    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))
    form1 = DateForm()
    if form1.submit1.data and form1.validate():
        """ """
        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
        session["token"] = new_day
        return redirect(url_for("home_blueprint.marketing"))

    form3 = StoreForm()
    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        data = (form3.store.data)
        session["store_list"] = tuple([x.id for x in data])
        return redirect(url_for("home_blueprint.store", store_id=store_id))

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
                    print(v)
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
                    print(v)
                    value.append(int(v.sales))

        return value

    # list of last 13 periods
    period_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
    slice1 = period_list[fiscal_dates["period"] :]
    slice2 = period_list[: fiscal_dates["period"]]
    period_order = slice1 + slice2
    print(period_order)

    print(fiscal_dates["last_threesixtyfive"])
    giftcard_sales = get_giftcard_sales(
        fiscal_dates["last_threesixtyfive"], fiscal_dates["start_day"], Calendar.period
    )
    print(giftcard_sales)
    giftcard_payments = get_giftcard_payments(
        fiscal_dates["last_threesixtyfive"], fiscal_dates["start_day"], Calendar.period
    )
    print(giftcard_payments)

    # TODO set to trailing year beginning in 2023
    giftcard_diff = []
    dif = 0
    for ii in range(len(giftcard_sales)):
        dif = (giftcard_sales[ii] - giftcard_payments[ii]) + dif
        print(dif)
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
        sales = pd.DataFrame.from_records(
            query, columns=["store", "amount", "quantity"]
        )
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

        payments = pd.DataFrame.from_records(
            query, columns=["restaurant_id", "payment"]
        )
        payments.sort_values(by=["payment"], ascending=False, inplace=True)
        payments = df_loc.merge(payments, on="restaurant_id")

        payments.loc["TOTALS"] = payments.sum(numeric_only=True)
        return payments

    gift_card_sales = get_giftcard_sales_per_store(
        fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    gift_card_payments = get_giftcard_payments_per_store(
        fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    gift_card_sales = gift_card_sales.merge(
        gift_card_payments, left_on="store", right_on="name"
    )
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
    form5 = RecipeForm()
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
        data = (form3.store.data)
        session["store_list"] = tuple([x.id for x in data])

        return redirect(url_for("home_blueprint.store", store_id=store_id))

    if form5.submit5.data and form5.validate():
        response = update_recipe_costs()
        if response == 0:
            flash(f"Recipe costs updated", "success")
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
    unassigned_sales = pd.DataFrame.from_records(
        query, columns=["store", "menuitem", "category", "amount", "quantity"]
    )
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
        fiscal_dates=fiscal_dates,
        form1=form1,
        form2=form2,
        form3=form3,
        form5=form5,
        unassigned_sales=unassigned_sales,
        do_not_use=do_not_use,
    )


@blueprint.route("/alcohol/", methods=["GET", "POST"])
@login_required
def alcohol():

    TODAY = datetime.date(datetime.now())
    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
    YSTDAY = TODAY - timedelta(days=1)

    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))

    form1 = DateForm()
    form3 = StoreForm()

    if form1.submit1.data and form1.validate():
        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
        session["token"] = new_day
        return redirect(url_for("home_blueprint.alcohol"))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        data = (form3.store.data)
        session["store_list"] = tuple([x.id for x in data])
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    steakhouse = [4, 9, 11, 17, 16]
    casual = [1, 3, 7, 8, 11, 12, 14, 21, 85]

    calendar = Calendar.query.with_entities(
        Calendar.date, Calendar.week, Calendar.period, Calendar.year
    ).all()
    cal_df = pd.DataFrame(calendar, columns=["date", "week", "period", "year"])

    def get_vendors(cat, time, concept):
        query = (
            Transactions.query.with_entities(Transactions.company)
            .filter(
                Transactions.account == cat,
                Transactions.company != "None",
                Transactions.store_id.in_(concept),
                Transactions.date >= time,
            )
            .group_by(Transactions.company)
        ).all()
        return query

    def get_purchases(cat, start, end, concept):
        items = (
            db.session.query(
                Transactions.date,
                Transactions.company,
                Transactions.item,
                Transactions.UofM,
                func.sum(Transactions.quantity).label("count"),
                func.sum(Transactions.amount).label("cost"),
            )
            .filter(
                Transactions.account == cat,
                Transactions.date.between(start, end),
                Transactions.store_id.in_(concept),
                Transactions.type == "AP Invoice",
            )
            .group_by(
                Transactions.date,
                Transactions.company,
                Transactions.item,
                Transactions.UofM,
            )
        ).all()
        item_list = []
        for i in items:
            qty, uofm = convert_uofm(i)
            # TODO fix the factor calc on purchasing
            bottle = qty / 25.360517  # convert from quarts to 750ml
            row_dict = dict(i)
            row_dict["factor"] = bottle
            item_list.append(row_dict)
        df = pd.DataFrame(item_list)
        df = df[(df != 0).all(1)]
        return df

    wine_vendors = get_vendors("Wine", fiscal_dates["start_year"], steakhouse)
    steakhouse_wine = get_purchases(
        "Wine", fiscal_dates["start_year"], fiscal_dates["end_year"], steakhouse
    )
    steakhouse_wine_values = steakhouse_wine.merge(cal_df, on="date", how="left")
    steakhouse_wine_values = steakhouse_wine_values.groupby(["period"]).sum()
    steakhouse_wine_chart = steakhouse_wine_values["cost"].tolist()
    steakhouse_wine_vendor = steakhouse_wine.groupby(["company"]).sum()
    steakhouse_wine_vendor.sort_values(by=["cost"], ascending=False, inplace=True)
    steakhouse_wine_vendor = steakhouse_wine_vendor.head(10)
    # steakhouse_wine_bottle = steakhouse_wine.groupby(["item"]).sum()
    # steakhouse_wine_bottle.sort_values(by=["cost"], ascending=False, inplace=True)

    liquor_vendors = get_vendors("Liquor", fiscal_dates["start_year"], steakhouse)
    steakhouse_liquor = get_purchases(
        "Liquor", fiscal_dates["start_year"], fiscal_dates["end_year"], steakhouse
    )
    steakhouse_liquor_values = steakhouse_liquor.merge(cal_df, on="date", how="left")
    steakhouse_liquor_values = steakhouse_liquor_values.groupby(["period"]).sum()
    steakhouse_liquor_chart = steakhouse_liquor_values["cost"].tolist()
    # steakhouse_liquor_vendor = steakhouse_liquor.groupby(["company"]).sum()
    # steakhouse_liquor_vendor.sort_values(by=["cost"], ascending=False, inplace=True)
    steakhouse_liquor_bottle = steakhouse_liquor.groupby(["item"]).sum()
    steakhouse_liquor_bottle.sort_values(by=["cost"], ascending=False, inplace=True)
    steakhouse_liquor_bottle = steakhouse_liquor_bottle.head(10)

    beer_vendors = get_vendors("Beer", fiscal_dates["start_year"], steakhouse)
    steakhouse_beer = get_purchases(
        "Beer", fiscal_dates["start_year"], fiscal_dates["end_year"], steakhouse
    )
    steakhouse_beer_values = steakhouse_beer.merge(cal_df, on="date", how="left")
    steakhouse_beer_values = steakhouse_beer_values.groupby(["period"]).sum()
    steakhouse_beer_chart = steakhouse_beer_values["cost"].tolist()
    # steakhouse_beer_vendor = steakhouse_beer.groupby(["company"]).sum()
    # steakhouse_beer_vendor.sort_values(by=["cost"], ascending=False, inplace=True)
    steakhouse_beer_bottle = steakhouse_beer.groupby(["item"]).sum()
    steakhouse_beer_bottle.sort_values(by=["cost"], ascending=False, inplace=True)
    steakhouse_beer_bottle = steakhouse_beer_bottle.head(10)

    wine_vendors = get_vendors("Wine", fiscal_dates["start_year"], casual)
    casual_wine = get_purchases(
        "Wine", fiscal_dates["start_year"], fiscal_dates["end_year"], casual
    )
    casual_wine_values = casual_wine.merge(cal_df, on="date", how="left")
    casual_wine_values = casual_wine_values.groupby(["period"]).sum()
    casual_wine_chart = casual_wine_values["cost"].tolist()
    casual_wine_vendor = casual_wine.groupby(["company"]).sum()
    casual_wine_vendor.sort_values(by=["cost"], ascending=False, inplace=True)
    casual_wine_vendor = casual_wine_vendor.head(10)
    # casual_wine_bottle = casual_wine.groupby(["item"]).sum()
    # casual_wine_bottle.sort_values(by=["cost"], ascending=False, inplace=True)

    liquor_vendors = get_vendors("Liquor", fiscal_dates["start_year"], casual)
    casual_liquor = get_purchases(
        "Liquor", fiscal_dates["start_year"], fiscal_dates["end_year"], casual
    )
    casual_liquor_values = casual_liquor.merge(cal_df, on="date", how="left")
    casual_liquor_values = casual_liquor_values.groupby(["period"]).sum()
    casual_liquor_chart = casual_liquor_values["cost"].tolist()
    # casual_liquor_vendor = casual_liquor.groupby(["company"]).sum()
    # casual_liquor_vendor.sort_values(by=["cost"], ascending=False, inplace=True)
    casual_liquor_bottle = casual_liquor.groupby(["item"]).sum()
    casual_liquor_bottle.sort_values(by=["cost"], ascending=False, inplace=True)
    casual_liquor_bottle = casual_liquor_bottle.head(10)

    beer_vendors = get_vendors("Beer", fiscal_dates["start_year"], casual)
    casual_beer = get_purchases(
        "Beer", fiscal_dates["start_year"], fiscal_dates["end_year"], casual
    )
    casual_beer_values = casual_beer.merge(cal_df, on="date", how="left")
    casual_beer_values = casual_beer_values.groupby(["period"]).sum()
    casual_beer_chart = casual_beer_values["cost"].tolist()
    # casual_beer_vendor = casual_beer.groupby(["company"]).sum()
    # casual_beer_vendor.sort_values(by=["cost"], ascending=False, inplace=True)
    casual_beer_bottle = casual_beer.groupby(["item"]).sum()
    casual_beer_bottle.sort_values(by=["cost"], ascending=False, inplace=True)
    casual_beer_bottle = casual_beer_bottle.head(10)

    return render_template(
        "home/alcohol.html",
        title="Alcohol",
        company_name=Config.COMPANY_NAME,
        segment="alcohol",
        fiscal_dates=fiscal_dates,
        form1=form1,
        form3=form3,
        steakhouse_wine_chart=steakhouse_wine_chart,
        steakhouse_wine_chart_ly=steakhouse_wine_chart,
        steakhouse_wine_vendor=steakhouse_wine_vendor,
        # steakhouse_wine_bottle=steakhouse_wine_bottle,
        steakhouse_liquor_chart=steakhouse_liquor_chart,
        steakhouse_liquor_chart_ly=steakhouse_liquor_chart,
        # steakhouse_liquor_vendor=steakhouse_liquor_vendor,
        steakhouse_liquor_bottle=steakhouse_liquor_bottle,
        steakhouse_beer_chart=steakhouse_beer_chart,
        steakhouse_beer_chart_ly=steakhouse_beer_chart,
        # steakhouse_beer_vendor=steakhouse_beer_vendor,
        steakhouse_beer_bottle=steakhouse_beer_bottle,
        casual_wine_chart=casual_wine_chart,
        casual_wine_chart_ly=casual_wine_chart,
        casual_wine_vendor=casual_wine_vendor,
        # casual_wine_bottle=casual_wine_bottle,
        casual_liquor_chart=casual_liquor_chart,
        casual_liquor_chart_ly=casual_liquor_chart,
        # casual_liquor_vendor=casual_liquor_vendor,
        casual_liquor_bottle=casual_liquor_bottle,
        casual_beer_chart=casual_beer_chart,
        casual_beer_chart_ly=casual_beer_chart,
        # casual_beer_vendor=casual_beer_vendor,
        casual_beer_bottle=casual_beer_bottle,
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

    if form1.submit1.data and form1.validate():
        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
        session["token"] = new_day
        return redirect(url_for("home_blueprint.profile"))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        data = (form3.store.data)
        session["store_list"] = tuple([x.id for x in data])
        return redirect(url_for("home_blueprint.profile"))

    return render_template(
        "home/profile.html",
        title="Profile",
        company_name=Config.COMPANY_NAME,
        segment="profile",
        fiscal_dates=fiscal_dates,
        form1=form1,
        form3=form3,
    )


@blueprint.route("/<int:store_id>/potato/", methods=["GET", "POST"])
@login_required
def potato(store_id):

    # TODO need to fix store ID
    TODAY = datetime.date(datetime.now())
    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
    YSTDAY = TODAY - timedelta(days=1)

    print(TODAY)
    print(session["token"])

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
    out_times = pd.read_csv(
        "/usr/local/share/potatochart.csv", usecols=["time", "in_time", "out_time"]
    )
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
    pdf.cell(
        page_width, 0.0, "* Calculated from previous 4 weeks same day sales", align="L"
    )
    pdf.ln(5)
    pdf.cell(page_width, 0.0, "- end of report -", align="C")

    return Response(
        pdf.output(dest="S").encode("latin-1"),
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment;filename=potato_loading.pdf"},
    )
