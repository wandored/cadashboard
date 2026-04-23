# -*- encmding: utf-8 -*-
"""
routes for supplies pages
"""

from datetime import datetime, timedelta

import pandas as pd
from flask import flash, redirect, render_template, session, url_for
from flask.helpers import url_for
from flask.wrappers import Response
from flask_security import current_user, login_required
from flask_security.decorators import roles_accepted
from fpdf import FPDF
from pandas.core.algorithms import isin
from sqlalchemy import and_, func, or_

from dashapp.authentication.forms import (
    DateForm,
    StoreForm,
)
from dashapp.authentication.models import Restaurants
from dashapp.config import Config
from dashapp.purchasing.util import (
    get_category_costs,
    get_category_topten,
    get_cost_per_store,
    get_cost_per_vendor,
    get_restaurant_topten,
    get_vendor_topten,
    period_purchases,
    set_dates,
)
from dashapp.supply import blueprint


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
        session["date_selected"] = form1.selectdate.data
        return redirect(url_for("supply_blueprint.supplies"))

    if form3.submit3.data and form3.validate():
        session["date_selected"] = fiscal_dates["start_day"]
        data = form3.stores.data
        session["store_list"] = tuple([x.id for x in data])
        if 98 in session["store_list"] and 99 in session["store_list"]:
            session["store_list"] = tuple(
                store.id
                for store in Restaurants.query.filter(Restaurants.active == True)  # noqa E712
                .order_by(Restaurants.name)
                .all()
            )
        elif 99 in session["store_list"]:
            session["store_list"] = tuple(
                store.id
                for store in Restaurants.query.filter(
                    and_(
                        Restaurants.active == True, Restaurants.concept == "Steakhouse"
                    )
                )
                .order_by(Restaurants.name)
                .all()
            )
        elif 98 in session["store_list"]:
            session["store_list"] = tuple(
                store.id
                for store in Restaurants.query.filter(
                    and_(Restaurants.active == True, Restaurants.concept == "Casual")
                )
            )
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    category_list = [
        "Restaurant Supplies",
        "Kitchen Supplies",
        "Cleaning Supplies",
        "Office Supplies",
        "Catering Supplies/Expense",
        "Bar Supplies",
    ]
    top_ten = get_category_topten(
        category_list,
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )

    category_costs = get_category_costs(
        category_list,
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    # Sum supply_category_costs Totals
    category_costs_total = category_costs["Totals"].sum()
    category_items = category_costs["Account"].tolist()
    category_values = category_costs["Totals"].tolist()

    top_ten_vendor = get_vendor_topten(
        category_list,
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_vendor["percent"] = top_ten_vendor["Cost"] / category_costs_total

    # Fry Oil data
    fryoil_chart = period_purchases(
        "KIT SUP Fryer Oil", fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    del fryoil_chart[fiscal_dates["period"] :]
    fryoil_chart_ly = period_purchases(
        "KIT SUP Fryer Oil",
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
    )
    fryer_oil_store = get_cost_per_store(
        "KIT SUP Fryer Oil", fiscal_dates["last_seven"]
    )
    fryer_oil_vendor = get_cost_per_vendor(
        "KIT SUP Fryer Oil", fiscal_dates["last_seven"]
    )

    return render_template(
        "purchasing/supplies.html",
        title="Supplies",
        company_name=Config.COMPANY_NAME,
        segment="supplies",
        **locals(),
    )


@blueprint.route("/smallwares/", methods=["GET", "POST"])
@login_required
def smallwares():
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
        session["date_selected"] = form1.selectdate.data
        return redirect(url_for("supply_blueprint.smallwares"))

    if form3.submit3.data and form3.validate():
        session["date_selected"] = fiscal_dates["start_day"]
        data = form3.stores.data
        session["store_list"] = tuple([x.id for x in data])
        if 98 in session["store_list"] and 99 in session["store_list"]:
            session["store_list"] = tuple(
                store.id
                for store in Restaurants.query.filter(Restaurants.active == True)  # noqa E712
                .order_by(Restaurants.name)
                .all()
            )
        elif 99 in session["store_list"]:
            session["store_list"] = tuple(
                store.id
                for store in Restaurants.query.filter(
                    and_(
                        Restaurants.active == True, Restaurants.concept == "Steakhouse"
                    )
                )
                .order_by(Restaurants.name)
                .all()
            )
        elif 98 in session["store_list"]:
            session["store_list"] = tuple(
                store.id
                for store in Restaurants.query.filter(
                    and_(Restaurants.active == True, Restaurants.concept == "Casual")
                )
            )
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    category_list = [
        "Smallware",
        "China",
        "Silverware",
        "Glassware",
    ]
    top_ten = get_category_topten(
        category_list,
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )

    category_costs = get_category_costs(
        category_list,
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    # Sum supply_category_costs Totals
    category_costs_total = category_costs["Totals"].sum()
    category_items = category_costs["Account"].tolist()
    category_values = category_costs["Totals"].tolist()

    top_ten_vendor = get_vendor_topten(
        category_list,
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_vendor["percent"] = top_ten_vendor["Cost"] / category_costs_total

    return render_template(
        "purchasing/smallwares.html",
        title="Smallwares",
        company_name=Config.COMPANY_NAME,
        segment="supplies",
        **locals(),
    )


@blueprint.route("/linen/", methods=["GET", "POST"])
@login_required
def linen():
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
        session["date_selected"] = form1.selectdate.data
        return redirect(url_for("supply_blueprint.linen"))

    if form3.submit3.data and form3.validate():
        session["date_selected"] = fiscal_dates["start_day"]
        data = form3.stores.data
        session["store_list"] = tuple([x.id for x in data])
        if 98 in session["store_list"] and 99 in session["store_list"]:
            session["store_list"] = tuple(
                store.id
                for store in Restaurants.query.filter(Restaurants.active == True)  # noqa E712
                .order_by(Restaurants.name)
                .all()
            )
        elif 99 in session["store_list"]:
            session["store_list"] = tuple(
                store.id
                for store in Restaurants.query.filter(
                    and_(
                        Restaurants.active == True, Restaurants.concept == "Steakhouse"
                    )
                )
                .order_by(Restaurants.name)
                .all()
            )
        elif 98 in session["store_list"]:
            session["store_list"] = tuple(
                store.id
                for store in Restaurants.query.filter(
                    and_(Restaurants.active == True, Restaurants.concept == "Casual")
                )
            )
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    category_list = ["Linen"]

    top_ten = get_category_topten(
        category_list,
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_restaurant = get_restaurant_topten(
        category_list,
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )

    category_costs = get_category_costs(
        category_list,
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    # Sum supply_category_costs Totals
    category_costs_total = category_costs["Totals"].sum()
    category_items = category_costs["Account"].tolist()
    category_values = category_costs["Totals"].tolist()

    top_ten_vendor = get_vendor_topten(
        category_list,
        fiscal_dates["last_thirty"],
        fiscal_dates["start_day"],
    )
    top_ten_vendor["percent"] = top_ten_vendor["Cost"] / category_costs_total

    return render_template(
        "purchasing/linen.html",
        title="Linen",
        company_name=Config.COMPANY_NAME,
        segment="supplies",
        **locals(),
    )
