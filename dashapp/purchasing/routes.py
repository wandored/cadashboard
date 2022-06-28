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
    top_ten = get_category_topten(
        food_list,
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )

    category_costs = get_category_costs(
        food_list,
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    category_items = category_costs["Account"].tolist()
    category_values = category_costs["Totals"].tolist()

    category_costs.replace("Fish", "Seafood", inplace=True)
    category_costs.set_index("Account", inplace=True)

    top_ten_vendor = get_vendor_topten(
        food_list,
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    category_costs_total = category_costs["Totals"].sum()
    top_ten['percent'] = top_ten['Cost'] / category_costs_total
    top_ten_vendor['percent'] = top_ten_vendor['Cost'] / category_costs_total

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
        top_ten=top_ten,
        category_items=category_items,
        category_values=category_values,
        top_ten_vendor=top_ten_vendor,
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
    del prime_chart[fiscal_dates["period"] :]
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
    del choice_chart[fiscal_dates["period"] :]
    choice_chart_ly = period_purchases(
        "^(BEEF Steak).*(Choice)$",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )

    # Prime rib data
    prime_rib_chart = period_purchases(
        "BEEF Prime Rib Choice", fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    del prime_rib_chart[fiscal_dates["period"] :]
    prime_rib_chart_ly = period_purchases(
        "BEEF Prime Rib Choice",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )
    prime_rib_store = get_cost_per_store(
        "BEEF Prime Rib Choice", fiscal_dates["last_seven"]
    )
    prime_rib_vendor = get_cost_per_vendor(
        "BEEF Prime Rib Choice", fiscal_dates["last_seven"]
    )

    short_rib_chart = period_purchases(
        "BEEF Ribs Short Choice", fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    del short_rib_chart[fiscal_dates["period"] :]
    short_rib_chart_ly = period_purchases(
        "BEEF Ribs Short Choice",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )
    short_rib_store = get_cost_per_store(
        "BEEF Ribs Short Choice", fiscal_dates["last_seven"]
    )
    short_rib_vendor = get_cost_per_vendor(
        "BEEF Ribs Short Choice", fiscal_dates["last_seven"]
    )

    prime_tenderloin_chart = period_purchases(
        "BEEF Tenderloin Whole Prime", fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    del prime_tenderloin_chart[fiscal_dates["period"] :]
    prime_tenderloin_chart_ly = period_purchases(
        "BEEF Tenderloin Whole Prime",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )
    prime_tenderloin_store = get_cost_per_store(
        "BEEF Tenderloin Whole Prime", fiscal_dates["last_seven"]
    )
    prime_tenderloin_vendor = get_cost_per_vendor(
        "BEEF Tenderloin Whole Prime", fiscal_dates["last_seven"]
    )

    choice_tenderloin_chart = period_purchases(
        "BEEF Tenderloin Whole Choice", fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    del choice_tenderloin_chart[fiscal_dates["period"] :]
    choice_tenderloin_chart_ly = period_purchases(
        "BEEF Tenderloin Whole Choice",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )
    choice_tenderloin_store = get_cost_per_store(
        "BEEF Tenderloin Whole Choice", fiscal_dates["last_seven"]
    )
    choice_tenderloin_vendor = get_cost_per_vendor(
        "BEEF Tenderloin Whole Choice", fiscal_dates["last_seven"]
    )

    corned_beef_chart = period_purchases(
        "BEEF Corned Beef", fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    del corned_beef_chart[fiscal_dates["period"] :]
    corned_beef_chart_ly = period_purchases(
        "BEEF Corned Beef",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )
    corned_beef_store = get_cost_per_store(
        "BEEF Corned Beef", fiscal_dates["last_seven"]
    )
    corned_beef_vendor = get_cost_per_vendor(
        "BEEF Corned Beef", fiscal_dates["last_seven"]
    )
    burger_patty_chart = period_purchases(
        "BEEF Patty Grnd Beef 8oz", fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    del burger_patty_chart[fiscal_dates["period"] :]
    burger_patty_chart_ly = period_purchases(
        "BEEF Patty Grnd Beef 8oz",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )
    burger_patty_store = get_cost_per_store(
        "BEEF Patty Grnd Beef 8oz", fiscal_dates["last_seven"]
    )
    burger_patty_vendor = get_cost_per_vendor(
        "BEEF Patty Grnd Beef 8oz", fiscal_dates["last_seven"]
    )

    return render_template(
        "purchasing/beef.html",
        title="Beef",
        company_name=Config.COMPANY_NAME,
        segment="purchasing",
        **locals(),

        #fiscal_dates=fiscal_dates,
        #form1=form1,
        #form3=form3,
        #current_user=current_user,
        #top_ten_prime=top_ten_prime,
        #prime_chart=prime_chart,
        #prime_chart_ly=prime_chart_ly,
        #top_ten_choice=top_ten_choice,
        #choice_chart=choice_chart,
        #choice_chart_ly=choice_chart_ly,
        #prime_rib_chart=prime_rib_chart,
        #prime_rib_chart_ly=prime_rib_chart_ly,
        #prime_rib_store=prime_rib_store,
        #prime_rib_vendor=prime_rib_vendor,
        #short_rib_chart=short_rib_chart,
        #short_rib_chart_ly=short_rib_chart_ly,
        #short_rib_store=short_rib_store,
        #short_rib_vendor=short_rib_vendor,
        #corned_beef_chart=corned_beef_chart,
        #corned_beef_chart_ly=corned_beef_chart_ly,
        #corned_beef_store=corned_beef_store,
        #corned_beef_vendor=corned_beef_vendor,
        #prime_tenderloin_chart=prime_tenderloin_chart,
        #prime_tenderloin_chart_ly=prime_tenderloin_chart_ly,
        #prime_tenderloin_store=prime_tenderloin_store,
        #prime_tenderloin_vendor=prime_tenderloin_vendor,
        #choice_tenderloin_chart=choice_tenderloin_chart,
        #choice_tenderloin_chart_ly=choice_tenderloin_chart_ly,
        #choice_tenderloin_store=choice_tenderloin_store,
        #choice_tenderloin_vendor=choice_tenderloin_vendor,
        #burger_patty_chart=burger_patty_chart,
        #burger_patty_chart_ly=burger_patty_chart_ly,
        #burger_patty_store=burger_patty_store,
        #burger_patty_vendor=burger_patty_vendor,
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
    top_ten_restaurant = get_restaurant_topten(
        ["Poultry"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_vendor = get_vendor_topten(
        ["Poultry"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )

    category_costs = get_category_costs(
        ["Poultry"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    category_costs_total = category_costs["Totals"].sum()
    top_ten['percent'] = top_ten['Cost'] / category_costs_total
    top_ten_vendor['percent'] = top_ten_vendor['Cost'] / category_costs_total

    # Create charts for items in top ten list
    product_list = top_ten["Item"].tolist()
    product_dict = {}
    store_cost_dict = {}
    vendor_cost_dict = {}
    x = 1
    product_names = []
    for pl in product_list:
        this_year = period_purchases(
            "^({})$".format(pl), fiscal_dates["start_year"], fiscal_dates["end_year"]
        )
        del this_year[fiscal_dates["period"] :]  # remove zeros from future periods
        last_year = period_purchases(
            "^({})$".format(pl), fiscal_dates["start_year_ly"], fiscal_dates["end_year_ly"]
        )
        product_dict["{}_ty".format(x)] = this_year
        product_dict["{}_ly".format(x)] = last_year
        product_names.append(pl)

        store_cost_dict["{}".format(x)] = get_cost_per_store(
            "^({})$".format(pl), fiscal_dates["last_seven"]
        )

        vendor_cost_dict["{}".format(x)] = get_cost_per_vendor(
            "^({})$".format(pl), fiscal_dates["last_seven"]
        )
        x = x + 1

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
        top_ten_restaurant=top_ten_restaurant,
        top_ten_vendor=top_ten_vendor,
        product_dict=product_dict,
        product_names=product_names,
        store_cost_dict=store_cost_dict,
        vendor_cost_dict=vendor_cost_dict,
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
    top_ten_restaurant = get_restaurant_topten(
        ["Fish"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_vendor = get_vendor_topten(
        ["Fish"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )

    category_costs = get_category_costs(
        ["Fish"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    category_costs_total = category_costs["Totals"].sum()
    top_ten['percent'] = top_ten['Cost'] / category_costs_total
    top_ten_vendor['percent'] = top_ten_vendor['Cost'] / category_costs_total

    # Create charts for items in top ten list
    product_list = top_ten["Item"].tolist()
    product_dict = {}
    store_cost_dict = {}
    vendor_cost_dict = {}
    x = 1
    product_names = []
    for pl in product_list:
        this_year = period_purchases(
            "^({})$".format(pl), fiscal_dates["start_year"], fiscal_dates["end_year"]
        )
        del this_year[fiscal_dates["period"] :]
        last_year = period_purchases(
            "^({})$".format(pl), fiscal_dates["start_year_ly"], fiscal_dates["end_year_ly"]
        )
        product_dict["{}_ty".format(x)] = this_year
        product_dict["{}_ly".format(x)] = last_year
        product_names.append(pl)

        store_cost_dict["{}".format(x)] = get_cost_per_store(
            "^({})$".format(pl), fiscal_dates["last_seven"]
        )

        vendor_cost_dict["{}".format(x)] = get_cost_per_vendor(
            "^({})$".format(pl), fiscal_dates["last_seven"]
        )
        x = x + 1

    return render_template(
        "purchasing/seafood.html",
        title="Seafood",
        company_name=Config.COMPANY_NAME,
        segment="purchasing",
        fiscal_dates=fiscal_dates,
        form1=form1,
        form3=form3,
        current_user=current_user,
        top_ten=top_ten,
        top_ten_vendor=top_ten_vendor,
        top_ten_restaurant=top_ten_restaurant,
        product_dict=product_dict,
        product_names=product_names,
        store_cost_dict=store_cost_dict,
        vendor_cost_dict=vendor_cost_dict,
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
    top_ten_restaurant = get_restaurant_topten(
        ["Pork"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_vendor = get_vendor_topten(
        ["Pork"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )

    category_costs = get_category_costs(
        ["Pork"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    category_costs_total = category_costs["Totals"].sum()
    top_ten['percent'] = top_ten['Cost'] / category_costs_total
    top_ten_vendor['percent'] = top_ten_vendor['Cost'] / category_costs_total

    # Create charts for items in top ten list
    product_list = top_ten["Item"].tolist()
    product_dict = {}
    store_cost_dict = {}
    vendor_cost_dict = {}
    x = 1
    product_names = []
    for pl in product_list:
        this_year = period_purchases(
            "^({})$".format(pl), fiscal_dates["start_year"], fiscal_dates["end_year"]
        )
        del this_year[fiscal_dates["period"] :]
        last_year = period_purchases(
            "^({})$".format(pl), fiscal_dates["start_year_ly"], fiscal_dates["end_year_ly"]
        )
        product_dict["{}_ty".format(x)] = this_year
        product_dict["{}_ly".format(x)] = last_year
        product_names.append(pl)

        store_cost_dict["{}".format(x)] = get_cost_per_store(
            "^({})$".format(pl), fiscal_dates["last_seven"]
        )

        vendor_cost_dict["{}".format(x)] = get_cost_per_vendor(
            "^({})$".format(pl), fiscal_dates["last_seven"]
        )
        x = x + 1

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
        top_ten_vendor=top_ten_vendor,
        top_ten_restaurant=top_ten_restaurant,
        product_dict=product_dict,
        product_names=product_names,
        store_cost_dict=store_cost_dict,
        vendor_cost_dict=vendor_cost_dict,
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
    top_ten_restaurant = get_restaurant_topten(
        ["Produce"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_vendor = get_vendor_topten(
        ["Produce"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )

    category_costs = get_category_costs(
        ["Produce"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    category_costs_total = category_costs["Totals"].sum()
    top_ten['percent'] = top_ten['Cost'] / category_costs_total
    top_ten_vendor['percent'] = top_ten_vendor['Cost'] / category_costs_total

    # Create charts for items in top ten list
    product_list = top_ten["Item"].tolist()
    product_dict = {}
    store_cost_dict = {}
    vendor_cost_dict = {}
    x = 1
    product_names = []
    for pl in product_list:
        this_year = period_purchases(
            "^({})$".format(pl), fiscal_dates["start_year"], fiscal_dates["end_year"]
        )
        del this_year[fiscal_dates["period"] :]
        last_year = period_purchases(
            "^({})$".format(pl), fiscal_dates["start_year_ly"], fiscal_dates["end_year_ly"]
        )
        product_dict["{}_ty".format(x)] = this_year
        product_dict["{}_ly".format(x)] = last_year
        product_names.append(pl)

        store_cost_dict["{}".format(x)] = get_cost_per_store(
            "^({})$".format(pl), fiscal_dates["last_seven"]
        )

        vendor_cost_dict["{}".format(x)] = get_cost_per_vendor(
            "^({})$".format(pl), fiscal_dates["last_seven"]
        )
        x = x + 1

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
        top_ten_vendor=top_ten_vendor,
        top_ten_restaurant=top_ten_restaurant,
        product_dict=product_dict,
        product_names=product_names,
        store_cost_dict=store_cost_dict,
        vendor_cost_dict=vendor_cost_dict,
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
    top_ten_restaurant = get_restaurant_topten(
        ["Food Other"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_vendor = get_vendor_topten(
        ["Food Other"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )

    category_costs = get_category_costs(
        ["Food Other"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    category_costs_total = category_costs["Totals"].sum()
    top_ten['percent'] = top_ten['Cost'] / category_costs_total
    top_ten_vendor['percent'] = top_ten_vendor['Cost'] / category_costs_total

    # Create charts for items in top ten list
    product_list = top_ten["Item"].tolist()
    product_dict = {}
    store_cost_dict = {}
    vendor_cost_dict = {}
    x = 1
    product_names = []
    for pl in product_list:
        this_year = period_purchases(
            "^({})$".format(pl), fiscal_dates["start_year"], fiscal_dates["end_year"]
        )
        del this_year[fiscal_dates["period"] :]
        last_year = period_purchases(
            "^({})$".format(pl), fiscal_dates["start_year_ly"], fiscal_dates["end_year_ly"]
        )
        product_dict["{}_ty".format(x)] = this_year
        product_dict["{}_ly".format(x)] = last_year
        product_names.append(pl)

        store_cost_dict["{}".format(x)] = get_cost_per_store(
            "^({})$".format(pl), fiscal_dates["last_seven"]
        )

        vendor_cost_dict["{}".format(x)] = get_cost_per_vendor(
            "^({})$".format(pl), fiscal_dates["last_seven"]
        )
        x = x + 1

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
        top_ten_vendor=top_ten_vendor,
        top_ten_restaurant=top_ten_restaurant,
        product_dict=product_dict,
        product_names=product_names,
        store_cost_dict=store_cost_dict,
        vendor_cost_dict=vendor_cost_dict,
    )
