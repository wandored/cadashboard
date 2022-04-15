# -*- encmding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import re
import pandas as pd
from fpdf import FPDF
from flask.helpers import url_for
from flask_security.decorators import roles_accepted
from dashapp.home import blueprint
from flask import flash, render_template, session, redirect, url_for
from flask.wrappers import Response
from dashapp.home.util import (
    find_day_with_sales,
    refresh_data,
    get_daily_sales,
    get_daily_labor,
    convert_uofm,
    update_recipe_costs,
    set_dates,
)
from flask_security import login_required, current_user
from datetime import datetime, timedelta
from dashapp.authentication.forms import (
    DateForm,
    StoreForm,
    UpdateForm,
    PotatoForm,
    RecipeForm,
)
from dashapp.authentication.models import (
    Ingredients,
    Menuitems,
    db,
    Calendar,
    Sales,
    Labor,
    Restaurants,
    Budgets,
    Transactions,
    Potatoes,
    Unitsofmeasure,
    Recipes,
)
from sqlalchemy import and_, or_, func


TODAY = datetime.date(datetime.now())
CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
YSTDAY = TODAY - timedelta(days=1)


@blueprint.route("/", methods=["GET", "POST"])
@blueprint.route("/index/", methods=["GET", "POST"])
@login_required
def index():

    if not "token" in session:
        session["token"] = YSTDAY.strftime("%Y-%m-%d")
        return redirect(url_for("home_blueprint.index"))

    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))

    # Check for no sales
    if not Sales.query.filter_by(date=fiscal_dates["start_day"]).first():
        session["token"] = find_day_with_sales(fiscal_dates["start_day"])
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
        store_id = form3.store.data.id

        return redirect(url_for("home_blueprint.store", store_id=store_id))

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

    values1 = get_chart_values(
        fiscal_dates["start_week"], fiscal_dates["end_week"], Calendar.date
    )
    values1_ly = get_chart_values(
        fiscal_dates["start_week_ly"], fiscal_dates["end_week_ly"], Calendar.date
    )

    values2 = get_chart_values(
        fiscal_dates["start_period"], fiscal_dates["end_period"], Calendar.week
    )
    values2_ly = get_chart_values(
        fiscal_dates["start_period_ly"], fiscal_dates["end_period_ly"], Calendar.week
    )

    values3 = get_chart_values(
        fiscal_dates["start_year"], fiscal_dates["end_year"], Calendar.period
    )
    values3_ly = get_chart_values(
        fiscal_dates["start_year_ly"], fiscal_dates["end_year_ly"], Calendar.period
    )

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
        db.session.query(Sales.name, func.sum(Sales.sales).label("total_sales"))
        .filter(Sales.date == fiscal_dates["start_day"])
        .group_by(Sales.name)
        .all()
    )

    sales_day_ly = (
        db.session.query(Sales.name, func.sum(Sales.sales).label("total_sales_ly"))
        .filter(Sales.date == fiscal_dates["start_day_ly"])
        .group_by(Sales.name)
        .all()
    )

    entree_count = (
        db.session.query(
            Menuitems.name,
            func.sum(Menuitems.quantity).label("guest_count"),
        )
        .filter(
            Menuitems.date == fiscal_dates["start_day"],
            Menuitems.menu_category.regexp_match("ENTREE*"),
        )
        .group_by(Menuitems.name)
        .all()
    )
    # replace ly with guest check average
    entree_count_ly = (
        db.session.query(
            Menuitems.name,
            func.sum(Menuitems.quantity).label("guest_count"),
        )
        .filter(
            Menuitems.date == fiscal_dates["start_day_ly"],
            Menuitems.menu_category.regexp_match("ENTREE*"),
        )
        .group_by(Menuitems.name)
        .all()
    )

    df_sales_day = pd.DataFrame.from_records(sales_day, columns=["name", "sales"])
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

    # List of stores to add ID so i can pass to other templates
    data = Restaurants.query.all()
    store_list = pd.DataFrame([x.as_dict() for x in data])
    daily_table = daily_table.merge(store_list, how="left")

    daily_table.set_index("name", inplace=True)

    # Grab top sales over last year before we add totals
    daily_table.fillna(0, inplace=True)
    daily_table["doly"] = daily_table.sales - daily_table.sales_ly
    daily_table["poly"] = (
        (daily_table.sales - daily_table.sales_ly) / daily_table.sales_ly * 100
    )
    daily_top = daily_table[["doly", "poly"]]
    daily_top = daily_top.nlargest(5, "poly", keep="all")

    # daily_table.loc["TOTALS"] = daily_table.sum(numeric_only=True)
    daily_table["check_avg"] = daily_table["sales"] / daily_table["guest_count"].astype(
        float
    )
    daily_table["labor_pct"] = daily_table.dollars / daily_table.sales
    daily_table["labor_pct_ly"] = daily_table.dollars_ly / daily_table.sales_ly
    daily_table.fillna(0, inplace=True)
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
    weekly_table.set_index("name", inplace=True)

    # Grab top sales over last year before we add totals
    weekly_table.fillna(0, inplace=True)
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
    period_table.set_index("name", inplace=True)

    # Grab top sales over last year before we add totals
    period_table.fillna(0, inplace=True)
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
    yearly_table.set_index("name", inplace=True)

    # Grab top sales over last year before we add totals
    yearly_table.fillna(0, inplace=True)
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
        title="CentraArchy",
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

    store = Restaurants.query.filter_by(id=store_id).first()
    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))

    if store_id in [4, 9, 11, 17, 16]:
        concept = "steakhouse"
    else:
        concept = "casual"

    data = Restaurants.query.all()
    store_list = pd.DataFrame([x.as_dict() for x in data])

    if not Sales.query.filter_by(
        date=fiscal_dates["start_day"], name=store.name
    ).first():
        session["token"] = find_day_with_sales(fiscal_dates["start_day"])
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
        store_id = form3.store.data.id
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    if form4.validate_on_submit():

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

    values1 = get_chart_values(
        fiscal_dates["start_week"], fiscal_dates["end_week"], Calendar.date
    )
    values1_ly = get_chart_values(
        fiscal_dates["start_week_ly"], fiscal_dates["end_week_ly"], Calendar.date
    )
    values2 = get_chart_values(
        fiscal_dates["start_period"], fiscal_dates["end_period"], Calendar.week
    )
    values2_ly = get_chart_values(
        fiscal_dates["start_period_ly"], fiscal_dates["end_period_ly"], Calendar.week
    )
    values3 = get_chart_values(
        fiscal_dates["start_year"], fiscal_dates["end_year"], Calendar.period
    )
    values3_ly = get_chart_values(
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

    def sales_labor_table(start, end):
        # Build sales and labor stats for the time period given

        food_sales = get_daily_sales(start, end, store.name, "FOOD")
        beer_sales = get_daily_sales(start, end, store.name, "BEER")
        liquor_sales = get_daily_sales(start, end, store.name, "LIQUOR")
        wine_sales = get_daily_sales(start, end, store.name, "WINE")
        gift_card_sales = get_daily_sales(start, end, store.name, "GIFT CARDS")

        sales_table = food_sales.merge(beer_sales)
        sales_table = sales_table.merge(liquor_sales)
        sales_table = sales_table.merge(wine_sales)
        sales_table = sales_table.merge(gift_card_sales, how="outer")
        sales_table.rename(
            columns={
                "FOOD": "food",
                "BEER": "beer",
                "LIQUOR": "liquor",
                "WINE": "wine",
                "GIFT CARDS": "gift_cards",
            },
            inplace=True,
        )
        sales_table.fillna(value=0, inplace=True)
        sales_table["alcohol_sales"] = (
            sales_table.beer + sales_table.liquor + sales_table.wine
        )
        sales_table["total_sales"] = sales_table.food + sales_table.alcohol_sales
        sales_table["net_sales"] = sales_table.total_sales + sales_table.gift_cards

        # Labor
        bar_labor = get_daily_labor(start, end, store.name, "Bar")
        host_labor = get_daily_labor(start, end, store.name, "Host")
        restaurant_labor = get_daily_labor(start, end, store.name, "Restaurant")
        kitchen_labor = get_daily_labor(start, end, store.name, "Kitchen")

        labor_table = bar_labor.merge(host_labor)
        labor_table = labor_table.merge(restaurant_labor)
        labor_table = labor_table.merge(kitchen_labor)
        labor_table.fillna(value=0, inplace=True)

        labor_table["Total_Labor"] = (
            labor_table.Bar
            + labor_table.Host
            + labor_table.Restaurant
            + labor_table.Kitchen
        )

        join_data = labor_table[
            [
                "Bar",
                "Host",
                "Restaurant",
                "Kitchen",
                "Total_Labor",
            ]
        ]
        _table = sales_table.join(join_data)
        _table["Labor_pct"] = _table.Total_Labor / _table.total_sales
        _table["Bar_pct"] = _table.Bar / (_table.alcohol_sales)
        _table["Host_pct"] = _table.Host / (_table.food)
        _table["Restaurant_pct"] = _table.Restaurant / (_table.food)
        _table["Kitchen_pct"] = _table.Kitchen / (_table.food)
        _table["name"] = store.name

        _table = _table.merge(store_list, how="left")
        totals = _table.sum()
        return totals

    weekly_totals = sales_labor_table(
        fiscal_dates["start_week"], fiscal_dates["end_week"]
    )
    period_totals = sales_labor_table(
        fiscal_dates["start_period"], fiscal_dates["end_period"]
    )

    lobster_items = []
    stone_items = []
    sea_bass = []
    salmon = []
    feature = []

    def get_shellfish(regex):

        lst = (
            db.session.query(Transactions.item)
            .filter(Transactions.item.regexp_match(regex))
            .group_by(Transactions.item)
        ).all()
        items = []
        for i in lst:
            cost = (
                db.session.query(
                    Transactions.item,
                    Transactions.date,
                    Transactions.debit,
                    Transactions.quantity,
                )
                .filter(
                    Transactions.item == i.item,
                    Transactions.store_id == store_id,
                    Transactions.type == "AP Invoice",
                )
                .order_by(Transactions.date.desc())
            ).first()
            if cost:
                row_dict = dict(cost)
                ext = re.findall(r"\d*\.?\d", i.item)
                if not ext:
                    ext = re.findall(r"\d{1,2}", i.item)
                size = float(ext[0])
                row_dict["size"] = size
                items.append(row_dict)
        return items

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

    if concept == "steakhouse":
        lobster_items = get_shellfish("SEAFOOD Lobster Live*")
        stone_items = get_shellfish("^(SEAFOOD Crab Stone Claw)")
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
                func.sum(Transactions.amount).label("costs"),
            )
            .select_from(Transactions)
            .join(Calendar, Calendar.date == Transactions.date)
            .group_by(Calendar.period)
            .order_by(Calendar.period)
            .filter(
                Transactions.date.between(start, end),
                Transactions.category2.in_(cat),
                Transactions.name == store.name,
            )
        )
        dol_lst = []
        pct_lst = []
        for v in query:
            amount = v.costs - v.credits
            dol_lst.append(amount)
        add_items = len(sales) - len(dol_lst)
        for i in range(0, add_items):
            dol_lst.append(0)
        for i in range(0, len(sales)):
            pct_lst.append(dol_lst[i] / sales[i])
        return dol_lst, pct_lst

    # TODO check for no purchases of supplies
    supply_cost_dol, supply_cost_pct = get_category_costs(
        fiscal_dates["start_year"],
        fiscal_dates["end_year"],
        values3,
        cat=[
            "Rest. Supplies",
            "Kitchen Supplies",
            "Cleaning Supplies",
            "Office Supplies",
            "Bar Supplies",
        ],
    )
    supply_cost_dol_ly, supply_cost_pct_ly = get_category_costs(
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
        values3_ly,
        cat=[
            "Rest. Supplies",
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
    smallware_cost_dol, smallware_cost_pct = get_category_costs(
        fiscal_dates["start_year"],
        fiscal_dates["end_year"],
        values3,
        cat=["China", "Silverware", "Glassware", "Smallwares"],
    )
    smallware_cost_dol_ly, smallware_cost_pct_ly = get_category_costs(
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
        values3_ly,
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

    current_supply_cost = supply_cost_dol[fiscal_dates["period"] - 1]
    current_supply_budget = supply_budget[fiscal_dates["period"] - 1]
    current_smallware_cost = smallware_cost_dol[fiscal_dates["period"] - 1]
    current_smallware_budget = smallware_budget[fiscal_dates["period"] - 1]

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
        values1=values1,
        values2=values2,
        values3=values3,
        values1_ly=values1_ly,
        values2_ly=values2_ly,
        values3_ly=values3_ly,
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
        weekly_totals=weekly_totals,
        period_totals=period_totals,
        lobster_items=lobster_items,
        stone_items=stone_items,
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
        store_id = form3.store.data.id
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    # Gift Card Sales

    def get_giftcard_values(start, end, time):
        chart = (
            db.session.query(func.sum(Menuitems.amount).label("sales"))
            .select_from(Menuitems)
            .join(Calendar, Calendar.date == Menuitems.date)
            .group_by(time)
            .order_by(time)
            .filter(
                Menuitems.date.between(start, end),
                Menuitems.menuitem.regexp_match("(?i)GIFT CARD*"),
            )
        )
        value = []
        for v in chart:
            value.append(int(v.sales))

        return value

    giftcard_values1 = get_giftcard_values(
        fiscal_dates["start_year"], fiscal_dates["end_year"], Calendar.period
    )
    giftcard_values2 = get_giftcard_values(
        fiscal_dates["start_year_ly"], fiscal_dates["end_year_ly"], Calendar.period
    )

    def get_giftcard_sales(start, end):
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

    gift_card_sales = get_giftcard_sales(
        fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    gift_card_sales_ly = get_giftcard_sales(
        fiscal_dates["start_year_ly"], fiscal_dates["year_to_date"]
    )
    gift_card_sales = gift_card_sales.merge(gift_card_sales_ly, on="store")

    def get_lent_values(start, end, time):
        chart = (
            db.session.query(func.sum(Menuitems.quantity).label("count"))
            .select_from(Menuitems)
            .join(Calendar, Calendar.date == Menuitems.date)
            .group_by(time)
            .order_by(time)
            .filter(
                Menuitems.date.between(start, end),
                or_(
                    Menuitems.menuitem == "BLACKENED MAHI SANDWICH",
                    Menuitems.menuitem == "CRISPY FLOUNDER SANDWICH",
                ),
            )
        )
        value = []
        for v in chart:
            value.append(int(v.count))

        return value

    lent_values = get_lent_values(
        fiscal_dates["start_week"], fiscal_dates["end_week"], Calendar.date
    )

    query = (
        db.session.query(
            Menuitems.name,
            func.sum(Menuitems.quantity).label("count"),
            func.sum(Menuitems.amount).label("sales"),
        )
        .filter(
            Menuitems.date.between("2022-03-02", "2022-04-17"),
            or_(
                Menuitems.menuitem == "BLACKENED MAHI SANDWICH",
                Menuitems.menuitem == "CRISPY FLOUNDER SANDWICH",
            ),
        )
        .group_by(Menuitems.name)
    ).all()
    lent_sales = pd.DataFrame.from_records(query, columns=["store", "count", "sales"])
    lent_sales.sort_values(by=["count"], ascending=False, inplace=True)

    def get_fishfry_values(store, start, end, time):
        chart = (
            db.session.query(func.sum(Menuitems.quantity).label("count"))
            .select_from(Menuitems)
            .join(Calendar, Calendar.date == Menuitems.date)
            .group_by(time)
            .order_by(time)
            .filter(
                Menuitems.date.between(start, end),
                Menuitems.menuitem.regexp_match("FISH FRYDAY"),
                Menuitems.name == store,
            )
        )
        value = []
        for v in chart:
            value.append(int(v.count))

        return value

    fishfry_values1 = get_fishfry_values(
        "GULFSTREAM CAFE", "2022-03-02", "2022-04-17", Calendar.week
    )
    fishfry_values2 = get_fishfry_values(
        "CAROLINA ROADHOUSE", "2022-03-02", "2022-04-17", Calendar.week
    )

    fish_fry = (
        db.session.query(
            Menuitems.name,
            func.sum(Menuitems.quantity).label("count"),
            func.sum(Menuitems.amount).label("sales"),
        )
        .filter(
            Menuitems.date.between("2022-03-02", "2022-04-17"),
            Menuitems.menuitem.regexp_match("FISH FRYDAY"),
        )
        .group_by(Menuitems.name)
    ).all()
    fish_fryday = pd.DataFrame.from_records(
        fish_fry, columns=["store", "count", "sales"]
    )

    return render_template(
        "home/marketing.html",
        title="Marketing",
        segment="marketing",
        fiscal_dates=fiscal_dates,
        form1=form1,
        form3=form3,
        current_user=current_user,
        roles=current_user.roles,
        gift_card_sales=gift_card_sales,
        giftcard_values1=giftcard_values1,
        giftcard_values2=giftcard_values2,
        lent_sales=lent_sales,
        lent_values=lent_values,
        fish_fryday=fish_fryday,
        fishfry_values1=fishfry_values1,
        fishfry_values2=fishfry_values2,
    )


@blueprint.route("/purchasing/", methods=["GET", "POST"])
@login_required
def purchasing():

    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))

    # Get list of Restaurants
    data = Restaurants.query.all()
    store_list = pd.DataFrame([x.as_dict() for x in data])

    form1 = DateForm()
    form3 = StoreForm()

    if form1.submit1.data and form1.validate():
        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
        session["token"] = new_day
        return redirect(url_for("home_blueprint.purchasing"))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        store_id = form3.store.data.id
        return redirect(url_for("home_blueprint.store", store_id=store_id))

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

    def get_purchases(regex, days):

        items = (
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
                Transactions.date >= days,
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
        for i in items:
            qty, uofm = convert_uofm(i)
            # TODO fix the factor calc on purchasing
            pound = qty / 16
            row_dict = dict(i)
            row_dict["factor"] = pound
            item_list.append(row_dict)
        df = pd.DataFrame(item_list)
        if not df.empty:
            df = df[(df != 0).all(1)]
            df.dropna(axis=0, how="any", subset=["company"], inplace=True)
            df["cost_lb"] = df["cost"] / (df["count"] * df["factor"]).astype(float)
            df.sort_values(by=["date"], ascending=False, inplace=True)
        return df

    lobster_vendor = get_vendors("SEAFOOD Lobster Live*", fiscal_dates["last_seven"])
    lobster_df = get_purchases("SEAFOOD Lobster Live*", fiscal_dates["last_seven"])

    stone_vendor = get_vendors("^(SEAFOOD Crab Stone Claw)", fiscal_dates["last_seven"])
    stone_df = get_purchases("^(SEAFOOD Crab Stone Claw)", fiscal_dates["last_seven"])

    special_vendor = get_vendors("SEAFOOD Crabmeat Special", fiscal_dates["last_seven"])
    special_df = get_purchases("SEAFOOD Crabmeat Special", fiscal_dates["last_seven"])

    backfin_vendor = get_vendors("SEAFOOD Crabmeat Backfin", fiscal_dates["last_seven"])
    backfin_df = get_purchases("SEAFOOD Crabmeat Backfin", fiscal_dates["last_seven"])

    premium_vendor = get_vendors("SEAFOOD Crabmeat Premium", fiscal_dates["last_seven"])
    premium_df = get_purchases("SEAFOOD Crabmeat Premium", fiscal_dates["last_seven"])

    colossal_vendor = get_vendors(
        "SEAFOOD Crabmeat Colossal", fiscal_dates["last_seven"]
    )
    colossal_df = get_purchases("SEAFOOD Crabmeat Colossal", fiscal_dates["last_seven"])

    seabass_vendor = get_vendors("SEAFOOD Sea Bass Chilean", fiscal_dates["last_seven"])
    seabass_df = get_purchases("SEAFOOD Sea Bass Chilean", fiscal_dates["last_seven"])

    salmon_vendor = get_vendors("^(SEAFOOD) (Salmon)$", fiscal_dates["last_seven"])
    salmon_df = get_purchases("^(SEAFOOD) (Salmon)$", fiscal_dates["last_seven"])

    feature_vendor = get_vendors("SEAFOOD Feature Fish", fiscal_dates["last_seven"])
    feature_df = get_purchases("SEAFOOD Feature Fish", fiscal_dates["last_seven"])

    shrimp10_vendor = get_vendors(
        "SEAFOOD Shrimp U/10 White Headless", fiscal_dates["last_seven"]
    )
    shrimp10_df = get_purchases(
        "SEAFOOD Shrimp U/10 White Headless", fiscal_dates["last_seven"]
    )

    def period_purchases(regex, start, end):
        calendar = Calendar.query.with_entities(
            Calendar.date, Calendar.week, Calendar.period, Calendar.year
        ).all()
        cal_df = pd.DataFrame(calendar, columns=["date", "week", "period", "year"])

        items = (
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
        for i in items:
            if not i.UofM:
                continue
            qty, uofm = convert_uofm(i)
            # TODO fix the factor calc on purchasing
            pound = qty / 16.0
            row_dict = dict(i)
            row_dict["factor"] = pound
            item_list.append(row_dict)
        df = pd.DataFrame(item_list)
        df = df[(df != 0).all(1)]
        df["pounds"] = df["count"] * df["factor"]
        df = df.merge(cal_df, on="date", how="left")
        df = df.groupby(["period"]).sum()
        df["cost_lb"] = df["cost"] / df["pounds"]
        df_list = df["cost_lb"].tolist()
        return df_list

    prime_chart = period_purchases(
        "^(BEEF Steak).*(Prime)$", fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    prime_chart_ly = period_purchases(
        "^(BEEF Steak).*(Prime)$",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )

    choice_chart = period_purchases(
        "^(BEEF Steak).*(Choice)$", fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    choice_chart_ly = period_purchases(
        "^(BEEF Steak).*(Choice)$",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )

    prime_rib_chart = period_purchases(
        "BEEF Prime Rib Choice", fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    prime_rib_chart_ly = period_purchases(
        "BEEF Prime Rib Choice",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )

    crabmeat_chart = period_purchases(
        "SEAFOOD Crabmeat*", fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    crabmeat_chart_ly = period_purchases(
        "SEAFOOD Crabmeat*", fiscal_dates["start_year_ly"], fiscal_dates["end_year_ly"]
    )

    salmon_chart = period_purchases(
        "^(SEAFOOD) (Salmon)$", fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    salmon_chart_ly = period_purchases(
        "^(SEAFOOD) (Salmon)$",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )

    seabass_chart = period_purchases(
        "SEAFOOD Sea Bass Chilean", fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    seabass_chart_ly = period_purchases(
        "SEAFOOD Sea Bass Chilean",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )

    return render_template(
        "home/purchasing.html",
        title="Purchasing",
        segment="purchasing",
        fiscal_dates=fiscal_dates,
        form1=form1,
        form3=form3,
        current_user=current_user,
        lobster_df=lobster_df,
        lobster_vendor=lobster_vendor,
        stone_vendor=stone_vendor,
        stone_df=stone_df,
        special_df=special_df,
        special_vendor=special_vendor,
        backfin_df=backfin_df,
        backfin_vendor=backfin_vendor,
        premium_df=premium_df,
        premium_vendor=premium_vendor,
        colossal_df=colossal_df,
        colossal_vendor=colossal_vendor,
        seabass_vendor=seabass_vendor,
        seabass_df=seabass_df,
        salmon_vendor=salmon_vendor,
        salmon_df=salmon_df,
        shrimp10_vendor=shrimp10_vendor,
        shrimp10_df=shrimp10_df,
        feature_vendor=feature_vendor,
        feature_df=feature_df,
        prime_chart=prime_chart,
        prime_chart_ly=prime_chart_ly,
        choice_chart=choice_chart,
        choice_chart_ly=choice_chart_ly,
        prime_rib_chart=prime_rib_chart,
        prime_rib_chart_ly=prime_rib_chart_ly,
        crabmeat_chart=crabmeat_chart,
        crabmeat_chart_ly=crabmeat_chart_ly,
        salmon_chart=salmon_chart,
        salmon_chart_ly=salmon_chart_ly,
        seabass_chart=seabass_chart,
        seabass_chart_ly=seabass_chart_ly,
    )


@blueprint.route("/support/", methods=["GET", "POST"])
@login_required
@roles_accepted("admin")
def support():

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
        store_id = form3.store.data.id

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

    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))

    form1 = DateForm()
    form3 = StoreForm()

    if form1.submit1.data and form1.validate():
        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
        session["token"] = new_day
        return redirect(url_for("home_blueprint.alcohol"))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        store_id = form3.store.data.id
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
                Transactions.category2 == cat,
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
                Transactions.category2 == cat,
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

    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))
    form1 = DateForm()
    form3 = StoreForm()

    if form1.submit1.data and form1.validate():
        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
        session["token"] = new_day
        return redirect(url_for("home_blueprint.profile"))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        store_id = form3.store.data.id
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    return render_template(
        "home/profile.html",
        title="Profile",
        segment="profile",
        fiscal_dates=fiscal_dates,
        form1=form1,
        form3=form3,
    )


@blueprint.route("/<int:store_id>/potato/", methods=["GET", "POST"])
@login_required
def potato(store_id):

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
    pot_df.loc[:, "AVG"] = pot_df.mean(axis=1)
    pot_df.loc[:, "MEDIAN"] = pot_df.median(axis=1)
    pot_df.loc[:, "MAX"] = pot_df.max(axis=1)
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
