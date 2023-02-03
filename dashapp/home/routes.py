# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import re
import json
import pandas as pd
from fpdf import FPDF
from flask.helpers import url_for
from flask_security.core import current_user
from flask_security.decorators import roles_accepted, login_required
from pandas.core.algorithms import isin
from flask import flash, render_template, session, redirect, url_for
from flask.wrappers import Response
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
        print(store_id)
        return redirect(url_for("home_blueprint.potato", store_id=store_id))

    if form5.submit5.data and form5.validate():
        store_id = form5.store.data.id
        print(store_id)
        return redirect(url_for("home_blueprint.lobster", store_id=store_id))

    if form6.submit6.data and form6.validate():
        store_id = form6.store.data.id
        print(store_id)
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

    daily_sales_list = get_chart_values(fiscal_dates["start_week"], fiscal_dates["end_day"], Calendar.date)
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
        print(store_id)
        return redirect(url_for("home_blueprint.lobster", store_id=store_id))

    if form6.submit6.data and form6.validate():
        store_id = form6.store.data.id
        print(store_id)
        return redirect(url_for("home_blueprint.stone", store_id=store_id))

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

    sales_day = get_sales(fiscal_dates["start_day"], fiscal_dates["start_day"], store.name)
    sales_day_ly = get_sales(fiscal_dates["start_day_ly"], fiscal_dates["start_day_ly"], store.name)
    sales_week = get_sales(fiscal_dates["start_week"], fiscal_dates["end_week"], store.name)
    sales_week_ly = get_sales(fiscal_dates["start_week_ly"], fiscal_dates["week_to_date_ly"], store.name)
    sales_period = get_sales(fiscal_dates["start_period"], fiscal_dates["end_period"], store.name)
    sales_period_ly = get_sales(fiscal_dates["start_period_ly"], fiscal_dates["period_to_date_ly"], store.name)
    sales_year = get_sales(fiscal_dates["start_year"], fiscal_dates["end_year"], store.name)
    sales_year_ly = get_sales(fiscal_dates["start_year_ly"], fiscal_dates["year_to_date_ly"], store.name)

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

    daily_sales_list = get_chart_values(fiscal_dates["start_week"], fiscal_dates["end_week"], Calendar.date)
    daily_sales_list_ly = get_chart_values(fiscal_dates["start_week_ly"], fiscal_dates["end_week_ly"], Calendar.date)
    weekly_sales_list = get_chart_values(fiscal_dates["start_period"], fiscal_dates["end_period"], Calendar.week)
    weekly_sales_list_ly = get_chart_values(
        fiscal_dates["start_period_ly"], fiscal_dates["end_period_ly"], Calendar.week
    )
    period_sales_list = get_chart_values(fiscal_dates["start_year"], fiscal_dates["end_year"], Calendar.period)
    period_sales_list_ly = get_chart_values(fiscal_dates["start_year_ly"], fiscal_dates["end_year_ly"], Calendar.period)

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

    stone_items = []
    sea_bass = []
    salmon = []
    feature = []

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

    #live_lobster_avg_cost = get_item_avg_cost(
    #    "SEAFOOD Lobster Live*",
    #    fiscal_dates["last_thirty"],
    #    fiscal_dates["start_day"],
    #    store_id,
    #)
    #with open("./lobster_items.json") as file:
    #    lobster_items = json.load(file)

    #stone_claw_avg_cost = get_item_avg_cost(
    #    "^(SEAFOOD Crab Stone Claw)",
    #    fiscal_dates["last_thirty"],
    #    fiscal_dates["start_day"],
    #    store_id,
    #)
    #with open("./stone_claw_items.json") as file:
    #    stone_items = json.load(file)

    #if concept == "steakhouse":
    #    # lobster_items = get_shellfish("SEAFOOD Lobster Live*")
    #    # stone_items = get_shellfish("^(SEAFOOD Crab Stone Claw)")
    #    sea_bass = get_fish("SEAFOOD Sea Bass Chilean")
    #    salmon = get_fish("SEAFOOD Sea Bass Chilean")

    #if concept == "casual":
    #    feature = get_fish("SEAFOOD Feature Fish")
    #    salmon = get_fish("^(SEAFOOD) (Salmon)$")

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
                db.session.query(Recipes).filter(Recipes.recipe == p["recipe"], Recipes.name == store.name).first()
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
        unit_sales = get_unit_sales(fiscal_dates["start_week_ly"], fiscal_dates["end_week_ly"], unit_list)
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
    df_begin["inv_cost"] = df_begin["amount"] / (df_begin["base_qty"] * df_begin["quantity"])
    df_begin.drop(columns=["quantity", "amount"], inplace=True)
    food_today = get_transactions_by_category("Food", fiscal_dates["start_week"], CURRENT_DATE, "AP Invoice")
    df_today = pd.DataFrame(food_today)
    df_today["current_cost"] = df_today["amount"] / (df_today["base_qty"] * df_today["quantity"])
    df_today.drop(columns=["UofM", "quantity", "amount", "base_qty", "base_uofm"], inplace=True)
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
    # current_supply_budget = supply_budget[fiscal_dates["period"] - 1]
    current_smallware_cost = smallware_cost_dol[fiscal_dates["period"] - 1]
    # current_smallware_budget = smallware_budget[fiscal_dates["period"] - 1]
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
        print(store_id)
        return redirect(url_for("home_blueprint.lobster", store_id=store_id))

    if form6.submit6.data and form6.validate():
        store_id = form6.store.data.id
        print(store_id)
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
        print(store_id)
        return redirect(url_for("home_blueprint.lobster", store_id=store_id))

    if form6.submit6.data and form6.validate():
        store_id = form6.store.data.id
        print(store_id)
        return redirect(url_for("home_blueprint.stone", store_id=store_id))

    if form9.submit9.data and form9.validate():
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
        print(store_id)
        return redirect(url_for("home_blueprint.lobster", store_id=store_id))

    if form6.submit6.data and form6.validate():
        store_id = form6.store.data.id
        print(store_id)
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
