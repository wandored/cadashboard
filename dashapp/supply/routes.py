# -*- encmding: utf-8 -*-
"""
routes for supplies pages
"""

import pandas as pd
from fpdf import FPDF
from flask.helpers import url_for
from flask_security.decorators import roles_accepted
from pandas.core.algorithms import isin
from dashapp.supply import blueprint
from flask import flash, render_template, session, redirect, url_for
from flask.wrappers import Response
from dashapp.purchasing.util import *
from dashapp.config import Config
from flask_security import login_required, current_user
from datetime import datetime, timedelta
from dashapp.authentication.forms import *
from dashapp.authentication.models import *
from sqlalchemy import and_, or_, func


@blueprint.route("/supplies/", methods=["GET", "POST"])
@login_required
def supplies():

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
        return redirect(url_for("supply_blueprint.supplies"))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        store_id = form3.store.data.id
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    nonfood_list = [
        "Restaurant Supplies",
        "Kitchen Supplies",
        "Cleaning Supplies",
        "Office Supplies",
        "Catering Supplies/Expense",
        "Bar Supplies",
        "Smallware",
        "China",
        "Silverware",
        "Glassware",
        "Linen"
    ]
    top_ten_supplies = get_category_topten(
        nonfood_list,
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )

    supply_category_costs = get_category_costs(
        nonfood_list,
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    # Sum supply_category_costs Totals
    supply_category_costs_total = supply_category_costs["Totals"].sum()
    supply_category_items = supply_category_costs["Account"].tolist()
    supply_category_values = supply_category_costs["Totals"].tolist()

    top_ten_vendor = get_vendor_topten(
        nonfood_list,
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_vendor['percent'] = top_ten_vendor['Cost'] / supply_category_costs_total

    # TODO refactor with **locals() in render_template

    return render_template(
        "purchasing/supplies.html",
        title="Supplies",
        company_name=Config.COMPANY_NAME,
        segment="supplies",
        fiscal_dates=fiscal_dates,
        form1=form1,
        form3=form3,
        current_user=current_user,
        top_ten_supplies=top_ten_supplies,
        supply_category_items=supply_category_items,
        supply_category_values=supply_category_values,
        top_ten_vendor=top_ten_vendor,
    )


@blueprint.route("/restaurant/", methods=["GET", "POST"])
@login_required
def restaurant():

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
        return redirect(url_for("supply_blueprint.restaurant"))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        store_id = form3.store.data.id
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    top_ten = get_category_topten(
        ["Restaurant Supplies"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_restaurant = get_restaurant_topten(
        ["Restaurant Supplies"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_vendor = get_vendor_topten(
        ["Restaurant Supplies"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )

    category_costs = get_category_costs(
        ["Restaurant Supplies"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    category_costs_total = category_costs["Totals"].sum()
    top_ten['percent'] = top_ten['Cost'] / category_costs_total
    top_ten_vendor['percent'] = top_ten_vendor['Cost'] / category_costs_total


    return render_template(
        "supply/restaurant.html",
        title="Restaurant",
        company_name=Config.COMPANY_NAME,
        segment="supplies",
        fiscal_dates=fiscal_dates,
        form1=form1,
        form3=form3,
        current_user=current_user,
        top_ten=top_ten,
        top_ten_restaurant=top_ten_restaurant,
        top_ten_vendor=top_ten_vendor,
    )


@blueprint.route("/kitchen/", methods=["GET", "POST"])
@login_required
def kitchen():

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
        return redirect(url_for("supply_blueprint.kitchen"))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        store_id = form3.store.data.id
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    top_ten = get_category_topten(
        ["Kitchen Supplies"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_restaurant = get_restaurant_topten(
        ["Kitchen Supplies"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_vendor = get_vendor_topten(
        ["Kitchen Supplies"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )

    category_costs = get_category_costs(
        ["Kitchen Supplies"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    category_costs_total = category_costs["Totals"].sum()
    top_ten['percent'] = top_ten['Cost'] / category_costs_total
    top_ten_vendor['percent'] = top_ten_vendor['Cost'] / category_costs_total

    return render_template(
        "supply/kitchen.html",
        title="Kitchen",
        company_name=Config.COMPANY_NAME,
        segment="supplies",
        fiscal_dates=fiscal_dates,
        form1=form1,
        form3=form3,
        current_user=current_user,
        top_ten=top_ten,
        top_ten_restaurant=top_ten_restaurant,
        top_ten_vendor=top_ten_vendor,
    )


@blueprint.route("/cleaning/", methods=["GET", "POST"])
@login_required
def cleaning():

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
        return redirect(url_for("supply_blueprint.cleaning"))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        store_id = form3.store.data.id
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    top_ten = get_category_topten(
        ["Cleaning Supplies"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_restaurant = get_restaurant_topten(
        ["Cleaning Supplies"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_vendor = get_vendor_topten(
        ["Cleaning Supplies"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )

    category_costs = get_category_costs(
        ["Cleaning Supplies"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    category_costs_total = category_costs["Totals"].sum()
    top_ten['percent'] = top_ten['Cost'] / category_costs_total
    top_ten_vendor['percent'] = top_ten_vendor['Cost'] / category_costs_total

    return render_template(
        "supply/cleaning.html",
        title="Cleaning",
        company_name=Config.COMPANY_NAME,
        segment="supplies",
        fiscal_dates=fiscal_dates,
        form1=form1,
        form3=form3,
        current_user=current_user,
        top_ten=top_ten,
        top_ten_restaurant=top_ten_restaurant,
        top_ten_vendor=top_ten_vendor,
    )


@blueprint.route("/catering/", methods=["GET", "POST"])
@login_required
def catering():

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
        return redirect(url_for("supply_blueprint.catering"))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        store_id = form3.store.data.id
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    top_ten = get_category_topten(
        ["Catering Supplies/Expense"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_restaurant = get_restaurant_topten(
        ["Catering Supplies/Expense"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_vendor = get_vendor_topten(
        ["Catering Supplies/Expense"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )

    category_costs = get_category_costs(
        ["Catering Supplies/Expense"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    category_costs_total = category_costs["Totals"].sum()
    top_ten['percent'] = top_ten['Cost'] / category_costs_total
    top_ten_vendor['percent'] = top_ten_vendor['Cost'] / category_costs_total

    return render_template(
        "supply/catering.html",
        title="Catering",
        company_name=Config.COMPANY_NAME,
        segment="supplies",
        fiscal_dates=fiscal_dates,
        form1=form1,
        form3=form3,
        current_user=current_user,
        top_ten=top_ten,
        top_ten_restaurant=top_ten_restaurant,
        top_ten_vendor=top_ten_vendor,
    )


@blueprint.route("/bar/", methods=["GET", "POST"])
@login_required
def bar():

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
        return redirect(url_for("supply_blueprint.bar"))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        store_id = form3.store.data.id
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    top_ten = get_category_topten(
        ["Bar Supplies"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_restaurant = get_restaurant_topten(
        ["Bar Supplies"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_vendor = get_vendor_topten(
        ["Bar Supplies"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )

    category_costs = get_category_costs(
        ["Bar Supplies"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    category_costs_total = category_costs["Totals"].sum()
    top_ten['percent'] = top_ten['Cost'] / category_costs_total
    top_ten_vendor['percent'] = top_ten_vendor['Cost'] / category_costs_total

    return render_template(
        "supply/bar.html",
        title="Bar",
        company_name=Config.COMPANY_NAME,
        segment="supplies",
        fiscal_dates=fiscal_dates,
        form1=form1,
        form3=form3,
        current_user=current_user,
        top_ten=top_ten,
        top_ten_restaurant=top_ten_restaurant,
        top_ten_vendor=top_ten_vendor,
    )


@blueprint.route("/smallware/", methods=["GET", "POST"])
@login_required
def smallware():

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
        return redirect(url_for("supply_blueprint.smallware"))

    if form3.submit3.data and form3.validate():
        session["token"] = fiscal_dates["start_day"]
        store_id = form3.store.data.id
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    top_ten = get_category_topten(
        ["Smallware"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_restaurant = get_restaurant_topten(
        ["Smallware"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_vendor = get_vendor_topten(
        ["Smallware"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )

    category_costs = get_category_costs(
        ["Smallware"],
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    category_costs_total = category_costs["Totals"].sum()
    top_ten['percent'] = top_ten['Cost'] / category_costs_total
    top_ten_vendor['percent'] = top_ten_vendor['Cost'] / category_costs_total

    return render_template(
        "supply/smallware.html",
        title="Smallware",
        company_name=Config.COMPANY_NAME,
        segment="supplies",
        fiscal_dates=fiscal_dates,
        form1=form1,
        form3=form3,
        current_user=current_user,
        top_ten=top_ten,
        top_ten_restaurant=top_ten_restaurant,
        top_ten_vendor=top_ten_vendor,
    )
