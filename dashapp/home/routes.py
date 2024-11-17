# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import json
from datetime import datetime, timedelta

import pandas as pd
from flask import redirect, render_template, session
from flask.helpers import url_for
from flask.wrappers import Response
from flask_security import current_user, login_required
from flask_security.decorators import roles_accepted
from fpdf import FPDF
from icecream import ic
from pandas._libs.tslibs import period  # noqa: F401
from sqlalchemy import func, and_

from dashapp.authentication.forms import (
    DateForm,
    LobsterForm,
    PotatoForm,
    StoneForm,
    StoreForm,
    UpdateForm,
)
from dashapp.authentication.models import (
    GiftCardRedeem,
    GiftCardSales,
    LaborTotals,
    PotatoSales,
    Restaurants,
    SalesTotals,
    StockCount,
    Users,
    db,
)
from dashapp.config import Config
from dashapp.home import blueprint
from dashapp.home.util import (
    find_day_with_sales,
    get_category_sales,
    get_daypart_sales,
    get_giftcard_redeem,
    get_giftcard_sales,
    get_item_avg_cost,
    get_sales_charts,
    get_timeing_data,
    get_togo_sales,
    SalesRecordsDay,
    SalesRecordsPeriod,
    SalesRecordsWeek,
    SalesRecordsYear,
    set_dates,
)


@blueprint.route("/", methods=["GET", "POST"])
@blueprint.route("/index/", methods=["GET", "POST"])
@login_required
def index():
    TODAY = datetime.date(datetime.now())
    if "date_selected" not in session:
        session["date_selected"] = TODAY
        return redirect(url_for("home_blueprint.index"))

    # set store list to all active stores
    session["store_list"] = tuple(
        [
            store.id
            for store in Restaurants.query.filter(Restaurants.active == True)  # noqa: E712
            .order_by(Restaurants.name)
            .all()
        ]
    )

    fiscal_dates = set_dates(session["date_selected"])

    # Check for no sales
    if not SalesTotals.query.filter_by(date=fiscal_dates["start_day"]).all():
        session["date_selected"] = find_day_with_sales(day=fiscal_dates["start_day"])
        return redirect(url_for("home_blueprint.index"))

    # Get Data
    form1 = DateForm()
    form3 = StoreForm()
    form4 = PotatoForm()
    form5 = LobsterForm()
    form6 = StoneForm()

    if form1.submit1.data and form1.validate():
        """
        Change date_selected
        """
        session["date_selected"] = form1.selectdate.data
        return redirect(url_for("home_blueprint.index"))

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
                    )  # noqa E712
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
        return redirect(url_for("home_blueprint.index"))

    if form4.submit4.data and form4.validate():
        store_id = form4.store.data.id
        return redirect(url_for("home_blueprint.potato", store_id=store_id))

    if form5.submit5.data and form5.validate():
        store_id = form5.store.data.id
        return redirect(url_for("home_blueprint.lobster", store_id=store_id))

    if form6.submit6.data and form6.validate():
        store_id = form6.store.data.id
        return redirect(url_for("home_blueprint.stone", store_id=store_id))

    # Sales Chart
    def get_chart_values(start, end, time_frame):
        query = (
            db.session.query(func.sum(SalesTotals.net_sales).label("total_sales"))
            .select_from(SalesTotals)
            .filter(SalesTotals.date.between(start, end))
            .group_by(time_frame)
            .order_by(time_frame)
        )
        value = [v.total_sales for v in query]
        return value

    daily_sales_list = get_sales_charts(
        fiscal_dates["start_week"],
        fiscal_dates["start_day"],
        "date",
        session["store_list"],
    )
    weekly_sales = sum(daily_sales_list)

    daily_sales_list_ly = get_sales_charts(
        fiscal_dates["start_week_ly"],
        fiscal_dates["end_week_ly"],
        "date",
        session["store_list"],
    )
    weekly_sales_ly = sum(daily_sales_list_ly)

    week_to_date_sales_ly = get_sales_charts(
        fiscal_dates["start_week_ly"],
        fiscal_dates["start_day_ly"],
        "date",
        session["store_list"],
    )
    wtd_sales_ly = sum(week_to_date_sales_ly)

    weekly_sales_list = get_sales_charts(
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        "week",
        session["store_list"],
    )
    period_sales = sum(weekly_sales_list)

    weekly_sales_list_ly = get_sales_charts(
        fiscal_dates["start_period_ly"],
        fiscal_dates["end_period_ly"],
        "week",
        session["store_list"],
    )
    period_sales_ly = sum(weekly_sales_list_ly)

    period_to_date_sales_ly = get_sales_charts(
        fiscal_dates["start_period_ly"],
        fiscal_dates["start_day_ly"],
        "week",
        session["store_list"],
    )
    ptd_sales_ly = sum(period_to_date_sales_ly)

    period_sales_list = get_sales_charts(
        fiscal_dates["start_year"],
        fiscal_dates["start_day"],
        "period",
        session["store_list"],
    )
    yearly_sales = sum(period_sales_list)

    period_sales_list_ly = get_sales_charts(
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
        "period",
        session["store_list"],
    )
    yearly_sales_ly = sum(period_sales_list_ly)

    year_to_date_sales_ly = get_sales_charts(
        fiscal_dates["start_year_ly"],
        fiscal_dates["start_day_ly"],
        "period",
        session["store_list"],
    )
    ytd_sales_ly = sum(year_to_date_sales_ly)

    def build_sales_table(start, end, start_ly, end_ly, time_frame):
        sales = (
            db.session.query(
                SalesTotals.store,
                SalesTotals.id,
                func.sum(SalesTotals.net_sales).label("total_sales"),
                func.sum(SalesTotals.guest_count).label("total_guests"),
            )
            .filter(SalesTotals.date.between(start, end))
            .group_by(SalesTotals.store, SalesTotals.id)
            .all()
        )

        sales_ly = (
            db.session.query(
                SalesTotals.store,
                SalesTotals.id,
                func.sum(SalesTotals.net_sales).label("total_sales_ly"),
                func.sum(SalesTotals.guest_count).label("total_guests_ly"),
            )
            .filter(SalesTotals.date.between(start_ly, end_ly))
            .group_by(SalesTotals.store, SalesTotals.id)
            .all()
        )
        # Get the top sales for each store and merge with sales_table
        table_class = globals()[
            f"SalesRecords{time_frame}"
        ]  # how you use a variable in query
        sales_query = table_class.query.with_entities(
            table_class.store, table_class.id, table_class.net_sales
        ).all()

        top_sales = pd.DataFrame.from_records(
            sales_query, columns=["store", "id", "top_sales"]
        )
        # round to 2 decimal places
        top_sales["top_sales"] = top_sales["top_sales"].round(2)
        top_sales.set_index("store", inplace=True)
        sales_table = pd.DataFrame.from_records(
            sales, columns=["store", "id", "sales", "guests"]
        )
        sales_table_ly = pd.DataFrame.from_records(
            sales_ly, columns=["store", "id", "sales_ly", "guests_ly"]
        )
        sales_table = sales_table.merge(sales_table_ly, how="outer", sort=True)
        sales_table = sales_table.merge(
            top_sales, how="left", left_on=["store", "id"], right_on=["store", "id"]
        )

        labor = (
            db.session.query(
                LaborTotals.store,
                LaborTotals.id,
                func.sum(LaborTotals.total_hours),
                func.sum(LaborTotals.total_dollars),
            )
            .filter(LaborTotals.date.between(start, end))
            .group_by(LaborTotals.store, LaborTotals.id)
            .all()
        )

        labor_ly = (
            db.session.query(
                LaborTotals.store,
                LaborTotals.id,
                func.sum(LaborTotals.total_hours).label("total_hours_ly"),
                func.sum(LaborTotals.total_dollars).label("total_dollars_ly"),
            )
            .filter(LaborTotals.date.between(start_ly, end_ly))
            .group_by(LaborTotals.store, LaborTotals.id)
            .all()
        )

        df_labor = pd.DataFrame.from_records(
            labor, columns=["store", "id", "hours", "dollars"]
        )
        df_labor_ly = pd.DataFrame.from_records(
            labor_ly, columns=["store", "id", "hours_ly", "dollars_ly"]
        )
        labor_table = df_labor.merge(df_labor_ly, how="outer", sort=True)
        table = sales_table.merge(labor_table, how="outer", sort=True)
        table = table.set_index("store")

        # Grab top sales over last year before we add totals
        table = table.fillna(0)
        table["doly"] = table.sales - table.sales_ly
        table["poly"] = (table.sales - table.sales_ly) / table.sales_ly * 100
        #drop row if sales_ly is 0
        top_table = table[table.sales_ly != 0]
        top = top_table[["doly", "poly"]]
        top = top.nlargest(5, "poly", keep="all")
        table["guest_check_avg"] = table["sales"] / table["guests"].astype(float)
        table["guest_check_avg_ly"] = table["sales_ly"] / table["guests_ly"].astype(
            float
        )
        table["labor_pct"] = table.dollars / table.sales
        table["labor_pct_ly"] = table.dollars_ly / table.sales_ly
        totals = table.sum()

        return totals, table, top

    daily_totals, daily_table, daily_top = build_sales_table(
        fiscal_dates["start_day"],
        fiscal_dates["start_day"],
        fiscal_dates["start_day_ly"],
        fiscal_dates["start_day_ly"],
        "Day",
    )

    weekly_totals, weekly_table, weekly_top = build_sales_table(
        fiscal_dates["start_week"],
        fiscal_dates["start_day"],
        fiscal_dates["start_week_ly"],
        fiscal_dates["week_to_date_ly"],
        "Week",
    )

    period_totals, period_table, period_top = build_sales_table(
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        fiscal_dates["start_period_ly"],
        fiscal_dates["period_to_date_ly"],
        "Period",
    )

    yearly_totals, yearly_table, yearly_top = build_sales_table(
        fiscal_dates["start_year"],
        fiscal_dates["start_day"],
        fiscal_dates["start_year_ly"],
        fiscal_dates["year_to_date_ly"],
        "Year",
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
    store = Restaurants.query.filter_by(id=store_id).first()
    session["store_list"] = [store.id]

    if "date_selected" not in session:
        session["date_selected"] = TODAY
        return redirect(url_for("home_blueprint.store", store_id=store.id))

    fiscal_dates = set_dates(session["date_selected"])

    if not SalesTotals.query.filter_by(
        date=fiscal_dates["start_day"], store=store.name
    ).first():
        session["date_selected"] = find_day_with_sales(
            day=fiscal_dates["start_day"], store=store.name
        )
        return redirect(url_for("home_blueprint.store", store_id=store.id))

    # Get Data
    form1 = DateForm()
    form3 = StoreForm()
    form4 = PotatoForm()
    form5 = LobsterForm()
    form6 = StoneForm()

    if form1.submit1.data and form1.validate():
        session["date_selected"] = form1.selectdate.data
        return redirect(url_for("home_blueprint.store", store_id=store.id))

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
                    )  # noqa E712
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
        for x in data:
            # select only 1 store for store page
            if x.id in session["store_list"]:
                store_id = x.id
                break
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    if form4.submit4.data and form4.validate():
        store_id = form4.store.data.id
        return redirect(url_for("home_blueprint.potato", store_id=store_id))

    if form5.submit5.data and form5.validate():
        store_id = form5.store.data.id
        return redirect(url_for("home_blueprint.lobster", store_id=store_id))

    if form6.submit6.data and form6.validate():
        store_id = form6.store.data.id
        return redirect(url_for("home_blueprint.stone", store_id=store_id))

    # Sales Charts
    daily_sales_list = get_sales_charts(
        fiscal_dates["start_week"],
        fiscal_dates["start_day"],
        "date",
        session["store_list"],
    )
    weekly_sales = sum(daily_sales_list)

    daily_sales_list_ly = get_sales_charts(
        fiscal_dates["start_week_ly"],
        fiscal_dates["end_week_ly"],
        "date",
        session["store_list"],
    )
    weekly_sales_ly = sum(daily_sales_list_ly)

    week_to_date_sales_ly = get_sales_charts(
        fiscal_dates["start_week_ly"],
        fiscal_dates["start_day_ly"],
        "date",
        session["store_list"],
    )
    wtd_sales_ly = sum(week_to_date_sales_ly)

    weekly_sales_list = get_sales_charts(
        fiscal_dates["start_period"],
        fiscal_dates["period_to_date"],
        "week",
        session["store_list"],
    )
    period_sales = sum(weekly_sales_list)

    weekly_sales_list_ly = get_sales_charts(
        fiscal_dates["start_period_ly"],
        fiscal_dates["end_period_ly"],
        "week",
        session["store_list"],
    )
    period_sales_ly = sum(weekly_sales_list_ly)

    period_to_date_sales_ly = get_sales_charts(
        fiscal_dates["start_period_ly"],
        fiscal_dates["start_day_ly"],
        "week",
        session["store_list"],
    )
    ptd_sales_ly = sum(period_to_date_sales_ly)

    period_sales_list = get_sales_charts(
        fiscal_dates["start_year"],
        fiscal_dates["start_day"],
        "period",
        session["store_list"],
    )
    yearly_sales = sum(period_sales_list)

    period_sales_list_ly = get_sales_charts(
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
        "period",
        session["store_list"],
    )
    yearly_sales_ly = sum(period_sales_list_ly)

    year_to_date_sales_ly = get_sales_charts(
        fiscal_dates["start_year_ly"],
        fiscal_dates["start_day_ly"],
        "period",
        session["store_list"],
    )
    ytd_sales_ly = sum(year_to_date_sales_ly)

    daily_sales = daily_sales_list[-1]
    daily_sales_ly = daily_sales_list_ly[fiscal_dates["dow"] - 1]

    # lunch and dinner sales
    week_lunch_sales, week_dinner_sales = get_daypart_sales(
        fiscal_dates["start_week"], fiscal_dates["week_to_date"], session["store_list"]
    )
    week_lunch_sales_list = week_lunch_sales[week_lunch_sales.daypart == "Lunch"][
        "sales"
    ].tolist()
    week_lunch_sales_total = sum(week_lunch_sales_list)
    week_dinner_sales_list = week_dinner_sales[week_dinner_sales.daypart == "Dinner"][
        "sales"
    ].tolist()
    week_dinner_sales_total = sum(week_dinner_sales_list)
    # TODO fix the week to date calculations

    week_lunch_sales_ly, week_dinner_sales_ly = get_daypart_sales(
        fiscal_dates["start_week_ly"],
        fiscal_dates["end_week_ly"],
        session["store_list"],
    )
    week_lunch_sales_list_ly = week_lunch_sales_ly[
        week_lunch_sales_ly.daypart == "Lunch"
    ]["sales"].tolist()
    wtd_lunch_sales_total_ly = sum(week_lunch_sales_list_ly[: fiscal_dates["dow"]])
    week_dinner_sales_list_ly = week_dinner_sales_ly[
        week_dinner_sales_ly.daypart == "Dinner"
    ]["sales"].tolist()
    wtd_dinner_sales_total_ly = sum(week_dinner_sales_list_ly[: fiscal_dates["dow"]])

    period_lunch_sales, period_dinner_sales = get_daypart_sales(
        fiscal_dates["start_period"],
        fiscal_dates["period_to_date"],
        session["store_list"],
    )
    # drop date column and group by week
    period_lunch_sales = period_lunch_sales.drop(columns=["date"])
    period_lunch_sales = (
        period_lunch_sales.groupby(["week", "daypart"]).sum().reset_index()
    )
    period_lunch_sales_list = period_lunch_sales["sales"].tolist()
    period_lunch_sales_total = sum(period_lunch_sales_list)
    period_dinner_sales = period_dinner_sales.drop(columns=["date"])
    period_dinner_sales = (
        period_dinner_sales.groupby(["week", "daypart"]).sum().reset_index()
    )
    period_dinner_sales = period_dinner_sales[
        period_dinner_sales["daypart"] == "Dinner"
    ]
    period_dinner_sales_list = period_dinner_sales["sales"].tolist()
    period_dinner_sales_total = sum(period_dinner_sales_list)

    period_lunch_sales_ly, period_dinner_sales_ly = get_daypart_sales(
        fiscal_dates["start_period_ly"],
        fiscal_dates["end_period_ly"],
        session["store_list"],
    )
    ptd_lunch_sales_ly = period_lunch_sales_ly[
        period_lunch_sales_ly["date"] <= fiscal_dates["start_day_ly"]
    ]
    ptd_dinner_sales_ly = period_dinner_sales_ly[
        period_dinner_sales_ly["date"] <= fiscal_dates["start_day_ly"]
    ]
    ptd_lunch_sales_total_ly = ptd_lunch_sales_ly["sales"].sum()
    ptd_dinner_sales_total_ly = ptd_dinner_sales_ly["sales"].sum()

    period_lunch_sales_ly = period_lunch_sales_ly.drop(columns=["date"])
    period_dinner_sales_ly = period_dinner_sales_ly.drop(columns=["date"])
    period_lunch_sales_ly = (
        period_lunch_sales_ly.groupby(["week", "daypart"]).sum().reset_index()
    )
    period_lunch_sales_list_ly = period_lunch_sales_ly["sales"].tolist()
    period_dinner_sales_ly = (
        period_dinner_sales_ly.groupby(["week", "daypart"]).sum().reset_index()
    )
    period_dinner_sales_list_ly = period_dinner_sales_ly["sales"].tolist()

    year_lunch_sales, year_dinner_sales = get_daypart_sales(
        fiscal_dates["start_year"], fiscal_dates["year_to_date"], session["store_list"]
    )
    year_lunch_sales = year_lunch_sales.drop(columns=["date"])
    year_lunch_sales = (
        year_lunch_sales.groupby(["period", "daypart"]).sum().reset_index()
    )
    year_lunch_sales_list = year_lunch_sales["sales"].tolist()
    year_lunch_sales_total = sum(year_lunch_sales_list)
    year_dinner_sales = year_dinner_sales.drop(columns=["date"])
    year_dinner_sales = (
        year_dinner_sales.groupby(["period", "daypart"]).sum().reset_index()
    )
    year_dinner_sales_list = year_dinner_sales["sales"].tolist()
    year_dinner_sales_total = sum(year_dinner_sales_list)

    year_lunch_sales_ly, year_dinner_sales_ly = get_daypart_sales(
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
        session["store_list"],
    )
    ytd_lunch_sales_ly = year_lunch_sales_ly[
        year_lunch_sales_ly["date"] <= fiscal_dates["start_day_ly"]
    ]
    ytd_dinner_sales_ly = year_dinner_sales_ly[
        year_dinner_sales_ly["date"] <= fiscal_dates["start_day_ly"]
    ]
    ytd_lunch_sales_total_ly = ytd_lunch_sales_ly["sales"].sum()
    ytd_dinner_sales_total_ly = ytd_dinner_sales_ly["sales"].sum()

    year_lunch_sales_ly = year_lunch_sales_ly.drop(columns=["date"])
    year_dinner_sales_ly = year_dinner_sales_ly.drop(columns=["date"])
    year_lunch_sales_ly = (
        year_lunch_sales_ly.groupby(["period", "daypart"]).sum().reset_index()
    )
    year_lunch_sales_list_ly = year_lunch_sales_ly["sales"].tolist()
    year_dinner_sales_ly = (
        year_dinner_sales_ly.groupby(["period", "daypart"]).sum().reset_index()
    )
    year_dinner_sales_list_ly = year_dinner_sales_ly["sales"].tolist()
    # calculate percent of sales difference from previous year correcting for division by zero
    if wtd_lunch_sales_total_ly != 0:
        wtd_lunch_sales_pct = (
            (week_lunch_sales_total - wtd_lunch_sales_total_ly)
            / wtd_lunch_sales_total_ly
            * 100
        )
    else:
        wtd_lunch_sales_pct = 0
    if wtd_dinner_sales_total_ly != 0:
        wtd_dinner_sales_pct = (
            (week_dinner_sales_total - wtd_dinner_sales_total_ly)
            / wtd_dinner_sales_total_ly
            * 100
        )
    else:
        wtd_dinner_sales_pct = 0
    if ptd_lunch_sales_total_ly != 0:
        ptd_lunch_sales_pct = (
            (period_lunch_sales_total - ptd_lunch_sales_total_ly)
            / ptd_lunch_sales_total_ly
            * 100
        )
    else:
        ptd_lunch_sales_pct = 0
    if ptd_dinner_sales_total_ly != 0:
        ptd_dinner_sales_pct = (
            (period_dinner_sales_total - ptd_dinner_sales_total_ly)
            / ptd_dinner_sales_total_ly
            * 100
        )
    else:
        ptd_dinner_sales_pct = 0
    if ytd_lunch_sales_total_ly != 0:
        ytd_lunch_sales_pct = (
            (year_lunch_sales_total - ytd_lunch_sales_total_ly)
            / ytd_lunch_sales_total_ly
            * 100
        )
    else:
        ytd_lunch_sales_pct = 0
    if ytd_dinner_sales_total_ly != 0:
        ytd_dinner_sales_pct = (
            (year_dinner_sales_total - ytd_dinner_sales_total_ly)
            / ytd_dinner_sales_total_ly
            * 100
        )
    else:
        ytd_dinner_sales_pct = 0

    # togo sales
    week_togo_sales = get_togo_sales(
        fiscal_dates["start_week"], fiscal_dates["week_to_date"], session["store_list"]
    )
    week_togo_sales_list = week_togo_sales["sales"].tolist()
    week_togo_sales_total = sum(week_togo_sales_list)
    period_togo_sales = get_togo_sales(
        fiscal_dates["start_period"],
        fiscal_dates["period_to_date"],
        session["store_list"],
    )
    period_togo_sales = period_togo_sales.drop(columns=["date"])
    period_togo_sales = period_togo_sales.groupby(["week"]).sum().reset_index()
    period_togo_sales_list = period_togo_sales["sales"].tolist()
    period_togo_sales_total = sum(period_togo_sales_list)
    year_togo_sales = get_togo_sales(
        fiscal_dates["start_year"], fiscal_dates["year_to_date"], session["store_list"]
    )
    year_togo_sales = year_togo_sales.drop(columns=["date"])
    year_togo_sales = year_togo_sales.groupby(["period"]).sum().reset_index()
    year_togo_sales_list = year_togo_sales["sales"].tolist()
    year_togo_sales_total = sum(year_togo_sales_list)

    week_togo_sales_ly = get_togo_sales(
        fiscal_dates["start_week_ly"],
        fiscal_dates["end_week_ly"],
        session["store_list"],
    )
    week_togo_sales_list_ly = week_togo_sales_ly["sales"].tolist()
    wtd_togo_sales_total_ly = sum(week_togo_sales_list_ly[: fiscal_dates["dow"]])
    period_togo_sales_ly = get_togo_sales(
        fiscal_dates["start_period_ly"],
        fiscal_dates["end_period_ly"],
        session["store_list"],
    )
    ptd_togo_sales_ly = period_togo_sales_ly[
        period_togo_sales_ly["date"] <= fiscal_dates["start_day_ly"]
    ]
    ptd_togo_sales_total_ly = sum(ptd_togo_sales_ly["sales"])
    period_togo_sales_ly = period_togo_sales_ly.drop(columns=["date"])
    period_togo_sales_ly = period_togo_sales_ly.groupby(["week"]).sum().reset_index()
    period_togo_sales_list_ly = period_togo_sales_ly["sales"].tolist()
    year_togo_sales_ly = get_togo_sales(
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
        session["store_list"],
    )
    ytd_togo_sales_ly = year_togo_sales_ly[
        year_togo_sales_ly["date"] <= fiscal_dates["start_day_ly"]
    ]
    ytd_togo_sales_total_ly = sum(ytd_togo_sales_ly["sales"])
    year_togo_sales_ly = year_togo_sales_ly.drop(columns=["date"])
    year_togo_sales_ly = year_togo_sales_ly.groupby(["period"]).sum().reset_index()
    year_togo_sales_list_ly = year_togo_sales_ly["sales"].tolist()
    # calculate percent of togo sales difference from previous year correcting for division by zero
    if wtd_togo_sales_total_ly != 0:
        wtd_togo_sales_pct = (
            (week_togo_sales_total - wtd_togo_sales_total_ly)
            / wtd_togo_sales_total_ly
            * 100
        )
    else:
        wtd_togo_sales_pct = 0
    if ptd_togo_sales_total_ly != 0:
        ptd_togo_sales_pct = (
            (period_togo_sales_total - ptd_togo_sales_total_ly)
            / ptd_togo_sales_total_ly
            * 100
        )
    else:
        ptd_togo_sales_pct = 0
    if ytd_togo_sales_total_ly != 0:
        ytd_togo_sales_pct = (
            (year_togo_sales_total - ytd_togo_sales_total_ly)
            / ytd_togo_sales_total_ly
            * 100
        )
    else:
        ytd_togo_sales_pct = 0

    # giftcard sales
    week_giftcard_sales = get_giftcard_sales(
        fiscal_dates["start_week"], fiscal_dates["week_to_date"], session["store_list"]
    )
    week_giftcard_sales_list = week_giftcard_sales["sales"].tolist()
    week_giftcard_sales_total = sum(week_giftcard_sales_list)
    period_giftcard_sales = get_giftcard_sales(
        fiscal_dates["start_period"],
        fiscal_dates["period_to_date"],
        session["store_list"],
    )
    period_giftcard_sales = period_giftcard_sales.drop(columns=["date"])
    period_giftcard_sales = period_giftcard_sales.groupby(["week"]).sum().reset_index()
    period_giftcard_sales_list = period_giftcard_sales["sales"].tolist()
    period_giftcard_sales_total = sum(period_giftcard_sales_list)
    year_giftcard_sales = get_giftcard_sales(
        fiscal_dates["start_year"], fiscal_dates["year_to_date"], session["store_list"]
    )
    year_giftcard_sales = year_giftcard_sales.drop(columns=["date"])
    year_giftcard_sales = year_giftcard_sales.groupby(["period"]).sum().reset_index()
    year_giftcard_sales_list = year_giftcard_sales["sales"].tolist()
    year_giftcard_sales_total = sum(year_giftcard_sales_list)

    # giftcard sales last year
    week_giftcard_sales_ly = get_giftcard_sales(
        fiscal_dates["start_week_ly"],
        fiscal_dates["end_week_ly"],
        session["store_list"],
    )
    week_giftcard_sales_list_ly = week_giftcard_sales_ly["sales"].tolist()
    wtd_giftcard_sales_total_ly = sum(
        week_giftcard_sales_list_ly[: fiscal_dates["dow"]]
    )
    period_giftcard_sales_ly = get_giftcard_sales(
        fiscal_dates["start_period_ly"],
        fiscal_dates["end_period_ly"],
        session["store_list"],
    )
    ptd_giftcard_sales_ly = period_giftcard_sales_ly[
        period_giftcard_sales_ly["date"] <= fiscal_dates["start_day_ly"]
    ]
    ptd_giftcard_sales_total_ly = sum(ptd_giftcard_sales_ly["sales"])
    period_giftcard_sales_ly = period_giftcard_sales_ly.drop(columns=["date"])
    period_giftcard_sales_ly = (
        period_giftcard_sales_ly.groupby(["week"]).sum().reset_index()
    )
    period_giftcard_sales_list_ly = period_giftcard_sales_ly["sales"].tolist()
    year_giftcard_sales_ly = get_giftcard_sales(
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
        session["store_list"],
    )
    ytd_giftcard_sales_ly = year_giftcard_sales_ly[
        year_giftcard_sales_ly["date"] <= fiscal_dates["start_day_ly"]
    ]
    ytd_giftcard_sales_total_ly = sum(ytd_giftcard_sales_ly["sales"])
    year_giftcard_sales_ly = year_giftcard_sales_ly.drop(columns=["date"])
    year_giftcard_sales_ly = (
        year_giftcard_sales_ly.groupby(["period"]).sum().reset_index()
    )
    year_giftcard_sales_list_ly = year_giftcard_sales_ly["sales"].tolist()
    # calculate percent of giftcard sales difference from previous year correcting for division by zero
    if wtd_giftcard_sales_total_ly != 0:
        wtd_giftcard_sales_pct = (
            (week_giftcard_sales_total - wtd_giftcard_sales_total_ly)
            / wtd_giftcard_sales_total_ly
            * 100
        )
    else:
        wtd_giftcard_sales_pct = 0
    if ptd_giftcard_sales_total_ly != 0:
        ptd_giftcard_sales_pct = (
            (period_giftcard_sales_total - ptd_giftcard_sales_total_ly)
            / ptd_giftcard_sales_total_ly
            * 100
        )
    else:
        ptd_giftcard_sales_pct = 0
    if ytd_giftcard_sales_total_ly != 0:
        ytd_giftcard_sales_pct = (
            (year_giftcard_sales_total - ytd_giftcard_sales_total_ly)
            / ytd_giftcard_sales_total_ly
            * 100
        )
    else:
        ytd_giftcard_sales_pct = 0

    # giftcard redeem
    week_giftcard_redeem = get_giftcard_redeem(
        fiscal_dates["start_week"], fiscal_dates["week_to_date"], session["store_list"]
    )
    week_giftcard_redeem_list = week_giftcard_redeem["sales"].tolist()
    week_giftcard_redeem_total = sum(week_giftcard_redeem_list)
    period_giftcard_redeem = get_giftcard_redeem(
        fiscal_dates["start_period"],
        fiscal_dates["period_to_date"],
        session["store_list"],
    )
    period_giftcard_redeem = period_giftcard_redeem.drop(columns=["date"])
    period_giftcard_redeem = (
        period_giftcard_redeem.groupby(["week"]).sum().reset_index()
    )
    period_giftcard_redeem_list = period_giftcard_redeem["sales"].tolist()
    period_giftcard_redeem_total = sum(period_giftcard_redeem_list)
    year_giftcard_redeem = get_giftcard_redeem(
        fiscal_dates["start_year"], fiscal_dates["year_to_date"], session["store_list"]
    )
    year_giftcard_redeem = year_giftcard_redeem.drop(columns=["date"])
    year_giftcard_redeem = year_giftcard_redeem.groupby(["period"]).sum().reset_index()
    year_giftcard_redeem_list = year_giftcard_redeem["sales"].tolist()
    year_giftcard_redeem_total = sum(year_giftcard_redeem_list)

    # giftcard redeem last year
    week_giftcard_redeem_ly = get_giftcard_redeem(
        fiscal_dates["start_week_ly"],
        fiscal_dates["end_week_ly"],
        session["store_list"],
    )
    week_giftcard_redeem_list_ly = week_giftcard_redeem_ly["sales"].tolist()
    wtd_giftcard_redeem_total_ly = sum(
        week_giftcard_redeem_list_ly[: fiscal_dates["dow"]]
    )
    period_giftcard_redeem_ly = get_giftcard_redeem(
        fiscal_dates["start_period_ly"],
        fiscal_dates["end_period_ly"],
        session["store_list"],
    )
    ptd_giftcard_redeem_ly = period_giftcard_redeem_ly[
        period_giftcard_redeem_ly["date"] <= fiscal_dates["start_day_ly"]
    ]
    ptd_giftcard_redeem_total_ly = sum(ptd_giftcard_redeem_ly["sales"])
    period_giftcard_redeem_ly = period_giftcard_redeem_ly.drop(columns=["date"])
    period_giftcard_redeem_ly = (
        period_giftcard_redeem_ly.groupby(["week"]).sum().reset_index()
    )
    period_giftcard_redeem_list_ly = period_giftcard_redeem_ly["sales"].tolist()
    year_giftcard_redeem_ly = get_giftcard_redeem(
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
        session["store_list"],
    )
    ytd_giftcard_redeem_ly = year_giftcard_redeem_ly[
        year_giftcard_redeem_ly["date"] <= fiscal_dates["start_day_ly"]
    ]
    ytd_giftcard_redeem_total_ly = sum(ytd_giftcard_redeem_ly["sales"])
    year_giftcard_redeem_ly = year_giftcard_redeem_ly.drop(columns=["date"])
    year_giftcard_redeem_ly = (
        year_giftcard_redeem_ly.groupby(["period"]).sum().reset_index()
    )
    year_giftcard_redeem_list_ly = year_giftcard_redeem_ly["sales"].tolist()
    # calculate percent of giftcard redeem difference from previous year correcting for division by zero
    if wtd_giftcard_redeem_total_ly != 0:
        wtd_giftcard_redeem_pct = (
            (week_giftcard_redeem_total - wtd_giftcard_redeem_total_ly)
            / wtd_giftcard_redeem_total_ly
            * 100
        )
    else:
        wtd_giftcard_redeem_pct = 0
    if ptd_giftcard_redeem_total_ly != 0:
        ptd_giftcard_redeem_pct = (
            (period_giftcard_redeem_total - ptd_giftcard_redeem_total_ly)
            / ptd_giftcard_redeem_total_ly
            * 100
        )
    else:
        ptd_giftcard_redeem_pct = 0
    if ytd_giftcard_redeem_total_ly != 0:
        ytd_giftcard_redeem_pct = (
            (year_giftcard_redeem_total - ytd_giftcard_redeem_total_ly)
            / ytd_giftcard_redeem_total_ly
            * 100
        )
    else:
        ytd_giftcard_redeem_pct = 0

    #    # giftcard balance
    #    week_giftcard_balance = []
    #    diff = 0
    #    for i in range(len(week_giftcard_sales_list)):
    #        diff += week_giftcard_sales_list[i] - week_giftcard_redeem_list[i]
    #        week_giftcard_balance.append(diff)
    #    week_giftcard_balance_total = sum(week_giftcard_balance)
    #    week_giftcard_balance_ly = []
    #    diff = 0
    #    for i in range(len(week_giftcard_sales_list_ly)):
    #        diff += week_giftcard_sales_list_ly[i] - week_giftcard_redeem_list_ly[i]
    #        week_giftcard_balance_ly.append(diff)
    #    week_giftcard_balance_total_ly = sum(week_giftcard_balance_ly[: fiscal_dates["dow"]])
    #
    #    period_giftcard_balance = []
    #    diff = 0
    #    for i in range(len(period_giftcard_sales_list)):
    #        diff += period_giftcard_sales_list[i] - period_giftcard_redeem_list[i]
    #        period_giftcard_balance.append(diff)
    #
    #    year_giftcard_balance = []
    #    diff = 0
    #    for i in range(len(year_giftcard_sales_list)):
    #        diff += year_giftcard_sales_list[i] - year_giftcard_redeem_list[i]
    #        year_giftcard_balance.append(diff)
    #
    #    if week_giftcard_balance_total_ly != 0:
    #        wtd_giftcard_balance_pct = (
    #            (week_giftcard_balance_total - week_giftcard_balance_total_ly)
    #            / week_giftcard_balance_total_ly
    #            * 100
    #        )
    #    else:
    #        wtd_giftcard_sales_pct = 0
    #    if ptd_giftcard_sales_total_ly != 0:
    #        ptd_giftcard_sales_pct = (
    #            (period_giftcard_sales_total - ptd_giftcard_sales_total_ly)
    #            / ptd_giftcard_sales_total_ly
    #            * 100
    #        )
    #    else:
    #        ptd_giftcard_sales_pct = 0
    #    if ytd_giftcard_sales_total_ly != 0:
    #        ytd_giftcard_sales_pct = (
    #            (year_giftcard_sales_total - ytd_giftcard_sales_total_ly)
    #            / ytd_giftcard_sales_total_ly
    #            * 100
    #        )
    #    else:
    #        ytd_giftcard_sales_pct = 0

    # labor tables

    def get_period_labor(start, end, catg):
        query = (
            db.session.query(
                LaborTotals.date,
                LaborTotals.dow,
                LaborTotals.week,
                LaborTotals.period,
                LaborTotals.year,
                func.sum(LaborTotals.total_hours).label("total_hours"),
                func.sum(LaborTotals.total_dollars).label("total_dollars"),
            )
            .filter(
                LaborTotals.date.between(start, end),
                LaborTotals.category == catg,
                LaborTotals.store == store.name,
            )
            .group_by(
                LaborTotals.date,
                LaborTotals.dow,
                LaborTotals.week,
                LaborTotals.period,
                LaborTotals.year,
            )
            .all()
        )
        return pd.DataFrame.from_records(
            query, columns=["date", "dow", "week", "period", "year", "hours", "dollars"]
        )

    day_host_labor = get_period_labor(
        fiscal_dates["start_day"], fiscal_dates["end_day"], "Host"
    )
    day_host_labor_ly = get_period_labor(
        fiscal_dates["start_day_ly"], fiscal_dates["start_day_ly"], "Host"
    )

    week_host_labor = get_period_labor(
        fiscal_dates["start_week"], fiscal_dates["week_to_date"], "Host"
    )
    week_host_labor_ly = get_period_labor(
        fiscal_dates["start_week_ly"], fiscal_dates["start_day_ly"], "Host"
    )

    period_host_labor = get_period_labor(
        fiscal_dates["start_period"], fiscal_dates["period_to_date"], "Host"
    )
    period_host_labor_ly = get_period_labor(
        fiscal_dates["start_period_ly"], fiscal_dates["start_day_ly"], "Host"
    )

    year_host_labor = get_period_labor(
        fiscal_dates["start_year"], fiscal_dates["year_to_date"], "Host"
    )
    year_host_labor_ly = get_period_labor(
        fiscal_dates["start_year_ly"], fiscal_dates["start_day_ly"], "Host"
    )

    day_host_dollar_ty = day_host_labor["dollars"].sum()
    day_host_pct_ty = day_host_dollar_ty / daily_sales * 100
    day_host_dollar_ly = day_host_labor_ly["dollars"].sum()
    day_host_pct_ly = (day_host_dollar_ly / daily_sales_ly * 100) if daily_sales_ly else 0
    day_host_dollar_var = day_host_dollar_ty - day_host_dollar_ly
    day_host_percent_var = day_host_pct_ty - day_host_pct_ly
    week_host_dollar_ty = week_host_labor["dollars"].sum()
    week_host_pct_ty = week_host_dollar_ty / weekly_sales * 100
    week_host_dollar_ly = week_host_labor_ly["dollars"].sum()
    week_host_pct_ly = (week_host_dollar_ly / weekly_sales_ly * 100) if weekly_sales_ly else 0
    week_host_dollar_var = week_host_dollar_ty - week_host_dollar_ly
    week_host_percent_var = week_host_pct_ty - week_host_pct_ly
    period_host_dollar_ty = period_host_labor["dollars"].sum()
    period_host_pct_ty = period_host_dollar_ty / period_sales * 100
    period_host_dollar_ly = period_host_labor_ly["dollars"].sum()
    period_host_pct_ly = (period_host_dollar_ly / period_sales_ly * 100) if period_sales_ly else 0
    period_host_dollar_var = period_host_dollar_ty - period_host_dollar_ly
    period_host_percent_var = period_host_pct_ty - period_host_pct_ly
    year_host_dollar_ty = year_host_labor["dollars"].sum()
    year_host_pct_ty = year_host_dollar_ty / yearly_sales * 100
    year_host_dollar_ly = year_host_labor_ly["dollars"].sum()
    year_host_pct_ly = (year_host_dollar_ly / yearly_sales_ly * 100) if yearly_sales_ly else 0
    year_host_dollar_var = year_host_dollar_ty - year_host_dollar_ly
    year_host_percent_var = year_host_pct_ty - year_host_pct_ly

    # get food sales to calculate BOH labor
    daily_food_sales = get_category_sales(
        fiscal_dates["start_day"],
        fiscal_dates["end_day"],
        "Food Sales",
        session["store_list"],
    )
    daily_food_sales_ly = get_category_sales(
        fiscal_dates["start_day_ly"],
        fiscal_dates["end_day_ly"],
        "Food Sales",
        session["store_list"],
    )
    weekly_food_sales = get_category_sales(
        fiscal_dates["start_week"],
        fiscal_dates["week_to_date"],
        "Food Sales",
        session["store_list"],
    )
    weekly_food_sales_ly = get_category_sales(
        fiscal_dates["start_week_ly"],
        fiscal_dates["start_day_ly"],
        "Food Sales",
        session["store_list"],
    )
    period_food_sales = get_category_sales(
        fiscal_dates["start_period"],
        fiscal_dates["period_to_date"],
        "Food Sales",
        session["store_list"],
    )
    period_food_sales_ly = get_category_sales(
        fiscal_dates["start_period_ly"],
        fiscal_dates["start_day_ly"],
        "Food Sales",
        session["store_list"],
    )
    year_food_sales = get_category_sales(
        fiscal_dates["start_year"],
        fiscal_dates["year_to_date"],
        "Food Sales",
        session["store_list"],
    )
    year_food_sales_ly = get_category_sales(
        fiscal_dates["start_year_ly"],
        fiscal_dates["start_day_ly"],
        "Food Sales",
        session["store_list"],
    )
    daily_food_sales_total = daily_food_sales["sales"].sum()
    daily_food_sales_total_ly = daily_food_sales_ly["sales"].sum()
    weekly_food_sales_total = weekly_food_sales["sales"].sum()
    weekly_food_sales_total_ly = weekly_food_sales_ly["sales"].sum()
    period_food_sales_total = period_food_sales["sales"].sum()
    period_food_sales_total_ly = period_food_sales_ly["sales"].sum()
    year_food_sales_total = year_food_sales["sales"].sum()
    year_food_sales_total_ly = year_food_sales_ly["sales"].sum()

    day_BOH_labor = get_period_labor(
        fiscal_dates["start_day"], fiscal_dates["end_day"], "Kitchen"
    )
    day_BOH_labor_ly = get_period_labor(
        fiscal_dates["start_day_ly"], fiscal_dates["start_day_ly"], "Kitchen"
    )

    week_BOH_labor = get_period_labor(
        fiscal_dates["start_week"], fiscal_dates["week_to_date"], "Kitchen"
    )
    week_BOH_labor_ly = get_period_labor(
        fiscal_dates["start_week_ly"], fiscal_dates["start_day_ly"], "Kitchen"
    )

    period_BOH_labor = get_period_labor(
        fiscal_dates["start_period"], fiscal_dates["period_to_date"], "Kitchen"
    )
    period_BOH_labor_ly = get_period_labor(
        fiscal_dates["start_period_ly"], fiscal_dates["start_day_ly"], "Kitchen"
    )

    year_BOH_labor = get_period_labor(
        fiscal_dates["start_year"], fiscal_dates["year_to_date"], "Kitchen"
    )
    year_BOH_labor_ly = get_period_labor(
        fiscal_dates["start_year_ly"], fiscal_dates["start_day_ly"], "Kitchen"
    )

    day_BOH_dollar_ty = day_BOH_labor["dollars"].sum()
    day_BOH_pct_ty = day_BOH_dollar_ty / daily_food_sales_total * 100
    day_BOH_dollar_ly = day_BOH_labor_ly["dollars"].sum()
    day_BOH_pct_ly = (day_BOH_dollar_ly / daily_food_sales_total_ly * 100) if daily_food_sales_total_ly else 0
    day_BOH_dollar_var = day_BOH_dollar_ty - day_BOH_dollar_ly
    day_BOH_percent_var = day_BOH_pct_ty - day_BOH_pct_ly
    week_BOH_dollar_ty = week_BOH_labor["dollars"].sum()
    week_BOH_pct_ty = week_BOH_dollar_ty / weekly_food_sales_total * 100
    week_BOH_dollar_ly = week_BOH_labor_ly["dollars"].sum()
    week_BOH_pct_ly = (week_BOH_dollar_ly / weekly_food_sales_total_ly * 100) if weekly_food_sales_total_ly else 0
    week_BOH_dollar_var = week_BOH_dollar_ty - week_BOH_dollar_ly
    week_BOH_percent_var = week_BOH_pct_ty - week_BOH_pct_ly
    period_BOH_dollar_ty = period_BOH_labor["dollars"].sum()
    period_BOH_pct_ty = period_BOH_dollar_ty / period_food_sales_total * 100
    period_BOH_dollar_ly = period_BOH_labor_ly["dollars"].sum()
    period_BOH_pct_ly = (period_BOH_dollar_ly / period_food_sales_total_ly * 100) if period_food_sales_total_ly else 0
    period_BOH_dollar_var = period_BOH_dollar_ty - period_BOH_dollar_ly
    period_BOH_percent_var = period_BOH_pct_ty - period_BOH_pct_ly
    year_BOH_dollar_ty = year_BOH_labor["dollars"].sum()
    year_BOH_pct_ty = year_BOH_dollar_ty / year_food_sales_total * 100
    year_BOH_dollar_ly = year_BOH_labor_ly["dollars"].sum()
    year_BOH_pct_ly = (year_BOH_dollar_ly / year_food_sales_total_ly * 100) if year_food_sales_total_ly else 0
    year_BOH_dollar_var = year_BOH_dollar_ty - year_BOH_dollar_ly
    year_BOH_percent_var = year_BOH_pct_ty - year_BOH_pct_ly

    # Beer Sales
    week_beer_sales = get_category_sales(
        fiscal_dates["start_week"],
        fiscal_dates["start_day"],
        "Beer Sales",
        session["store_list"],
    )
    period_beer_sales = get_category_sales(
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        "Beer Sales",
        session["store_list"],
    )
    year_beer_sales = get_category_sales(
        fiscal_dates["start_year"],
        fiscal_dates["start_day"],
        "Beer Sales",
        session["store_list"],
    )
    week_beer_sales_ly = get_category_sales(
        fiscal_dates["start_week_ly"],
        fiscal_dates["end_week_ly"],
        "Beer Sales",
        session["store_list"],
    )
    period_beer_sales_ly = get_category_sales(
        fiscal_dates["start_period_ly"],
        fiscal_dates["end_period_ly"],
        "Beer Sales",
        session["store_list"],
    )
    year_beer_sales_ly = get_category_sales(
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
        "Beer Sales",
        session["store_list"],
    )

    week_beer_sales_list = week_beer_sales["sales"].tolist()
    week_beer_sales_list_ly = week_beer_sales_ly["sales"].tolist()

    ptd_beer_sales = (
        period_beer_sales[period_beer_sales["date"] <= fiscal_dates["start_day"]]
        .groupby(["week"])
        .sum(numeric_only=True)
        .reset_index()
    )
    ptd_beer_sales_ly = (
        period_beer_sales_ly[
            period_beer_sales_ly["date"] <= fiscal_dates["start_day_ly"]
        ]
        .groupby(["week"])
        .sum(numeric_only=True)
        .reset_index()
    )
    period_beer_sales_list = ptd_beer_sales["sales"].tolist()
    period_beer_sales_by_week_ly = period_beer_sales_ly.groupby("week")["sales"].sum()
    period_beer_sales_list_ly = period_beer_sales_by_week_ly.tolist()

    ytd_beer_sales = (
        year_beer_sales[year_beer_sales["date"] <= fiscal_dates["start_day"]]
        .groupby(["period"])
        .sum(numeric_only=True)
        .reset_index()
    )
    ytd_beer_sales_ly = (
        year_beer_sales_ly[year_beer_sales_ly["date"] <= fiscal_dates["start_day_ly"]]
        .groupby(["period"])
        .sum(numeric_only=True)
        .reset_index()
    )
    year_beer_sales_list = ytd_beer_sales["sales"].tolist()
    year_beer_sales_by_period_ly = year_beer_sales_ly.groupby("period")["sales"].sum()
    year_beer_sales_list_ly = year_beer_sales_by_period_ly.tolist()

    week_beer_sales_total = week_beer_sales["sales"].sum()
    wtd_beer_sales_total_ly = week_beer_sales_ly[
        week_beer_sales_ly["date"] <= fiscal_dates["start_day_ly"]
    ]["sales"].sum()

    period_beer_sales_total = period_beer_sales["sales"].sum()
    if 'sales' in ptd_beer_sales_ly.columns:
        ptd_beer_sales_total_ly = ptd_beer_sales_ly["sales"].sum()
    else:
        ptd_beer_sales_total_ly = 0

    year_beer_sales_total = year_beer_sales["sales"].sum()
    if 'sales' in ytd_beer_sales_ly.columns:
        ytd_beer_sales_total_ly = ytd_beer_sales_ly[year_beer_sales_ly["date"] <= fiscal_dates["start_day"]]["sales"].sum()
    else:
        ytd_beer_sales_total_ly = 0

    if wtd_beer_sales_total_ly != 0:
        wtd_beer_sales_pct = (
            (week_beer_sales_total - wtd_beer_sales_total_ly)
            / wtd_beer_sales_total_ly
            * 100
        )
    else:
        wtd_beer_sales_pct = 0
    if ptd_beer_sales_total_ly != 0:
        ptd_beer_sales_pct = (
            (period_beer_sales_total - ptd_beer_sales_total_ly)
            / ptd_beer_sales_total_ly
            * 100
        )
    else:
        ptd_beer_sales_pct = 0
    if ytd_beer_sales_total_ly != 0:
        ytd_beer_sales_pct = (
            (year_beer_sales_total - ytd_beer_sales_total_ly)
            / ytd_beer_sales_total_ly
            * 100
        )
    else:
        ytd_beer_sales_pct = 0

    # Liquor Sales
    week_liquor_sales = get_category_sales(
        fiscal_dates["start_week"],
        fiscal_dates["start_day"],
        "Liquor Sales",
        session["store_list"],
    )
    period_liquor_sales = get_category_sales(
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        "Liquor Sales",
        session["store_list"],
    )
    year_liquor_sales = get_category_sales(
        fiscal_dates["start_year"],
        fiscal_dates["start_day"],
        "Liquor Sales",
        session["store_list"],
    )
    week_liquor_sales_ly = get_category_sales(
        fiscal_dates["start_week_ly"],
        fiscal_dates["end_week_ly"],
        "Liquor Sales",
        session["store_list"],
    )
    period_liquor_sales_ly = get_category_sales(
        fiscal_dates["start_period_ly"],
        fiscal_dates["end_period_ly"],
        "Liquor Sales",
        session["store_list"],
    )
    year_liquor_sales_ly = get_category_sales(
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
        "Liquor Sales",
        session["store_list"],
    )
    week_liquor_sales_list = week_liquor_sales["sales"].tolist()
    week_liquor_sales_list_ly = week_liquor_sales_ly["sales"].tolist()

    ptd_liquor_sales = (
        period_liquor_sales[period_liquor_sales["date"] <= fiscal_dates["start_day"]]
        .groupby(["week"])
        .sum(numeric_only=True)
        .reset_index()
    )
    ptd_liquor_sales_ly = (
        period_liquor_sales_ly[
            period_liquor_sales_ly["date"] <= fiscal_dates["start_day_ly"]
        ]
        .groupby(["week"])
        .sum(numeric_only=True)
        .reset_index()
    )
    period_liquor_sales_list = ptd_liquor_sales["sales"].tolist()
    period_liquor_sales_by_week_ly = period_liquor_sales_ly.groupby("week")[
        "sales"
    ].sum()
    period_liquor_sales_list_ly = period_liquor_sales_by_week_ly.tolist()

    ytd_liquor_sales = (
        year_liquor_sales[year_liquor_sales["date"] <= fiscal_dates["start_day"]]
        .groupby(["period"])
        .sum(numeric_only=True)
        .reset_index()
    )
    ytd_liquor_sales_ly = (
        year_liquor_sales_ly[
            year_liquor_sales_ly["date"] <= fiscal_dates["start_day_ly"]
        ]
        .groupby(["period"])
        .sum(numeric_only=True)
        .reset_index()
    )
    year_liquor_sales_list = ytd_liquor_sales["sales"].tolist()
    year_liquor_sales_by_period_ly = year_liquor_sales_ly.groupby("period")[
        "sales"
    ].sum()
    year_liquor_sales_list_ly = year_liquor_sales_by_period_ly.tolist()

    week_liquor_sales_total = week_liquor_sales["sales"].sum()
    wtd_liquor_sales_total_ly = week_liquor_sales_ly[
        week_liquor_sales_ly["date"] <= fiscal_dates["start_day_ly"]
    ]["sales"].sum()

    period_liquor_sales_total = period_liquor_sales["sales"].sum()
    if 'sales' in ptd_liquor_sales_ly.columns:
        ptd_liquor_sales_total_ly = ptd_liquor_sales_ly["sales"].sum()
    else:
        ptd_liquor_sales_total_ly = 0

    year_liquor_sales_total = year_liquor_sales["sales"].sum()
    if 'sales' in ytd_liquor_sales_ly.columns:
        ytd_liquor_sales_total_ly = ytd_liquor_sales_ly["sales"].sum()
    else:
        ytd_liquor_sales_total_ly = 0

    if wtd_liquor_sales_total_ly != 0:
        wtd_liquor_sales_pct = (
            (week_liquor_sales_total - wtd_liquor_sales_total_ly)
            / wtd_liquor_sales_total_ly
            * 100
        )
    else:
        wtd_liquor_sales_pct = 0
    if ptd_liquor_sales_total_ly != 0:
        ptd_liquor_sales_pct = (
            (period_liquor_sales_total - ptd_liquor_sales_total_ly)
            / ptd_liquor_sales_total_ly
            * 100
        )
    else:
        ptd_liquor_sales_pct = 0
    if ytd_liquor_sales_total_ly != 0:
        ytd_liquor_sales_pct = (
            (year_liquor_sales_total - ytd_liquor_sales_total_ly)
            / ytd_liquor_sales_total_ly
            * 100
        )
    else:
        ytd_liquor_sales_pct = 0

    # Wine Sales
    week_wine_sales = get_category_sales(
        fiscal_dates["start_week"],
        fiscal_dates["start_day"],
        "Wine Sales",
        session["store_list"],
    )
    period_wine_sales = get_category_sales(
        fiscal_dates["start_period"],
        fiscal_dates["start_day"],
        "Wine Sales",
        session["store_list"],
    )
    year_wine_sales = get_category_sales(
        fiscal_dates["start_year"],
        fiscal_dates["start_day"],
        "Wine Sales",
        session["store_list"],
    )
    week_wine_sales_ly = get_category_sales(
        fiscal_dates["start_week_ly"],
        fiscal_dates["end_week_ly"],
        "Wine Sales",
        session["store_list"],
    )
    period_wine_sales_ly = get_category_sales(
        fiscal_dates["start_period_ly"],
        fiscal_dates["end_period_ly"],
        "Wine Sales",
        session["store_list"],
    )
    year_wine_sales_ly = get_category_sales(
        fiscal_dates["start_year_ly"],
        fiscal_dates["end_year_ly"],
        "Wine Sales",
        session["store_list"],
    )
    week_wine_sales_list = week_wine_sales["sales"].tolist()
    week_wine_sales_list_ly = week_wine_sales_ly["sales"].tolist()

    ptd_wine_sales = (
        period_wine_sales[period_wine_sales["date"] <= fiscal_dates["start_day"]]
        .groupby(["week"])
        .sum(numeric_only=True)
        .reset_index()
    )
    ptd_wine_sales_ly = (
        period_wine_sales_ly[
            period_wine_sales_ly["date"] <= fiscal_dates["start_day_ly"]
        ]
        .groupby(["week"])
        .sum(numeric_only=True)
        .reset_index()
    )
    period_wine_sales_list = ptd_wine_sales["sales"].tolist()
    period_wine_sales_by_week_ly = period_wine_sales_ly.groupby("week")["sales"].sum()
    period_wine_sales_list_ly = period_wine_sales_by_week_ly.tolist()

    ytd_wine_sales = (
        year_wine_sales[year_wine_sales["date"] <= fiscal_dates["start_day"]]
        .groupby(["period"])
        .sum(numeric_only=True)
        .reset_index()
    )
    ytd_wine_sales_ly = (
        year_wine_sales_ly[year_wine_sales_ly["date"] <= fiscal_dates["start_day_ly"]]
        .groupby(["period"])
        .sum(numeric_only=True)
        .reset_index()
    )
    year_wine_sales_list = ytd_wine_sales["sales"].tolist()
    year_wine_sales_by_period_ly = year_wine_sales_ly.groupby("period")["sales"].sum()
    year_wine_sales_list_ly = year_wine_sales_by_period_ly.tolist()

    week_wine_sales_total = week_wine_sales["sales"].sum()
    wtd_wine_sales_total_ly = week_wine_sales_ly[
        week_wine_sales_ly["date"] <= fiscal_dates["start_day_ly"]
    ]["sales"].sum()

    period_wine_sales_total = period_wine_sales["sales"].sum()
    if 'sales' in ptd_wine_sales_ly.columns:
        ptd_wine_sales_total_ly = ptd_wine_sales_ly["sales"].sum()
    else:
        ptd_wine_sales_total_ly = 0

    year_wine_sales_total = year_wine_sales["sales"].sum()
    if 'sales' in ytd_wine_sales_ly.columns:
        ytd_wine_sales_total_ly = ytd_wine_sales_ly["sales"].sum()
    else:
        ytd_wine_sales_total_ly = 0

    if wtd_wine_sales_total_ly != 0:
        wtd_wine_sales_pct = (
            (week_wine_sales_total - wtd_wine_sales_total_ly)
            / wtd_wine_sales_total_ly
            * 100
        )
    else:
        wtd_wine_sales_pct = 0
    if ptd_wine_sales_total_ly != 0:
        ptd_wine_sales_pct = (
            (period_wine_sales_total - ptd_wine_sales_total_ly)
            / ptd_wine_sales_total_ly
            * 100
        )
    else:
        ptd_wine_sales_pct = 0
    if ytd_wine_sales_total_ly != 0:
        ytd_wine_sales_pct = (
            (year_wine_sales_total - ytd_wine_sales_total_ly)
            / ytd_wine_sales_total_ly
            * 100
        )
    else:
        ytd_wine_sales_pct = 0

    # TODO this code fails because empty index
    # df["store"] = data[0]

    # # service duration Charts
    # table_turn_df = get_timeing_data(
    #     fiscal_dates["start_week"], fiscal_dates["start_day"], session["store_list"]
    # )
    # bar_list = table_turn_df["bar"].tolist()
    # dining_room_list = table_turn_df["dining_room"].tolist()
    # handheld_list = table_turn_df["handheld"].tolist()
    # patio_list = table_turn_df["patio"].tolist()
    # online_ordering_list = table_turn_df["online_ordering"].tolist()

    # table_turn_df_avg = get_timeing_data(
    #     fiscal_dates["start_period"], fiscal_dates["start_day"], session["store_list"]
    # )
    # # pivot table on dow to get average time
    # table_turn_df_avg = table_turn_df_avg.pivot_table(
    #     values=["bar", "dining_room", "handheld", "patio", "online_ordering"],
    #     index=["dow"],
    #     aggfunc="mean",
    # )
    # bar_list_avg = table_turn_df_avg["bar"].tolist()
    # dining_room_list_avg = table_turn_df_avg["dining_room"].tolist()
    # handheld_list_avg = table_turn_df_avg["handheld"].tolist()
    # patio_list_avg = table_turn_df_avg["patio"].tolist()
    # online_ordering_list_avg = table_turn_df_avg["online_ordering"].tolist()

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
    fiscal_dates = set_dates(session["date_selected"])
    form1 = DateForm()
    form4 = PotatoForm()
    form5 = LobsterForm()
    form6 = StoneForm()
    if form1.submit1.data and form1.validate():
        """ """
        session["date_selected"] = form1.selectdate.data
        return redirect(url_for("home_blueprint.marketing"))

    form3 = StoreForm()
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
                    )  # noqa E712
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
        for x in data:
            # select only 1 store for store page
            if x.id in session["store_list"]:
                store_id = x.id
                break
        session["date_selected"] = fiscal_dates["start_day"]
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    if form4.submit4.data and form4.validate():
        store_id = form4.store.data.id
        return redirect(url_for("home_blueprint.potato", store_id=store_id))

    if form5.submit5.data and form5.validate():
        store_id = form5.store.data.id
        return redirect(url_for("home_blueprint.lobster", store_id=store_id))

    if form6.submit6.data and form6.validate():
        store_id = form6.store.data.id
        return redirect(url_for("home_blueprint.stone", store_id=store_id))

    # Gift Card Sales

    def get_giftcard_sales(start, end):
        chart = (
            db.session.query(
                GiftCardSales.period,
                func.sum(GiftCardSales.amount).label("sales"),
                func.sum(GiftCardSales.quantity).label("count"),
            )
            .select_from(GiftCardSales)
            .filter(GiftCardSales.date.between(start, end))
            .group_by(GiftCardSales.period)
        )
        value = []
        number = []
        for p in period_order:
            for v in chart:
                if v.period == p:
                    value.append(int(v.sales))
                    number.append(int(v.count))

        return value, number

    def get_giftcard_payments(start, end):
        chart = (
            db.session.query(
                GiftCardRedeem.period, func.sum(GiftCardRedeem.amount).label("sales")
            )
            .select_from(GiftCardRedeem)
            .filter(GiftCardRedeem.date.between(start, end))
            .group_by(GiftCardRedeem.period)
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

    giftcard_sales, giftcard_count = get_giftcard_sales(
        fiscal_dates["last_threesixtyfive"], fiscal_dates["start_day"]
    )
    giftcard_payments = get_giftcard_payments(
        fiscal_dates["last_threesixtyfive"], fiscal_dates["start_day"]
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
                GiftCardSales.name,
                func.sum(GiftCardSales.amount).label("sales"),
                func.sum(GiftCardSales.quantity).label("count"),
            )
            .filter(
                GiftCardSales.date.between(start, end),
            )
            .group_by(GiftCardSales.name)
        ).all()
        sales = pd.DataFrame.from_records(
            query, columns=["store", "amount", "quantity"]
        )
        sales.sort_values(by=["amount"], ascending=False, inplace=True)
        sales.loc["TOTALS"] = sales.sum(numeric_only=True)
        return sales

    def get_giftcard_payments_per_store(start, end):
        # data = Restaurants.query.with_entities(Restaurants.name, Restaurants.id).all()
        # df_loc = pd.DataFrame([x.as_dict() for x in data])
        # df_loc.rename(
        #    columns={
        #        "id": "name",
        #    },
        #    inplace=True,
        # )

        query = (
            db.session.query(
                GiftCardRedeem.name,
                GiftCardRedeem.period,
                func.sum(GiftCardRedeem.amount).label("payment"),
            )
            .filter(
                GiftCardRedeem.date.between(start, end),
            )
            .group_by(GiftCardRedeem.name, GiftCardRedeem.period)
        ).all()

        payments = pd.DataFrame.from_records(
            query, columns=["name", "payment", "period"]
        )
        payments.sort_values(by=["payment"], ascending=False, inplace=True)

        payments.loc["TOTALS"] = payments.sum(numeric_only=True)
        return payments

    gift_card_sales = get_giftcard_sales_per_store(
        fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    gift_card_payments = get_giftcard_payments_per_store(
        fiscal_dates["start_year"], fiscal_dates["end_year"]
    )
    gift_card_sales = gift_card_sales.merge(
        gift_card_payments, left_on="store", right_on="name"
    )
    gift_card_sales["diff"] = gift_card_sales["amount"] - gift_card_sales["payment"]
    gift_card_sales.sort_values(by=["diff"], ascending=False, inplace=True)

    return render_template(
        "home/marketing.html",
        title="Marketing",
        company_name=Config.COMPANY_NAME,
        segment="marketing",
        roles=current_user.roles,
        **locals(),
    )


@blueprint.route("/support/", methods=["GET", "POST"])
@login_required
@roles_accepted("admin")
def support():
    TODAY = datetime.date(datetime.now())

    fiscal_dates = set_dates(session["date_selected"])

    form1 = DateForm()
    form2 = UpdateForm()
    form3 = StoreForm()
    form4 = PotatoForm()
    form5 = LobsterForm()
    form6 = StoneForm()

    if form1.submit1.data and form1.validate():
        """ """
        session["date_selected"] = form1.selectdate.data
        return redirect(url_for("home_blueprint.support"))

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
                    )  # noqa E712
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
        for x in data:
            # select only 1 store for store page
            if x.id in session["store_list"]:
                store_id = x.id
                break
        return redirect(url_for("home_blueprint.store", store_id=store_id))

    if form4.submit4.data and form4.validate():
        store_id = form4.store.data.id
        return redirect(url_for("home_blueprint.potato", store_id=store_id))

    if form5.submit5.data and form5.validate():
        store_id = form5.store.data.id
        return redirect(url_for("home_blueprint.lobster", store_id=store_id))

    if form6.submit6.data and form6.validate():
        store_id = form6.store.data.id
        return redirect(url_for("home_blueprint.stone", store_id=store_id))

    query = (
        db.session.query(
            Users.first_name,
            Users.last_name,
            Users.id,
            Users.email,
            Users.active,
            Users.confirmed_at,
            Users.last_login_at,
            Users.current_login_at,
            Users.login_count,
        )
        .order_by(Users.current_login_at.desc())
        .all()
    )
    user_table = pd.DataFrame.from_records(
        query,
        columns=[
            "first_name",
            "last_name",
            "id",
            "email",
            "active",
            "confirmed_at",
            "last_login_at",
            "current_login_at",
            "login_count",
        ],
    )
    # get interger from confirmed_at till today
    user_table["days_since_confirmed"] = user_table["confirmed_at"].apply(
        lambda x: (TODAY - x).days
    )
    no_login = user_table[user_table["current_login_at"].isnull()]
    no_login = no_login.sort_values(by=["confirmed_at"], ascending=True)
    lapsed_users = user_table[
        user_table["current_login_at"] < TODAY - timedelta(days=30)
    ].sort_values(by=["current_login_at"], ascending=True)
    users_this_week = user_table[
        user_table["current_login_at"] >= TODAY - timedelta(days=7)
    ]
    # sort by last login
    users_this_week = users_this_week.sort_values(
        by=["current_login_at"], ascending=False
    )

    # DO NOT USE items on stock count
    query = (
        db.session.query(StockCount.store, StockCount.item)
        .filter(
            StockCount.date >= fiscal_dates["start_week"],
            StockCount.item.regexp_match("^DO NOT USE*"),
        )
        .group_by(StockCount.store, StockCount.item)
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

    fiscal_dates = set_dates(session["date_selected"])
    form1 = DateForm()
    form3 = StoreForm()
    form4 = PotatoForm()
    form5 = LobsterForm()
    form6 = StoneForm()

    if form1.submit1.data and form1.validate():
        session["date_selected"] = form1.selectdate.data
        return redirect(url_for("home_blueprint.profile"))

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
                    )  # noqa E712
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
        return redirect(url_for("home_blueprint.profile"))

    if form4.submit4.data and form4.validate():
        store_id = form4.store.data.id
        return redirect(url_for("home_blueprint.potato", store_id=store_id))

    if form5.submit5.data and form5.validate():
        store_id = form5.store.data.id
        return redirect(url_for("home_blueprint.lobster", store_id=store_id))

    if form6.submit6.data and form6.validate():
        store_id = form6.store.data.id
        return redirect(url_for("home_blueprint.stone", store_id=store_id))

    store_list = [x.name for x in current_user.stores]

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
    TODAY = datetime.date(datetime.now())
    fiscal_dates = set_dates(datetime.date(datetime.now()))

    store = Restaurants.query.filter_by(id=store_id).first()

    load_times = pd.read_sql_table("potato_load_times", con=db.engine)
    pot_df = pd.DataFrame(columns=["time", "in_time", "out_time"])
    for num in [7, 14, 21, 28]:
        day_pot_sales = pd.DataFrame(
            columns=["time", "in_time", "out_time", "quantity"]
        )
        for index, row in load_times.iterrows():
            query = (
                db.session.query(
                    func.sum(PotatoSales.quantity).label("quantity")
                ).filter(
                    PotatoSales.time.between(row["start_time"], row["stop_time"]),
                    PotatoSales.dow == fiscal_dates["dow"],
                    PotatoSales.name == store.name,
                    PotatoSales.date == TODAY - timedelta(days=num),
                )
            ).all()
            day_pot_sales = pd.concat(
                [
                    day_pot_sales,
                    pd.DataFrame(
                        {
                            "time": [row["time"]],
                            "in_time": [row["in_time"]],
                            "out_time": [row["out_time"]],
                            "quantity": [query[0][0]],
                        }
                    ),
                ],
                ignore_index=True,
            )
        pot_df = pot_df.merge(
            day_pot_sales,
            on=["time", "in_time", "out_time"],
            how="outer",
            suffixes=("", f"_{num}"),
        )

    pot_df.fillna(0, inplace=True)
    pot_df.loc[:, "AVG"] = pot_df.mean(numeric_only=True, axis=1)
    pot_df.loc[:, "MEDIAN"] = pot_df.median(numeric_only=True, axis=1)
    pot_df.loc[:, "MAX"] = pot_df.max(numeric_only=True, axis=1)

    # out_times = pd.read_csv("/usr/local/share/potatochart.csv", usecols=["time", "in_time", "out_time"])
    # out_times = pd.read_sql_table('PotatoLoadTimes', con=db.engine, columns=["time", "in_time", "out_time"])
    # rotation = pot_df.merge(out_times, on="time", how="left")
    pot_df.loc["TOTALS"] = pot_df.sum(numeric_only=True)

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
    for k, v in pot_df.iterrows():
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


@blueprint.route("/<int:store_id>/lobster/", methods=["GET", "POST"])
@login_required
def lobster(store_id):
    TODAY = datetime.date(datetime.now())
    fiscal_dates = set_dates(session["date_selected"])

    store = Restaurants.query.filter_by(id=store_id).first()

    live_lobster_avg_cost = get_item_avg_cost(
        "SEAFOOD Lobster Live Maine",
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
    pdf.cell(
        col_width,
        th,
        "${:,.2f}".format(round(live_lobster_avg_cost, 2)),
        align="R",
        border=1,
    )
    pdf.ln(2 * th)
    pdf.cell(size_width, th, str("Size"), border=1)
    pdf.cell(col_width, th, str("Cost"), border=1)
    pdf.cell(col_width, th, str("Price @40%"), border=1)
    pdf.ln(th)

    for v in lobster_items["lobster_sizes"]:
        pdf.cell(size_width, th, str(v["item"]), border=1)
        pdf.cell(
            col_width,
            th,
            "${:,.2f}".format(round(live_lobster_avg_cost * v["factor"], 2)),
            align="R",
            border=1,
        )
        pdf.cell(
            col_width,
            th,
            "${:,.2f}".format(round(live_lobster_avg_cost * v["factor"] / 0.4)),
            align="R",
            border=1,
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
    fiscal_dates = set_dates(session["date_selected"])

    store = Restaurants.query.filter_by(id=store_id).first()

    stone_claw_avg_cost = get_item_avg_cost(
        "SEAFOOD Crab Stone Claws",
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
    pdf.cell(
        col_width,
        th,
        "${:,.2f}".format(round(stone_claw_avg_cost, 2)),
        align="R",
        border=1,
    )
    pdf.ln(2 * th)
    pdf.cell(size_width, th, str("Size"), border=1)
    pdf.cell(col_width, th, str("Cost"), border=1)
    pdf.cell(col_width, th, str("Price @40%"), border=1)
    pdf.ln(th)

    for v in stone_items["stone_sizes"]:
        pdf.cell(size_width, th, str(v["item"]), border=1)
        pdf.cell(
            col_width,
            th,
            "${:,.2f}".format(round(stone_claw_avg_cost * v["factor"], 2)),
            align="R",
            border=1,
        )
        pdf.cell(
            col_width,
            th,
            "${:,.2f}".format(round(stone_claw_avg_cost * v["factor"] / 0.4)),
            align="R",
            border=1,
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
        headers={"Content-Disposition": "attachment;filename=stone_claw_prices.pdf"},
    )
