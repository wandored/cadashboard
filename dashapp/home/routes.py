# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
Modified by wandored
"""

from flask.helpers import url_for
import pandas as pd
from sqlalchemy.util.langhelpers import NoneType
from dashapp.home import blueprint
from flask import flash, render_template, session, request, redirect, url_for
from dashapp.home.util import labor_detail, get_period, get_lastyear, sales_employee
from flask_login import login_required
from jinja2 import TemplateNotFound
from datetime import datetime, timedelta
from dashapp import Config, db
from dashapp.authentication.forms import DateForm
from dashapp.authentication.models import Calendar, Sales, Labor
from dashapp import Config
from sqlalchemy import and_, func


@blueprint.route('/index', methods=["GET", "POST"])
@login_required
def index(targetdate=None):
    fiscal_dates = get_period(datetime.strptime(session['targetdate'], "%Y-%m-%d"))
    start_day = end_day = start_week = end_week = start_period = end_period = start_year = end_year = calendar_day = ""
    form = DateForm()
    # Get Data
    if  form.validate_on_submit():
        ''' update screen with new date '''
        session['targetdate'] = form.selectdate.data.strftime("%Y-%m-%d")
        return redirect(url_for('home_blueprint.index'))


    for i in fiscal_dates:
        day_start = datetime.strptime(i.date, "%Y-%m-%d")
        day_end = day_start + timedelta(days=1)
        week_start = datetime.strptime(i.week_start, "%Y-%m-%d")
        week_end = datetime.strptime(i.week_end, "%Y-%m-%d")
        period_start = datetime.strptime(i.period_start, "%Y-%m-%d")
        period_end = datetime.strptime(i.period_end, "%Y-%m-%d")
        year_start = datetime.strptime(i.year_start, "%Y-%m-%d")
        year_end = datetime.strptime(i.year_end, "%Y-%m-%d")

        start_day = day_start.strftime("%Y-%m-%d")
        end_day = day_end.strftime("%Y-%m-%d")
        start_week = week_start.strftime("%Y-%m-%d")
        end_week = week_end.strftime("%Y-%m-%d")
        start_period = period_start.strftime("%Y-%m-%d")
        end_period = period_end.strftime("%Y-%m-%d")
        start_year = year_start.strftime("%Y-%m-%d")
        end_year = year_end.strftime("%Y-%m-%d")


    # Get matching day, week and period start and end dates
    start_day_ly = get_lastyear(start_day)
    end_day_ly = get_lastyear(end_day)
    start_week_ly = get_lastyear(start_week)
    end_week_ly = get_lastyear(end_week)
    start_period_ly = get_lastyear(start_period)
    end_period_ly = get_lastyear(end_period)
    start_year_ly = get_lastyear(start_year)
    end_year_ly = get_lastyear(end_year)

    # Get the Day Of Week integer
    last_day = Calendar.query.filter_by(date=start_day).first()
    WTD = last_day.dow
    print(f'this is the {WTD} dow')

    # SalesEmployee
    # delete current days data from database and replace with fresh data
    Sales.query.filter_by(date=start_day).delete()
    db.session.commit()
    baddates = sales_employee(start_day, end_day)

    if baddates == 1:
        flash(f'The date you selected does not have sales.  Please select another date!', 'warning')
        session['targetdate'] = Config.YSTDAY.strftime('%Y-%m-%d')
        return redirect(url_for('home_blueprint.index'))

    # query dail, weekly, period sales
#    daily_sales = (
#        db.session.query(
#            Sales,
#            func.sum(Sales.sales).label('total_sales'),
#            func.sum(Sales.guests).label('total_guests'),
#        )
#        .filter(
#            Sales.date == start_day,
#        )
#        .all()
#    )
#
#    daily_sales_ly = (
#        db.session.query(
#            Sales,
#            func.sum(Sales.sales).label('total_sales'),
#            func.sum(Sales.guests).label('total_guests'),
#        )
#        .filter(
#            Sales.date == start_day_ly,
#        )
#        .all()
#    )

    weekly_sales = (
        db.session.query(
            Sales,
            func.sum(Sales.sales).label('total_sales'),
            func.sum(Sales.guests).label('total_guests'),
        )
        .filter(
            Sales.date >= start_week,
            Sales.date <= end_week,
        )
        .all()
    )

    weekly_sales_ly = (
        db.session.query(
            Sales,
            func.sum(Sales.sales).label('total_sales'),
            func.sum(Sales.guests).label('total_guests'),
        )
        .filter(
            Sales.date >= start_week_ly,
            Sales.date <= end_week_ly,
        )
        .all()
    )

    period_sales = (
        db.session.query(
            Sales,
            func.sum(Sales.sales).label('total_sales'),
            func.sum(Sales.guests).label('total_guests'),
        )
        .filter(
            Sales.date >= start_period,
            Sales.date <end_period,
        )
        .all()
    )

    period_sales_ly = (
        db.session.query(
            Sales,
            func.sum(Sales.sales).label('total_sales'),
            func.sum(Sales.guests).label('total_guests'),
        )
        .filter(
            Sales.date >= start_period_ly,
            Sales.date <= end_period_ly,
        )
        .all()
    )

    yearly_sales = (
        db.session.query(
            Sales,
            func.sum(Sales.sales).label('total_sales'),
            func.sum(Sales.guests).label('total_guests'),
        )
        .filter(
            Sales.date >= start_year,
            Sales.date <end_year,
        )
        .all()
    )

    yearly_sales_ly = (
        db.session.query(
            Sales,
            func.sum(Sales.sales).label('total_sales'),
            func.sum(Sales.guests).label('total_guests'),
        )
        .filter(
            Sales.date >= start_year_ly,
            Sales.date <= end_year_ly,
        )
        .all()
    )

    # LaborDetail
    Labor.query.filter_by(date=start_day).delete()
    db.session.commit()
    labor_detail(start_day, end_day)

    # query dail, weekly, period labor
#    daily_labor = (
#        db.session.query(
#            Labor,
#            func.sum(Labor.dollars).label('total_dollars'),
#            func.sum(Labor.hours).label('total_hours'),
#        )
#        .filter(Labor.date == start_day).all()
#    )
#
#    daily_labor_ly = (
#        db.session.query(
#            Labor,
#            func.sum(Labor.dollars).label('total_dollars'),
#            func.sum(Labor.hours).label('total_hours'),
#        )
#        .filter(
#            Labor.date == start_day_ly,
#        )
#        .all()
#    )

    weekly_labor = (
        db.session.query(
            Labor,
            func.sum(Labor.dollars).label('total_dollars'),
            func.sum(Labor.hours).label('total_hours'),
        )
        .filter(
            Labor.date >= start_week,
            Labor.date <= end_week,
        )
        .all()
    )

    weekly_labor_ly = (
        db.session.query(
            Labor,
            func.sum(Labor.dollars).label('total_dollars'),
            func.sum(Labor.hours).label('total_hours'),
        )
        .filter(
            Labor.date >= start_week_ly,
            Labor.date <= end_week_ly,
        )
        .all()
    )

    period_labor = (
        db.session.query(
            Labor,
            func.sum(Labor.dollars).label('total_dollars'),
            func.sum(Labor.hours).label('total_hours'),
        )
        .filter(
            Labor.date >= start_period,
            Labor.date <end_period,
        )
        .all()
    )

    period_labor_ly = (
        db.session.query(
            Labor,
            func.sum(Labor.dollars).label('total_dollars'),
            func.sum(Labor.hours).label('total_hours'),
        )
        .filter(
            Labor.date >= start_period_ly,
            Labor.date <= end_period_ly,
        )
        .all()
    )

    # Daily Chart
    daily_chart = db.session.query(Sales,
                                   func.sum(Sales.sales).label('total_sales')
                                   ).filter(Sales.date >= start_week,
                                           Sales.date <= end_week
                                            ).group_by(Sales.date
                                                       ).order_by(Sales.date)
    values1 = []
    for v in daily_chart:
        values1.append(v.total_sales)

    daily_chart_ly = db.session.query(Sales,
                                   func.sum(Sales.sales).label('total_sales')
                                   ).filter(Sales.date >= start_week_ly,
                                           Sales.date <= end_week_ly
                                            ).group_by(Sales.date
                                                       ).order_by(Sales.date)
    values1_ly = []
    for v in daily_chart_ly:
        values1_ly.append(v.total_sales)

    # Weekly Chart
    weekly_chart = db.session.query(Sales,
                                   func.sum(Sales.sales).label('total_sales')
                                    ).select_from(Sales).join(Calendar, Calendar.date == Sales.date
                                    ).group_by(Calendar.week
                                    ).filter(Sales.date >= start_period,
                                           Sales.date <= end_period
                                            )
    values2 = []
    for v in weekly_chart:
        values2.append(v.total_sales)

    weekly_chart_ly = db.session.query(Sales,
                                   func.sum(Sales.sales).label('total_sales')
                                    ).select_from(Sales).join(Calendar, Calendar.date == Sales.date
                                    ).group_by(Calendar.week
                                    ).filter(Sales.date >= start_period_ly,
                                           Sales.date <= end_period_ly
                                            )
    values2_ly = []
    for v in weekly_chart_ly:
        values2_ly.append(v.total_sales)

    # Yearly Chart
    period_chart = db.session.query(Sales,
                                   func.sum(Sales.sales).label('total_sales')
                                    ).select_from(Sales).join(Calendar, Calendar.date == Sales.date
                                    ).group_by(Calendar.period
                                    ).filter(Sales.date >= start_year,
                                           Sales.date <= end_year
                                            )
    values3 = []
    for v in period_chart:
        values3.append(v.total_sales)

    period_chart_ly = db.session.query(Sales,
                                   func.sum(Sales.sales).label('total_sales')
                                    ).select_from(Sales).join(Calendar, Calendar.date == Sales.date
                                    ).group_by(Calendar.period
                                    ).filter(Sales.date >= start_year_ly,
                                           Sales.date <= end_year_ly
                                            )
    values3_ly = []
    for v in period_chart_ly:
        values3_ly.append(v.total_sales)

    # Daily Sales Table
    sales_day = db.session.query(Sales.name,
                                   func.sum(Sales.sales).label('total_sales'),
                                   func.sum(Sales.guests).label('total_guests')
                                   ).filter(Sales.date == start_day
                                            ).group_by(Sales.name).all()


    sales_day_ly = db.session.query(Sales.name,
                                   func.sum(Sales.sales).label('total_sales_ly'),
                                    func.sum(Sales.guests).label('total_guests_ly')
                                   ).filter(Sales.date == start_day_ly
                                            ).group_by(Sales.name).all()

    df_sales_day = pd.DataFrame.from_records(sales_day, columns=['name', 'sales', 'guests'])
    df_sales_day_ly = pd.DataFrame.from_records(sales_day_ly, columns=['name', 'sales_ly', 'guests_ly'])
    print(df_sales_day_ly)
    sales_table = df_sales_day.merge(df_sales_day_ly, how='outer', sort=True)

    labor_day = db.session.query(Labor.name,
                                   func.sum(Labor.hours).label('total_hours'),
                                   func.sum(Labor.dollars).label('total_dollars')
                                   ).filter(Labor.date == start_day
                                            ).group_by(Labor.name).all()


    labor_day_ly = db.session.query(Labor.name,
                                   func.sum(Labor.hours).label('total_hours_ly'),
                                    func.sum(Labor.dollars).label('total_dollars_ly')
                                   ).filter(Labor.date == start_day_ly
                                            ).group_by(Labor.name).all()

    df_labor_day = pd.DataFrame.from_records(labor_day, columns=['name', 'hours', 'dollars'])
    df_labor_day_ly = pd.DataFrame.from_records(labor_day_ly, columns=['name', 'hours_ly', 'dollars_ly'])
    labor_table = df_labor_day.merge(df_labor_day_ly, how='outer', sort=True)

    daily_table = sales_table.merge(labor_table, how='outer', sort=True)
    daily_table.set_index('name', inplace=True)
    daily_table.loc['TOTALS'] = daily_table.sum()
    daily_totals = daily_table.loc['TOTALS']
    print(daily_table)
    print(daily_totals)


    return render_template(
        'home/index.html',
        form=form,
        segment='index',
        fiscal_dates=fiscal_dates,
#        daily_sales=daily_sales,
#        daily_sales_ly=daily_sales_ly,
        weekly_sales=weekly_sales,
        weekly_sales_ly=weekly_sales_ly,
        period_sales=period_sales,
        period_sales_ly=period_sales_ly,
        yearly_sales=yearly_sales,
        yearly_sales_ly=yearly_sales_ly,
#        daily_labor=daily_labor,
        weekly_labor=weekly_labor,
        period_labor=period_labor,
#        daily_labor_ly=daily_labor_ly,
        weekly_labor_ly=weekly_labor_ly,
        period_labor_ly=period_labor_ly,
        values1=values1,
        values1_ly=values1_ly,
        values2=values2,
        values3=values3,
        values2_ly=values2_ly,
        values3_ly=values3_ly,
        daily_table=daily_table,
        daily_totals=daily_totals
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
