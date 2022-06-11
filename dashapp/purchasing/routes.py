# -*- encmding: utf-8 -*-
"""
routes for purchasing pages
"""

import pandas as pd
from fpdf import FPDF
from flask.helpers import url_for
from flask_security.decorators import roles_accepted
from pandas.core.algorithms import isin
from dashapp.purchasing import blueprint
from flask import flash, render_template, session, redirect, url_for
from flask.wrappers import Response
from dashapp.purchasing.util import *
from dashapp.config import Config
from flask_security import login_required, current_user
from datetime import datetime, timedelta
from dashapp.authentication.forms import *
from dashapp.authentication.models import *
from sqlalchemy import and_, or_, func


@blueprint.route("/purchasing/", methods=["GET", "POST"])
@login_required
def purchasing():

    TODAY = datetime.date(datetime.now())
    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
    YSTDAY = TODAY - timedelta(days=1)

    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))

    # Get list of Restaurants
    data = Restaurants.query.all()
    store_df = pd.DataFrame([x.as_dict() for x in data])

    form1 = DateForm()
    form3 = StoreForm()

    if form1.submit1.data and form1.validate():
        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
        session["token"] = new_day
        return redirect(url_for("purchasing_blueprint.purchasing"))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        store_id = form3.store.data.id
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    food_list = ["Beef", "Food Other", "Pork", "Poultry", "Produce", "Fish"]
    top_ten_food = get_category_topten(
        food_list,
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_food_items = top_ten_food["Item"].tolist()
    top_ten_food_values = top_ten_food["Cost"].tolist()

    food_category_costs = get_category_costs(
        food_list,
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )

    non_food_list = [
        "Restaurant Supplies",
        "Kitchen Supplies",
        "Cleaning Supplies",
        "Office Supplies",
        "Catering Supplies/Expense",
        "Bar Supplies" "Smallware",
        "China",
        "Silverware",
        "Glassware",
    ]
    non_food_category_costs = get_category_costs(
        non_food_list,
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )

    # supply_list = [
    #    "Restaurant Supplies",
    #    "Kitchen Supplies",
    #    "Cleaning Supplies",
    #    "Office Supplies",
    #    "Catering Supplies/Expense",
    #    "Bar Supplies"
    # ]
    # top_ten_supply = get_category_topten(
    #    food_list,
    #    fiscal_dates['last_thirty'],
    #    fiscal_dates['start_day'],
    # )
    # top_ten_supply_items = top_ten_supply['Item'].tolist()
    # top_ten_supply_values = top_ten_supply['Cost'].tolist()

    # smallware_list = [
    #    "Smallware",
    #    "China",
    #    "Silverware",
    #    "Glassware",
    # ]
    # top_ten_smallware = get_category_topten(
    #    food_list,
    #    fiscal_dates['last_thirty'],
    #    fiscal_dates['start_day'],
    # )
    # top_ten_smallware_items = top_ten_smallware['Item'].tolist()
    # top_ten_smallware_values = top_ten_smallware['Cost'].tolist()

    # TODO refactor with **locals() in render_template

    return render_template(
        "purchasing/purchasing.html",
        title="Purchasing",
        company_name=Config.COMPANY_NAME,
        segment="purchasing",
        fiscal_dates=fiscal_dates,
        form1=form1,
        form3=form3,
        current_user=current_user,
        top_ten=top_ten_food,
        top_ten_items=top_ten_food_items,
        top_ten_values=top_ten_food_values,
        # top_ten_supply=top_ten_supply,
        # top_ten_supply_items=top_ten_supply_items,
        # top_ten_supply_values=top_ten_supply_values,
        food_category_costs=food_category_costs,
        non_food_category_costs=non_food_category_costs,
    )


@blueprint.route("/purchasing/beef", methods=["GET", "POST"])
@login_required
def beef():

    TODAY = datetime.date(datetime.now())
    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
    YSTDAY = TODAY - timedelta(days=1)

    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))

    # Get list of Restaurants
    data = Restaurants.query.all()
    store_df = pd.DataFrame([x.as_dict() for x in data])

    form1 = DateForm()
    form3 = StoreForm()

    if form1.submit1.data and form1.validate():
        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
        session["token"] = new_day
        return redirect(url_for("home_blueprint.beef"))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        store_id = form3.store.data.id
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    # Prime Steak data
    top_ten_prime = get_item_topten(
        "^(BEEF Steak).*(Prime)$",
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    prime_chart = period_purchases(
        "^(BEEF Steak).*(Prime)$", fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    prime_chart_ly = period_purchases(
        "^(BEEF Steak).*(Prime)$",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )

    # Choice Steak data
    top_ten_choice = get_item_topten(
        "^(BEEF Steak).*(Choice)$",
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    choice_chart = period_purchases(
        "^(BEEF Steak).*(Choice)$", fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    choice_chart_ly = period_purchases(
        "^(BEEF Steak).*(Choice)$",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )

    # Prime rib data
    prime_rib_chart = period_purchases(
        "BEEF Prime Rib Choice", fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    prime_rib_df = get_cost_per_vendor(
        "BEEF Prime Rib Choice", fiscal_dates["last_thirty"]
    )
    prime_rib_chart_ly = period_purchases(
        "BEEF Prime Rib Choice",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )

    return render_template(
        "purchasing/beef.html",
        title="Beef",
        company_name=Config.COMPANY_NAME,
        segment="purchasing",
        fiscal_dates=fiscal_dates,
        form1=form1,
        form3=form3,
        current_user=current_user,
        prime_chart=prime_chart,
        prime_chart_ly=prime_chart_ly,
        choice_chart=choice_chart,
        choice_chart_ly=choice_chart_ly,
        prime_rib_df=prime_rib_df,
        prime_rib_chart=prime_rib_chart,
        prime_rib_chart_ly=prime_rib_chart_ly,
        top_ten_choice=top_ten_choice,
        top_ten_prime=top_ten_prime,
    )


@blueprint.route("/purchasing/poultry", methods=["GET", "POST"])
@login_required
def poultry():

    TODAY = datetime.date(datetime.now())
    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
    YSTDAY = TODAY - timedelta(days=1)

    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))

    # Get list of Restaurants
    data = Restaurants.query.all()
    store_df = pd.DataFrame([x.as_dict() for x in data])

    form1 = DateForm()
    form3 = StoreForm()

    if form1.submit1.data and form1.validate():
        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
        session["token"] = new_day
        return redirect(url_for("purchasing_blueprint.poultry"))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        store_id = form3.store.data.id
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    top_ten = get_category_topten(
        ["Poultry"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_items = top_ten["Item"].tolist()
    top_ten_values = top_ten["Cost"].tolist()

    return render_template(
        "purchasing/poultry.html",
        title="Poultry",
        company_name=Config.COMPANY_NAME,
        segment="purchasing",
        fiscal_dates=fiscal_dates,
        form1=form1,
        form3=form3,
        current_user=current_user,
        top_ten=top_ten,
        top_ten_items=top_ten_items,
        top_ten_values=top_ten_values,
    )


@blueprint.route("/purchasing/seafood", methods=["GET", "POST"])
@login_required
def seafood():

    TODAY = datetime.date(datetime.now())
    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
    YSTDAY = TODAY - timedelta(days=1)

    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))

    # Get list of Restaurants
    data = Restaurants.query.all()
    store_df = pd.DataFrame([x.as_dict() for x in data])

    form1 = DateForm()
    form3 = StoreForm()

    if form1.submit1.data and form1.validate():
        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
        session["token"] = new_day
        return redirect(url_for("purchasing_blueprint.seafood"))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        store_id = form3.store.data.id
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    top_ten = get_category_topten(
        ["Fish"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_items = top_ten["Item"].tolist()
    top_ten_values = top_ten["Cost"].tolist()

    lobster_live_df = get_cost_per_vendor(
        "SEAFOOD Lobster Live*", fiscal_dates["last_thirty"]
    )
    lobster_tail_df = get_cost_per_vendor(
        "SEAFOOD Lobster Tail*", fiscal_dates["last_thirty"]
    )

    stone_df = get_cost_per_vendor(
        "^(SEAFOOD Crab Stone Claw)", fiscal_dates["last_thirty"]
    )

    special_df = get_cost_per_vendor(
        "SEAFOOD Crabmeat Special", fiscal_dates["last_thirty"]
    )
    backfin_df = get_cost_per_vendor(
        "SEAFOOD Crabmeat Backfin", fiscal_dates["last_thirty"]
    )
    premium_df = get_cost_per_vendor(
        "SEAFOOD Crabmeat Premium", fiscal_dates["last_thirty"]
    )
    colossal_df = get_cost_per_vendor(
        "SEAFOOD Crabmeat Colossal", fiscal_dates["last_thirty"]
    )

    seabass_df = get_cost_per_vendor(
        "SEAFOOD Sea Bass Chilean", fiscal_dates["last_thirty"]
    )
    salmon_df = get_cost_per_vendor("^(SEAFOOD) (Salmon)$", fiscal_dates["last_thirty"])
    feature_df = get_cost_per_vendor(
        "SEAFOOD Feature Fish", fiscal_dates["last_thirty"]
    )

    shrimp10_df = get_cost_per_vendor(
        "SEAFOOD Shrimp U/10 White Headless", fiscal_dates["last_thirty"]
    )
    shrimp3135_df = get_cost_per_vendor(
        "SEAFOOD Shrimp 31/35 Butterfly", fiscal_dates["last_thirty"]
    )
    shrimp5160_df = get_cost_per_vendor(
        "SEAFOOD Shrimp 51/60 P&D", fiscal_dates["last_thirty"]
    )
    shrimp2630_df = get_cost_per_vendor(
        "SEAFOOD Shrimp 26/30 P&D", fiscal_dates["last_thirty"]
    )

    special_crabmeat_chart = period_purchases(
        "SEAFOOD Crabmeat Special*",
        fiscal_dates["start_year"],
        fiscal_dates["end_year"],
    )
    special_crabmeat_chart_ly = period_purchases(
        "SEAFOOD Crabmeat Special*",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )
    backfin_crabmeat_chart = period_purchases(
        "SEAFOOD Crabmeat Backfin*",
        fiscal_dates["start_year"],
        fiscal_dates["end_year"],
    )
    backfin_crabmeat_chart_ly = period_purchases(
        "SEAFOOD Crabmeat Backfin*",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )
    premium_crabmeat_chart = period_purchases(
        "SEAFOOD Crabmeat Premium*",
        fiscal_dates["start_year"],
        fiscal_dates["end_year"],
    )
    premium_crabmeat_chart_ly = period_purchases(
        "SEAFOOD Crabmeat Premium*",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )
    colossal_crabmeat_chart = period_purchases(
        "SEAFOOD Crabmeat Colossal*",
        fiscal_dates["start_year"],
        fiscal_dates["end_year"],
    )
    colossal_crabmeat_chart_ly = period_purchases(
        "SEAFOOD Crabmeat Colossal*",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
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
    feature_fish_chart = period_purchases(
        "SEAFOOD Feature Fish", fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    feature_fish_chart_ly = period_purchases(
        "SEAFOOD Feature Fish",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )
    lobster_live_chart = period_purchases(
        "SEAFOOD Lobster Live*", fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    lobster_live_chart_ly = period_purchases(
        "SEAFOOD Lobster Live*",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )
    lobster_tail_chart = period_purchases(
        "SEAFOOD Lobster Tail*", fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    lobster_tail_chart_ly = period_purchases(
        "SEAFOOD Lobster Tail*",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )
    stone_chart = period_purchases(
        "SEAFOOD Crab Stone Claw*", fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    # this mess is for the stone crab offseason to add zeors to the chart
    if 5 < fiscal_dates["period"]:
        if fiscal_dates["period"] > 10:
            dd = 10
        else:
            dd = fiscal_dates["period"]
        for ii in range(5, dd):
            stone_chart[ii:ii] = [0]

    stone_chart_ly = period_purchases(
        "SEAFOOD Crab Stone Claw*",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )
    off_season = [0, 0, 0, 0, 0]
    stone_chart_ly[5:5] = off_season
    shrimp10_chart = period_purchases(
        "SEAFOOD Shrimp U/10*", fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    shrimp10_chart_ly = period_purchases(
        "SEAFOOD Shrimp U/10*",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )
    shrimp3135_chart = period_purchases(
        "SEAFOOD Shrimp 31/35*", fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    shrimp3135_chart_ly = period_purchases(
        "SEAFOOD Shrimp 31/35*",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )
    shrimp2630_chart = period_purchases(
        "SEAFOOD Shrimp 26/30*", fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    shrimp2630_chart_ly = period_purchases(
        "SEAFOOD Shrimp 26/30*",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )

    return render_template(
        "purchasing/seafood.html",
        title="Seafood",
        company_name=Config.COMPANY_NAME,
        segment="purchasing",
        fiscal_dates=fiscal_dates,
        form1=form1,
        form3=form3,
        current_user=current_user,
        lobster_live_df=lobster_live_df,
        lobster_live_chart=lobster_live_chart,
        lobster_live_chart_ly=lobster_live_chart_ly,
        lobster_tail_df=lobster_tail_df,
        lobster_tail_chart=lobster_tail_chart,
        lobster_tail_chart_ly=lobster_tail_chart_ly,
        stone_df=stone_df,
        stone_chart=stone_chart,
        stone_chart_ly=stone_chart_ly,
        special_df=special_df,
        special_crabmeat_chart=special_crabmeat_chart,
        special_crabmeat_chart_ly=special_crabmeat_chart_ly,
        backfin_df=backfin_df,
        backfin_crabmeat_chart=backfin_crabmeat_chart,
        backfin_crabmeat_chart_ly=backfin_crabmeat_chart_ly,
        premium_df=premium_df,
        premium_crabmeat_chart=premium_crabmeat_chart,
        premium_crabmeat_chart_ly=premium_crabmeat_chart_ly,
        colossal_df=colossal_df,
        colossal_crabmeat_chart=colossal_crabmeat_chart,
        colossal_crabmeat_chart_ly=colossal_crabmeat_chart_ly,
        seabass_df=seabass_df,
        seabass_chart=seabass_chart,
        seabass_chart_ly=seabass_chart_ly,
        salmon_df=salmon_df,
        salmon_chart=salmon_chart,
        salmon_chart_ly=salmon_chart_ly,
        shrimp10_df=shrimp10_df,
        shrimp10_chart=shrimp10_chart,
        shrimp10_chart_ly=shrimp10_chart_ly,
        shrimp3135_df=shrimp3135_df,
        shrimp3135_chart=shrimp3135_chart,
        shrimp3135_chart_ly=shrimp3135_chart_ly,
        shrimp2630_df=shrimp2630_df,
        shrimp2630_chart=shrimp2630_chart,
        shrimp2630_chart_ly=shrimp2630_chart_ly,
        feature_df=feature_df,
        feature_fish_chart=feature_fish_chart,
        feature_fish_chart_ly=feature_fish_chart_ly,
        top_ten=top_ten,
        top_ten_items=top_ten_items,
        top_ten_values=top_ten_values,
    )


@blueprint.route("/purchasing/pork", methods=["GET", "POST"])
@login_required
def pork():

    TODAY = datetime.date(datetime.now())
    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
    YSTDAY = TODAY - timedelta(days=1)

    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))

    # Get list of Restaurants
    data = Restaurants.query.all()
    store_df = pd.DataFrame([x.as_dict() for x in data])

    form1 = DateForm()
    form3 = StoreForm()

    if form1.submit1.data and form1.validate():
        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
        session["token"] = new_day
        return redirect(url_for("purchasing_blueprint.pork"))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        store_id = form3.store.data.id
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    top_ten = get_category_topten(
        ["Pork"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_items = top_ten["Item"].tolist()
    top_ten_values = top_ten["Cost"].tolist()

    return render_template(
        "purchasing/pork.html",
        title="pork",
        company_name=Config.COMPANY_NAME,
        segment="purchasing",
        fiscal_dates=fiscal_dates,
        form1=form1,
        form3=form3,
        current_user=current_user,
        top_ten=top_ten,
        top_ten_items=top_ten_items,
        top_ten_values=top_ten_values,
    )


@blueprint.route("/purchasing/produce", methods=["GET", "POST"])
@login_required
def produce():

    TODAY = datetime.date(datetime.now())
    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
    YSTDAY = TODAY - timedelta(days=1)

    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))

    # Get list of Restaurants
    data = Restaurants.query.all()
    store_df = pd.DataFrame([x.as_dict() for x in data])

    form1 = DateForm()
    form3 = StoreForm()

    if form1.submit1.data and form1.validate():
        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
        session["token"] = new_day
        return redirect(url_for("purchasing_blueprint.produce"))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        store_id = form3.store.data.id
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    top_ten = get_category_topten(
        ["Produce"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_items = top_ten["Item"].tolist()
    top_ten_values = top_ten["Cost"].tolist()

    return render_template(
        "purchasing/produce.html",
        title="Produce",
        company_name=Config.COMPANY_NAME,
        segment="purchasing",
        fiscal_dates=fiscal_dates,
        form1=form1,
        form3=form3,
        current_user=current_user,
        top_ten=top_ten,
        top_ten_items=top_ten_items,
        top_ten_values=top_ten_values,
    )


@blueprint.route("/purchasing/foodother", methods=["GET", "POST"])
@login_required
def foodother():

    TODAY = datetime.date(datetime.now())
    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
    YSTDAY = TODAY - timedelta(days=1)

    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))

    # Get list of Restaurants
    data = Restaurants.query.all()
    store_df = pd.DataFrame([x.as_dict() for x in data])

    form1 = DateForm()
    form3 = StoreForm()

    if form1.submit1.data and form1.validate():
        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
        session["token"] = new_day
        return redirect(url_for("purchasing_blueprint.foodother"))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        store_id = form3.store.data.id
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    top_ten = get_category_topten(
        ["Food Other"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_items = top_ten["Item"].tolist()
    top_ten_values = top_ten["Cost"].tolist()

    return render_template(
        "purchasing/foodother.html",
        title="Food Other",
        company_name=Config.COMPANY_NAME,
        segment="purchasing",
        fiscal_dates=fiscal_dates,
        form1=form1,
        form3=form3,
        current_user=current_user,
        top_ten=top_ten,
        top_ten_items=top_ten_items,
        top_ten_values=top_ten_values,
    )
