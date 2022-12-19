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
        data = form3.stores.data
        session["store_list"] = tuple([x.id for x in data])
        return redirect(url_for("purchasing_blueprint.purchasing"))

    food_list = ["Beef", "Food Other", "Dairy", "Pork", "Poultry", "Produce", "Fish"]
    top_ten = get_category_topten(
        food_list,
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        session["store_list"],
    )
    print(top_ten)

    category_costs = get_category_costs(
        food_list,
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        session["store_list"],
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
        session["store_list"],
    )
    category_costs_total = category_costs["Totals"].sum()
    top_ten["percent"] = top_ten["Cost"] / category_costs_total
    top_ten_vendor["percent"] = top_ten_vendor["Cost"] / category_costs_total

    # get name from Restaurants table based on session["store_list"]
    store_names = db.session.query(Restaurants.name).filter(Restaurants.id.in_(session["store_list"]))
    store_names = [x[0] for x in store_names]
    store_names = ", ".join(store_names)

    return render_template(
        "purchasing/purchasing.html",
        title="Purchasing",
        company_name=Config.COMPANY_NAME,
        segment="purchasing",
        **locals(),
    )


@blueprint.route("/purchasing/<product>", methods=["GET", "POST"])
@login_required
def beef(product):

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
        return redirect(url_for("purchasing_blueprint.beef", product=product))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        data = form3.stores.data
        session["store_list"] = tuple([x.id for x in data])
        return redirect(url_for("purchasing_blueprint.beef", product=product))

    top_ten = get_category_topten(
        [product],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        session["store_list"],
    )
    top_ten_restaurant = get_restaurant_topten(
        [product],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        session["store_list"],
    )
    top_ten_vendor = get_vendor_topten(
        [product],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        session["store_list"],
    )
    category_costs = get_category_costs(
        [product],
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        session["store_list"],
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
            session["store_list"],
        )
        del this_year[fiscal_dates["period"] :]  # remove zeros from future periods
        last_year = period_purchases(
            "^({})$".format(pl),
            fiscal_dates["start_year_ly"],
            fiscal_dates["end_year_ly"],
            session["store_list"],
        )
        product_dict_ty["{}".format(x)] = this_year
        product_dict_ly["{}".format(x)] = last_year
        product_names.append(pl)

        store_cost_dict["{}".format(x)] = get_cost_per_store(
            "^({})$".format(pl),
            fiscal_dates["start_period"],
            session["store_list"],
        )

        vendor_cost_dict["{}".format(x)] = get_cost_per_vendor(
            "^({})$".format(pl),
            fiscal_dates["start_period"],
            session["store_list"],
        )
        x = x + 1

    # assign color based on product value
    def color_assigner(product):
        switch={
            'Beef':'primary',
            'Dairy': 'info',
            'Food Other': 'secondary',
            'Pork': 'danger',
            'Poultry': 'warning',
            'Produce': 'success',
            'Fish': 'info',
            'Beer': 'warning',
            'Wine': 'danger',
            'Liquor': 'primary',
        }
        return switch.get(product, 'secondary')

    color = color_assigner(product)

    store_names = db.session.query(Restaurants.name).filter(Restaurants.id.in_(session["store_list"]))
    store_names = [x[0] for x in store_names]
    store_names = ", ".join(store_names)

    return render_template(
        "purchasing/beef.html",
        title=product,
        company_name=Config.COMPANY_NAME,
        segment="purchasing",
        **locals(),
    )


#@blueprint.route("/purchasing/dairy", methods=["GET", "POST"])
#@login_required
#def dairy():
#
#    TODAY = datetime.date(datetime.now())
#    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
#    YSTDAY = TODAY - timedelta(days=1)
#
#    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))
#
#    # Get list of Restaurants
#    data = Restaurants.query.all()
#    store_df = pd.DataFrame([x.as_dict() for x in data])
#
#    form1 = DateForm()
#    form3 = StoreForm()
#
#    if form1.submit1.data and form1.validate():
#        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
#        session["token"] = new_day
#        return redirect(url_for("purchasing_blueprint.dairy"))
#
#    if form3.submit3.data and form3.validate():
#        session["token"] = fiscal_dates["start_day"]
#        data = form3.stores.data
#        session["store_list"] = tuple([x.id for x in data])
#        return redirect(url_for("purchasing_blueprint.dairy"))
#
#    top_ten = get_category_topten(
#        ["Dairy"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    top_ten_restaurant = get_restaurant_topten(
#        ["Dairy"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    top_ten_vendor = get_vendor_topten(
#        ["Dairy"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#
#    category_costs = get_category_costs(
#        ["Dairy"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    category_costs_total = category_costs["Totals"].sum()
#    top_ten["percent"] = top_ten["Cost"] / category_costs_total
#    top_ten_vendor["percent"] = top_ten_vendor["Cost"] / category_costs_total
#
#    # Create charts for items in top ten list
#    product_list = top_ten["Item"].tolist()
#    product_dict_ty = {}
#    product_dict_ly = {}
#    store_cost_dict = {}
#    vendor_cost_dict = {}
#    x = 1
#    product_names = []
#    for pl in product_list:
#        this_year = period_purchases(
#            "^({})$".format(pl),
#            fiscal_dates["start_year"],
#            fiscal_dates["end_year"],
#            session["store_list"],
#        )
#        del this_year[fiscal_dates["period"] :]  # remove zeros from future periods
#        last_year = period_purchases(
#            "^({})$".format(pl),
#            fiscal_dates["start_year_ly"],
#            fiscal_dates["end_year_ly"],
#            session["store_list"],
#        )
#        product_dict_ty["{}".format(x)] = this_year
#        product_dict_ly["{}".format(x)] = last_year
#        product_names.append(pl)
#
#        store_cost_dict["{}".format(x)] = get_cost_per_store(
#            "^({})$".format(pl),
#            fiscal_dates["start_period"],
#            session["store_list"],
#        )
#
#        vendor_cost_dict["{}".format(x)] = get_cost_per_vendor(
#            "^({})$".format(pl),
#            fiscal_dates["start_period"],
#            session["store_list"],
#        )
#        x = x + 1
#
#    store_names = db.session.query(Restaurants.name).filter(Restaurants.id.in_(session["store_list"]))
#    store_names = [x[0] for x in store_names]
#    store_names = ", ".join(store_names)
#
#    return render_template(
#        "purchasing/beef.html",
#        title="Dairy",
#        company_name=Config.COMPANY_NAME,
#        segment="purchasing",
#        **locals(),
#    )
#
#
#@blueprint.route("/purchasing/poultry", methods=["GET", "POST"])
#@login_required
#def poultry():
#
#    TODAY = datetime.date(datetime.now())
#    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
#    YSTDAY = TODAY - timedelta(days=1)
#
#    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))
#
#    # Get list of Restaurants
#    data = Restaurants.query.all()
#    store_df = pd.DataFrame([x.as_dict() for x in data])
#
#    form1 = DateForm()
#    form3 = StoreForm()
#
#    if form1.submit1.data and form1.validate():
#        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
#        session["token"] = new_day
#        return redirect(url_for("purchasing_blueprint.poultry"))
#
#    if form3.submit3.data and form3.validate():
#        session["token"] = fiscal_dates["start_day"]
#        data = form3.stores.data
#        session["store_list"] = tuple([x.id for x in data])
#        return redirect(url_for("purchasing_blueprint.poultry"))
#
#    top_ten = get_category_topten(
#        ["Poultry"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    top_ten_restaurant = get_restaurant_topten(
#        ["Poultry"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    top_ten_vendor = get_vendor_topten(
#        ["Poultry"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#
#    category_costs = get_category_costs(
#        ["Poultry"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    category_costs_total = category_costs["Totals"].sum()
#    top_ten["percent"] = top_ten["Cost"] / category_costs_total
#    top_ten_vendor["percent"] = top_ten_vendor["Cost"] / category_costs_total
#
#    # Create charts for items in top ten list
#    product_list = top_ten["Item"].tolist()
#    product_dict_ty = {}
#    product_dict_ly = {}
#    store_cost_dict = {}
#    vendor_cost_dict = {}
#    x = 1
#    product_names = []
#    for pl in product_list:
#        this_year = period_purchases(
#            "^({})$".format(pl),
#            fiscal_dates["start_year"],
#            fiscal_dates["end_year"],
#            session["store_list"],
#        )
#        del this_year[fiscal_dates["period"] :]  # remove zeros from future periods
#        last_year = period_purchases(
#            "^({})$".format(pl),
#            fiscal_dates["start_year_ly"],
#            fiscal_dates["end_year_ly"],
#            session["store_list"],
#        )
#        product_dict_ty["{}".format(x)] = this_year
#        product_dict_ly["{}".format(x)] = last_year
#        product_names.append(pl)
#
#        store_cost_dict["{}".format(x)] = get_cost_per_store(
#            "^({})$".format(pl),
#            fiscal_dates["start_period"],
#            session["store_list"],
#        )
#
#        vendor_cost_dict["{}".format(x)] = get_cost_per_vendor(
#            "^({})$".format(pl),
#            fiscal_dates["start_period"],
#            session["store_list"],
#        )
#        x = x + 1
#
#    store_names = db.session.query(Restaurants.name).filter(Restaurants.id.in_(session["store_list"]))
#    store_names = [x[0] for x in store_names]
#    store_names = ", ".join(store_names)
#
#    return render_template(
#        "purchasing/beef.html",
#        title="Poultry",
#        company_name=Config.COMPANY_NAME,
#        segment="purchasing",
#        **locals(),
#    )
#
#
#@blueprint.route("/purchasing/seafood", methods=["GET", "POST"])
#@login_required
#def seafood():
#
#    TODAY = datetime.date(datetime.now())
#    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
#    YSTDAY = TODAY - timedelta(days=1)
#
#    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))
#
#    # Get list of Restaurants
#    data = Restaurants.query.all()
#    store_df = pd.DataFrame([x.as_dict() for x in data])
#
#    form1 = DateForm()
#    form3 = StoreForm()
#
#    if form1.submit1.data and form1.validate():
#        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
#        session["token"] = new_day
#        return redirect(url_for("purchasing_blueprint.seafood"))
#
#    if form3.submit3.data and form3.validate():
#        session["token"] = fiscal_dates["start_day"]
#        data = form3.stores.data
#        session["store_list"] = tuple([x.id for x in data])
#        return redirect(url_for("purchasing_blueprint.seafood"))
#
#    top_ten = get_category_topten(
#        ["Fish"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    top_ten_restaurant = get_restaurant_topten(
#        ["Fish"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    top_ten_vendor = get_vendor_topten(
#        ["Fish"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#
#    category_costs = get_category_costs(
#        ["Fish"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    category_costs_total = category_costs["Totals"].sum()
#    top_ten["percent"] = top_ten["Cost"] / category_costs_total
#    top_ten_vendor["percent"] = top_ten_vendor["Cost"] / category_costs_total
#
#    # Create charts for items in top ten list
#    product_list = top_ten["Item"].tolist()
#    product_dict_ty = {}
#    product_dict_ly = {}
#    store_cost_dict = {}
#    vendor_cost_dict = {}
#    x = 1
#    product_names = []
#    for pl in product_list:
#        this_year = period_purchases(
#            "^({})$".format(pl),
#            fiscal_dates["start_year"],
#            fiscal_dates["end_year"],
#            session["store_list"],
#        )
#        del this_year[fiscal_dates["period"] :]
#        last_year = period_purchases(
#            "^({})$".format(pl),
#            fiscal_dates["start_year_ly"],
#            fiscal_dates["end_year_ly"],
#            session["store_list"],
#        )
#        product_dict_ty["{}".format(x)] = this_year
#        product_dict_ly["{}".format(x)] = last_year
#        product_names.append(pl)
#
#        store_cost_dict["{}".format(x)] = get_cost_per_store(
#            "^({})$".format(pl),
#            fiscal_dates["start_period"],
#            session["store_list"],
#        )
#
#        vendor_cost_dict["{}".format(x)] = get_cost_per_vendor(
#            "^({})$".format(pl),
#            fiscal_dates["start_period"],
#            session["store_list"],
#        )
#        x = x + 1
#
#    store_names = db.session.query(Restaurants.name).filter(Restaurants.id.in_(session["store_list"]))
#    store_names = [x[0] for x in store_names]
#    store_names = ", ".join(store_names)
#
#    return render_template(
#        "purchasing/beef.html",
#        title="Seafood",
#        company_name=Config.COMPANY_NAME,
#        segment="purchasing",
#        **locals(),
#    )
#
#
#@blueprint.route("/purchasing/pork", methods=["GET", "POST"])
#@login_required
#def pork():
#
#    TODAY = datetime.date(datetime.now())
#    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
#    YSTDAY = TODAY - timedelta(days=1)
#
#    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))
#
#    # Get list of Restaurants
#    data = Restaurants.query.all()
#    store_df = pd.DataFrame([x.as_dict() for x in data])
#
#    form1 = DateForm()
#    form3 = StoreForm()
#
#    if form1.submit1.data and form1.validate():
#        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
#        session["token"] = new_day
#        return redirect(url_for("purchasing_blueprint.pork"))
#
#    if form3.submit3.data and form3.validate():
#        session["token"] = fiscal_dates["start_day"]
#        data = form3.stores.data
#        session["store_list"] = tuple([x.id for x in data])
#        return redirect(url_for("purchasing_blueprint.pork"))
#
#    top_ten = get_category_topten(
#        ["Pork"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    top_ten_restaurant = get_restaurant_topten(
#        ["Pork"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    top_ten_vendor = get_vendor_topten(
#        ["Pork"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#
#    category_costs = get_category_costs(
#        ["Pork"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    category_costs_total = category_costs["Totals"].sum()
#    top_ten["percent"] = top_ten["Cost"] / category_costs_total
#    top_ten_vendor["percent"] = top_ten_vendor["Cost"] / category_costs_total
#
#    # Create charts for items in top ten list
#    product_list = top_ten["Item"].tolist()
#    product_dict_ty = {}
#    product_dict_ly = {}
#    store_cost_dict = {}
#    vendor_cost_dict = {}
#    x = 1
#    product_names = []
#    for pl in product_list:
#        this_year = period_purchases(
#            "^({})$".format(pl),
#            fiscal_dates["start_year"],
#            fiscal_dates["end_year"],
#            session["store_list"],
#        )
#        del this_year[fiscal_dates["period"] :]
#        last_year = period_purchases(
#            "^({})$".format(pl),
#            fiscal_dates["start_year_ly"],
#            fiscal_dates["end_year_ly"],
#            session["store_list"],
#        )
#        product_dict_ty["{}".format(x)] = this_year
#        product_dict_ly["{}".format(x)] = last_year
#        product_names.append(pl)
#
#        store_cost_dict["{}".format(x)] = get_cost_per_store(
#            "^({})$".format(pl),
#            fiscal_dates["start_period"],
#            session["store_list"],
#        )
#
#        vendor_cost_dict["{}".format(x)] = get_cost_per_vendor(
#            "^({})$".format(pl),
#            fiscal_dates["start_period"],
#            session["store_list"],
#        )
#        x = x + 1
#
#    store_names = db.session.query(Restaurants.name).filter(Restaurants.id.in_(session["store_list"]))
#    store_names = [x[0] for x in store_names]
#    store_names = ", ".join(store_names)
#
#    return render_template(
#        "purchasing/beef.html",
#        title="Pork",
#        company_name=Config.COMPANY_NAME,
#        segment="purchasing",
#        **locals(),
#    )
#
#
#@blueprint.route("/purchasing/produce", methods=["GET", "POST"])
#@login_required
#def produce():
#
#    TODAY = datetime.date(datetime.now())
#    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
#    YSTDAY = TODAY - timedelta(days=1)
#
#    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))
#
#    # Get list of Restaurants
#    data = Restaurants.query.all()
#    store_df = pd.DataFrame([x.as_dict() for x in data])
#
#    form1 = DateForm()
#    form3 = StoreForm()
#
#    if form1.submit1.data and form1.validate():
#        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
#        session["token"] = new_day
#        return redirect(url_for("purchasing_blueprint.produce"))
#
#    if form3.submit3.data and form3.validate():
#        session["token"] = fiscal_dates["start_day"]
#        data = form3.stores.data
#        session["store_list"] = tuple([x.id for x in data])
#        return redirect(url_for("purchasing_blueprint.produce"))
#
#    top_ten = get_category_topten(
#        ["Produce"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    top_ten_restaurant = get_restaurant_topten(
#        ["Produce"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    top_ten_vendor = get_vendor_topten(
#        ["Produce"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#
#    category_costs = get_category_costs(
#        ["Produce"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    category_costs_total = category_costs["Totals"].sum()
#    top_ten["percent"] = top_ten["Cost"] / category_costs_total
#    top_ten_vendor["percent"] = top_ten_vendor["Cost"] / category_costs_total
#
#    # Create charts for items in top ten list
#    product_list = top_ten["Item"].tolist()
#    product_dict_ty = {}
#    product_dict_ly = {}
#    store_cost_dict = {}
#    vendor_cost_dict = {}
#    x = 1
#    product_names = []
#    for pl in product_list:
#        this_year = period_purchases(
#            "^({})$".format(pl),
#            fiscal_dates["start_year"],
#            fiscal_dates["end_year"],
#            session["store_list"],
#        )
#        del this_year[fiscal_dates["period"] :]
#        last_year = period_purchases(
#            "^({})$".format(pl),
#            fiscal_dates["start_year_ly"],
#            fiscal_dates["end_year_ly"],
#            session["store_list"],
#        )
#        product_dict_ty["{}".format(x)] = this_year
#        product_dict_ly["{}".format(x)] = last_year
#        product_names.append(pl)
#
#        store_cost_dict["{}".format(x)] = get_cost_per_store(
#            "^({})$".format(pl),
#            fiscal_dates["start_period"],
#            session["store_list"],
#        )
#
#        vendor_cost_dict["{}".format(x)] = get_cost_per_vendor(
#            "^({})$".format(pl),
#            fiscal_dates["start_period"],
#            session["store_list"],
#        )
#        x = x + 1
#
#    store_names = db.session.query(Restaurants.name).filter(Restaurants.id.in_(session["store_list"]))
#    store_names = [x[0] for x in store_names]
#    store_names = ", ".join(store_names)
#
#    return render_template(
#        "purchasing/beef.html",
#        title="Produce",
#        company_name=Config.COMPANY_NAME,
#        segment="purchasing",
#        **locals(),
#    )
#
#
#@blueprint.route("/purchasing/foodother", methods=["GET", "POST"])
#@login_required
#def foodother():
#
#    TODAY = datetime.date(datetime.now())
#    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
#    YSTDAY = TODAY - timedelta(days=1)
#
#    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))
#
#    # Get list of Restaurants
#    data = Restaurants.query.all()
#    store_df = pd.DataFrame([x.as_dict() for x in data])
#
#    form1 = DateForm()
#    form3 = StoreForm()
#
#    if form1.submit1.data and form1.validate():
#        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
#        session["token"] = new_day
#        return redirect(url_for("purchasing_blueprint.foodother"))
#
#    if form3.submit3.data and form3.validate():
#        session["token"] = fiscal_dates["start_day"]
#        data = form3.stores.data
#        session["store_list"] = tuple([x.id for x in data])
#        return redirect(url_for("purchasing_blueprint.foodother"))
#
#    top_ten = get_category_topten(
#        ["Food Other"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    top_ten_restaurant = get_restaurant_topten(
#        ["Food Other"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    top_ten_vendor = get_vendor_topten(
#        ["Food Other"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#
#    category_costs = get_category_costs(
#        ["Food Other"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    category_costs_total = category_costs["Totals"].sum()
#    top_ten["percent"] = top_ten["Cost"] / category_costs_total
#    top_ten_vendor["percent"] = top_ten_vendor["Cost"] / category_costs_total
#
#    # Create charts for items in top ten list
#    product_list = top_ten["Item"].tolist()
#    product_dict_ty = {}
#    product_dict_ly = {}
#    store_cost_dict = {}
#    vendor_cost_dict = {}
#    x = 1
#    product_names = []
#    for pl in product_list:
#        this_year = period_purchases(
#            "^({})$".format(pl),
#            fiscal_dates["start_year"],
#            fiscal_dates["end_year"],
#            session["store_list"],
#        )
#        del this_year[fiscal_dates["period"] :]
#        last_year = period_purchases(
#            "^({})$".format(pl),
#            fiscal_dates["start_year_ly"],
#            fiscal_dates["end_year_ly"],
#            session["store_list"],
#        )
#        product_dict_ty["{}".format(x)] = this_year
#        product_dict_ly["{}".format(x)] = last_year
#        product_names.append(pl)
#
#        store_cost_dict["{}".format(x)] = get_cost_per_store(
#            "^({})$".format(pl),
#            fiscal_dates["start_period"],
#            session["store_list"],
#        )
#
#        vendor_cost_dict["{}".format(x)] = get_cost_per_vendor(
#            "^({})$".format(pl),
#            fiscal_dates["start_period"],
#            session["store_list"],
#        )
#        x = x + 1
#
#    store_names = db.session.query(Restaurants.name).filter(Restaurants.id.in_(session["store_list"]))
#    store_names = [x[0] for x in store_names]
#    store_names = ", ".join(store_names)
#
#    return render_template(
#        "purchasing/beef.html",
#        title="Food Other",
#        company_name=Config.COMPANY_NAME,
#        segment="purchasing",
#        **locals(),
#    )
#
#
#@blueprint.route("/purchasing/beer", methods=["GET", "POST"])
#@login_required
#def beer():
#
#    TODAY = datetime.date(datetime.now())
#    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
#    YSTDAY = TODAY - timedelta(days=1)
#
#    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))
#
#    # Get list of Restaurants
#    data = Restaurants.query.all()
#    store_df = pd.DataFrame([x.as_dict() for x in data])
#
#    form1 = DateForm()
#    form3 = StoreForm()
#
#    if form1.submit1.data and form1.validate():
#        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
#        session["token"] = new_day
#        return redirect(url_for("purchasing_blueprint.beer"))
#
#    if form3.submit3.data and form3.validate():
#        session["token"] = fiscal_dates["start_day"]
#        data = form3.stores.data
#        session["store_list"] = tuple([x.id for x in data])
#        return redirect(url_for("purchasing_blueprint.beer"))
#
#    top_ten = get_category_topten(
#        ["Beer"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    top_ten_restaurant = get_restaurant_topten(
#        ["Beer"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    top_ten_vendor = get_vendor_topten(
#        ["Beer"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#
#    category_costs = get_category_costs(
#        ["Beer"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    category_costs_total = category_costs["Totals"].sum()
#    top_ten["percent"] = top_ten["Cost"] / category_costs_total
#    top_ten_vendor["percent"] = top_ten_vendor["Cost"] / category_costs_total
#
#    # Create charts for items in top ten list
#    product_list = top_ten["Item"].tolist()
#    product_dict_ty = {}
#    product_dict_ly = {}
#    store_cost_dict = {}
#    vendor_cost_dict = {}
#    x = 1
#    product_names = []
#    for pl in product_list:
#        this_year = period_purchases(
#            "^({})$".format(pl),
#            fiscal_dates["start_year"],
#            fiscal_dates["end_year"],
#            session["store_list"],
#        )
#        del this_year[fiscal_dates["period"] :]
#        last_year = period_purchases(
#            "^({})$".format(pl),
#            fiscal_dates["start_year_ly"],
#            fiscal_dates["end_year_ly"],
#            session["store_list"],
#        )
#        product_dict_ty["{}".format(x)] = this_year
#        product_dict_ly["{}".format(x)] = last_year
#        product_names.append(pl)
#
#        store_cost_dict["{}".format(x)] = get_cost_per_store(
#            "^({})$".format(pl),
#            fiscal_dates["start_period"],
#            session["store_list"],
#        )
#
#        vendor_cost_dict["{}".format(x)] = get_cost_per_vendor(
#            "^({})$".format(pl),
#            fiscal_dates["start_period"],
#            session["store_list"],
#        )
#        x = x + 1
#
#    store_names = db.session.query(Restaurants.name).filter(Restaurants.id.in_(session["store_list"]))
#    store_names = [x[0] for x in store_names]
#    store_names = ", ".join(store_names)
#
#    return render_template(
#        "purchasing/beef.html",
#        title="Beer",
#        company_name=Config.COMPANY_NAME,
#        segment="purchasing",
#        **locals(),
#    )
#
#
#@blueprint.route("/purchasing/wine", methods=["GET", "POST"])
#@login_required
#def wine():
#
#    TODAY = datetime.date(datetime.now())
#    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
#    YSTDAY = TODAY - timedelta(days=1)
#
#    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))
#
#    # Get list of Restaurants
#    data = Restaurants.query.all()
#    store_df = pd.DataFrame([x.as_dict() for x in data])
#
#    form1 = DateForm()
#    form3 = StoreForm()
#
#    if form1.submit1.data and form1.validate():
#        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
#        session["token"] = new_day
#        return redirect(url_for("purchasing_blueprint.wine"))
#
#    if form3.submit3.data and form3.validate():
#        session["token"] = fiscal_dates["start_day"]
#        data = form3.stores.data
#        session["store_list"] = tuple([x.id for x in data])
#        return redirect(url_for("purchasing_blueprint.wine"))
#
#    top_ten = get_category_topten(
#        ["Wine"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    top_ten_restaurant = get_restaurant_topten(
#        ["Wine"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    top_ten_vendor = get_vendor_topten(
#        ["Wine"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#
#    category_costs = get_category_costs(
#        ["Wine"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    category_costs_total = category_costs["Totals"].sum()
#    top_ten["percent"] = top_ten["Cost"] / category_costs_total
#    top_ten_vendor["percent"] = top_ten_vendor["Cost"] / category_costs_total
#
#    # Create charts for items in top ten list
#    product_list = top_ten["Item"].tolist()
#    product_dict_ty = {}
#    product_dict_ly = {}
#    store_cost_dict = {}
#    vendor_cost_dict = {}
#    x = 1
#    product_names = []
#    for pl in product_list:
#        this_year = period_purchases(
#            "^({})$".format(pl),
#            fiscal_dates["start_year"],
#            fiscal_dates["end_year"],
#            session["store_list"],
#        )
#        del this_year[fiscal_dates["period"] :]
#        last_year = period_purchases(
#            "^({})$".format(pl),
#            fiscal_dates["start_year_ly"],
#            fiscal_dates["end_year_ly"],
#            session["store_list"],
#        )
#        product_dict_ty["{}".format(x)] = this_year
#        product_dict_ly["{}".format(x)] = last_year
#        product_names.append(pl)
#
#        store_cost_dict["{}".format(x)] = get_cost_per_store(
#            "^({})$".format(pl),
#            fiscal_dates["start_period"],
#            session["store_list"],
#        )
#
#        vendor_cost_dict["{}".format(x)] = get_cost_per_vendor(
#            "^({})$".format(pl),
#            fiscal_dates["start_period"],
#            session["store_list"],
#        )
#        x = x + 1
#
#    store_names = db.session.query(Restaurants.name).filter(Restaurants.id.in_(session["store_list"]))
#    store_names = [x[0] for x in store_names]
#    store_names = ", ".join(store_names)
#
#    return render_template(
#        "purchasing/beef.html",
#        title="Wine",
#        company_name=Config.COMPANY_NAME,
#        segment="purchasing",
#        **locals(),
#    )
#
#
#@blueprint.route("/purchasing/liquor", methods=["GET", "POST"])
#@login_required
#def liquor():
#
#    TODAY = datetime.date(datetime.now())
#    CURRENT_DATE = TODAY.strftime("%Y-%m-%d")
#    YSTDAY = TODAY - timedelta(days=1)
#
#    fiscal_dates = set_dates(datetime.strptime(session["token"], "%Y-%m-%d"))
#
#    # Get list of Restaurants
#    data = Restaurants.query.all()
#    store_df = pd.DataFrame([x.as_dict() for x in data])
#
#    form1 = DateForm()
#    form3 = StoreForm()
#
#    if form1.submit1.data and form1.validate():
#        new_day = form1.selectdate.data.strftime("%Y-%m-%d")
#        session["token"] = new_day
#        return redirect(url_for("purchasing_blueprint.liquor"))
#
#    if form3.submit3.data and form3.validate():
#        session["token"] = fiscal_dates["start_day"]
#        data = form3.stores.data
#        session["store_list"] = tuple([x.id for x in data])
#        return redirect(url_for("purchasing_blueprint.liquor"))
#
#    top_ten = get_category_topten(
#        ["Liquor"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    top_ten_restaurant = get_restaurant_topten(
#        ["Liquor"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    top_ten_vendor = get_vendor_topten(
#        ["Liquor"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#
#    category_costs = get_category_costs(
#        ["Liquor"],
#        fiscal_dates["start_period"],
#        fiscal_dates["start_day"],
#        session["store_list"],
#    )
#    category_costs_total = category_costs["Totals"].sum()
#    top_ten["percent"] = top_ten["Cost"] / category_costs_total
#    top_ten_vendor["percent"] = top_ten_vendor["Cost"] / category_costs_total
#
#    # Create charts for items in top ten list
#    product_list = top_ten["Item"].tolist()
#    product_dict_ty = {}
#    product_dict_ly = {}
#    store_cost_dict = {}
#    vendor_cost_dict = {}
#    x = 1
#    product_names = []
#    for pl in product_list:
#        this_year = period_purchases(
#            "^({})$".format(pl),
#            fiscal_dates["start_year"],
#            fiscal_dates["end_year"],
#            session["store_list"],
#        )
#        del this_year[fiscal_dates["period"] :]
#        last_year = period_purchases(
#            "^({})$".format(pl),
#            fiscal_dates["start_year_ly"],
#            fiscal_dates["end_year_ly"],
#            session["store_list"],
#        )
#        product_dict_ty["{}".format(x)] = this_year
#        product_dict_ly["{}".format(x)] = last_year
#        product_names.append(pl)
#
#        store_cost_dict["{}".format(x)] = get_cost_per_store(
#            "^({})$".format(pl),
#            fiscal_dates["start_period"],
#            session["store_list"],
#        )
#
#        vendor_cost_dict["{}".format(x)] = get_cost_per_vendor(
#            "^({})$".format(pl),
#            fiscal_dates["start_period"],
#            session["store_list"],
#        )
#        x = x + 1
#
#    store_names = db.session.query(Restaurants.name).filter(Restaurants.id.in_(session["store_list"]))
#    store_names = [x[0] for x in store_names]
#    store_names = ", ".join(store_names)
#
#    return render_template(
#        "purchasing/beef.html",
#        title="Liquor",
#        company_name=Config.COMPANY_NAME,
#        segment="purchasing",
#        **locals(),
#    )
