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
from flask_security import current_user, login_required
from flask_security.decorators import roles_accepted
from fpdf import FPDF
import pandas as pd
from pandas._libs.tslibs import dtypes
from pandas.core.algorithms import isin
from sqlalchemy import and_, func, or_

from dashapp.authentication.forms import *
from dashapp.authentication.models import *
from dashapp.config import Config
from dashapp.home import blueprint
from dashapp.home.util import *
import time


@blueprint.route("/", methods=["GET", "POST"])
@blueprint.route("/index/", methods=["GET", "POST"])
@login_required
def index():

    TODAY = datetime.date(datetime.now())
    if not "date_selected" in session:
        session["date_selected"] = TODAY
        return redirect(url_for("home_blueprint.index"))

    # TODO fix restaurant list selection
    if not "store_list" in session:
        session["store_list"] = tuple(
            [
                store.id
                for store in Restaurants.query.filter(Restaurants.active==True)
                .order_by(Restaurants.name)
                .all()
            ]
        )
        return redirect(url_for("home_blueprint.index"))

    fiscal_dates = set_dates(session["date_selected"])

    # Check for no sales
    if not SalesTotals.query.filter_by(date=fiscal_dates["start_day"]).all():
        session["date_selected"] = find_day_with_sales(day=fiscal_dates["start_day"])
        return redirect(url_for("home_blueprint.index"))


    # Get Data
    form1 = DateForm()
    form3 = StoreForm()
    form4 = PotatoForm()
    form5 = LobsterForm()
    form6 = StoneForm()

    if form1.submit1.data and form1.validate():
        """
        Change date_selected
        """
        session["date_selected"] = form1.selectdate.data
        return redirect(url_for("home_blueprint.index"))

    if form3.submit3.data and form3.validate():
        session["date_selected"] = fiscal_dates["start_day"]
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
    def get_chart_values(start, end, time_frame):
        query = (
            db.session.query(func.sum(SalesTotals.net_sales).label("total_sales"))
            .select_from(SalesTotals)
            .filter(SalesTotals.date.between(start, end))
            .group_by(time_frame)
        )
        value = [v.total_sales for v in query]
        return value

    daily_sales_list = get_chart_values(
            fiscal_dates["start_week"],
            fiscal_dates["start_day"],
            SalesTotals.date)
    weekly_sales = sum(daily_sales_list)

    daily_sales_list_ly = get_chart_values(
            fiscal_dates["start_week_ly"],
            fiscal_dates["end_week_ly"],
            SalesTotals.date)
    weekly_sales_ly = sum(daily_sales_list_ly)

    week_to_date_sales_ly = get_chart_values(
            fiscal_dates["start_week_ly"],
            fiscal_dates["start_day_ly"],
            SalesTotals.date)
    wtd_sales_ly = sum(week_to_date_sales_ly)

    weekly_sales_list = get_chart_values(
            fiscal_dates["start_period"],
            fiscal_dates["start_day"],
            SalesTotals.week)
    period_sales = sum(weekly_sales_list)

    weekly_sales_list_ly = get_chart_values(
            fiscal_dates["start_period_ly"],
            fiscal_dates["end_period_ly"],
            SalesTotals.week)
    period_sales_ly = sum(weekly_sales_list_ly)

    period_to_date_sales_ly = get_chart_values(
            fiscal_dates["start_period_ly"],
            fiscal_dates["start_day_ly"],
            SalesTotals.week)
    ptd_sales_ly = sum(period_to_date_sales_ly)

    period_sales_list = get_chart_values(
            fiscal_dates["start_year"],
            fiscal_dates["start_day"],
            SalesTotals.period)
    yearly_sales = sum(period_sales_list)

    period_sales_list_ly = get_chart_values(
            fiscal_dates["start_year_ly"],
            fiscal_dates["end_year_ly"],
            SalesTotals.period)
    yearly_sales_ly = sum(period_sales_list_ly)

    year_to_date_sales_ly = get_chart_values(
            fiscal_dates["start_year_ly"],
            fiscal_dates["start_day_ly"],
            SalesTotals.period)
    ytd_sales_ly = sum(year_to_date_sales_ly)

    def build_sales_table(start, end, start_ly, end_ly, time_frame):
        #sales_view = (
        #    db.session.query(
        #        SalesTotals.store,
        #        func.sum(SalesTotals.net_sales).label("total_sales"),
        #        func.sum(SalesTotals.guest_count).label("total_guests"),
        #    )
        #    .filter(SalesTotals.date.between(start, end))
        #    .group_by(SalesTotals.store)
        #    .all()
        #)
        sales = (
                db.session.query(
                    Restaurants.name.label("store"),
                    func.sum(SalesEmployee.netsales).label('total_sales'),
                    func.sum(SalesEmployee.numberofguests).label('total_guests')
                )
                .join(SalesEmployee, Restaurants.locationid == SalesEmployee.location)
                .filter(SalesEmployee.date.between(start, end))
                .group_by(Restaurants.name)
                .all()
        )

        sales_ly = (
            db.session.query(
                Restaurants.name.label("store"),
                func.sum(SalesEmployee.netsales).label("total_sales_ly"),
                func.sum(SalesEmployee.numberofguests).label("total_guests_ly"),
            )
            .join(SalesEmployee, Restaurants.locationid == SalesEmployee.location)
            .filter(SalesEmployee.date.between(start_ly, end_ly))
            .group_by(Restaurants.name)
            .all()
        )
        # Get the top sales for each store and merge with sales_table
        table_class = globals()[f'SalesRecords{time_frame}'] # how you use a variable in query
        sales_query = table_class.query.with_entities(table_class.store, table_class.net_sales).all()

        top_sales = pd.DataFrame.from_records(sales_query, columns=['store', 'top_sales'])
        top_sales.set_index('store', inplace=True)
        sales_table = pd.DataFrame.from_records(sales, columns=["store", "sales", "guests"])
        sales_table_ly = pd.DataFrame.from_records(sales_ly, columns=["store", "sales_ly", "guests_ly"])
        sales_table = sales_table.merge(sales_table_ly, how="outer", sort=True)
        sales_table = sales_table.merge(top_sales, how="left", left_on='store', right_on='store')

        # TODO datetime needs to be change to datetime in the database to work like this
        labor = (
            db.session.query(
                Restaurants.name.label("store"),
                func.sum(LaborDetail.hours).label("total_hours"),
                func.sum(LaborDetail.total).label("total_dollars"),
            )
            .join(LaborDetail, Restaurants.locationid == LaborDetail.location_id)
            .filter(LaborDetail.dateworked.between(start, end))
            .group_by(Restaurants.name)
            .all()
        )

        labor_ly = (
            db.session.query(
                Restaurants.name.label("store"),
                func.sum(LaborDetail.hours).label("total_hours_ly"),
                func.sum(LaborDetail.total).label("total_dollars_ly"),
            )
            .join(LaborDetail, Restaurants.locationid == LaborDetail.location_id)
            .filter(LaborDetail.dateworked.between(start_ly, end_ly))
            .group_by(Restaurants.name)
            .all()
        )

        df_labor = pd.DataFrame.from_records(labor, columns=["store", "hours", "dollars"])
        df_labor_ly = pd.DataFrame.from_records(labor_ly, columns=["store", "hours_ly", "dollars_ly"])
        labor_table = df_labor.merge(df_labor_ly, how="outer", sort=True)
        table = sales_table.merge(labor_table, how="outer", sort=True)

        # List of stores to add ID so i can pass to other templates
        data = Restaurants.query.with_entities(Restaurants.name, Restaurants.id).all()
        location_list = pd.DataFrame.from_records(data, columns=['store', 'id'])
        table = table.merge(location_list, on='store')
        table = table.set_index("store")

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
        fiscal_dates["end_day"],
        fiscal_dates["start_day_ly"],
        fiscal_dates["end_day_ly"],
        "Day",
    )

    weekly_totals, weekly_table, weekly_top = build_sales_table(
        fiscal_dates["start_week"],
        fiscal_dates["week_to_date"] + timedelta(days=1),
        fiscal_dates["start_week_ly"],
        fiscal_dates["week_to_date_ly"] + timedelta(days=1),
        "Week",
    )

    period_totals, period_table, period_top = build_sales_table(
        fiscal_dates["start_period"],
        fiscal_dates["period_to_date"] + timedelta(days=1),
        fiscal_dates["start_period_ly"],
        fiscal_dates["period_to_date_ly"] + timedelta(days=1),
        "Period",
    )

    yearly_totals, yearly_table, yearly_top = build_sales_table(
        fiscal_dates["start_year"],
        fiscal_dates["year_to_date"] + timedelta(days=1),
        fiscal_dates["start_year_ly"],
        fiscal_dates["year_to_date_ly"] + timedelta(days=1),
        "Year",
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

    store = Restaurants.query.filter_by(id=store_id).first()

    if not "date_selected" in session:
        session["date_selected"] = TODAY
        return redirect(url_for("home_blueprint.store", store_id=store.id))

    fiscal_dates = set_dates(session["date_selected"])

    if not SalesTotals.query.filter_by(date=fiscal_dates["start_day"], store=store.name).first():
        session["date_selected"] = find_day_with_sales(day=fiscal_dates["start_day"], store=store.name)
        return redirect(url_for("home_blueprint.store", store_id=store.id))

    # Get Data
    form1 = DateForm()
    form3 = StoreForm()
    form4 = PotatoForm()
    form5 = LobsterForm()
    form6 = StoneForm()

    if form1.submit1.data and form1.validate():
        session["date_selected"] = form1.selectdate.data
        return redirect(url_for("home_blueprint.store", store_id=store.id))

    if form3.submit3.data and form3.validate():
        session["date_selected"] = fiscal_dates["start_day"]
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
            db.session.query(func.sum(SalesTotals.net_sales).label("total_sales"))
            .select_from(SalesTotals)
            .group_by(time)
            .order_by(time)
            .filter(SalesTotals.date.between(start, end), SalesTotals.store == store.name)
        )
        value = []
        for v in chart:
            value.append(v.total_sales)

        return value

    daily_sales_list = get_chart_values(
            fiscal_dates["start_week"],
            fiscal_dates["start_day"],
            SalesTotals.date)
    weekly_sales = sum(daily_sales_list)

    daily_sales_list_ly = get_chart_values(
            fiscal_dates["start_week_ly"],
            fiscal_dates["end_week_ly"],
            SalesTotals.date)
    weekly_sales_ly = sum(daily_sales_list_ly)

    week_to_date_sales_ly = get_chart_values(
            fiscal_dates["start_week_ly"],
            fiscal_dates["start_day_ly"],
            SalesTotals.date)
    wtd_sales_ly = sum(week_to_date_sales_ly)

    weekly_sales_list = get_chart_values(
            fiscal_dates["start_period"],
            fiscal_dates["start_day"],
            SalesTotals.week)
    period_sales = sum(weekly_sales_list)

    weekly_sales_list_ly = get_chart_values(
        fiscal_dates["start_period_ly"],
        fiscal_dates["end_period_ly"],
        SalesTotals.week)
    period_sales_ly = sum(weekly_sales_list_ly)

    period_to_date_sales_ly = get_chart_values(
        fiscal_dates["start_period_ly"],
        fiscal_dates["start_day_ly"],
        SalesTotals.week)
    ptd_sales_ly = sum(period_to_date_sales_ly)

    period_sales_list = get_chart_values(
            fiscal_dates["start_year"],
            fiscal_dates["start_day"],
            SalesTotals.period)
    yearly_sales = sum(period_sales_list)

    period_sales_list_ly = get_chart_values(
            fiscal_dates["start_year_ly"],
            fiscal_dates["end_year_ly"],
            SalesTotals.period)
    yearly_sales_ly = sum(period_sales_list_ly)

    year_to_date_sales_ly = get_chart_values(
        fiscal_dates["start_year_ly"],
        fiscal_dates["start_day_ly"],
        SalesTotals.period)
    ytd_sales_ly = sum(year_to_date_sales_ly)

    #  TODO need to use Menuitems to get category sales
    def build_category_sales_table(start, end, start_ly, end_ly, time_unit):

        lunch_sales = get_daypart_sales(start, end, store.name, "Lunch")
        ls = pd.DataFrame.from_records(lunch_sales, columns=["date", "dow", "week", "period", "year", "category", "sales", "guests"])
        dinner_sales = get_daypart_sales(start, end, store.name, "Dinner")
        ds = pd.DataFrame.from_records(dinner_sales, columns=["date", "dow", "week", "period", "year", "category", "sales", "guests"])
        #lunch_guests = get_daypart_guest(start, end, store.name, "Lunch")
        #lg = pd.DataFrame.from_records(lunch_guests, columns=["date", "category", "amount"])
        #lg["category"] = lg["category"].str.replace("Lunch", "Lunch Guests")
        #dinner_guests = get_daypart_guest(start, end, store.name, "Dinner")
        #dg = pd.DataFrame.from_records(dinner_guests, columns=["date", "category", "amount"])
        #dg["category"] = dg["category"].str.replace("Dinner", "Dinner Guests")

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
        #sales_guests = sales_guests.merge(lg, how="outer", sort=True)
        #sales_guests = sales_guests.merge(dg, how="outer", sort=True)
        # sales_guests = sales_guests.merge(calendar, how="left", sort=True)
        sales_guests = sales_guests.set_index("date")

        #menu_items = (
        #    db.session.query(
        #        Menuitems.date,
        #        Menuitems.category,
        #        func.sum(Menuitems.total_sales).label("sales"),
        #    )
        #    .filter(Menuitems.date.between(start, end), Menuitems.name == store.name)
        #    .group_by(Menuitems.date, Menuitems.category)
        #    .all()
        #)

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
        #menuitems_table = pd.DataFrame.from_records(menu_items, columns=["date", "category", "amount"])
        ## df_ly = pd.DataFrame.from_records(menuitems_ly, columns=["date", "category", "amount"])
        ## menuitems_table = df.merge(df_ly, how="outer", sort=True)
        #menuitems_table = menuitems_table.merge(calendar, how="left", sort=True)
        #menuitems_table = menuitems_table.set_index("date")

        labor = (
            db.session.query(
                LaborTotals.date,
                LaborTotals.category,
                func.sum(LaborTotals.total_dollars).label("total_dollars"),
            )
            .filter(LaborTotals.date.between(start, end), LaborTotals.store == store.name)
            .group_by(LaborTotals.date, LaborTotals.category)
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
        print(sales_guests)
        sales = pd.pivot_table(
            sales_guests,
            values=["sales", "guests"],
            index=["category", "dow", "week", "period", "year"],
            columns=[time_unit],
            aggfunc=np.sum,
            fill_value=0,
        )
        sales.columns = sales.columns.droplevel(0)
        print(sales)
        #sales.loc["Total Guests"] = sales.loc["Lunch Guests"] + sales.loc["Dinner Guests"]
        #sales.loc["Total Sales"] = sales.loc["Lunch"] + sales.loc["Dinner"]
        #sales = sales.reindex(
        #    [
        #        "Lunch Guests",
        #        "Dinner Guests",
        #        "Total Guests",
        #        "Lunch",
        #        "Dinner",
        #        "Total Sales",
        #    ]
        #)
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

#    daily_table, daily_labor = build_category_sales_table(
#        fiscal_dates["start_day"],
#        fiscal_dates["start_day"],
#        fiscal_dates["start_day_ly"],
#        fiscal_dates["start_day_ly"],
#        "date",
#    )
#
#    weekly_table, weekly_labor = build_category_sales_table(
#        fiscal_dates["start_week"],
#        fiscal_dates["week_to_date"],
#        fiscal_dates["start_week_ly"],
#        fiscal_dates["week_to_date_ly"],
#        "dow",
#    )
#
#    # replace dow with day names 1 = "Wednesday"
#    weekly_table = weekly_table.rename(
#        columns={
#            1: "Wednesday",
#            2: "Thursday",
#            3: "Friday",
#            4: "Saturday",
#            5: "Sunday",
#            6: "Monday",
#            7: "Tuesday",
#        }
#    )
#    weekly_labor = weekly_labor.rename(
#        columns={
#            1: "Wednesday",
#            2: "Thursday",
#            3: "Friday",
#            4: "Saturday",
#            5: "Sunday",
#            6: "Monday",
#            7: "Tuesday",
#        }
#    )
#
#    period_table, period_labor = build_category_sales_table(
#        fiscal_dates["start_period"],
#        fiscal_dates["period_to_date"],
#        fiscal_dates["start_period_ly"],
#        fiscal_dates["period_to_date_ly"],
#        "week",
#    )
#
#    quarterly_table, quarterly_labor = build_category_sales_table(
#        fiscal_dates["start_quarter"],
#        fiscal_dates["quarter_to_date"],
#        fiscal_dates["start_quarter_ly"],
#        fiscal_dates["quarter_to_date_ly"],
#        "period",
#    )
#
#    yearly_table, yearly_labor = build_category_sales_table(
#        fiscal_dates["start_year"],
#        fiscal_dates["year_to_date"],
#        fiscal_dates["start_year_ly"],
#        fiscal_dates["year_to_date_ly"],
#        "quarter",
#    )
#
    daily_sales = daily_sales_list[-1]
    daily_sales_ly = daily_sales_list_ly[-1]

    #budget_chart = (
    #    db.session.query(func.sum(Budgets.total_sales).label("total_sales"))
    #    .select_from(Budgets)
    #    .group_by(Budgets.period)
    #    .order_by(Budgets.period)
    #    .filter(Budgets.year == fiscal_dates["year"], Budgets.name == store.name)
    #)
    #budgets3 = []
    #for v in budget_chart:
    #    budgets3.append(v.total_sales)

    # service duration Charts
    def get_timeing_data(start, end):
        results = db.session.query(TableTurns).filter(TableTurns.date.between(
                    start, end), 
                    TableTurns.store == store.name).all()
        #convert results to list of dictionaries
        data = [
                {
                    'store': row.store,
                    'date': row.date,
                    'dow': row.dow,
                    'week': row.week,
                    'period': row.period,
                    'year': row.year,
                    'bar': row.bar,
                    'dining_room': row.dining_room,
                    'handheld': row.handheld,
                    'patio': row.patio,
                    'online_ordering': row.online_ordering,
                    } for row in results
                ]

        df = pd.DataFrame(data)
        columns_to_convert = ['bar', 'dining_room', 'handheld', 'patio', 'online_ordering']
        for column in columns_to_convert:
            df[column] = pd.to_timedelta(df[column].astype(str)).dt.total_seconds().astype(int)
        return df

    table_turn_df = get_timeing_data(fiscal_dates["start_week"], fiscal_dates["start_day"])
    print(table_turn_df)
    bar_list = table_turn_df['bar'].tolist()
    dining_room_list = table_turn_df['dining_room'].tolist()
    handheld_list = table_turn_df['handheld'].tolist()
    patio_list = table_turn_df['patio'].tolist()
    online_ordering_list = table_turn_df['online_ordering'].tolist()

    table_turn_df_avg = get_timeing_data(fiscal_dates["start_period"], fiscal_dates["start_day"])
    # pivot table on dow to get average time
    table_turn_df_avg = table_turn_df_avg.pivot_table(values=['bar', 'dining_room', 'handheld', 'patio', 'online_ordering'], index=['dow'], aggfunc='mean')
    bar_list_avg = table_turn_df_avg['bar'].tolist()
    dining_room_list_avg = table_turn_df_avg['dining_room'].tolist()
    handheld_list_avg = table_turn_df_avg['handheld'].tolist()
    patio_list_avg = table_turn_df_avg['patio'].tolist()
    online_ordering_list_avg = table_turn_df_avg['online_ordering'].tolist()
    print(table_turn_df_avg)



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

    fiscal_dates = set_dates(session["date_selected"])
    form1 = DateForm()
    form4 = PotatoForm()
    form5 = LobsterForm()
    form6 = StoneForm()
    if form1.submit1.data and form1.validate():
        """ """
        session["date_selected"] = form1.selectdate.data
        return redirect(url_for("home_blueprint.marketing"))

    form3 = StoreForm()
    if form3.submit3.data and form3.validate():
        session["date_selected"] = fiscal_dates["start_day"]
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
            db.session.query(
                func.sum(Menuitems.total_sales).label("sales"), calendar.period,
                func.sum(Menuitems.total_count).label("count"), calendar.period)
            .select_from(Menuitems)
            .group_by(epoch)
            .order_by(epoch)
            .filter(
                Menuitems.date.between(start, end),
                or_(
                    Menuitems.menuitem.regexp_match("(?i)Gift Card*"),
                    Menuitems.menuitem.regexp_match("(?i)ToastCard*")
                )
            )
        )
        value = []
        number = []
        for p in period_order:
            for v in chart:
                if v.period == p:
                    value.append(int(v.sales))
                    number.append(int(v.count))

        return value, number

    def get_giftcard_payments(start, end, epoch):
        chart = (
            db.session.query(func.sum(SalesPayment.amount).label("sales"), calendar.period)
            .select_from(Payments)
            .group_by(epoch)
            .order_by(epoch)
            .filter(
                Payments.date.between(start, end),
                or_(
                    Payments.paymenttype.regexp_match("(?i)GIFT CARD*"),
                    Payments.paymenttype.regexp_match("(?i)GIFTCARD*")
                    )
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

    giftcard_sales, giftcard_count = get_giftcard_sales(
       fiscal_dates["last_threesixtyfive"],
       fiscal_dates["start_day"],
       calendar.period
   )
    giftcard_payments = get_giftcard_payments(
        fiscal_dates["last_threesixtyfive"],
        fiscal_dates["start_day"],
        calendar.period
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

    fiscal_dates = set_dates(session["date_selected"])

    form1 = DateForm()
    form2 = UpdateForm()
    form3 = StoreForm()
    form4 = PotatoForm()
    form5 = LobsterForm()
    form6 = StoneForm()
    uofm_form = UofMForm()
    form9 = RecipeForm()
    user_form = UserForm()

    if form1.submit1.data and form1.validate():
        """ """
        session["date_selected"] = form1.selectdate.data
        return redirect(url_for("home_blueprint.support"))

    if form2.submit2.data and form2.validate():
        """ """
        new_start_day = form2.selectdate.data
        new_end_day = form2.selectdate.data + timedelta(days=1)

        baddates = refresh_data(new_start_day, new_end_day)
        if baddates == 1:
            flash(
                f"I cannot find sales for the day you selected.  Please select another date!",
                "warning",
            )
        session["date_selected"] = new_start_day
        return redirect(url_for("home_blueprint.support"))

    if form3.submit3.data and form3.validate():
        session["date_selected"] = fiscal_dates["start_day"]
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
        session["date_selected"] = fiscal_dates["start_day"]
        return redirect(url_for("home_blueprint.support"))

    if form9.submit9.data and form9.validate():
        file = request.files["file"]
        receiving_by_purchased_item(file)
        session["date_selected"] = fiscal_dates["start_day"]
        return redirect(url_for("home_blueprint.support"))

    if user_form.submit_user.data and user_form.validate():
        session["date_selected"] = fiscal_dates["start_day"]
        return redirect(url_for("home_blueprint.users"))

#    query = (
#        db.session.query(
#            menuitems.store,
#            menuitems.menuitem,
#            Menuitems.category,
#            func.sum(Menuitems.amount).label("sales"),
#            func.sum(Menuitems.quantity).label("count"),
#        )
#        .filter(
#            Menuitems.date == fiscal_dates["start_day"],
#            or_(
#                Menuitems.menuitem == "Unassigned",
#                Menuitems.category == "Unassigned",
#            ),
#        )
#        .group_by(Menuitems.name, Menuitems.menuitem, Menuitems.category)
#    ).all()
#    unassigned_sales = pd.DataFrame.from_records(query, columns=["store", "menuitem", "category", "amount", "quantity"])
#    unassigned_sales.sort_values(by=["amount"], ascending=False, inplace=True)

#    query = (
#        db.session.query(Purchases.name, Purchases.item)
#        .filter(
#            Purchases.date >= fiscal_dates["start_week"],
#            Purchases.item.regexp_match("^DO NOT USE*"),
#        )
#        .group_by(Purchases.name, Purchases.item)
#    ).all()
#    do_not_use = pd.DataFrame.from_records(query, columns=["store", "menuitem"])
#    do_not_use.sort_values(by=["store"], inplace=True)

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

    fiscal_dates = set_dates(session["date_selected"])
    form1 = DateForm()
    form3 = StoreForm()
    form4 = PotatoForm()
    form5 = LobsterForm()
    form6 = StoneForm()

    if form1.submit1.data and form1.validate():
        session["date_selected"] = form1.selectdate.data
        return redirect(url_for("home_blueprint.profile"))

    if form3.submit3.data and form3.validate():
        session["date_selected"] = fiscal_dates["start_day"]
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
    fiscal_dates = set_dates(datetime.date(datetime.now()))

    store = Restaurants.query.filter_by(id=store_id).first()

    load_times = pd.read_sql_table('potato_load_times', con=db.engine)
    pot_df = pd.DataFrame(columns=['time', 'in_time', 'out_time'])
    for num in [7, 14, 21, 28]:
        day_pot_sales = pd.DataFrame(columns=['time', 'in_time', 'out_time', 'quantity'])
        for index, row in load_times.iterrows():
            query = (
                db.session.query(func.sum(potato_sales.quantity).label("quantity"))
                .filter(
                    potato_sales.time.between(row['start_time'], row['stop_time']),
                    potato_sales.dow == fiscal_dates['dow'],
                    potato_sales.name == store.name,
                    potato_sales.date == TODAY - timedelta(days=num))
                ).all()
            day_pot_sales = pd.concat([day_pot_sales, pd.DataFrame({'time': [row['time']], 'in_time': [row['in_time']], 'out_time': [row['out_time']], 'quantity': [query[0][0]]})], ignore_index=True)
        pot_df = pot_df.merge(day_pot_sales, on=['time', 'in_time', 'out_time'], how='outer', suffixes=('', f'_{num}'))

    pot_df.fillna(0, inplace=True)
    pot_df.loc[:, "AVG"] = pot_df.mean(numeric_only=True, axis=1)
    pot_df.loc[:, "MEDIAN"] = pot_df.median(numeric_only=True, axis=1)
    pot_df.loc[:, "MAX"] = pot_df.max(numeric_only=True, axis=1)

    #out_times = pd.read_csv("/usr/local/share/potatochart.csv", usecols=["time", "in_time", "out_time"])
    #out_times = pd.read_sql_table('potato_load_times', con=db.engine, columns=["time", "in_time", "out_time"])
    #rotation = pot_df.merge(out_times, on="time", how="left")
    pot_df.loc["TOTALS"] = pot_df.sum(numeric_only=True)

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
    for k, v in pot_df.iterrows():
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
    fiscal_dates = set_dates(session["date_selected"])

    store = Restaurants.query.filter_by(id=store_id).first()

    live_lobster_avg_cost = get_item_avg_cost(
        "SEAFOOD Lobster Live Maine",
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
    fiscal_dates = set_dates(session["date_selected"])

    store = Restaurants.query.filter_by(id=store_id).first()

    stone_claw_avg_cost = get_item_avg_cost(
        "SEAFOOD Crab Stone Claws",
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


@blueprint.route("/users/", methods=["GET", "POST"])
@login_required
def users():

    user_list = get_user_list()
    # ask user to select directory to save file
#    file_path = filedialog.askdirectory()
#    # export user_list to csv file
#    with open(f"{file_path}/user_list.csv", "w", newline="") as file:
#        writer = csv.writer(file)
#        writer.writerow(["ID", "Email", "Active", "Confirmed", "Last Login", "Login Count"])
#        for row in user_list:
#            writer.writerow(row)
#
#    return redirect(url_for("home_blueprint.support"))


   # format pdf page
    pdf_date = TODAY.strftime("%A, %B-%d")
    pdf = FPDF()
    pdf.add_page()
    page_width = pdf.w - 2 * pdf.l_margin
    pdf.set_font("Times", "B", 14.0)
    pdf.cell(page_width, 0.0, "User Activity List", align="C")
    pdf.ln(5)
    pdf.cell(page_width, 0.0, pdf_date, align="C")
    pdf.ln(5)

    pdf.set_font("Courier", "", 12)
    col_width = page_width / 4
    id_width = page_width / 8
    pdf.ln(1)
    th = pdf.font_size + 1

    pdf.cell(col_width, th, str("Email"), border=1)
    pdf.cell(id_width, th, str("Active"), border=1)
    pdf.cell(col_width, th, str("Confirimed"), border=1)
    pdf.cell(col_width, th, str("Last Login"), border=1)
    pdf.cell(col_width, th, str("Login Count"), border=1)
    pdf.ln(th)

    for v in user_table:
        pdf.cell(col_width, th, str(v["email"]), border=1)
        pdf.cell(id_width, th, str(v["active"]), border=1)
        pdf.cell(col_width, th, str(v["confirmed_at"]), border=1)
        pdf.cell(col_width, th, str(v["last_login_at"]), border=1)
        pdf.cell(col_width, th, str(v["login_count"]), border=1)
        pdf.ln(th)

    pdf.ln(5)
    pdf.cell(page_width, 0.0, "- end of report -", align="C")

    return Response(
        pdf.output(dest="S").encode("latin-1"),
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment;filename=user_activity_report.pdf"},
    )
