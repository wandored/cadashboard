# -*- encmding: utf-8 -*-
"""
routes for purchasing pages
"""

import pandas as pd
from pandas.core.algorithms import isin
from datetime import datetime, timedelta
from fpdf import FPDF
from sqlalchemy import and_, or_, func
from flask import flash, render_template, session, redirect, url_for
from flask.helpers import url_for
from flask_security.decorators import roles_accepted
from flask.wrappers import Response
from flask_security import login_required, current_user
from dashapp.purchasing import blueprint
from dashapp.purchasing.util import *
from dashapp.config import Config
from dashapp.authentication.forms import *
from dashapp.authentication.models import *


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

    store_list = (4, 9, 11, 16, 17)
    # store_list = (3, 5, 6, 10, 12, 13, 14, 15, 18)
    # store_list = (2)

    food_list = ["Beef", "Food Other", "Dairy", "Pork", "Poultry", "Produce", "Fish"]
    top_ten = get_category_topten(
        food_list,
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )
    print(top_ten)

    category_costs = get_category_costs(
        food_list,
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )
    print(category_costs)
    category_items = category_costs["Account"].tolist()
    category_values = category_costs["Totals"].tolist()
    print(category_values)

    category_costs.replace("Fish", "Seafood", inplace=True)
    category_costs.set_index("Account", inplace=True)

    top_ten_vendor = get_vendor_topten(
        food_list,
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )
    category_costs_total = category_costs["Totals"].sum()
    top_ten["percent"] = top_ten["Cost"] / category_costs_total
    top_ten_vendor["percent"] = top_ten_vendor["Cost"] / category_costs_total

    return render_template(
        "purchasing/purchasing.html",
        title="Purchasing",
        company_name=Config.COMPANY_NAME,
        segment="purchasing",
        **locals(),
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
        return redirect(url_for("purchasing_blueprint.beef"))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        store_id = form3.store.data.id
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    # store_list = (4, 9, 11, 16, 17)
    store_list = (3, 5, 6, 10, 12, 13, 14, 15, 18)
    # store_list = (2)

    top_ten = get_category_topten(
        ["Beef"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )
    top_ten_restaurant = get_restaurant_topten(
        ["Beef"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )
    top_ten_vendor = get_vendor_topten(
        ["Beef"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )

    category_costs = get_category_costs(
        ["Beef"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )
    category_costs_total = category_costs["Totals"].sum()
    top_ten["percent"] = top_ten["Cost"] / category_costs_total
    top_ten_vendor["percent"] = top_ten_vendor["Cost"] / category_costs_total

    # Create charts for items in top ten list
    product_list = top_ten["Item"].tolist()
    product_dict_ty = {}
    product_dict_ly = {}
    store_cost_dict = {}
    vendor_cost_dict = {}
    x = 1
    product_names = []
    for pl in product_list:
        this_year = period_purchases(
            "^({})$".format(pl),
            fiscal_dates["start_year"],
            fiscal_dates["end_year"],
            store_list,
        )
        del this_year[fiscal_dates["period"] :]  # remove zeros from future periods
        last_year = period_purchases(
            "^({})$".format(pl),
            fiscal_dates["start_year_ly"],
            fiscal_dates["end_year_ly"],
            store_list,
        )
        product_dict_ty["{}".format(x)] = this_year
        product_dict_ly["{}".format(x)] = last_year
        product_names.append(pl)

        store_cost_dict["{}".format(x)] = get_cost_per_store(
            "^({})$".format(pl),
            fiscal_dates["start_period"],
            store_list,
        )

        vendor_cost_dict["{}".format(x)] = get_cost_per_vendor(
            "^({})$".format(pl),
            fiscal_dates["start_period"],
            store_list,
        )
        x = x + 1

    return render_template(
        "purchasing/beef.html",
        title="Beef",
        company_name=Config.COMPANY_NAME,
        segment="purchasing",
        **locals(),
    )


@blueprint.route("/purchasing/dairy", methods=["GET", "POST"])
@login_required
def dairy():

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
        return redirect(url_for("purchasing_blueprint.dairy"))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        store_id = form3.store.data.id
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    store_list = (4, 9, 11, 16, 17)
    # store_list = (3, 5, 6, 10, 12, 13, 14, 15, 18)
    # store_list = (2)

    top_ten = get_category_topten(
        ["Dairy"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )
    top_ten_restaurant = get_restaurant_topten(
        ["Dairy"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )
    top_ten_vendor = get_vendor_topten(
        ["Dairy"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )

    category_costs = get_category_costs(
        ["Dairy"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )
    category_costs_total = category_costs["Totals"].sum()
    top_ten["percent"] = top_ten["Cost"] / category_costs_total
    top_ten_vendor["percent"] = top_ten_vendor["Cost"] / category_costs_total

    # Create charts for items in top ten list
    product_list = top_ten["Item"].tolist()
    product_dict_ty = {}
    product_dict_ly = {}
    store_cost_dict = {}
    vendor_cost_dict = {}
    x = 1
    product_names = []
    for pl in product_list:
        this_year = period_purchases(
            "^({})$".format(pl),
            fiscal_dates["start_year"],
            fiscal_dates["end_year"],
            store_list,
        )
        del this_year[fiscal_dates["period"] :]  # remove zeros from future periods
        last_year = period_purchases(
            "^({})$".format(pl),
            fiscal_dates["start_year_ly"],
            fiscal_dates["end_year_ly"],
            store_list,
        )
        product_dict_ty["{}".format(x)] = this_year
        product_dict_ly["{}".format(x)] = last_year
        product_names.append(pl)

        store_cost_dict["{}".format(x)] = get_cost_per_store(
            "^({})$".format(pl),
            fiscal_dates["start_period"],
            store_list,
        )

        vendor_cost_dict["{}".format(x)] = get_cost_per_vendor(
            "^({})$".format(pl),
            fiscal_dates["start_period"],
            store_list,
        )
        x = x + 1

    return render_template(
        "purchasing/dairy.html",
        title="Dairy",
        company_name=Config.COMPANY_NAME,
        segment="purchasing",
        **locals(),
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

    store_list = (4, 9, 11, 16, 17)
    # store_list = (3, 5, 6, 10, 12, 13, 14, 15, 18)
    # store_list = (2)

    top_ten = get_category_topten(
        ["Poultry"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )
    top_ten_restaurant = get_restaurant_topten(
        ["Poultry"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )
    top_ten_vendor = get_vendor_topten(
        ["Poultry"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )

    category_costs = get_category_costs(
        ["Poultry"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )
    category_costs_total = category_costs["Totals"].sum()
    top_ten["percent"] = top_ten["Cost"] / category_costs_total
    top_ten_vendor["percent"] = top_ten_vendor["Cost"] / category_costs_total

    # Create charts for items in top ten list
    product_list = top_ten["Item"].tolist()
    product_dict_ty = {}
    product_dict_ly = {}
    store_cost_dict = {}
    vendor_cost_dict = {}
    x = 1
    product_names = []
    for pl in product_list:
        this_year = period_purchases(
            "^({})$".format(pl),
            fiscal_dates["start_year"],
            fiscal_dates["end_year"],
            store_list,
        )
        del this_year[fiscal_dates["period"] :]  # remove zeros from future periods
        last_year = period_purchases(
            "^({})$".format(pl),
            fiscal_dates["start_year_ly"],
            fiscal_dates["end_year_ly"],
            store_list,
        )
        product_dict_ty["{}".format(x)] = this_year
        product_dict_ly["{}".format(x)] = last_year
        product_names.append(pl)

        store_cost_dict["{}".format(x)] = get_cost_per_store(
            "^({})$".format(pl),
            fiscal_dates["start_period"],
            store_list,
        )

        vendor_cost_dict["{}".format(x)] = get_cost_per_vendor(
            "^({})$".format(pl),
            fiscal_dates["start_period"],
            store_list,
        )
        x = x + 1

    return render_template(
        "purchasing/poultry.html",
        title="Poultry",
        company_name=Config.COMPANY_NAME,
        segment="purchasing",
        **locals(),
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

    store_list = (11, 16, 17)
    # store_list = (3, 5, 6, 10, 12, 13, 14, 15, 18)
    # store_list = (2)

    top_ten = get_category_topten(
        ["Fish"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )
    top_ten_restaurant = get_restaurant_topten(
        ["Fish"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )
    top_ten_vendor = get_vendor_topten(
        ["Fish"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )

    category_costs = get_category_costs(
        ["Fish"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )
    category_costs_total = category_costs["Totals"].sum()
    top_ten["percent"] = top_ten["Cost"] / category_costs_total
    top_ten_vendor["percent"] = top_ten_vendor["Cost"] / category_costs_total

    # Create charts for items in top ten list
    product_list = top_ten["Item"].tolist()
    product_dict_ty = {}
    product_dict_ly = {}
    store_cost_dict = {}
    vendor_cost_dict = {}
    x = 1
    product_names = []
    for pl in product_list:
        this_year = period_purchases(
            "^({})$".format(pl),
            fiscal_dates["start_year"],
            fiscal_dates["end_year"],
            store_list,
        )
        del this_year[fiscal_dates["period"] :]
        last_year = period_purchases(
            "^({})$".format(pl),
            fiscal_dates["start_year_ly"],
            fiscal_dates["end_year_ly"],
            store_list,
        )
        product_dict_ty["{}".format(x)] = this_year
        product_dict_ly["{}".format(x)] = last_year
        product_names.append(pl)

        store_cost_dict["{}".format(x)] = get_cost_per_store(
            "^({})$".format(pl),
            fiscal_dates["start_period"],
            store_list,
        )

        vendor_cost_dict["{}".format(x)] = get_cost_per_vendor(
            "^({})$".format(pl),
            fiscal_dates["start_period"],
            store_list,
        )
        x = x + 1

    return render_template(
        "purchasing/seafood.html",
        title="Seafood",
        company_name=Config.COMPANY_NAME,
        segment="purchasing",
        **locals(),
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

    store_list = (4, 9, 11, 16, 17)
    # store_list = (3, 5, 6, 10, 12, 13, 14, 15, 18)
    # store_list = (2)

    top_ten = get_category_topten(
        ["Pork"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )
    top_ten_restaurant = get_restaurant_topten(
        ["Pork"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )
    top_ten_vendor = get_vendor_topten(
        ["Pork"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )

    category_costs = get_category_costs(
        ["Pork"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )
    category_costs_total = category_costs["Totals"].sum()
    top_ten["percent"] = top_ten["Cost"] / category_costs_total
    top_ten_vendor["percent"] = top_ten_vendor["Cost"] / category_costs_total

    # Create charts for items in top ten list
    product_list = top_ten["Item"].tolist()
    product_dict_ty = {}
    product_dict_ly = {}
    store_cost_dict = {}
    vendor_cost_dict = {}
    x = 1
    product_names = []
    for pl in product_list:
        this_year = period_purchases(
            "^({})$".format(pl),
            fiscal_dates["start_year"],
            fiscal_dates["end_year"],
            store_list,
        )
        del this_year[fiscal_dates["period"] :]
        last_year = period_purchases(
            "^({})$".format(pl),
            fiscal_dates["start_year_ly"],
            fiscal_dates["end_year_ly"],
            store_list,
        )
        product_dict_ty["{}".format(x)] = this_year
        product_dict_ly["{}".format(x)] = last_year
        product_names.append(pl)

        store_cost_dict["{}".format(x)] = get_cost_per_store(
            "^({})$".format(pl),
            fiscal_dates["start_period"],
            store_list,
        )

        vendor_cost_dict["{}".format(x)] = get_cost_per_vendor(
            "^({})$".format(pl),
            fiscal_dates["start_period"],
            store_list,
        )
        x = x + 1

    return render_template(
        "purchasing/pork.html",
        title="Pork",
        company_name=Config.COMPANY_NAME,
        segment="purchasing",
        **locals(),
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

    store_list = (11, 16, 17)
    # store_list = (3, 5, 6, 10, 12, 13, 14, 15, 18)
    # store_list = (2)

    top_ten = get_category_topten(
        ["Produce"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )
    top_ten_restaurant = get_restaurant_topten(
        ["Produce"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )
    top_ten_vendor = get_vendor_topten(
        ["Produce"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )

    category_costs = get_category_costs(
        ["Produce"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )
    category_costs_total = category_costs["Totals"].sum()
    top_ten["percent"] = top_ten["Cost"] / category_costs_total
    top_ten_vendor["percent"] = top_ten_vendor["Cost"] / category_costs_total

    # Create charts for items in top ten list
    product_list = top_ten["Item"].tolist()
    product_dict_ty = {}
    product_dict_ly = {}
    store_cost_dict = {}
    vendor_cost_dict = {}
    x = 1
    product_names = []
    for pl in product_list:
        this_year = period_purchases(
            "^({})$".format(pl),
            fiscal_dates["start_year"],
            fiscal_dates["end_year"],
            store_list,
        )
        del this_year[fiscal_dates["period"] :]
        last_year = period_purchases(
            "^({})$".format(pl),
            fiscal_dates["start_year_ly"],
            fiscal_dates["end_year_ly"],
            store_list,
        )
        product_dict_ty["{}".format(x)] = this_year
        product_dict_ly["{}".format(x)] = last_year
        product_names.append(pl)

        store_cost_dict["{}".format(x)] = get_cost_per_store(
            "^({})$".format(pl),
            fiscal_dates["start_period"],
            store_list,
        )

        vendor_cost_dict["{}".format(x)] = get_cost_per_vendor(
            "^({})$".format(pl),
            fiscal_dates["start_period"],
            store_list,
        )
        x = x + 1

    return render_template(
        "purchasing/produce.html",
        title="Produce",
        company_name=Config.COMPANY_NAME,
        segment="purchasing",
        **locals(),
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

    # store_list = (4, 9, 11, 16, 17)
    # store_list = (3, 5, 6, 10, 12, 13, 14, 15, 18)
    store_list = (4, 9)

    top_ten = get_category_topten(
        ["Food Other"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )
    top_ten_restaurant = get_restaurant_topten(
        ["Food Other"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )
    top_ten_vendor = get_vendor_topten(
        ["Food Other"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )

    category_costs = get_category_costs(
        ["Food Other"],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        store_list,
    )
    category_costs_total = category_costs["Totals"].sum()
    top_ten["percent"] = top_ten["Cost"] / category_costs_total
    top_ten_vendor["percent"] = top_ten_vendor["Cost"] / category_costs_total

    # Create charts for items in top ten list
    product_list = top_ten["Item"].tolist()
    product_dict_ty = {}
    product_dict_ly = {}
    store_cost_dict = {}
    vendor_cost_dict = {}
    x = 1
    product_names = []
    for pl in product_list:
        this_year = period_purchases(
            "^({})$".format(pl),
            fiscal_dates["start_year"],
            fiscal_dates["end_year"],
            store_list,
        )
        del this_year[fiscal_dates["period"] :]
        last_year = period_purchases(
            "^({})$".format(pl),
            fiscal_dates["start_year_ly"],
            fiscal_dates["end_year_ly"],
            store_list,
        )
        product_dict_ty["{}".format(x)] = this_year
        product_dict_ly["{}".format(x)] = last_year
        product_names.append(pl)

        store_cost_dict["{}".format(x)] = get_cost_per_store(
            "^({})$".format(pl),
            fiscal_dates["start_period"],
            store_list,
        )

        vendor_cost_dict["{}".format(x)] = get_cost_per_vendor(
            "^({})$".format(pl),
            fiscal_dates["start_period"],
            store_list,
        )
        x = x + 1

    return render_template(
        "purchasing/foodother.html",
        title="Food Other",
        company_name=Config.COMPANY_NAME,
        segment="purchasing",
        **locals(),
    )
