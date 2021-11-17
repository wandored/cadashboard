# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
Modified by wandored
"""

from flask.helpers import url_for
from sqlalchemy.util.langhelpers import NoneType
from dashapp.home import blueprint
from flask import render_template, session, request, redirect, url_for
from dashapp.home.util import query_sales, query_labor, get_period
from flask_login import login_required
from jinja2 import TemplateNotFound
from datetime import datetime, timedelta
from dashapp.authentication.forms import DateForm
from dashapp import Config

@blueprint.route('/index', methods=["GET", "POST"])
@login_required
def index(targetdate=None):
    fiscal_dates = get_period(datetime.strptime(session['targetdate'], "%Y-%m-%d"))
    start_day = end_day = start_week = end_week = ""
    form = DateForm()
    # Get Data
    if  form.validate_on_submit():
        ''' update screen with new date '''
        session['targetdate'] = form.selectdate.data.strftime("%Y-%m-%d")
        return redirect(url_for('home_blueprint.index'))


    for i in fiscal_dates:
        day_start = datetime.strptime(i.date, "%m/%d/%Y")
        day_end = day_start + timedelta(days=1)
        week_start = datetime.strptime(i.week_start, "%m/%d/%Y")
        week_end = datetime.strptime(i.week_end, "%m/%d/%Y")
#        period_start = datetime.strptime(i.period_start, "%m/%d/%Y")
#        period_end = datetime.strptime(i.period_end, "%m/%d/%Y")

        start_day = day_start.strftime("%Y-%m-%d")
        end_day = day_end.strftime("%Y-%m-%d")
        start_week = week_start.strftime("%Y-%m-%d")
        end_week = week_end.strftime("%Y-%m-%d")
#        start_period = period_start.strftime("%Y-%m-%d")
#        end_period = period_end.strftime("%Y-%m-%d")

    # SalesEmployee
    daily_sales = query_sales(start_day, end_day)
    weekly_sales = query_sales(start_week, end_week)
    daily_sales_totals = daily_sales.loc['Totals',]
    weekly_sales_totals = weekly_sales.loc['Totals',]
    # LaborDetail
    daily_labor = query_labor(start_day, end_day)
    weekly_labor = query_labor(start_week, end_week)
    daily_labor_totals = daily_labor.loc['Totals',]
    weekly_labor_totals = weekly_labor.loc['Totals',]
    dailySalesLabor = daily_sales.merge(daily_labor, on='LocationName')


    return render_template(
        'home/index.html',
        form=form,
        segment='index',
        fiscal_dates=fiscal_dates,
        daily_sales=daily_sales,
        weekly_sales=weekly_sales,
        daily_sales_totals=daily_sales_totals,
        dailySalesLabor=dailySalesLabor,
        weekly_sales_totals=weekly_sales_totals
    )


@blueprint.route('/<template>')
@login_required
def route_template(template):

    try:

        if not template.endswith('.html'):
            template += '.html'

        # Detect the current page
        segment = get_segment(request)

        # Serve the file (if exists) from app/templates/home/FILE.html
        return render_template("home/" + template, segment=segment)

    except TemplateNotFound:
        return render_template('home/page-404.html'), 404

    except:
        return render_template('home/page-500.html'), 500


# Helper - Extract current page name from request
def get_segment(request):

    try:

        segment = request.path.split('/')[-1]

        if segment == '':
            segment = 'index'

        return segment

    except:
        return None
