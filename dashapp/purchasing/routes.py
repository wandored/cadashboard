# -*- encmding: utf-8 -*-
"""
routes for purchasing pages
"""

from flask import redirect, render_template, session, url_for
from flask.helpers import url_for
from flask_security import login_required
from icecream import ic

from dashapp.authentication.forms import (
    DateForm,
    LobsterForm,
    PotatoForm,
    StoneForm,
    StoreForm,
)
from dashapp.authentication.models import (
    Restaurants,
    db,
)
from dashapp.config import Config
from dashapp.purchasing import blueprint
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


@blueprint.route("/purchasing/", methods=["GET", "POST"])
@login_required
def purchasing():
    fiscal_dates = set_dates(session["date_selected"])

    form1 = DateForm()
    form3 = StoreForm()
    form4 = PotatoForm()
    form5 = LobsterForm()
    form6 = StoneForm()

    if form1.submit1.data and form1.validate():
        session["date_selected"] = form1.selectdate.data
        return redirect(url_for("purchasing_blueprint.purchasing"))

    if form3.submit3.data and form3.validate():
        session["date_selected"] = fiscal_dates["start_day"]
        data = form3.stores.data
        session["store_list"] = tuple([x.id for x in data])
        if 98 in session["store_list"] and 99 in session["store_list"]:
            session["store_list"] = tuple([19, 9, 4, 11, 17, 16, 10, 5, 18, 12, 14, 3, 6, 15, 13])
        elif 99 in session["store_list"]:
            session["store_list"] = tuple([19, 9, 4, 11, 17, 16])
        elif 98 in session["store_list"]:
            session["store_list"] = tuple([10, 5, 18, 12, 14, 3, 6, 15, 13])
        return redirect(url_for("purchasing_blueprint.purchasing"))

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

    food_list = ["Beef", "Food Other", "Dairy", "Pork", "Poultry", "Produce", "Fish"]
    top_ten = get_category_topten(
        food_list,
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        session["store_list"],
    )

    category_costs = get_category_costs(
        food_list,
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        session["store_list"],
    )
    category_items = category_costs["Account"].tolist()
    category_values = category_costs["Totals"].tolist()

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
    store_names = db.session.query(Restaurants.name).filter(
        Restaurants.id.in_(session["store_list"])
    )
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
def purchase(product):
    fiscal_dates = set_dates(session["date_selected"])

    form1 = DateForm()
    form3 = StoreForm()
    form4 = PotatoForm()
    form5 = LobsterForm()
    form6 = StoneForm()

    if form1.submit1.data and form1.validate():
        session["date_selected"] = form1.selectdate.data
        return redirect(url_for("purchasing_blueprint.purchase", product=product))

    if form3.submit3.data and form3.validate():
        session["date_selected"] = fiscal_dates["start_day"]
        data = form3.stores.data
        session["store_list"] = tuple([x.id for x in data])
        if 98 in session["store_list"] and 99 in session["store_list"]:
            session["store_list"] = tuple([19, 9, 4, 11, 17, 16, 10, 5, 18, 12, 14, 3, 6, 15, 13])
        elif 99 in session["store_list"]:
            session["store_list"] = tuple([19, 9, 4, 11, 17, 16])
        elif 98 in session["store_list"]:
            session["store_list"] = tuple([10, 5, 18, 12, 14, 3, 6, 15, 13])
        return redirect(url_for("purchasing_blueprint.purchase", product=product))

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
        try:
            del this_year[fiscal_dates["period"] :]  # remove zeros from future periods
        except:
            pass
        last_year = period_purchases(
            "^({})$".format(pl),
            fiscal_dates["start_year_ly"],
            fiscal_dates["end_year_ly"],
            session["store_list"],
        )
        # if last year is empty, fill with zeros
        if len(last_year) == 0:
            last_year = [0] * len(this_year)

        product_dict_ty["{}".format(x)] = this_year
        product_dict_ly["{}".format(x)] = last_year
        product_names.append(pl)

        store_cost_dict["{}".format(x)] = get_cost_per_store(
            "^({})$".format(pl),
            fiscal_dates["start_period"],
            fiscal_dates["end_day"],
            session["store_list"],
        )

        vendor_cost_dict["{}".format(x)] = get_cost_per_vendor(
            "^({})$".format(pl),
            fiscal_dates["start_period"],
            fiscal_dates["end_day"],
            session["store_list"],
        )
        x = x + 1

    # assign color based on product value
    def color_assigner(product):
        switch = {
            "Beef": "primary",
            "Dairy": "info",
            "Food Other": "secondary",
            "Pork": "danger",
            "Poultry": "warning",
            "Produce": "success",
            "Fish": "info",
            "Beer": "warning",
            "Wine": "danger",
            "Liquor": "primary",
        }
        return switch.get(product, "secondary")

    color = color_assigner(product)

    store_names = db.session.query(Restaurants.name).filter(
        Restaurants.id.in_(session["store_list"])
    )
    store_names = [x[0] for x in store_names]
    store_names = ", ".join(store_names)

    return render_template(
        "purchasing/purchase.html",
        title=product,
        company_name=Config.COMPANY_NAME,
        segment="purchasing",
        **locals(),
    )
