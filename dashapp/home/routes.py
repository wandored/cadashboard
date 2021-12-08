# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from flask.helpers import url_for
from flask_security.decorators import auth_required
import pandas as pd
from dashapp.home import blueprint
from flask import flash, render_template, session, request, redirect, url_for
from dashapp.home.util import get_period, get_lastyear, refresh_data, refresh_data
from flask_security import login_required, current_user
from jinja2 import TemplateNotFound
from datetime import datetime, timedelta
from dashapp.authentication.forms import DateForm
from dashapp.authentication.models import db, Calendar, Sales, Labor, Restaurants
from sqlalchemy import and_, func


@blueprint.route("/")
def route_default():
    TODAY = datetime.date(datetime.now())
    YSTDAY = TODAY - timedelta(days=1)
    session["targetdate"] = YSTDAY.strftime("%Y-%m-%d")
    return redirect(url_for("home_blueprint.index"))


@blueprint.route("/index", methods=["GET", "POST"])
@login_required
def index(targetdate=None):

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

    # Check for no sales
    if not Sales.query.filter_by(date=start_day).first():
        baddates = refresh_data(start_day, end_day)
        if baddates == 1 and start_day == session['targetdate']:
            flash(
                f"Sales have not pulled for yesterday yet.  Please try again later or change the date!",
                "warning",
            )
            TODAY = datetime.date(datetime.now())
            YSTDAY = TODAY - timedelta(days=2)
            session["targetdate"] = YSTDAY.strftime("%Y-%m-%d")
            return redirect(url_for("home_blueprint.index"))

        session["targetdate"] = start_day
        return redirect(url_for("home_blueprint.index"))


    # Get Data
    form = DateForm()
    if form.validate_on_submit():
        """
        When new date submitted, the data for that date will be replaced with new data from R365
        We check if there are infact sales for that day, if not, it resets to yesterday, if
        there are sales, then labor is polled
        """
        start_day = form.selectdate.data.strftime("%Y-%m-%d")
        day_end = form.selectdate.data + timedelta(days=1)
        end_day = day_end.strftime("%Y-%m-%d")

        baddates = refresh_data(start_day, end_day)
        if baddates == 1:
            flash(
                f"I cannot find sales for the day you selected.  Please select another date!",
                "warning",
            )
            TODAY = datetime.date(datetime.now())
            YSTDAY = TODAY - timedelta(days=1)
            session["targetdate"] = YSTDAY.strftime("%Y-%m-%d")
            return redirect(url_for("home_blueprint.route_default"))


        session["targetdate"] = start_day
        return redirect(url_for("home_blueprint.index"))

    # Daily Chart
    daily_chart = (
        db.session.query(func.sum(Sales.sales).label("total_sales"))
        .filter(Sales.date >= start_week, Sales.date <= end_week)
        .group_by(Sales.date)
        .order_by(Sales.date)
    )
    values1 = []
    for v in daily_chart:
        values1.append(v.total_sales)

    daily_chart_ly = (
        db.session.query(func.sum(Sales.sales).label("total_sales"))
        .filter(Sales.date >= start_week_ly, Sales.date <= end_week_ly)
        .group_by(Sales.date)
        .order_by(Sales.date)
    )
    values1_ly = []
    for v in daily_chart_ly:
        values1_ly.append(v.total_sales)

    # Weekly Chart
    weekly_chart = (
        db.session.query(func.sum(Sales.sales).label("total_sales"))
        .select_from(Sales)
        .join(Calendar, Calendar.date == Sales.date)
        .group_by(Calendar.week)
        .order_by(Calendar.week)
        .filter(Sales.date >= start_period, Sales.date <= end_period)
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
        .filter(Sales.date >= start_period_ly, Sales.date <= end_period_ly)
    )
    values2_ly = []
    for v in weekly_chart_ly:
        values2_ly.append(v.total_sales)

    # Yearly Chart
    period_chart = (
        db.session.query(func.sum(Sales.sales).label("total_sales"))
        .select_from(Sales)
        .join(Calendar, Calendar.date == Sales.date)
        .group_by(Calendar.period)
        .order_by(Calendar.period)
        .filter(Sales.date >= start_year, Sales.date <= end_year)
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
        .filter(Sales.date >= start_year_ly, Sales.date <= end_year_ly)
    )
    values3_ly = []
    for v in period_chart_ly:
        values3_ly.append(v.total_sales)

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

    df_sales_day = pd.DataFrame.from_records(
        sales_day, columns=["name", "sales"]
    )
    df_sales_day_ly = pd.DataFrame.from_records(
        sales_day_ly, columns=["name", "sales_ly"]
    )
    sales_table = df_sales_day.merge(df_sales_day_ly, how="outer", sort=True)

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
    dy_sales = daily_table.sales - daily_table.sales_ly
    dy_top_sales = dy_sales.nlargest(5)
    dy_sales_avg = (
        (daily_table.sales - daily_table.sales_ly) / daily_table.sales_ly * 100
    )
    dy_avg_sales = dy_sales_avg.nlargest(5)

    daily_table.loc["TOTALS"] = daily_table.sum()
    daily_table['labor_pct'] = daily_table.dollars / daily_table.sales
    daily_table['labor_pct_ly'] = daily_table.dollars_ly / daily_table.sales_ly
    daily_totals = daily_table.loc["TOTALS"]

    # Weekly Sales Table
    sales_week = (
        db.session.query(
            Sales.name,
            func.sum(Sales.sales).label("total_sales")
        )
        .filter(Sales.date >= start_week,
                Sales.date <= end_week)
        .group_by(Sales.name)
        .all()
    )

    sales_week_ly = (
        db.session.query(
            Sales.name,
            func.sum(Sales.sales).label("total_sales_ly")
        )
        .filter(
            Sales.date >= start_week_ly,
            Sales.date <= week_to_date,
        )
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
        .filter(Labor.date >= start_week, Labor.date <= end_week)
        .group_by(Labor.name)
        .all()
    )

    labor_week_ly = (
        db.session.query(
            Labor.name,
            func.sum(Labor.hours).label("total_hours_ly"),
            func.sum(Labor.dollars).label("total_dollars_ly"),
        )
        .filter(Labor.date >= start_week_ly, Labor.date <= week_to_date)
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
    wk_sales = weekly_table.sales - weekly_table.sales_ly
    wk_top_sales = wk_sales.nlargest(5)
    wk_sales_avg = (
        (weekly_table.sales - weekly_table.sales_ly) / weekly_table.sales_ly * 100
    )
    wk_avg_sales = wk_sales_avg.nlargest(5)

    weekly_table.loc["TOTALS"] = weekly_table.sum()
    weekly_table['labor_pct'] = weekly_table.dollars / weekly_table.sales
    weekly_table['labor_pct_ly'] = weekly_table.dollars_ly / weekly_table.sales_ly
    weekly_totals = weekly_table.loc["TOTALS"]

    # Period Sales Table
    sales_period = (
        db.session.query(
            Sales.name,
            func.sum(Sales.sales).label("total_sales")
        )
        .filter(Sales.date >= start_period, Sales.date <= end_period)
        .group_by(Sales.name)
        .all()
    )

    sales_period_ly = (
        db.session.query(
            Sales.name,
            func.sum(Sales.sales).label("total_sales_ly")
        )
        .filter(Sales.date >= start_period_ly, Sales.date <= period_to_date)
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
        .filter(Labor.date >= start_period, Labor.date <= end_period)
        .group_by(Labor.name)
        .all()
    )

    labor_period_ly = (
        db.session.query(
            Labor.name,
            func.sum(Labor.hours).label("total_hours_ly"),
            func.sum(Labor.dollars).label("total_dollars_ly"),
        )
        .filter(Labor.date >= start_period_ly, Labor.date <= period_to_date)
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
    pd_sales = period_table.sales - period_table.sales_ly
    pd_top_sales = pd_sales.nlargest(5)
    pd_sales_avg = (
        (period_table.sales - period_table.sales_ly) / period_table.sales_ly * 100
    )
    pd_avg_sales = pd_sales_avg.nlargest(5)

    period_table.loc["TOTALS"] = period_table.sum()
    period_table['labor_pct'] = period_table.dollars / period_table.sales
    period_table['labor_pct_ly'] = period_table.dollars_ly / period_table.sales_ly
    period_totals = period_table.loc["TOTALS"]


    # Yearly Sales Table
    sales_yearly = (
        db.session.query(
            Sales.name,
            func.sum(Sales.sales).label("total_sales")
        )
        .filter(Sales.date >= start_year, Sales.date <= end_year)
        .group_by(Sales.name)
        .all()
    )

    sales_yearly_ly = (
        db.session.query(
            Sales.name,
            func.sum(Sales.sales).label("total_sales_ly")
        )
        .filter(Sales.date >= start_year_ly, Sales.date <= year_to_date)
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
        .filter(Labor.date >= start_year, Labor.date <= end_year)
        .group_by(Labor.name)
        .all()
    )

    labor_yearly_ly = (
        db.session.query(
            Labor.name,
            func.sum(Labor.hours).label("total_hours_ly"),
            func.sum(Labor.dollars).label("total_dollars_ly"),
        )
        .filter(Labor.date >= start_year_ly, Labor.date <= year_to_date)
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
    yr_sales = yearly_table.sales - yearly_table.sales_ly
    yr_top_sales = yr_sales.nlargest(5)
    yr_sales_avg = (
        (yearly_table.sales - yearly_table.sales_ly) / yearly_table.sales_ly * 100
    )
    yr_avg_sales = yr_sales_avg.nlargest(5)

    yearly_table.loc["TOTALS"] = yearly_table.sum()
    yearly_table['labor_pct'] = yearly_table.dollars / yearly_table.sales
    yearly_table['labor_pct_ly'] = yearly_table.dollars_ly / yearly_table.sales_ly
    yearly_totals = yearly_table.loc["TOTALS"]

    # Scorecard

    return render_template(
        "home/index.html",
        title='CentraArchy',
        form=form,
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
        daily_table=daily_table,
        daily_totals=daily_totals,
        weekly_table=weekly_table,
        weekly_totals=weekly_totals,
        period_table=period_table,
        period_totals=period_totals,
        yearly_table=yearly_table,
        yearly_totals=yearly_totals,
        dy_top_sales=dy_top_sales,
        dy_avg_sales=dy_avg_sales,
        wk_top_sales=wk_top_sales,
        wk_avg_sales=wk_avg_sales,
        pd_top_sales=pd_top_sales,
        pd_avg_sales=pd_avg_sales,
    )


@blueprint.route("/<int:store_id>/store", methods=["GET", "POST"])
@login_required
def store(store_id):

    form = DateForm()
    store = Restaurants.query.filter_by(id=store_id).first()
    if not store:
        flash(
            f"Please don't click on Totals",
            "warning",
        )
        TODAY = datetime.date(datetime.now())
        YSTDAY = TODAY - timedelta(days=1)
        session["targetdate"] = YSTDAY.strftime("%Y-%m-%d")
        return redirect(url_for("home_blueprint.index"))

    print(store.name)
    start_day = start_week = end_week = start_period = end_period = start_year = end_year = ""
    fiscal_dates = get_period(datetime.strptime(session["targetdate"], "%Y-%m-%d"))
    for i in fiscal_dates:
        day_start = datetime.strptime(i.date, "%Y-%m-%d")
        day_end = day_start + timedelta(days=1)

        start_day = i.date
        start_week = i.week_start
        end_week = i.week_end
        start_period = i.period_start
        end_period = i.period_end
        start_year = i.year_start
        end_year = i.year_end

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
    form = DateForm()
    if form.validate_on_submit():
        """
        When new date submitted, the data for that date will be replaced with new data from R365
        We check if there are infact sales for that day, if not, it resets to yesterday, if
        there are sales, then labor is polled
        """
        start_day = form.selectdate.data.strftime("%Y-%m-%d")
        day_end = form.selectdate.data + timedelta(days=1)
        end_day = day_end.strftime("%Y-%m-%d")

        baddates = refresh_data(start_day, end_day)
        if baddates == 1:
            flash(
                f"I cannot find sales for the day you selected.  Please select another date!",
                "warning",
            )
            TODAY = datetime.date(datetime.now())
            YSTDAY = TODAY - timedelta(days=1)
            session["targetdate"] = YSTDAY.strftime("%Y-%m-%d")
            return redirect(url_for("home_blueprint.route_default"))


        session["targetdate"] = start_day
        return redirect(url_for("home_blueprint.store", store_id=store.id))


    # Daily Chart
    daily_chart = (
        db.session.query(func.sum(Sales.sales).label("total_sales"))
        .filter(Sales.date >= start_week,
                Sales.date <= end_week,
                Sales.name == store.name)
        .group_by(Sales.date)
        .order_by(Sales.date)
    )
    values1 = []
    for v in daily_chart:
        values1.append(v.total_sales)

    daily_chart_ly = (
        db.session.query(func.sum(Sales.sales).label("total_sales"))
        .filter(Sales.date >= start_week_ly,
                Sales.date <= end_week_ly,
                Sales.name == store.name)
        .group_by(Sales.date)
        .order_by(Sales.date)
    )
    values1_ly = []
    for v in daily_chart_ly:
        values1_ly.append(v.total_sales)

    # Weekly Chart
    weekly_chart = (
        db.session.query(func.sum(Sales.sales).label("total_sales"))
        .select_from(Sales)
        .join(Calendar, Calendar.date == Sales.date)
        .group_by(Calendar.week)
        .order_by(Calendar.week)
        .filter(Sales.date >= start_period,
                Sales.date <= end_period,
                Sales.name == store.name
        )
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
        .filter(Sales.date >= start_period_ly,
                Sales.date <= end_period_ly,
                Sales.name == store.name)
    )
    values2_ly = []
    for v in weekly_chart_ly:
        values2_ly.append(v.total_sales)

    # Yearly Chart
    period_chart = (
        db.session.query(func.sum(Sales.sales).label("total_sales"))
        .select_from(Sales)
        .join(Calendar, Calendar.date == Sales.date)
        .group_by(Calendar.period)
        .order_by(Calendar.period)
        .filter(Sales.date >= start_year,
                Sales.date <= end_year,
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
        .filter(Sales.date >= start_year_ly,
                Sales.date <= end_year_ly,
                Sales.name == store.name)
    )
    values3_ly = []
    for v in period_chart_ly:
        values3_ly.append(v.total_sales)


    # Daily Sales Table
    sales_day = (
        db.session.query(
            Sales.name,
            func.sum(Sales.sales).label("total_sales")
        )
        .filter(Sales.date == start_day,
                Sales.name == store.name)
        .group_by(Sales.name)
        .all()
    )

    sales_day_ly = (
        db.session.query(
            Sales.name,
            func.sum(Sales.sales).label("total_sales_ly")
        )
        .filter(Sales.date == start_day_ly,
                Sales.name == store.name)
        .group_by(Sales.name)
        .all()
    )

    df_sales_day = pd.DataFrame.from_records(
        sales_day, columns=["name", "sales"]
    )
    df_sales_day_ly = pd.DataFrame.from_records(
        sales_day_ly, columns=["name", "sales_ly"]
    )
    sales_table = df_sales_day.merge(df_sales_day_ly, how="outer", sort=True)

    labor_day = (
        db.session.query(
            Labor.name,
            func.sum(Labor.hours).label("total_hours"),
            func.sum(Labor.dollars).label("total_dollars"),
        )
        .filter(Labor.date == start_day,
                Labor.name == store.name)
        .group_by(Labor.name)
        .all()
    )

    labor_day_ly = (
        db.session.query(
            Labor.name,
            func.sum(Labor.hours).label("total_hours_ly"),
            func.sum(Labor.dollars).label("total_dollars_ly"),
        )
        .filter(Labor.date == start_day_ly,
                Labor.name == store.name)
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

    if daily_table.sales.empty:
        print('table empty')

        baddates = refresh_data(start_day, end_day)
        if baddates == 1 and start_day == session['targetdate']:
            flash(
                f"Sales have not pulled for yesterday yet.  Please try again later or change the date!",
                "warning",
            )
            TODAY = datetime.date(datetime.now())
            YSTDAY = TODAY - timedelta(days=2)
            session["targetdate"] = YSTDAY.strftime("%Y-%m-%d")
            return redirect(url_for("home_blueprint.index"))

        session["targetdate"] = start_day
        return redirect(url_for("home_blueprint.index"))

    daily_table['labor_pct'] = daily_table.dollars / daily_table.sales
    daily_table['labor_pct_ly'] = daily_table.dollars_ly / daily_table.sales_ly
    daily_table.loc["TOTALS"] = daily_table.sum()
    daily_totals = daily_table.loc["TOTALS"]


    # Weekly Sales Table
    dates = Calendar.query.filter(Calendar.date >= start_week, Calendar.date <= end_week).all()
    dates = pd.DataFrame([x.as_dict() for x in dates])
    sales_week = (
        db.session.query(
            Sales.date,
            func.sum(Sales.sales).label("total_sales")
        )
        .filter(Sales.date >= start_week,
                Sales.date <= end_week,
                Sales.name == store.name
                )
        .group_by(Sales.date)
        .all()
    )

    dates_ly = Calendar.query.filter(Calendar.date >= start_week_ly, Calendar.date <= end_week_ly).all()
    dates_ly = pd.DataFrame([x.as_dict() for x in dates_ly])
    sales_week_ly = (
        db.session.query(
            Sales.date,
            func.sum(Sales.sales).label("total_sales_ly")
        )
        .filter(
            Sales.date >= start_week_ly,
            Sales.date <= week_to_date,
            Sales.name == store.name
        )
        .group_by(Sales.date)
        .all()
    )

    df_sales_week = pd.DataFrame.from_records(
        sales_week, columns=["date", "sales"]
    )
    df_sales_week_ly = pd.DataFrame.from_records(
        sales_week_ly, columns=["date", "sales_ly"]
    )
    sales_table_ty = df_sales_week.merge(dates, how="outer", sort=True)
    sales_table_ly = df_sales_week_ly.merge(dates_ly, how="outer")
    sales_table_wk = sales_table_ty.merge(sales_table_ly, on=['day', 'week', 'period'])
    sales_table_wk.drop(columns=['date_y', 'quarter_y', 'year_y', 'dow_y'], inplace=True)

    labor_week = (
        db.session.query(
            Labor.date,
            func.sum(Labor.hours).label("total_hours"),
            func.sum(Labor.dollars).label("total_dollars"),
        )
        .filter(Labor.date >= start_week,
                Labor.date <= end_week,
                Labor.name == store.name
                )
        .group_by(Labor.date)
        .all()
    )

    labor_week_ly = (
        db.session.query(
            Labor.date,
            func.sum(Labor.hours).label("total_hours_ly"),
            func.sum(Labor.dollars).label("total_dollars_ly"),
        )
        .filter(Labor.date >= start_week_ly,
                Labor.date <= week_to_date,
                Labor.name == store.name
                )
        .group_by(Labor.date)
        .all()
    )

    df_labor_week = pd.DataFrame.from_records(
        labor_week, columns=["date", "hours", "dollars"]
    )
    df_labor_week_ly = pd.DataFrame.from_records(
        labor_week_ly, columns=["day", "hours_ly", "dollars_ly"]
    )
    labor_table_ty = df_labor_week.merge(dates, how="outer", sort=True)
    labor_table_ly = df_labor_week_ly.merge(dates_ly, how="outer")
    labor_table_wk = labor_table_ty.merge(labor_table_ly, on=['day', 'week', 'period'])
    labor_table_wk.drop(columns=['date_y', 'quarter_y', 'year_y', 'dow_y'], inplace=True)

    weekly_table = sales_table_wk.merge(labor_table_wk, how="outer", sort=True)
    weekly_table.set_index("day", inplace=True)

    # Grab top sales over last year before we add totals
    weekly_table.loc["TOTALS"] = weekly_table.sum()
    weekly_table['labor_pct'] = weekly_table.dollars / weekly_table.sales
    weekly_table['labor_pct_ly'] = weekly_table.dollars_ly / weekly_table.sales_ly
    weekly_totals = weekly_table.loc["TOTALS"]


    # Period Sales Table
    dates = Calendar.query.filter(Calendar.date >= start_period, Calendar.date <= end_period).all()
    dates = pd.DataFrame([x.as_dict() for x in dates])
    sales_period = (
        db.session.query(
            Sales.date,
            func.sum(Sales.sales).label("total_sales")
        )
        .filter(Sales.date >= start_period,
                Sales.date <= end_period,
                Sales.name == store.name
                )
        .group_by(Sales.date)
        .all()
    )

    dates_ly = Calendar.query.filter(Calendar.date >= start_period_ly, Calendar.date <= end_period_ly).all()
    dates_ly = pd.DataFrame([x.as_dict() for x in dates_ly])
    sales_period_ly = (
        db.session.query(
            Sales.date,
            func.sum(Sales.sales).label("total_sales_ly")
        )
        .filter(
            Sales.date >= start_period_ly,
            Sales.date <= period_to_date,
            Sales.name == store.name
        )
        .group_by(Sales.date)
        .all()
    )

    df_sales_period = pd.DataFrame.from_records(
        sales_period, columns=["date", "sales"]
    )
    df_sales_period_ly = pd.DataFrame.from_records(
        sales_period_ly, columns=["date", "sales_ly"]
    )
    sales_table_ty = df_sales_period.merge(dates, how="outer", sort=True)
    sales_table_ly = df_sales_period_ly.merge(dates_ly, how="outer")
    sales_table_yr = sales_table_ty.merge(sales_table_ly, on=['day', 'week', 'period'])
    sales_table_yr.drop(columns=['date_y', 'quarter_y', 'year_y', 'dow_y'], inplace=True)

    labor_period = (
        db.session.query(
            Labor.date,
            func.sum(Labor.hours).label("total_hours"),
            func.sum(Labor.dollars).label("total_dollars"),
        )
        .filter(Labor.date >= start_period,
                Labor.date <= end_period,
                Labor.name == store.name
                )
        .group_by(Labor.date)
        .all()
    )

    labor_period_ly = (
        db.session.query(
            Labor.date,
            func.sum(Labor.hours).label("total_hours_ly"),
            func.sum(Labor.dollars).label("total_dollars_ly"),
        )
        .filter(Labor.date >= start_period_ly,
                Labor.date <= period_to_date,
                Labor.name == store.name
                )
        .group_by(Labor.date)
        .all()
    )

    df_labor_period = pd.DataFrame.from_records(
        labor_period, columns=["date", "hours", "dollars"]
    )
    df_labor_period_ly = pd.DataFrame.from_records(
        labor_period_ly, columns=["day", "hours_ly", "dollars_ly"]
    )
    labor_table_ty = df_labor_period.merge(dates, how="outer", sort=True)
    labor_table_ly = df_labor_period_ly.merge(dates_ly, how="outer")
    labor_table_yr = labor_table_ty.merge(labor_table_ly, on=['day', 'week', 'period'])
    labor_table_yr.drop(columns=['date_y', 'quarter_y', 'year_y', 'dow_y'], inplace=True)

    period_table = sales_table_yr.merge(labor_table_yr, how="outer", sort=True)
#    period_table.set_index("day", inplace=True)

    # Grab top sales over last year before we add totals
    period_table['labor_pct'] = period_table.dollars / period_table.sales
    period_table['labor_pct_ly'] = period_table.dollars_ly / period_table.sales_ly
    period_table_w1 = period_table.loc[period_table['week'] == 1 ]
    period_table_w2 = period_table.loc[period_table['week'] == 2 ]
    period_table_w3 = period_table.loc[period_table['week'] == 3 ]
    period_table_w4 = period_table.loc[period_table['week'] == 4 ]
    period_table_w1.loc["TOTALS"] = period_table_w1.sum()
    period_table_w2.loc["TOTALS"] = period_table_w2.sum()
    period_table_w3.loc["TOTALS"] = period_table_w3.sum()
    period_table_w4.loc["TOTALS"] = period_table_w4.sum()
    period_table.loc["TOTALS"] = period_table.sum()
    period_totals = period_table.loc["TOTALS"]


    # Yearly Sales Table
    dates = Calendar.query.filter(Calendar.date >= start_year, Calendar.date <= end_year).all()
    dates = pd.DataFrame([x.as_dict() for x in dates])
    sales_yearly = (
        db.session.query(
            Sales.date,
            func.sum(Sales.sales).label("total_sales")
        )
        .filter(Sales.date >= start_year,
                Sales.date <= end_year,
                Sales.name == store.name
                )
        .group_by(Sales.date)
        .all()
    )

    dates_ly = Calendar.query.filter(Calendar.date >= start_year_ly, Calendar.date <= end_year_ly).all()
    dates_ly = pd.DataFrame([x.as_dict() for x in dates_ly])
    sales_yearly_ly = (
        db.session.query(
            Sales.date,
            func.sum(Sales.sales).label("total_sales_ly")
        )
        .filter(
            Sales.date >= start_year_ly,
            Sales.date <= year_to_date,
            Sales.name == store.name
        )
        .group_by(Sales.date)
        .all()
    )

    df_sales_yearly = pd.DataFrame.from_records(
        sales_yearly, columns=["date", "sales"]
    )
    df_sales_yearly_ly = pd.DataFrame.from_records(
        sales_yearly_ly, columns=["date", "sales_ly"]
    )
    sales_table_ty = df_sales_yearly.merge(dates, how="outer", sort=True)
    sales_table_ly = df_sales_yearly_ly.merge(dates_ly, how="outer")
    sales_table_yr = sales_table_ty.merge(sales_table_ly, on=['day', 'week', 'period'])
    sales_table_yr.drop(columns=['date_y', 'quarter_y', 'year_y', 'dow_y'], inplace=True)

    labor_yearly = (
        db.session.query(
            Labor.date,
            func.sum(Labor.hours).label("total_hours"),
            func.sum(Labor.dollars).label("total_dollars"),
        )
        .filter(Labor.date >= start_year,
                Labor.date <= end_year,
                Labor.name == store.name
                )
        .group_by(Labor.date)
        .all()
    )

    labor_yearly_ly = (
        db.session.query(
            Labor.date,
            func.sum(Labor.hours).label("total_hours_ly"),
            func.sum(Labor.dollars).label("total_dollars_ly"),
        )
        .filter(Labor.date >= start_year_ly,
                Labor.date <= year_to_date,
                Labor.name == store.name
                )
        .group_by(Labor.date)
        .all()
    )

    df_labor_yearly = pd.DataFrame.from_records(
        labor_yearly, columns=["date", "hours", "dollars"]
    )
    df_labor_yearly_ly = pd.DataFrame.from_records(
        labor_yearly_ly, columns=["day", "hours_ly", "dollars_ly"]
    )
    labor_table_ty = df_labor_yearly.merge(dates, how="outer", sort=True)
    labor_table_ly = df_labor_yearly_ly.merge(dates_ly, how="outer")
    labor_table_yr = labor_table_ty.merge(labor_table_ly, on=['day', 'week', 'period'])
    labor_table_yr.drop(columns=['date_y', 'quarter_y', 'year_y', 'dow_y'], inplace=True)

    yearly_table = sales_table_yr.merge(labor_table_yr, how="outer", sort=True)
    yearly_table.set_index("day", inplace=True)

    # Grab top sales over last year before we add totals
    yearly_table.loc["TOTALS"] = yearly_table.sum()
    yearly_table['labor_pct'] = yearly_table.dollars / yearly_table.sales
    yearly_table['labor_pct_ly'] = yearly_table.dollars_ly / yearly_table.sales_ly
    yearly_totals = yearly_table.loc["TOTALS"]

    print('period_table')
    print(period_table_w1)
    print('period_totals')


    return render_template(
        "home/store.html",
        title=store.name,
        form=form,
        current_user=current_user,
        roles=current_user.roles,
        fiscal_dates=fiscal_dates,
        values1=values1,
        values2=values2,
        values3=values3,
        values1_ly=values1_ly,
        values2_ly=values2_ly,
        values3_ly=values3_ly,
        daily_table=daily_table,
        daily_totals=daily_totals,
        weekly_table=weekly_table,
        weekly_totals=weekly_totals,
        period_table=period_table,
        period_totals=period_totals,
        period_table_w1=period_table_w1,
        period_table_w2=period_table_w2,
        period_table_w3=period_table_w3,
        period_table_w4=period_table_w4,
        yearly_table=yearly_table,
        yearly_totals=yearly_totals,
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
