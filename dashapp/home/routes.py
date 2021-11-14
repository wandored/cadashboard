# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
Modified by wandored
"""

from flask.helpers import url_for
from sqlalchemy.util.langhelpers import NoneType
from dashapp.home import blueprint
from flask import render_template, session, request, redirect, url_for
from dashapp.home.util import daily_sales
from flask_login import login_required
from jinja2 import TemplateNotFound
from datetime import datetime, timedelta
from dashapp.authentication.forms import DateForm
from dashapp import Config

@blueprint.route('/index', methods=["GET", "POST"])
@login_required
def index(targetdate=None):
    startdate = datetime.strptime(session['targetdate'], "%Y-%m-%d")
    enddate = startdate + timedelta(days = 1)
    start = startdate.strftime('%Y-%m-%d')
    end = enddate.strftime('%Y-%m-%d')
    form = DateForm()
    # Get Data
    if  form.validate_on_submit():
        session['targetdate'] = form.selectdate.data.strftime("%Y-%m-%d")
        return redirect(url_for('home_blueprint.index'))

    net_sales = daily_sales(start, end)
    totals = net_sales.loc['Totals',]

    return render_template(
        'home/index.html',
        form=form,
        segment='index',
        startdate=start,
        net_sales=net_sales,
        totals=totals
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
