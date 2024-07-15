# -*- encmding: utf-8 -*-
"""
routes for purchasing pages
"""

from flask import redirect, render_template, session, url_for

# from flask.helpers import url_for
from flask_security import login_required
from icecream import ic
from sqlalchemy import and_, func

from dashapp.authentication.forms import (
    DateForm,
    LobsterForm,
    PotatoForm,
    StoneForm,
    StoreForm,
)
from dashapp.authentication.models import (
    Purchases,
    Restaurants,
    SalesAccount,
    db,
)
from dashapp.config import Config
from dashapp.home.util import get_category_sales
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

    food_category_list = (
        db.session.query(Purchases.category2)
        .filter(Purchases.category1 == "Food")
        .all()
    )
    food_category_list = [x[0] for x in food_category_list]
    food_category_list = list(set(food_category_list))
    food_category_list = [x for x in food_category_list if x is not None]
    food_category_list.sort()

    # food_sales_accounts = (
    #     db.session.query(SalesAccount.category)
    #     .filter(SalesAccount.sales_type == "Food Sales")
    #     .all()
    # )
    # food_sales_accounts = [x[0] for x in food_sales_accounts]
    # food_sales_accounts = list(set(food_sales_accounts))
    # food_sales_accounts.sort()

    # beer_sales_accounts = (
    #     db.session.query(SalesAccount.category)
    #     .filter(SalesAccount.sales_type == "Beer Sales")
    #     .all()
    # )
    # beer_sales_accounts = [x[0] for x in beer_sales_accounts]
    # beer_sales_accounts = list(set(beer_sales_accounts))
    # beer_sales_accounts.sort()

    # wine_sales_accounts = (
    #     db.session.query(SalesAccount.category)
    #     .filter(SalesAccount.sales_type == "Wine Sales")
    #     .all()
    # )
    # wine_sales_accounts = [x[0] for x in wine_sales_accounts]
    # wine_sales_accounts = list(set(wine_sales_accounts))
    # wine_sales_accounts.sort()

    # liquor_sales_accounts = (
    #     db.session.query(SalesAccount.category)
    #     .filter(SalesAccount.sales_type == "Liquor Sales")
    #     .all()
    # )
    # liquor_sales_accounts = [x[0] for x in liquor_sales_accounts]
    # liquor_sales_accounts = list(set(liquor_sales_accounts))
    # liquor_sales_accounts.sort()

    # Current period purchases
    top_ten = get_category_topten(
        food_category_list,
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        session["store_list"],
    )

    category_costs = get_category_costs(
        food_category_list,
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        session["store_list"],
    )
    category_items = category_costs["Account"].tolist()
    category_values = category_costs["Totals"].tolist()

    category_costs.replace("Fish", "Seafood", inplace=True)
    category_costs.set_index("Account", inplace=True)

    top_ten_vendor = get_vendor_topten(
        food_category_list,
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

    # Yearly sales & costs
    # TODO get account costs for charts
    def get_period_category_costs(category, start, end, store_list):
        return (
            db.session.query(
                Purchases.period,
                func.sum(Purchases.debit).label("cost"),
            )
            .filter(
                Purchases.date.between(start, end),
                Purchases.account.in_(category),
                Purchases.id.in_(store_list),
            )
            .group_by(Purchases.period)
            .all()
        )

    ytd_food_cost_query = get_period_category_costs(
        food_category_list,
        fiscal_dates["start_year"],
        fiscal_dates["start_day"],
        session["store_list"],
    )
    ytd_food_cost = [x[1] for x in ytd_food_cost_query]

    ytd_beer_cost_query = get_period_category_costs(
        ["Beer"],
        fiscal_dates["start_year"],
        fiscal_dates["start_day"],
        session["store_list"],
    )
    ytd_beer_cost = [x[1] for x in ytd_beer_cost_query]
    ytd_liquor_cost_query = get_period_category_costs(
        ["Liquor"],
        fiscal_dates["start_year"],
        fiscal_dates["start_day"],
        session["store_list"],
    )
    ytd_liquor_cost = [x[1] for x in ytd_liquor_cost_query]
    ytd_wine_cost_query = get_period_category_costs(
        ["Wine"],
        fiscal_dates["start_year"],
        fiscal_dates["start_day"],
        session["store_list"],
    )
    ytd_wine_cost = [x[1] for x in ytd_wine_cost_query]

    food_sales_table = get_category_sales(
        fiscal_dates["start_year"],
        fiscal_dates["start_day"],
        "Food Sales",
        session["store_list"],
    )
    beer_sales_table = get_category_sales(
        fiscal_dates["start_year"],
        fiscal_dates["start_day"],
        "Beer Sales",
        session["store_list"],
    )
    wine_sales_table = get_category_sales(
        fiscal_dates["start_year"],
        fiscal_dates["start_day"],
        "Wine Sales",
        session["store_list"],
    )
    liquor_sales_table = get_category_sales(
        fiscal_dates["start_year"],
        fiscal_dates["start_day"],
        "Liquor Sales",
        session["store_list"],
    )
    ytd_period_food_sales = food_sales_table.groupby("period")["sales"].sum()
    ytd_period_food_sales_list = ytd_period_food_sales.tolist()
    ytd_period_beer_sales = beer_sales_table.groupby("period")["sales"].sum()
    ytd_period_beer_sales_list = ytd_period_beer_sales.tolist()
    ytd_period_wine_sales = wine_sales_table.groupby("period")["sales"].sum()
    ytd_period_wine_sales_list = ytd_period_wine_sales.tolist()
    ytd_period_liquor_sales = liquor_sales_table.groupby("period")["sales"].sum()
    ytd_period_liquor_sales_list = ytd_period_liquor_sales.tolist()

    ytd_food_cost_pct = [
        x / y * 100 for x, y in zip(ytd_food_cost, ytd_period_food_sales_list)
    ]
    ytd_beer_cost_pct = [
        x / y * 100 for x, y in zip(ytd_beer_cost, ytd_period_beer_sales_list)
    ]
    ytd_wine_cost_pct = [
        x / y * 100 for x, y in zip(ytd_wine_cost, ytd_period_wine_sales_list)
    ]
    ytd_liquor_cost_pct = [
        x / y * 100 for x, y in zip(ytd_liquor_cost, ytd_period_liquor_sales_list)
    ]

    total_food_sales = food_sales_table["sales"].sum()
    total_beer_sales = beer_sales_table["sales"].sum()
    total_wine_sales = wine_sales_table["sales"].sum()
    total_liquor_sales = liquor_sales_table["sales"].sum()

    local_vars = locals()
    for key, value in local_vars.items():
        ic(key)
    return render_template(
        "purchasing/purchasing.html",
        title="Purchasing",
        company_name=Config.COMPANY_NAME,
        segment="purchasing",
        form1=form1,
        form3=form3,
        form4=form4,
        form5=form5,
        form6=form6,
        fiscal_dates=fiscal_dates,
        top_ten=top_ten,
        top_ten_vendor=top_ten_vendor,
        category_items=category_items,
        category_values=category_values,
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
