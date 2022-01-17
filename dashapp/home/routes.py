# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import json
import re
import pandas as pd
from flask.helpers import url_for
from flask_security.decorators import roles_accepted
from sqlalchemy.sql.expression import column
from dashapp.home import blueprint
from flask import flash, render_template, session, redirect, url_for
from dashapp.home.util import get_period, get_lastyear, refresh_data, get_daily_sales, get_daily_labor
from flask_security import login_required, current_user
from datetime import datetime, timedelta
from dashapp.authentication.forms import DateForm, StoreForm, UpdateForm
from dashapp.authentication.models import Menuitems, db, Calendar, Sales, Labor, Restaurants, Budgets, Transactions
from sqlalchemy import and_, or_, func


@blueprint.route("/")
@login_required
def route_default():
    TODAY = datetime.date(datetime.now())
    YSTDAY = TODAY - timedelta(days=1)
    session["targetdate"] = YSTDAY.strftime("%Y-%m-%d")
    if not Sales.query.filter_by(date=session['targetdate']).first():
        flash(
            f"Sales are not available for the selected day.  Please try again later or select a different date!",
            "warning",
        )
        TODAY = datetime.date(datetime.now())
        YSTDAY = TODAY - timedelta(days=2)
        session["targetdate"] = YSTDAY.strftime("%Y-%m-%d")
        return redirect(url_for("home_blueprint.index"))
    return redirect(url_for("home_blueprint.index"))


@blueprint.route("/index/", methods=["GET", "POST"])
@login_required
def index():

    start_day = end_day = start_week = end_week = start_period = end_period = start_year = end_year = ""
    period = year = 0
    if not session['targetdate']:
        return redirect(url_for('home_blueprint.route_default'))
    fiscal_dates = get_period(datetime.strptime(session["targetdate"], "%Y-%m-%d"))
    for i in fiscal_dates:
        day_start = datetime.strptime(i.date, "%Y-%m-%d")
        day_end = day_start + timedelta(days=1)
        end_day = day_end.strftime("%Y-%m-%d")
        start_day = i.date
        start_week = i.week_start
        end_week = i.week_end
        start_period = i.period_start
        end_period = i.period_end
        start_year = i.year_start
        end_year = i.year_end
        period = i.period
        year = i.year

    # Get matching day, week and period start and end dates
    start_day_ly = get_lastyear(start_day)
    #    end_day_ly = get_lastyear(end_day)
    start_week_ly = get_lastyear(start_week)
    end_week_ly = get_lastyear(end_week)
    week_to_date = get_lastyear(start_day)
    start_period_ly = get_lastyear(start_period)
    end_period_ly = get_lastyear(end_period)
    period_to_date = get_lastyear(start_day)
    start_year_ly = get_lastyear(start_year)
    end_year_ly = get_lastyear(end_year)
    year_to_date = get_lastyear(start_day)

    # Check for no sales
    if not Sales.query.filter_by(date=start_day).first():
        return redirect(url_for("home_blueprint.route_default"))


    # Get Data
    form1 = DateForm()
    form3 = StoreForm()
    if form1.submit1.data and form1.validate():
        """
        Change targetdate
        """
        start_day = form1.selectdate.data.strftime("%Y-%m-%d")
        session["targetdate"] = start_day
        return redirect(url_for("home_blueprint.index"))


    if form3.submit3.data and form3.validate():

        session["targetdate"] = start_day
        store_id = form3.store.data.id

        return redirect(url_for("home_blueprint.store", store_id=store_id))


    # Daily Chart
    daily_chart = (
        db.session.query(func.sum(Sales.sales).label("total_sales"))
        .filter(Sales.date.between(start_week, end_week))
        .group_by(Sales.date)
        .order_by(Sales.date)
    )
    values1 = []
    for v in daily_chart:
        values1.append(v.total_sales)

    daily_chart_ly = (
        db.session.query(func.sum(Sales.sales).label("total_sales"))
        .filter(Sales.date.between(start_week_ly, end_week_ly))
        .group_by(Sales.date)
        .order_by(Sales.date)
    )
    values1_ly = []
    for v in daily_chart_ly:
        values1_ly.append(v.total_sales)


    # TODO add daily budget


    # Weekly Chart
    weekly_chart = (
        db.session.query(func.sum(Sales.sales).label("total_sales"))
        .select_from(Sales)
        .join(Calendar, Calendar.date == Sales.date)
        .group_by(Calendar.week)
        .order_by(Calendar.week)
        .filter(Sales.date.between(start_period, end_period))
    )
    values2 = []
    for v in weekly_chart:
        values2.append(v.total_sales)

    weekly_chart_ly = (
        db.session.query(func.sum(Sales.sales).label("total_sales"))
        .select_from(Sales)
        .join(Calendar, Calendar.date == Sales.date)
        .group_by(Calendar.week)
        .order_by(Calendar.week)
        .filter(Sales.date.between(start_period_ly, end_period_ly))
    )
    values2_ly = []
    for v in weekly_chart_ly:
        values2_ly.append(v.total_sales)

    # TODO add weekly budget

    # Yearly Chart
    period_chart = (
        db.session.query(func.sum(Sales.sales).label("total_sales"))
        .select_from(Sales)
        .join(Calendar, Calendar.date == Sales.date)
        .group_by(Calendar.period)
        .order_by(Calendar.period)
        .filter(Sales.date.between(start_year, end_year))
    )
    values3 = []
    for v in period_chart:
        values3.append(v.total_sales)

    period_chart_ly = (
        db.session.query(func.sum(Sales.sales).label("total_sales"))
        .select_from(Sales)
        .join(Calendar, Calendar.date == Sales.date)
        .group_by(Calendar.period)
        .order_by(Calendar.period)
        .filter(Sales.date.between(start_year_ly, end_year_ly))
    )
    values3_ly = []
    for v in period_chart_ly:
        values3_ly.append(v.total_sales)

    budget_chart = (
        db.session.query(func.sum(Budgets.total_sales).label('total_sales'))
        .select_from(Budgets)
        .group_by(Budgets.period)
        .order_by(Budgets.period)
        .filter(Budgets.year == year)
    )
    budgets3 = []
    for v in budget_chart:
        budgets3.append(v.total_sales)

    # Daily Sales Table
    sales_day = (
        db.session.query(
            Sales.name,
            func.sum(Sales.sales).label("total_sales")
        )
        .filter(Sales.date == start_day)
        .group_by(Sales.name)
        .all()
    )

    sales_day_ly = (
        db.session.query(
            Sales.name,
            func.sum(Sales.sales).label("total_sales_ly")
        )
        .filter(Sales.date == start_day_ly)
        .group_by(Sales.name)
        .all()
    )

    entree_count = (db.session.query(
            Menuitems.name,
            func.sum(Menuitems.quantity).label('guest_count'),
        )
        .filter(Menuitems.date == start_day,
                Menuitems.menu_category.regexp_match('ENTREE*')
                )
        .group_by(Menuitems.name)
        .all()
    )
    # replace ly with guest check average
    entree_count_ly = (db.session.query(
            Menuitems.name,
            func.sum(Menuitems.quantity).label('guest_count'),
        )
        .filter(Menuitems.date == start_day_ly,
                Menuitems.menu_category.regexp_match('ENTREE*')
                )
        .group_by(Menuitems.name)
        .all()
    )

    df_sales_day = pd.DataFrame.from_records(
        sales_day, columns=["name", "sales"]
    )
    df_sales_day_ly = pd.DataFrame.from_records(
        sales_day_ly, columns=["name", "sales_ly"]
    )
    df_entree_count = pd.DataFrame.from_records(
        entree_count, columns=["name", "guest_count"]
    )
    df_entree_count_ly = pd.DataFrame.from_records(
        entree_count_ly, columns=["name", "guest_count_ly"]
    )
    sales_table = df_sales_day.merge(df_sales_day_ly, how="outer", sort=True)
    sales_table = sales_table.merge(df_entree_count, how="outer", sort=True)
    sales_table = sales_table.merge(df_entree_count_ly, how="outer", sort=True)

    labor_day = (
        db.session.query(
            Labor.name,
            func.sum(Labor.hours).label("total_hours"),
            func.sum(Labor.dollars).label("total_dollars"),
        )
        .filter(Labor.date == start_day)
        .group_by(Labor.name)
        .all()
    )

    labor_day_ly = (
        db.session.query(
            Labor.name,
            func.sum(Labor.hours).label("total_hours_ly"),
            func.sum(Labor.dollars).label("total_dollars_ly"),
        )
        .filter(Labor.date == start_day_ly)
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

    # List of stores to add ID so i can pass to other templates
    store_list = Restaurants.query.all()
    store_list = pd.DataFrame([x.as_dict() for x in store_list])
    daily_table = daily_table.merge(store_list, how="left")

    daily_table.set_index("name", inplace=True)

    # Grab top sales over last year before we add totals
    daily_table.fillna(0, inplace=True)
    daily_table['doly'] = daily_table.sales - daily_table.sales_ly
    daily_table['poly'] = (
        (daily_table.sales - daily_table.sales_ly) / daily_table.sales_ly * 100
    )
    daily_top = daily_table[['doly', 'poly']]
    daily_top = daily_top.nlargest(5, 'poly', keep='all')

    daily_table.loc["TOTALS"] = daily_table.sum(numeric_only=True)
    daily_table['check_avg'] = daily_table['sales']/daily_table['guest_count'].astype(float)
    daily_table['labor_pct'] = daily_table.dollars / daily_table.sales
    daily_table['labor_pct_ly'] = daily_table.dollars_ly / daily_table.sales_ly
    daily_table.fillna(0, inplace=True)
    daily_totals = daily_table.loc["TOTALS"]

    # Weekly Sales Table
    sales_week = (
        db.session.query(
            Sales.name,
            func.sum(Sales.sales).label("total_sales")
        )
        .filter(Sales.date.between(start_week, end_week))
        .group_by(Sales.name)
        .all()
    )

    sales_week_ly = (
        db.session.query(
            Sales.name,
            func.sum(Sales.sales).label("total_sales_ly")
        )
        .filter(
            Sales.date.between(start_week_ly, week_to_date))
        .group_by(Sales.name)
        .all()
    )

    df_sales_week = pd.DataFrame.from_records(
        sales_week, columns=["name", "sales"]
    )
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
        .filter(Labor.date.between(start_week, end_week))
        .group_by(Labor.name)
        .all()
    )

    labor_week_ly = (
        db.session.query(
            Labor.name,
            func.sum(Labor.hours).label("total_hours_ly"),
            func.sum(Labor.dollars).label("total_dollars_ly"),
        )
        .filter(Labor.date.between(start_week_ly, week_to_date))
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
    weekly_table.set_index("name", inplace=True)

    # Grab top sales over last year before we add totals
    weekly_table.fillna(0, inplace=True)
    weekly_table['doly'] = weekly_table.sales - weekly_table.sales_ly
    weekly_table['poly'] = (
        (weekly_table.sales - weekly_table.sales_ly) / weekly_table.sales_ly * 100
    )
    weekly_top = weekly_table[['doly', 'poly']]
    weekly_top = weekly_top.nlargest(5, 'poly', keep='all')

    weekly_table.loc["TOTALS"] = weekly_table.sum(numeric_only=True)
    weekly_table['labor_pct'] = weekly_table.dollars / weekly_table.sales
    weekly_table['labor_pct_ly'] = weekly_table.dollars_ly / weekly_table.sales_ly
    weekly_totals = weekly_table.loc["TOTALS"]

    # Period Sales Table
    sales_period = (
        db.session.query(
            Sales.name,
            func.sum(Sales.sales).label("total_sales")
        )
        .filter(Sales.date.between(start_period, end_period))
        .group_by(Sales.name)
        .all()
    )

    sales_period_ly = (
        db.session.query(
            Sales.name,
            func.sum(Sales.sales).label("total_sales_ly")
        )
        .filter(Sales.date.between(start_period_ly, period_to_date))
        .group_by(Sales.name)
        .all()
    )

    df_sales_period = pd.DataFrame.from_records(
        sales_period, columns=["name", "sales"]
    )
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
        .filter(Labor.date.between(start_period, end_period))
        .group_by(Labor.name)
        .all()
    )

    labor_period_ly = (
        db.session.query(
            Labor.name,
            func.sum(Labor.hours).label("total_hours_ly"),
            func.sum(Labor.dollars).label("total_dollars_ly"),
        )
        .filter(Labor.date.between(start_period_ly, period_to_date))
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
    period_table.set_index("name", inplace=True)

    # Grab top sales over last year before we add totals
    period_table.fillna(0, inplace=True)
    period_table['doly'] = period_table.sales - period_table.sales_ly
    period_table['poly'] = (
        (period_table.sales - period_table.sales_ly) / period_table.sales_ly * 100
    )
    period_top = period_table[['doly', 'poly']]
    period_top = period_top.nlargest(5, 'poly', keep='all')

    period_table.loc["TOTALS"] = period_table.sum(numeric_only=True)
    period_table['labor_pct'] = period_table.dollars / period_table.sales
    period_table['labor_pct_ly'] = period_table.dollars_ly / period_table.sales_ly
    period_totals = period_table.loc["TOTALS"]


    # Yearly Sales Table
    sales_yearly = (
        db.session.query(
            Sales.name,
            func.sum(Sales.sales).label("total_sales")
        )
        .filter(Sales.date.between(start_year, end_year))
        .group_by(Sales.name)
        .all()
    )

    sales_yearly_ly = (
        db.session.query(
            Sales.name,
            func.sum(Sales.sales).label("total_sales_ly")
        )
        .filter(Sales.date.between(start_year_ly, year_to_date))
        .group_by(Sales.name)
        .all()
    )

    df_sales_yearly = pd.DataFrame.from_records(
        sales_yearly, columns=["name", "sales"]
    )
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
        .filter(Labor.date.between(start_year, end_year))
        .group_by(Labor.name)
        .all()
    )

    labor_yearly_ly = (
        db.session.query(
            Labor.name,
            func.sum(Labor.hours).label("total_hours_ly"),
            func.sum(Labor.dollars).label("total_dollars_ly"),
        )
        .filter(Labor.date.between(start_year_ly, year_to_date))
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
    yearly_table.set_index("name", inplace=True)

    # Grab top sales over last year before we add totals
    yearly_table.fillna(0, inplace=True)
    yearly_table['doly'] = yearly_table.sales - yearly_table.sales_ly
    yearly_table['poly'] = (
        (yearly_table.sales - yearly_table.sales_ly) / yearly_table.sales_ly * 100
    )
    yearly_top = yearly_table[['doly', 'poly']]
    yearly_top = yearly_top.nlargest(5, 'poly', keep='all')

    yearly_table.loc["TOTALS"] = yearly_table.sum(numeric_only=True)
    yearly_table['labor_pct'] = yearly_table.dollars / yearly_table.sales
    yearly_table['labor_pct_ly'] = yearly_table.dollars_ly / yearly_table.sales_ly
    yearly_totals = yearly_table.loc["TOTALS"]


    return render_template(
        "home/index.html",
        title='CentraArchy',
        form1=form1,
        form3=form3,
        segment="index",
        current_user=current_user,
        roles=current_user.roles,
        fiscal_dates=fiscal_dates,
        values1=values1,
        values2=values2,
        values3=values3,
        values1_ly=values1_ly,
        values2_ly=values2_ly,
        values3_ly=values3_ly,
        budgets3=budgets3,
        daily_table=daily_table,
        daily_totals=daily_totals,
#        weekly_table=weekly_table,
        weekly_totals=weekly_totals,
#        period_table=period_table,
        period_totals=period_totals,
#        yearly_table=yearly_table,
        yearly_totals=yearly_totals,
        daily_top=daily_top,
        weekly_top=weekly_top,
        period_top=period_top,
#        yearly_top=yearly_top
    )


@blueprint.route("/<int:store_id>/store/", methods=["GET", "POST"])
@login_required
def store(store_id):

    form1 = DateForm()
    form3 = StoreForm()
    store = Restaurants.query.filter_by(id=store_id).first()

    print(store.name)
    start_day = end_day = start_week = end_week = start_period = end_period = start_year = end_year = ""
    period = year = week = 0
    fiscal_dates = get_period(datetime.strptime(session["targetdate"], "%Y-%m-%d"))
    for i in fiscal_dates:
        day_start = datetime.strptime(i.date, "%Y-%m-%d")
        day_end = day_start + timedelta(days=1)
        end_day = day_end.strftime("%Y-%m-%d")
        start_day = i.date
        start_week = i.week_start
        end_week = i.week_end
        start_period = i.period_start
        end_period = i.period_end
        start_year = i.year_start
        end_year = i.year_end
        period = i.period
        year = i.year
        week = i.week

    # Get matching day, week and period start and end dates
    start_day_ly = get_lastyear(start_day)
    start_week_ly = get_lastyear(start_week)
    end_week_ly = get_lastyear(end_week)
    week_to_date = get_lastyear(start_day)
    start_period_ly = get_lastyear(start_period)
    end_period_ly = get_lastyear(end_period)
    period_to_date = get_lastyear(start_day)
    start_year_ly = get_lastyear(start_year)
    end_year_ly = get_lastyear(end_year)
    year_to_date = get_lastyear(start_day)

    # Get Data
    form1 = DateForm()
    if form1.submit1.data and form1.validate():
        """
        When new date submitted, the data for that date will be replaced with new data from R365
        We check if there are infact sales for that day, if not, it resets to yesterday, if
        there are sales, then labor is polled
        """
        start_day = form1.selectdate.data.strftime("%Y-%m-%d")
        day_end = form1.selectdate.data + timedelta(days=1)
        end_day = day_end.strftime("%Y-%m-%d")

        # Check for no sales
        if not Sales.query.filter_by(date=start_day, name=store.name).first():
            flash(
                f"I cannot find sales for the day you selected.  Please select another date!",
                "warning",
            )
            TODAY = datetime.date(datetime.now())
            YSTDAY = TODAY - timedelta(days=1)
            session["targetdate"] = YSTDAY.strftime("%Y-%m-%d")
            return redirect(url_for("home_blueprint.store", store_id=store.id))

        session["targetdate"] = start_day
        return redirect(url_for("home_blueprint.store", store_id=store.id))


    if form3.submit3.data and form3.validate():

        session["targetdate"] = start_day
        store_id = form3.store.data.id

        return redirect(url_for("home_blueprint.store", store_id=store_id))

    # Week to Date Chart
    daily_chart = (
        db.session.query(func.sum(Sales.sales).label("total_sales"))
        .filter(Sales.date.between(start_week, end_week),
                Sales.name == store.name)
        .group_by(Sales.date)
        .order_by(Sales.date)
    )
    values1 = []
    for v in daily_chart:
        values1.append(v.total_sales)

    daily_chart_ly = (
        db.session.query(func.sum(Sales.sales).label("total_sales"))
        .filter(Sales.date.between(start_week_ly, end_week_ly),
                Sales.name == store.name)
        .group_by(Sales.date)
        .order_by(Sales.date)
    )
    values1_ly = []
    for v in daily_chart_ly:
        values1_ly.append(v.total_sales)

    # Period to Date Chart
    weekly_chart = (
        db.session.query(func.sum(Sales.sales).label("total_sales"))
        .select_from(Sales)
        .join(Calendar, Calendar.date == Sales.date)
        .group_by(Calendar.week)
        .order_by(Calendar.week)
        .filter(Sales.date.between(start_period, end_period),
                Sales.name == store.name)
    )
    values2 = []
    for v in weekly_chart:
        values2.append(v.total_sales)

    weekly_chart_ly = (
        db.session.query(func.sum(Sales.sales).label("total_sales"))
        .select_from(Sales)
        .join(Calendar, Calendar.date == Sales.date)
        .group_by(Calendar.week)
        .order_by(Calendar.week)
        .filter(Sales.date.between(start_period_ly, end_period_ly),
                Sales.name == store.name)
    )
    values2_ly = []
    for v in weekly_chart_ly:
        values2_ly.append(v.total_sales)

    # Year to Date Chart
    period_chart = (
        db.session.query(func.sum(Sales.sales).label("total_sales"))
        .select_from(Sales)
        .join(Calendar, Calendar.date == Sales.date)
        .group_by(Calendar.period)
        .order_by(Calendar.period)
        .filter(Sales.date.between(start_year, end_year),
                Sales.name == store.name)
    )
    values3 = []
    for v in period_chart:
        values3.append(v.total_sales)

    period_chart_ly = (
        db.session.query(func.sum(Sales.sales).label("total_sales"))
        .select_from(Sales)
        .join(Calendar, Calendar.date == Sales.date)
        .group_by(Calendar.period)
        .order_by(Calendar.period)
        .filter(Sales.date.between(start_year_ly, end_year_ly),
                Sales.name == store.name)
    )
    values3_ly = []
    for v in period_chart_ly:
        values3_ly.append(v.total_sales)


    budget_chart = (
        db.session.query(func.sum(Budgets.total_sales).label('total_sales'))
        .select_from(Budgets)
        .group_by(Budgets.period)
        .order_by(Budgets.period)
        .filter(Budgets.year == year,
                Budgets.name == store.name)
        )
    budgets3 = []
    for v in budget_chart:
        budgets3.append(v.total_sales)


    # Daily Sales Table
    food_sales = get_daily_sales(start_day, start_day, store.name, 'FOOD')
    beer_sales = get_daily_sales(start_day, start_day, store.name, 'BEER')
    liquor_sales = get_daily_sales(start_day, start_day, store.name, 'LIQUOR')
    wine_sales = get_daily_sales(start_day, start_day, store.name, 'WINE')
    gift_card_sales = get_daily_sales(start_day, start_day, store.name, 'GIFT CARDS')

    sales_table = food_sales.merge(beer_sales)
    sales_table = sales_table.merge(liquor_sales)
    sales_table = sales_table.merge(wine_sales)
    sales_table = sales_table.merge(gift_card_sales, how='outer')
    sales_table.rename(columns={'FOOD': 'food', 'BEER': 'beer', 'LIQUOR': 'liquor', 'WINE': 'wine', 'GIFT CARDS': 'gift_cards'}, inplace=True)
    sales_table.fillna(value=0, inplace=True)

    food_sales_ly = get_daily_sales(start_day_ly, start_day_ly, store.name, 'FOOD')
    beer_sales_ly = get_daily_sales(start_day_ly, start_day_ly, store.name, 'BEER')
    liquor_sales_ly = get_daily_sales(start_day_ly, start_day_ly, store.name, 'LIQUOR')
    wine_sales_ly = get_daily_sales(start_day_ly, start_day_ly, store.name, 'WINE')
    gift_card_sales_ly = get_daily_sales(start_day_ly, start_day_ly, store.name, 'GIFT CARDS')

    sales_table_ly = food_sales_ly.merge(beer_sales_ly)
    sales_table_ly = sales_table_ly.merge(liquor_sales_ly)
    sales_table_ly = sales_table_ly.merge(wine_sales_ly)
    sales_table_ly = sales_table_ly.merge(gift_card_sales_ly, how='outer')
    sales_table_ly.rename(columns={'FOOD': 'food_ly', 'BEER': 'beer_ly', 'LIQUOR': 'liquor_ly', 'WINE': 'wine_ly', 'GIFT CARDS': 'gift_cards_ly'}, inplace=True)
    sales_table_ly.fillna(value=0, inplace=True)

    col_sales_ly = sales_table_ly[['food_ly', 'beer_ly', 'liquor_ly', 'wine_ly', 'gift_cards_ly']]
    sales_table = sales_table.join(col_sales_ly)
    sales_table['alcohol_sales'] = (sales_table.beer + sales_table.liquor + sales_table.wine)
    sales_table['total_sales'] = (sales_table.food + sales_table.alcohol_sales)
    sales_table['alcohol_sales_ly'] = (sales_table.beer_ly + sales_table.liquor_ly + sales_table.wine_ly)
    sales_table['total_sales_ly'] = (sales_table.food_ly + sales_table.alcohol_sales_ly)
    sales_table['net_sales'] = (sales_table.total_sales + sales_table.gift_cards)
    sales_table['net_sales_ly'] = (sales_table.total_sales_ly + sales_table.gift_cards_ly)

    # Daily Labor
    bar_labor = get_daily_labor(start_day, start_day, store.name, 'Bar')
    host_labor = get_daily_labor(start_day, start_day, store.name, 'Host')
    restaurant_labor = get_daily_labor(start_day, start_day, store.name, 'Restaurant')
    kitchen_labor = get_daily_labor(start_day, start_day, store.name, 'Kitchen')

    bar_labor_ly = get_daily_labor(start_day_ly, start_day_ly, store.name, 'Bar')
    host_labor_ly = get_daily_labor(start_day_ly, start_day_ly, store.name, 'Host')
    restaurant_labor_ly = get_daily_labor(start_day_ly, start_day_ly, store.name, 'Restaurant')
    kitchen_labor_ly = get_daily_labor(start_day_ly, start_day_ly, store.name, 'Kitchen')

    labor_table = bar_labor.merge(host_labor)
    labor_table = labor_table.merge(restaurant_labor)
    labor_table = labor_table.merge(kitchen_labor)
    labor_table.fillna(value=0, inplace=True)

    labor_table_ly = bar_labor_ly.merge(host_labor_ly)
    labor_table_ly = labor_table_ly.merge(restaurant_labor_ly)
    labor_table_ly = labor_table_ly.merge(kitchen_labor_ly)
    labor_table_ly.rename(columns={'Bar': 'Bar_ly', 'Host': 'Host_ly', 'Restaurant': 'Restaurant_ly', 'Kitchen': 'Kitchen_ly'}, inplace=True)
    labor_table_ly.fillna(value=0, inplace=True)

    col_labor_ly = labor_table_ly[['Bar_ly', 'Host_ly', 'Restaurant_ly', 'Kitchen_ly']]
    labor_table = labor_table.join(col_labor_ly)
    labor_table['Total_Labor'] = (labor_table.Bar + labor_table.Host + labor_table.Restaurant + labor_table.Kitchen)
    labor_table['Total_Labor_ly'] = (labor_table_ly.Bar_ly + labor_table_ly.Host_ly + labor_table_ly.Restaurant_ly + labor_table_ly.Kitchen_ly)

    join_data = labor_table[['Bar', 'Host', 'Restaurant', 'Kitchen',  'Total_Labor', 'Bar_ly', 'Host_ly', 'Restaurant_ly', 'Kitchen_ly']]
    daily_table = sales_table.join(join_data)
    daily_table['Labor_pct'] = daily_table.Total_Labor / daily_table.total_sales
    daily_table['Bar_pct'] = daily_table.Bar / (daily_table.alcohol_sales)
    daily_table['Host_pct'] = daily_table.Host / (daily_table.food)
    daily_table['Restaurant_pct'] = daily_table.Restaurant / (daily_table.food)
    daily_table['Kitchen_pct'] = daily_table.Kitchen / (daily_table.food)
    daily_table['name'] = store.name

    # List of stores to add ID so i can pass to other templates
    store_list = Restaurants.query.all()
    store_list = pd.DataFrame([x.as_dict() for x in store_list])
    daily_table = daily_table.merge(store_list, how="left")
    if daily_table.empty:
        flash(
            f"I cannot find sales for {session['targetdate']}, i have to go back another day.",
            "warning",
        )
        currentDate = datetime.strptime(session["targetdate"], "%Y-%m-%d")
        newDate = currentDate - timedelta(days=1)
        session["targetdate"] = newDate.strftime("%Y-%m-%d")
        return redirect(url_for("home_blueprint.store", store_id=store.id))

    daily_table = daily_table.iloc[0]
    # TODO crashes with no sales


    # Weekly Sales Table
    food_sales = get_daily_sales(start_week, end_week, store.name, 'FOOD')
    beer_sales = get_daily_sales(start_week, end_week, store.name, 'BEER')
    liquor_sales = get_daily_sales(start_week, end_week, store.name, 'LIQUOR')
    wine_sales = get_daily_sales(start_week, end_week, store.name, 'WINE')
    gift_card_sales = get_daily_sales(start_week, end_week, store.name, 'GIFT CARDS')

    sales_table = food_sales.merge(beer_sales)
    sales_table = sales_table.merge(liquor_sales)
    sales_table = sales_table.merge(wine_sales)
    sales_table = sales_table.merge(gift_card_sales, how='outer')
    sales_table.rename(columns={'FOOD': 'food', 'BEER': 'beer', 'LIQUOR': 'liquor', 'WINE': 'wine', 'GIFT CARDS': 'gift_cards'}, inplace=True)
    sales_table.fillna(value=0, inplace=True)

    food_sales_ly = get_daily_sales(start_week_ly, week_to_date, store.name, 'FOOD')
    beer_sales_ly = get_daily_sales(start_week_ly, week_to_date, store.name, 'BEER')
    liquor_sales_ly = get_daily_sales(start_week_ly, week_to_date, store.name, 'LIQUOR')
    wine_sales_ly = get_daily_sales(start_week_ly, week_to_date, store.name, 'WINE')
    gift_card_sales_ly = get_daily_sales(start_week_ly, week_to_date, store.name, 'GIFT CARDS')

    sales_table_ly = food_sales_ly.merge(beer_sales_ly)
    sales_table_ly = sales_table_ly.merge(liquor_sales_ly)
    sales_table_ly = sales_table_ly.merge(wine_sales_ly)
    sales_table_ly = sales_table_ly.merge(gift_card_sales_ly, how='outer')
    sales_table_ly.rename(columns={'FOOD': 'food_ly', 'BEER': 'beer_ly', 'LIQUOR': 'liquor_ly', 'WINE': 'wine_ly', 'GIFT CARDS': 'gift_cards_ly'}, inplace=True)
    sales_table_ly.fillna(value=0, inplace=True)

    col_sales_ly = sales_table_ly[['food_ly', 'beer_ly', 'liquor_ly', 'wine_ly', 'gift_cards_ly']]
    sales_table = sales_table.join(col_sales_ly)
    sales_table['alcohol_sales'] = (sales_table.beer + sales_table.liquor + sales_table.wine)
    sales_table['total_sales'] = (sales_table.food + sales_table.alcohol_sales)
    sales_table['alcohol_sales_ly'] = (sales_table.beer_ly + sales_table.liquor_ly + sales_table.wine_ly)
    sales_table['total_sales_ly'] = (sales_table.food_ly + sales_table.alcohol_sales_ly)
    sales_table['net_sales'] = (sales_table.total_sales + sales_table.gift_cards)
    sales_table['net_sales_ly'] = (sales_table.total_sales_ly + sales_table.gift_cards_ly)

    # Weekly Labor
    bar_labor = get_daily_labor(start_week, end_week, store.name, 'Bar')
    host_labor = get_daily_labor(start_week, end_week, store.name, 'Host')
    restaurant_labor = get_daily_labor(start_week, end_week, store.name, 'Restaurant')
    kitchen_labor = get_daily_labor(start_week, end_week, store.name, 'Kitchen')

    bar_labor_ly = get_daily_labor(start_week_ly, week_to_date, store.name, 'Bar')
    host_labor_ly = get_daily_labor(start_week_ly, week_to_date, store.name, 'Host')
    restaurant_labor_ly = get_daily_labor(start_week_ly, week_to_date, store.name, 'Restaurant')
    kitchen_labor_ly = get_daily_labor(start_week_ly, week_to_date, store.name, 'Kitchen')

    labor_table = bar_labor.merge(host_labor)
    labor_table = labor_table.merge(restaurant_labor)
    labor_table = labor_table.merge(kitchen_labor)
    labor_table.fillna(value=0, inplace=True)

    labor_table_ly = bar_labor_ly.merge(host_labor_ly)
    labor_table_ly = labor_table_ly.merge(restaurant_labor_ly)
    labor_table_ly = labor_table_ly.merge(kitchen_labor_ly)
    labor_table_ly.rename(columns={'Bar': 'Bar_ly', 'Host': 'Host_ly', 'Restaurant': 'Restaurant_ly', 'Kitchen': 'Kitchen_ly'}, inplace=True)
    labor_table_ly.fillna(value=0, inplace=True)

    col_labor_ly = labor_table_ly[['Bar_ly', 'Host_ly', 'Restaurant_ly', 'Kitchen_ly']]
    labor_table = labor_table.join(col_labor_ly)
    labor_table['Total_Labor'] = (labor_table.Bar + labor_table.Host + labor_table.Restaurant + labor_table.Kitchen)
    labor_table['Total_Labor_ly'] = (labor_table_ly.Bar_ly + labor_table_ly.Host_ly + labor_table_ly.Restaurant_ly + labor_table_ly.Kitchen_ly)

    join_data = labor_table[['Bar', 'Host', 'Restaurant', 'Kitchen',  'Total_Labor', 'Bar_ly', 'Host_ly', 'Restaurant_ly', 'Kitchen_ly']]
    weekly_table = sales_table.join(join_data)
    weekly_table['Labor_pct'] = weekly_table.Total_Labor / weekly_table.total_sales
    weekly_table['Bar_pct'] = weekly_table.Bar / (weekly_table.alcohol_sales)
    weekly_table['Host_pct'] = weekly_table.Host / (weekly_table.food)
    weekly_table['Restaurant_pct'] = weekly_table.Restaurant / (weekly_table.food)
    weekly_table['Kitchen_pct'] = weekly_table.Kitchen / (weekly_table.food)
    weekly_table['name'] = store.name

    weekly_table = weekly_table.merge(store_list, how="left")
    weekly_table.loc["TOTALS"] = weekly_table.sum(numeric_only=True)
    weekly_totals = weekly_table.loc["TOTALS"]


    # Period Sales Table
    dates = Calendar.query.filter(Calendar.date.between(start_period, end_period)).all()
    dates = pd.DataFrame([x.as_dict() for x in dates])
    dates_ly = Calendar.query.filter(Calendar.date.between(start_period_ly, end_period_ly)).all()
    dates_ly = pd.DataFrame([x.as_dict() for x in dates_ly])

    food_sales = get_daily_sales(start_period, end_period, store.name, 'FOOD')
    beer_sales = get_daily_sales(start_period, end_period, store.name, 'BEER')
    liquor_sales = get_daily_sales(start_period, end_period, store.name, 'LIQUOR')
    wine_sales = get_daily_sales(start_period, end_period, store.name, 'WINE')
    gift_card_sales = get_daily_sales(start_period, end_period, store.name, 'GIFT CARDS')

    sales_table = food_sales.merge(beer_sales)
    sales_table = sales_table.merge(liquor_sales)
    sales_table = sales_table.merge(wine_sales)
    sales_table = sales_table.merge(gift_card_sales, how='outer')
    sales_table.rename(columns={'FOOD': 'food', 'BEER': 'beer', 'LIQUOR': 'liquor', 'WINE': 'wine', 'GIFT CARDS': 'gift_cards'}, inplace=True)
    sales_table.fillna(value=0, inplace=True)

#    sales_table = sales_table.merge(dates, how="outer", sort=True)

    food_sales_ly = get_daily_sales(start_period_ly, period_to_date, store.name, 'FOOD')
    beer_sales_ly = get_daily_sales(start_period_ly, period_to_date, store.name, 'BEER')
    liquor_sales_ly = get_daily_sales(start_period_ly, period_to_date, store.name, 'LIQUOR')
    wine_sales_ly = get_daily_sales(start_period_ly, period_to_date, store.name, 'WINE')
    gift_card_sales_ly = get_daily_sales(start_period_ly, period_to_date, store.name, 'GIFT CARDS')

    sales_table_ly = food_sales_ly.merge(beer_sales_ly)
    sales_table_ly = sales_table_ly.merge(liquor_sales_ly)
    sales_table_ly = sales_table_ly.merge(wine_sales_ly)
    sales_table_ly = sales_table_ly.merge(gift_card_sales_ly, how='outer')
    sales_table_ly.rename(columns={'FOOD': 'food_ly', 'BEER': 'beer_ly', 'LIQUOR': 'liquor_ly', 'WINE': 'wine_ly', 'GIFT CARDS': 'gift_cards_ly'}, inplace=True)
    sales_table_ly.fillna(value=0, inplace=True)

#    sales_table_ly = sales_table_ly.merge(dates_ly, how="outer")

    col_sales_ly = sales_table_ly[['food_ly', 'beer_ly', 'liquor_ly', 'wine_ly', 'gift_cards_ly']]
    sales_table = sales_table.join(col_sales_ly)
    sales_table['alcohol_sales'] = (sales_table.beer + sales_table.liquor + sales_table.wine)
    sales_table['total_sales'] = (sales_table.food + sales_table.alcohol_sales)
    sales_table['alcohol_sales_ly'] = (sales_table.beer_ly + sales_table.liquor_ly + sales_table.wine_ly)
    sales_table['total_sales_ly'] = (sales_table.food_ly + sales_table.alcohol_sales_ly)
    sales_table['net_sales'] = (sales_table.total_sales + sales_table.gift_cards)
    sales_table['net_sales_ly'] = (sales_table.total_sales_ly + sales_table.gift_cards_ly)

    # Period Labor
    bar_labor = get_daily_labor(start_period, end_period, store.name, 'Bar')
    host_labor = get_daily_labor(start_period, end_period, store.name, 'Host')
    restaurant_labor = get_daily_labor(start_period, end_period, store.name, 'Restaurant')
    kitchen_labor = get_daily_labor(start_period, end_period, store.name, 'Kitchen')

    bar_labor_ly = get_daily_labor(start_period_ly, period_to_date, store.name, 'Bar')
    host_labor_ly = get_daily_labor(start_period_ly, period_to_date, store.name, 'Host')
    restaurant_labor_ly = get_daily_labor(start_period_ly, period_to_date, store.name, 'Restaurant')
    kitchen_labor_ly = get_daily_labor(start_period_ly, period_to_date, store.name, 'Kitchen')

    labor_table = bar_labor.merge(host_labor)
    labor_table = labor_table.merge(restaurant_labor)
    labor_table = labor_table.merge(kitchen_labor)
    labor_table.fillna(value=0, inplace=True)

    labor_table_ly = bar_labor_ly.merge(host_labor_ly)
    labor_table_ly = labor_table_ly.merge(restaurant_labor_ly)
    labor_table_ly = labor_table_ly.merge(kitchen_labor_ly)
    labor_table_ly.rename(columns={'Bar': 'Bar_ly', 'Host': 'Host_ly', 'Restaurant': 'Restaurant_ly', 'Kitchen': 'Kitchen_ly'}, inplace=True)
    labor_table_ly.fillna(value=0, inplace=True)

    col_labor_ly = labor_table_ly[['Bar_ly', 'Host_ly', 'Restaurant_ly', 'Kitchen_ly']]
    labor_table = labor_table.join(col_labor_ly)
    labor_table['Total_Labor'] = (labor_table.Bar + labor_table.Host + labor_table.Restaurant + labor_table.Kitchen)
    labor_table['Total_Labor_ly'] = (labor_table_ly.Bar_ly + labor_table_ly.Host_ly + labor_table_ly.Restaurant_ly + labor_table_ly.Kitchen_ly)

    join_data = labor_table[['Bar', 'Host', 'Restaurant', 'Kitchen',  'Total_Labor', 'Bar_ly', 'Host_ly', 'Restaurant_ly', 'Kitchen_ly']]
    period_table = sales_table.join(join_data)
    period_table['Labor_pct'] = period_table.Total_Labor / period_table.total_sales
    period_table['Bar_pct'] = period_table.Bar / (period_table.alcohol_sales)
    period_table['Host_pct'] = period_table.Host / (period_table.food)
    period_table['Restaurant_pct'] = period_table.Restaurant / (period_table.food)
    period_table['Kitchen_pct'] = period_table.Kitchen / (period_table.food)
    period_table['name'] = store.name

#    period_table_w1 = period_table.loc[period_table['week'] == 1 ]
#    period_table_w1.fillna(value=0, inplace=True)
#    period_table_w2 = period_table.loc[period_table['week'] == 2 ]
#    period_table_w2.fillna(value=0, inplace=True)
#    period_table_w3 = period_table.loc[period_table['week'] == 3 ]
#    period_table_w3.fillna(value=0, inplace=True)
#    period_table_w4 = period_table.loc[period_table['week'] == 4 ]
#    period_table_w4.fillna(value=0, inplace=True)
#    period_table_w1.loc["TOTALS"] = period_table_w1.sum(numeric_only=True)
#    period_table_w1.at['TOTALS', 'date'] = '-'
#    period_table_w2.loc["TOTALS"] = period_table_w2.sum(numeric_only=True)
#    period_table_w2.at['TOTALS', 'date'] = '-'
#    period_table_w3.loc["TOTALS"] = period_table_w3.sum(numeric_only=True)
#    period_table_w3.at['TOTALS', 'date'] = '-'
#    period_table_w4.loc["TOTALS"] = period_table_w4.sum(numeric_only=True)
#    period_table_w4.at['TOTALS', 'date'] = '-'

    period_table = period_table.merge(store_list, how="left")
    period_table.loc["TOTALS"] = period_table.sum(numeric_only=True)
    period_totals = period_table.loc["TOTALS"]


    # Yearly Sales Table
    food_sales = get_daily_sales(start_year, end_year, store.name, 'FOOD')
    beer_sales = get_daily_sales(start_year, end_year, store.name, 'BEER')
    liquor_sales = get_daily_sales(start_year, end_year, store.name, 'LIQUOR')
    wine_sales = get_daily_sales(start_year, end_year, store.name, 'WINE')
    gift_card_sales = get_daily_sales(start_year, end_year, store.name, 'GIFT CARDS')

    sales_table = food_sales.merge(beer_sales)
    sales_table = sales_table.merge(liquor_sales)
    sales_table = sales_table.merge(wine_sales)
    sales_table = sales_table.merge(gift_card_sales, how='outer')
    sales_table.rename(columns={'FOOD': 'food', 'BEER': 'beer', 'LIQUOR': 'liquor', 'WINE': 'wine', 'GIFT CARDS': 'gift_cards'}, inplace=True)
    sales_table.fillna(value=0, inplace=True)

    food_sales_ly = get_daily_sales(start_year_ly, year_to_date, store.name, 'FOOD')
    beer_sales_ly = get_daily_sales(start_year_ly, year_to_date, store.name, 'BEER')
    liquor_sales_ly = get_daily_sales(start_year_ly, year_to_date, store.name, 'LIQUOR')
    wine_sales_ly = get_daily_sales(start_year_ly, year_to_date, store.name, 'WINE')
    gift_card_sales_ly = get_daily_sales(start_year_ly, year_to_date, store.name, 'GIFT CARDS')

    sales_table_ly = food_sales_ly.merge(beer_sales_ly)
    sales_table_ly = sales_table_ly.merge(liquor_sales_ly)
    sales_table_ly = sales_table_ly.merge(wine_sales_ly)
    sales_table_ly = sales_table_ly.merge(gift_card_sales_ly, how='outer')
    sales_table_ly.rename(columns={'FOOD': 'food_ly', 'BEER': 'beer_ly', 'LIQUOR': 'liquor_ly', 'WINE': 'wine_ly', 'GIFT CARDS': 'gift_cards_ly'}, inplace=True)
    sales_table_ly.fillna(value=0, inplace=True)

    col_sales_ly = sales_table_ly[['food_ly', 'beer_ly', 'liquor_ly', 'wine_ly', 'gift_cards_ly']]
    sales_table = sales_table.join(col_sales_ly)
    sales_table['alcohol_sales'] = (sales_table.beer + sales_table.liquor + sales_table.wine)
    sales_table['total_sales'] = (sales_table.food + sales_table.alcohol_sales)
    sales_table['alcohol_sales_ly'] = (sales_table.beer_ly + sales_table.liquor_ly + sales_table.wine_ly)
    sales_table['total_sales_ly'] = (sales_table.food_ly + sales_table.alcohol_sales_ly)
    sales_table['net_sales'] = (sales_table.total_sales + sales_table.gift_cards)
    sales_table['net_sales_ly'] = (sales_table.total_sales_ly + sales_table.gift_cards_ly)

    # get labor for day
    bar_labor = get_daily_labor(start_year, end_year, store.name, 'Bar')
    host_labor = get_daily_labor(start_year, end_year, store.name, 'Host')
    restaurant_labor = get_daily_labor(start_year, end_year, store.name, 'Restaurant')
    kitchen_labor = get_daily_labor(start_year, end_year, store.name, 'Kitchen')

    bar_labor_ly = get_daily_labor(start_year_ly, year_to_date, store.name, 'Bar')
    host_labor_ly = get_daily_labor(start_year_ly, year_to_date, store.name, 'Host')
    restaurant_labor_ly = get_daily_labor(start_year_ly, year_to_date, store.name, 'Restaurant')
    kitchen_labor_ly = get_daily_labor(start_year_ly, year_to_date, store.name, 'Kitchen')

    labor_table = bar_labor.merge(host_labor)
    labor_table = labor_table.merge(restaurant_labor)
    labor_table = labor_table.merge(kitchen_labor)
    labor_table.fillna(value=0, inplace=True)

    labor_table_ly = bar_labor_ly.merge(host_labor_ly)
    labor_table_ly = labor_table_ly.merge(restaurant_labor_ly)
    labor_table_ly = labor_table_ly.merge(kitchen_labor_ly)
    labor_table_ly.rename(columns={'Bar': 'Bar_ly', 'Host': 'Host_ly', 'Restaurant': 'Restaurant_ly', 'Kitchen': 'Kitchen_ly'}, inplace=True)
    labor_table_ly.fillna(value=0, inplace=True)

    col_labor_ly = labor_table_ly[['Bar_ly', 'Host_ly', 'Restaurant_ly', 'Kitchen_ly']]
    labor_table = labor_table.join(col_labor_ly)
    labor_table['Total_Labor'] = (labor_table.Bar + labor_table.Host + labor_table.Restaurant + labor_table.Kitchen)
    labor_table['Total_Labor_ly'] = (labor_table_ly.Bar_ly + labor_table_ly.Host_ly + labor_table_ly.Restaurant_ly + labor_table_ly.Kitchen_ly)

    join_data = labor_table[['Bar', 'Host', 'Restaurant', 'Kitchen',  'Total_Labor', 'Bar_ly', 'Host_ly', 'Restaurant_ly', 'Kitchen_ly']]
    yearly_table = sales_table.join(join_data)
    yearly_table['Labor_pct'] = yearly_table.Total_Labor / yearly_table.total_sales
    yearly_table['Bar_pct'] = yearly_table.Bar / (yearly_table.alcohol_sales)
    yearly_table['Host_pct'] = yearly_table.Host / (yearly_table.food)
    yearly_table['Restaurant_pct'] = yearly_table.Restaurant / (yearly_table.food)
    yearly_table['Kitchen_pct'] = yearly_table.Kitchen / (yearly_table.food)
    yearly_table['name'] = store.name

    yearly_table = yearly_table.merge(store_list, how="left")
    yearly_table.loc["TOTALS"] = yearly_table.sum(numeric_only=True)
    yearly_totals = yearly_table.loc["TOTALS"]


    lobster_list = (db.session.query(Transactions.item)
            .filter(Transactions.item.regexp_match('SEAFOOD Lobster Live*'))
            .group_by(Transactions.item)
        ).all()
    lobster_items = []
    for i in lobster_list:
        lobster_cost = (
            db.session.query(Transactions.item,
                             Transactions.date,
                             Transactions.debit,
                             Transactions.quantity,
                             )
                .filter(Transactions.item == i.item,
                        Transactions.store_id == store_id,
                        Transactions.type == 'AP Invoice')
                .order_by(Transactions.date.desc())
                ).first()
        if lobster_cost:
            row_dict = dict(lobster_cost)
            ext = re.findall(r'\d*\.?\d', i.item)
            if not ext:
                ext = re.findall(r'\d{1,2}', i.item)
            size = float(ext[0])
            row_dict['size'] = size
            lobster_items.append(row_dict)


    stone_list = (db.session.query(Transactions.item)
            .filter(Transactions.item.regexp_match('^(SEAFOOD Crab Stone Claw)'))
            .group_by(Transactions.item)
        ).all()
    stone_items = []
    for i in stone_list:
        stone_cost = (
            db.session.query(Transactions.item,
                             Transactions.date,
                             Transactions.debit,
                             Transactions.quantity,
                             )
                .filter(Transactions.item == i.item,
                        Transactions.store_id == store_id,
                        Transactions.type == 'AP Invoice')
                .order_by(Transactions.date.desc())
                ).first()
        if stone_cost:
            row_dict = dict(stone_cost)
            ext = re.findall(r'\d{1,2}', i.item)
            size = int(ext[0])
            row_dict['size'] = size
            stone_items.append(row_dict)

    sea_bass = (
        db.session.query(Transactions.item,
                         Transactions.date,
                         Transactions.UofM,
                         func.sum(Transactions.amount).label('cost'),
                         func.sum(Transactions.quantity).label('count'),
                         )
            .filter(Transactions.item.regexp_match('SEAFOOD Sea Bass Chilean'),
                    Transactions.store_id == store_id,
                    Transactions.type == 'AP Invoice')
            .group_by(Transactions.item, Transactions.date, Transactions.UofM)
            .order_by(Transactions.date.desc())
        .limit(5).all()
    )


    cogs_wk = (
        db.session.query(Transactions.category2,
                         func.sum(Transactions.credit).label('credit'),
                         func.sum(Transactions.debit).label('debit')
                         )
            .filter(Transactions.name == store.name,
                    Transactions.date.between(start_week, end_week),
                    and_(or_(Transactions.type == 'AP Invoice',
                             Transactions.type == 'AP Credit Memo',
                             Transactions.type == 'Item Transfer'),
                         or_(Transactions.category1 == 'Food',
                             Transactions.category1 == 'LBW')
                         )
                    )
            .group_by(Transactions.category1, Transactions.category2).all()
    )
    cost_table = pd.DataFrame(cogs_wk, columns=['category', 'credit', 'debit'])
    for i in ['Beef', 'Dairy', 'Food Other', 'Pork', 'Poultry', 'Produce', 'Seafood', 'Beer', 'Liquor', 'Wine']:
        if i not in cost_table.values:
            cost_table.loc[len(cost_table.index)] = [i, 0, 0]

    cost_table['totals'] = abs(cost_table.credit - cost_table.debit)
    cost_table.drop(columns={'credit', 'debit'}, inplace=True)
    weekly_cogs = pd.Series(cost_table['totals'].values, index=cost_table['category'])

    cogs_pd = (
        db.session.query(Transactions.category2,
                         func.sum(Transactions.credit).label('credit'),
                         func.sum(Transactions.debit).label('debit')
                         )
            .filter(Transactions.name == store.name,
                    Transactions.date.between(start_period, end_period),
                    and_(or_(Transactions.type == 'AP Invoice',
                             Transactions.type == 'AP Credit Memo',
                             Transactions.type == 'Item Transfer'),
                         or_(Transactions.category1 == 'Food',
                             Transactions.category1 == 'LBW')
                         )
                    )
            .group_by(Transactions.category1, Transactions.category2).all()
    )
    cost_table = pd.DataFrame(cogs_pd, columns=['category', 'credit', 'debit'])
    for i in ['Beef', 'Dairy', 'Food Other', 'Pork', 'Poultry', 'Produce', 'Seafood', 'Beer', 'Liquor', 'Wine']:
        if i not in cost_table.values:
            cost_table.loc[len(cost_table.index)] = [i, 0, 0]

    cost_table['totals'] = abs(cost_table.credit - cost_table.debit)
    cost_table.drop(columns={'credit', 'debit'}, inplace=True)
    period_cogs = pd.Series(cost_table['totals'].values, index=cost_table['category'])


    if store_id in [4, 9, 11, 17, 16]:
        concept = 'steakhouse'
    else:
        concept = 'casual'


    return render_template(
        "home/store.html",
        title=store.name,
        segment='store',
        concept=concept,
        form1=form1,
        form3=form3,
        current_user=current_user,
        roles=current_user.roles,
        fiscal_dates=fiscal_dates,
        values1=values1,
        values2=values2,
        values3=values3,
        values1_ly=values1_ly,
        values2_ly=values2_ly,
        values3_ly=values3_ly,
        budgets3=budgets3,
        daily_table=daily_table,
#        weekly_table=weekly_table,
        weekly_totals=weekly_totals,
#        period_table=period_table,
        period_totals=period_totals,
#        period_table_w1=period_table_w1,
#        period_table_w2=period_table_w2,
#        period_table_w3=period_table_w3,
#        period_table_w4=period_table_w4,
#        yearly_table=yearly_table,
        yearly_totals=yearly_totals,
        weekly_cogs=weekly_cogs,
        period_cogs=period_cogs,
        lobster_items=lobster_items,
        stone_items=stone_items,
        sea_bass=sea_bass,
    )


@blueprint.route("/marketing/", methods=["GET", "POST"])
@login_required
def marketing(targetdate=None):

    start_day = end_day = start_week = end_week = start_period = end_period = start_year = end_year = ""
    fiscal_dates = get_period(datetime.strptime(session["targetdate"], "%Y-%m-%d"))
    for i in fiscal_dates:
        day_start = datetime.strptime(i.date, "%Y-%m-%d")
        day_end = day_start + timedelta(days=1)
        end_day = day_end.strftime("%Y-%m-%d")
        start_day = i.date
        start_week = i.week_start
        end_week = i.week_end
        start_period = i.period_start
        end_period = i.period_end
        start_year = i.year_start
        end_year = i.year_end

    # Get matching day, week and period start and end dates
    start_day_ly = get_lastyear(start_day)
    #    end_day_ly = get_lastyear(end_day)
    start_week_ly = get_lastyear(start_week)
    end_week_ly = get_lastyear(end_week)
    week_to_date = get_lastyear(start_day)
    start_period_ly = get_lastyear(start_period)
    end_period_ly = get_lastyear(end_period)
    period_to_date = get_lastyear(start_day)
    start_year_ly = get_lastyear(start_year)
    end_year_ly = get_lastyear(end_year)
    year_to_date = get_lastyear(start_day)

    form1 = DateForm()
    form3 = StoreForm()
    if form1.submit1.data and form1.validate():
        """
        """
        start_day = form1.selectdate.data.strftime("%Y-%m-%d")
        session["targetdate"] = start_day
        return redirect(url_for("home_blueprint.marketing"))


    if form3.submit3.data and form3.validate():

        session["targetdate"] = start_day
        store_id = form3.store.data.id

        return redirect(url_for("home_blueprint.store", store_id=store_id))

    # Gift Card Sales
    gift_cards = (
        db.session.query(Menuitems.name,
                         func.sum(Menuitems.amount).label("sales"),
                         func.sum(Menuitems.quantity).label("count"),
                         )
            .filter(Menuitems.date.between(start_period, end_period),
                    Menuitems.menuitem.regexp_match('(?i)GIFT CARD*'))
            .group_by(Menuitems.name)
        ).all()
    gift_card_sales = pd.DataFrame.from_records(
        gift_cards, columns=["store", "amount", "quantity"]
    )
    gift_card_sales.sort_values(by=['amount'], ascending=False, inplace=True)
    gift_card_sales.loc["TOTALS"] = gift_card_sales.sum(numeric_only=True)


    porterhouse = (
        db.session.query(Menuitems.name,
                         Menuitems.menuitem,
                         func.sum(Menuitems.quantity).label("count"),
                         func.sum(Menuitems.amount).label("sales"),
                         )
            .filter(Menuitems.date.between(start_period, end_period),
                    Menuitems.menuitem.regexp_match('PORTERHOUSE (FEAST*|DINNER*)')
                    )
            .group_by(Menuitems.menuitem, Menuitems.name)
        ).all()
    porterhouse_feast = pd.DataFrame.from_records(
        porterhouse, columns=["store", "menuitem", "count", "sales"]
    )
    porterhouse_feast['price'] = porterhouse_feast['sales'] / porterhouse_feast['count'].astype(float)
    porterhouse_feast.sort_values(by=['sales'], ascending=False, inplace=True)


    return render_template(
        "home/marketing.html",
        title='Marketing',
        segment='marketing',
        fiscal_dates=fiscal_dates,
        form1=form1,
        form3=form3,
        current_user=current_user,
        roles=current_user.roles,
        gift_card_sales=gift_card_sales,
        porterhouse_feast=porterhouse_feast,
    )


@blueprint.route("/purchasing/", methods=["GET", "POST"])
@login_required
def purchasing(targetdate=None):

    start_day = end_day = start_week = end_week = start_period = end_period = start_year = end_year = ""
    fiscal_dates = get_period(datetime.strptime(session["targetdate"], "%Y-%m-%d"))
    for i in fiscal_dates:
        day_start = datetime.strptime(i.date, "%Y-%m-%d")
        day_end = day_start + timedelta(days=1)
        end_day = day_end.strftime("%Y-%m-%d")
        start_day = i.date
        start_week = i.week_start
        end_week = i.week_end
        start_period = i.period_start
        end_period = i.period_end
        start_year = i.year_start
        end_year = i.year_end
        thirty = day_start - timedelta(days=30)
        last_thirty = thirty.strftime("%Y-%m-%d")

    # Get matching day, week and period start and end dates
    start_day_ly = get_lastyear(start_day)
    #    end_day_ly = get_lastyear(end_day)
    start_week_ly = get_lastyear(start_week)
    end_week_ly = get_lastyear(end_week)
    week_to_date = get_lastyear(start_day)
    start_period_ly = get_lastyear(start_period)
    end_period_ly = get_lastyear(end_period)
    period_to_date = get_lastyear(start_day)
    start_year_ly = get_lastyear(start_year)
    end_year_ly = get_lastyear(end_year)
    year_to_date = get_lastyear(start_day)

    # Get list of Restaurants
    store_list = []
    data = db.session.query(Restaurants.name).all()
    for i in data:
        store_list.append(i.name)

    form1 = DateForm()
    form3 = StoreForm()
    if form1.submit1.data and form1.validate():
        """
        """
        start_day = form1.selectdate.data.strftime("%Y-%m-%d")
        session["targetdate"] = start_day
        return redirect(url_for("home_blueprint.purchasing"))


    if form3.submit3.data and form3.validate():

        session["targetdate"] = start_day
        store_id = form3.store.data.id

        return redirect(url_for("home_blueprint.store", store_id=store_id))


    lobster_list = (db.session.query(Transactions.item)
            .filter(Transactions.item.regexp_match('SEAFOOD Lobster Live*'))
            .group_by(Transactions.item)
        ).all()

    lobster_df = pd.DataFrame(columns=['item'])
    for s in store_list:
        lobster_items = []
        for i in lobster_list:
            lobster_cost = (
                db.session.query(Transactions.item,
                                 Transactions.date,
                                 Transactions.UofM,
                                 Transactions.debit,
                                 Transactions.quantity,
                                 )
                    .filter(Transactions.item == i.item,
                            Transactions.date >= last_thirty,
                            Transactions.name == s,
                            Transactions.type == 'AP Invoice')
                    .order_by(Transactions.date.desc())
                    ).first()
            if lobster_cost:
                # extract the number from name to calculate cost per serving
                row_dict = dict(lobster_cost)
                ext = re.findall(r'\d*\.?\d', i.item)
                if not ext:
                    ext = re.findall(r'\d{1,2}', i.item)
                size = float(ext[0])
                row_dict['size'] = size
                lobster_items.append(row_dict)
        df = pd.DataFrame(lobster_items)
        if not df.empty:
            with open("/usr/local/share/uofm.json") as file:
                uofm = json.load(file)
            df_uofm = pd.DataFrame(list(uofm.items()), columns=['case', 'factor'])
            df = df.merge(df_uofm, left_on='UofM', right_on='case')
            df['cost/lb'] = df['debit']/df['quantity']/df['factor']
            df.rename(columns={'cost/lb': s}, inplace=True)
            df.drop(columns={'date', 'debit', 'quantity', 'size', 'UofM', 'case', 'factor'}, inplace=True)
            lobster_df = lobster_df.merge(df, how='outer')

    lobster_df.sort_values(by=['item'], inplace=True)
    lobster_df.fillna(0, inplace=True)

    stone_list = (db.session.query(Transactions.item)
            .filter(Transactions.item.regexp_match('^(SEAFOOD Crab Stone Claw)'))
            .group_by(Transactions.item)
        ).all()

    stone_df = pd.DataFrame(columns=['item'])
    for s in store_list:
        stone_items = []
        for i in stone_list:
            stone_cost = (
                db.session.query(Transactions.item,
                                 Transactions.date,
                                 Transactions.UofM,
                                 Transactions.debit,
                                 Transactions.quantity,
                                 )
                    .filter(Transactions.item == i.item,
                            Transactions.date >= last_thirty,
                            Transactions.name == s,
                            Transactions.type == 'AP Invoice')
                    .order_by(Transactions.date.desc())
                    ).first()
            if stone_cost:
                # extract the number from name to calculate cost per serving
                row_dict = dict(stone_cost)
                ext = re.findall(r'\d{1,2}', i.item)
                size = int(ext[0])
                row_dict['size'] = size
                stone_items.append(row_dict)
        df = pd.DataFrame(stone_items)
        if not df.empty:
            with open("/usr/local/share/uofm.json") as file:
                uofm = json.load(file)
            df_uofm = pd.DataFrame(list(uofm.items()), columns=['case', 'factor'])
            df = df.merge(df_uofm, left_on='UofM', right_on='case')
            df['cost/lb'] = df['debit']/df['quantity']/df['factor']
            df.rename(columns={'cost/lb': s}, inplace=True)
            df.drop(columns={'date', 'debit', 'quantity', 'size', 'UofM', 'case', 'factor'}, inplace=True)
            stone_df = stone_df.merge(df, how='outer')

    stone_df.sort_values(by=['item'], inplace=True)
    stone_df.fillna(0, inplace=True)

    steak_list = (db.session.query(Transactions.item)
            .filter(Transactions.item.regexp_match('^(BEEF Steak).*(Prime)$'))
            .group_by(Transactions.item)
        ).all()

    steak_df = pd.DataFrame(columns=['item'])
    for s in store_list:
        steak_items = []
        for i in steak_list:
            steak_cost = (
                db.session.query(Transactions.item,
                                 Transactions.date,
                                 Transactions.UofM,
                                 Transactions.debit,
                                 Transactions.quantity,
                                 )
                    .filter(Transactions.item == i.item,
                            Transactions.date >= last_thirty,
                            Transactions.name == s,
                            Transactions.type == 'AP Invoice')
                    .order_by(Transactions.date.desc())
                    ).first()
            if steak_cost:
                # extract the number from name to calculate cost per serving
                row_dict = dict(steak_cost)
                ext = re.findall(r'\d{1,2}', i.item)
                if ext:
                    size = int(ext[0])
                else:
                    size = 16
                row_dict['size'] = size
                steak_items.append(row_dict)
        df = pd.DataFrame(steak_items)
        if not df.empty:
            with open("/usr/local/share/uofm.json") as file:
                uofm = json.load(file)
            df_uofm = pd.DataFrame(list(uofm.items()), columns=['case', 'factor'])
            df = df.merge(df_uofm, left_on='UofM', right_on='case')
            df['cost/lb'] = df['debit']/df['quantity'] / df['factor']
            df.rename(columns={'cost/lb': s}, inplace=True)
            df.drop(columns={'date', 'debit', 'quantity', 'size', 'UofM', 'case', 'factor'}, inplace=True)
            steak_df = steak_df.merge(df, how='outer')

    steak_df.sort_values(by=['item'], inplace=True)
    steak_df.fillna(0, inplace=True)

    # TODO add uofm json comparison to the sea bass and shrimp
    sea_bass = (
        db.session.query(Transactions.item,
                         Transactions.name,
                         Transactions.UofM,
                         func.sum(Transactions.amount).label('cost'),
                         func.sum(Transactions.quantity).label('count'),
                         )
            .filter(Transactions.item.regexp_match('SEAFOOD Sea Bass Chilean'),
                    Transactions.date >= last_thirty,
                    Transactions.type == 'AP Invoice')
            .group_by(Transactions.item, Transactions.name, Transactions.UofM)
        .all()
    )

    shrimp10 = (db.session.query(Transactions.name)
            .filter(Transactions.item.regexp_match('SEAFOOD Shrimp U/10 White Headless'))
            .group_by(Transactions.name)
        ).all()
    shrimp_list = []
    for i in shrimp10:
        shrimp_cost = (
            db.session.query(Transactions.name,
                             Transactions.UofM,
                             Transactions.amount,
                             Transactions.quantity,
                             )
                .filter(Transactions.name == i.name,
                        Transactions.item.regexp_match('SEAFOOD Shrimp U/10 White Headless'),
                        Transactions.date >= last_thirty,
                        Transactions.type == 'AP Invoice')
                .order_by(Transactions.date.desc())
                ).first()
        if shrimp_cost:
            shrimp_list.append(shrimp_cost)
    shrimp_items = pd.DataFrame.from_records(shrimp_list, columns=["store", "UofM", "amount", "quantity"])


    return render_template(
        "home/purchasing.html",
        title='Purchasing',
        segment='purchasing',
        fiscal_dates=fiscal_dates,
        form1=form1,
        form3=form3,
        current_user=current_user,
        lobster_df=lobster_df,
        stone_df=stone_df,
        steak_df=steak_df,
        sea_bass=sea_bass,
        shrimp_items=shrimp_items,
    )


@blueprint.route("/support/", methods=["GET", "POST"])
@login_required
@roles_accepted('admin')
def support(targetdate=None):

    start_day = end_day = start_week = end_week = start_period = end_period = start_year = end_year = ""
    fiscal_dates = get_period(datetime.strptime(session["targetdate"], "%Y-%m-%d"))
    for i in fiscal_dates:
        day_start = datetime.strptime(i.date, "%Y-%m-%d")
        day_end = day_start + timedelta(days=1)
        end_day = day_end.strftime("%Y-%m-%d")
        start_day = i.date
        start_week = i.week_start
        end_week = i.week_end
        start_period = i.period_start
        end_period = i.period_end
        start_year = i.year_start
        end_year = i.year_end

    # Get matching day, week and period start and end dates
    start_day_ly = get_lastyear(start_day)
    #    end_day_ly = get_lastyear(end_day)
    start_week_ly = get_lastyear(start_week)
    end_week_ly = get_lastyear(end_week)
    week_to_date = get_lastyear(start_day)
    start_period_ly = get_lastyear(start_period)
    end_period_ly = get_lastyear(end_period)
    period_to_date = get_lastyear(start_day)
    start_year_ly = get_lastyear(start_year)
    end_year_ly = get_lastyear(end_year)
    year_to_date = get_lastyear(start_day)


    form1 = DateForm()
    form2 = UpdateForm()
    form3 = StoreForm()
    if form1.submit1.data and form1.validate():
        """
        """
        start_day = form1.selectdate.data.strftime("%Y-%m-%d")
        session["targetdate"] = start_day
        return redirect(url_for("home_blueprint.support"))


    if form2.submit2.data and form2.validate():
        """
        """
        start_day = form2.selectdate.data.strftime("%Y-%m-%d")
        day_end = form2.selectdate.data + timedelta(days=1)
        end_day = day_end.strftime("%Y-%m-%d")

        baddates = refresh_data(start_day, end_day)
        if baddates == 1:
            flash(
                f"I cannot find sales for the day you selected.  Please select another date!",
                "warning",
            )
            return redirect(url_for("home_blueprint.route_default"))
        session["targetdate"] = start_day
        return redirect(url_for("home_blueprint.support"))


    if form3.submit3.data and form3.validate():

        session["targetdate"] = start_day
        store_id = form3.store.data.id

        return redirect(url_for("home_blueprint.store", store_id=store_id))


    query = (
        db.session.query(Menuitems.name,
                         Menuitems.menuitem,
                         Menuitems.category,
                         func.sum(Menuitems.amount).label("sales"),
                         func.sum(Menuitems.quantity).label("count"),
                         )
            .filter(Menuitems.date == start_day,
                    or_(
                    Menuitems.menuitem == 'Unassigned',
                    Menuitems.category == 'Unassigned',
                    ))
            .group_by(Menuitems.name, Menuitems.menuitem, Menuitems.category)
        ).all()
    unassigned_sales = pd.DataFrame.from_records(
        query, columns=["store", "menuitem", "category", "amount", "quantity"]
    )
    unassigned_sales.sort_values(by=['amount'], ascending=False, inplace=True)

    query = (
        db.session.query(Transactions.name,
                         Transactions.item)
            .filter(Transactions.date >= start_week,
                    Transactions.item.regexp_match('^DO NOT USE*'))
            .group_by(Transactions.name, Transactions.item)
        ).all()
    do_not_use = pd.DataFrame.from_records(query, columns=['store', 'menuitem'])
    do_not_use.sort_values(by=['store'], inplace=True)

    return render_template(
        'home/support.html',
        title='Support',
        segment='support',
        fiscal_dates=fiscal_dates,
        form1=form1,
        form2=form2,
        form3=form3,
        unassigned_sales=unassigned_sales,
        do_not_use=do_not_use,
    )

#@blueprint.route("/<template>")
#@login_required
#def route_template(template):
#
#    try:
#
#        if not template.endswith(".html"):
#            template += ".html"
#
#        # Detect the current page
#        segment = get_segment(request)
#
#        # Serve the file (if exists) from app/templates/home/FILE.html
#        return render_template("home/" + template, segment=segment)
#
#    except TemplateNotFound:
#        return render_template("home/page-404.html"), 404
#
#    except:
#        return render_template("home/page-500.html"), 500
#
#
## Helper - Extract current page name from request
#def get_segment(request):
#
#    try:
#
#        segment = request.path.split("/")[-1]
#
#        if segment == "":
#            segment = "index"
#
#        return segment
#
#    except:
#        return None
