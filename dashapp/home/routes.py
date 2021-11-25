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
    DOW = WTD = PTD = 0
    form = DateForm()
    # Get Data
    if  form.validate_on_submit():
        ''' update screen with new date '''
        session['targetdate'] = form.selectdate.data.strftime("%Y-%m-%d")
        return redirect(url_for('home_blueprint.index'))


    for i in fiscal_dates:
        day_start = datetime.strptime(i.date, "%Y-%m-%d")
        day_end = day_start + timedelta(days=1)
#        week_start = datetime.strptime(i.week_start, "%Y-%m-%d")
#        week_end = datetime.strptime(i.week_end, "%Y-%m-%d")
#        period_start = datetime.strptime(i.period_start, "%Y-%m-%d")
#        period_end = datetime.strptime(i.period_end, "%Y-%m-%d")
#        year_start = datetime.strptime(i.year_start, "%Y-%m-%d")
#        year_end = datetime.strptime(i.year_end, "%Y-%m-%d")

#        start_day = day_start.strftime("%Y-%m-%d")
        start_day = i.date
        end_day = day_end.strftime("%Y-%m-%d")
        start_week = i.week_start
        end_week = i.week_end
        start_period = i.period_start
        end_period = i.period_end
        start_year = i.year_start
        end_year = i.year_end
#        start_week = week_start.strftime("%Y-%m-%d")
#        end_week = week_end.strftime("%Y-%m-%d")
#        start_period = period_start.strftime("%Y-%m-%d")
#        end_period = period_end.strftime("%Y-%m-%d")
#        start_year = year_start.strftime("%Y-%m-%d")
#        end_year = year_end.strftime("%Y-%m-%d")


    # Get matching day, week and period start and end dates
    start_day_ly = get_lastyear(start_day)
#    end_day_ly = get_lastyear(end_day)
    start_week_ly = get_lastyear(start_week)
    end_week_ly = get_lastyear(end_week)
    week_to_date = get_lastyear(start_day)
    start_period_ly = get_lastyear(start_period)
    end_period_ly = get_lastyear(end_period)
    period_to_date = get_lastyear(start_day)
    start_year_ly = get_lastyear(start_year)
    end_year_ly = get_lastyear(end_year)
    year_to_date = get_lastyear(start_day)

    # Get the Day Of Week integer
#    last_day = Calendar.query.filter_by(date=start_day).first()
#    WTD = last_day.dow
#    print(f'Period-{PTD}, Week-{WTD}, Day-{DOW}')

    # SalesEmployee
    # delete current days data from database and replace with fresh data
    Sales.query.filter_by(date=start_day).delete()
    db.session.commit()
    baddates = sales_employee(start_day, end_day)

    if baddates == 1:
        flash(f'I cannot find sales for the day you selected.  Please select another date!', 'warning')
        session['targetdate'] = Config.YSTDAY.strftime('%Y-%m-%d')
        return redirect(url_for('home_blueprint.index'))


    # LaborDetail
    Labor.query.filter_by(date=start_day).delete()
    db.session.commit()
    labor_detail(start_day, end_day)


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

    # Grab top sales over last year before we add totals
    dy_sales = daily_table.sales - daily_table.sales_ly
    dy_top_sales = dy_sales.nlargest(5)
    dy_sales_avg = (daily_table.sales - daily_table.sales_ly) / daily_table.sales_ly * 100
    dy_avg_sales = dy_sales_avg.nlargest(5)
    print(dy_top_sales.tolist())
    print(dy_avg_sales.tolist())

    daily_table.loc['TOTALS'] = daily_table.sum()
    daily_totals = daily_table.loc['TOTALS']


    # Weekly Sales Table
    sales_week = db.session.query(Sales.name,
                                   func.sum(Sales.sales).label('total_sales'),
                                   func.sum(Sales.guests).label('total_guests')
                                   ).filter(Sales.date >= start_week,
                                            Sales.date <= end_week
                                            ).group_by(Sales.name).all()


    sales_week_ly = db.session.query(Sales.name,
                                   func.sum(Sales.sales).label('total_sales_ly'),
                                    func.sum(Sales.guests).label('total_guests_ly')
                                   ).filter(Sales.date >= start_week_ly,
                                            Sales.date <= week_to_date,
                                            ).group_by(Sales.name).all()

    df_sales_week = pd.DataFrame.from_records(sales_week, columns=['name', 'sales', 'guests'])
    df_sales_week_ly = pd.DataFrame.from_records(sales_week_ly, columns=['name', 'sales_ly', 'guests_ly'])
    sales_table_wk = df_sales_week.merge(df_sales_week_ly, how='outer', sort=True)

    labor_week = db.session.query(Labor.name,
                                   func.sum(Labor.hours).label('total_hours'),
                                   func.sum(Labor.dollars).label('total_dollars')
                                   ).filter(Labor.date >= start_week,
                                            Labor.date <= end_week
                                            ).group_by(Labor.name).all()


    labor_week_ly = db.session.query(Labor.name,
                                   func.sum(Labor.hours).label('total_hours_ly'),
                                    func.sum(Labor.dollars).label('total_dollars_ly')
                                   ).filter(Labor.date >= start_week_ly,
                                            Labor.date <= week_to_date
                                            ).group_by(Labor.name).all()

    df_labor_week = pd.DataFrame.from_records(labor_week, columns=['name', 'hours', 'dollars'])
    df_labor_week_ly = pd.DataFrame.from_records(labor_week_ly, columns=['name', 'hours_ly', 'dollars_ly'])
    labor_table_wk = df_labor_week.merge(df_labor_week_ly, how='outer', sort=True)

    weekly_table = sales_table_wk.merge(labor_table_wk, how='outer', sort=True)
    weekly_table.set_index('name', inplace=True)

    # Grab top sales over last year before we add totals
    wk_sales = weekly_table.sales - weekly_table.sales_ly
    wk_top_sales = wk_sales.nlargest(5)
    wk_sales_avg = (weekly_table.sales - weekly_table.sales_ly) / weekly_table.sales_ly * 100
    wk_avg_sales = wk_sales_avg.nlargest(5)
    print(wk_top_sales.tolist())
    print(wk_avg_sales.tolist())

    weekly_table.loc['TOTALS'] = weekly_table.sum()
    weekly_totals = weekly_table.loc['TOTALS']


    # Period Sales Table
    sales_period = db.session.query(Sales.name,
                                   func.sum(Sales.sales).label('total_sales'),
                                   func.sum(Sales.guests).label('total_guests')
                                   ).filter(Sales.date >= start_period,
                                            Sales.date <= end_period
                                            ).group_by(Sales.name).all()


    sales_period_ly = db.session.query(Sales.name,
                                   func.sum(Sales.sales).label('total_sales_ly'),
                                    func.sum(Sales.guests).label('total_guests_ly')
                                   ).filter(Sales.date >= start_period_ly,
                                            Sales.date <= period_to_date
                                            ).group_by(Sales.name).all()

    df_sales_period = pd.DataFrame.from_records(sales_period, columns=['name', 'sales', 'guests'])
    df_sales_period_ly = pd.DataFrame.from_records(sales_period_ly, columns=['name', 'sales_ly', 'guests_ly'])
    sales_table_pd = df_sales_period.merge(df_sales_period_ly, how='outer', sort=True)

    labor_period = db.session.query(Labor.name,
                                   func.sum(Labor.hours).label('total_hours'),
                                   func.sum(Labor.dollars).label('total_dollars')
                                   ).filter(Labor.date >= start_period,
                                            Labor.date <= end_period
                                            ).group_by(Labor.name).all()


    labor_period_ly = db.session.query(Labor.name,
                                   func.sum(Labor.hours).label('total_hours_ly'),
                                    func.sum(Labor.dollars).label('total_dollars_ly')
                                   ).filter(Labor.date >= start_period_ly,
                                            Labor.date <= period_to_date
                                            ).group_by(Labor.name).all()

    df_labor_period = pd.DataFrame.from_records(labor_period, columns=['name', 'hours', 'dollars'])
    df_labor_period_ly = pd.DataFrame.from_records(labor_period_ly, columns=['name', 'hours_ly', 'dollars_ly'])
    labor_table_pd = df_labor_period.merge(df_labor_period_ly, how='outer', sort=True)

    period_table = sales_table_pd.merge(labor_table_pd, how='outer', sort=True)
    period_table.set_index('name', inplace=True)

    # Grab top sales over last year before we add totals
    pd_sales = period_table.sales - period_table.sales_ly
    pd_top_sales = pd_sales.nlargest(5)
    pd_sales_avg = (period_table.sales - period_table.sales_ly) / period_table.sales_ly * 100
    pd_avg_sales = pd_sales_avg.nlargest(5)
    print(pd_top_sales.tolist())

    period_table.loc['TOTALS'] = period_table.sum()
    period_totals = period_table.loc['TOTALS']


    # Yearly Sales Table
    sales_yearly = db.session.query(Sales.name,
                                   func.sum(Sales.sales).label('total_sales'),
                                   func.sum(Sales.guests).label('total_guests')
                                   ).filter(Sales.date >= start_year,
                                            Sales.date <= end_year
                                            ).group_by(Sales.name).all()


    sales_yearly_ly = db.session.query(Sales.name,
                                   func.sum(Sales.sales).label('total_sales_ly'),
                                    func.sum(Sales.guests).label('total_guests_ly')
                                   ).filter(Sales.date >= start_year_ly,
                                            Sales.date <= year_to_date
                                            ).group_by(Sales.name).all()

    df_sales_yearly = pd.DataFrame.from_records(sales_yearly, columns=['name', 'sales', 'guests'])
    df_sales_yearly_ly = pd.DataFrame.from_records(sales_yearly_ly, columns=['name', 'sales_ly', 'guests_ly'])
    sales_table_yr = df_sales_yearly.merge(df_sales_yearly_ly, how='outer', sort=True)

    labor_yearly = db.session.query(Labor.name,
                                   func.sum(Labor.hours).label('total_hours'),
                                   func.sum(Labor.dollars).label('total_dollars')
                                   ).filter(Labor.date >= start_year,
                                            Labor.date <= end_year
                                            ).group_by(Labor.name).all()


    labor_yearly_ly = db.session.query(Labor.name,
                                   func.sum(Labor.hours).label('total_hours_ly'),
                                    func.sum(Labor.dollars).label('total_dollars_ly')
                                   ).filter(Labor.date >= start_year_ly,
                                            Labor.date <= year_to_date
                                            ).group_by(Labor.name).all()

    df_labor_yearly = pd.DataFrame.from_records(labor_yearly, columns=['name', 'hours', 'dollars'])
    df_labor_yearly_ly = pd.DataFrame.from_records(labor_yearly_ly, columns=['name', 'hours_ly', 'dollars_ly'])
    labor_table_yr = df_labor_yearly.merge(df_labor_yearly_ly, how='outer', sort=True)

    yearly_table = sales_table_yr.merge(labor_table_yr, how='outer', sort=True)
    yearly_table.set_index('name', inplace=True)

    # Grab top sales over last year before we add totals
    yr_sales = yearly_table.sales - yearly_table.sales_ly
    yr_top_sales = yr_sales.nlargest(5)
    yr_sales_avg = (yearly_table.sales - yearly_table.sales_ly) / yearly_table.sales_ly * 100
    yr_avg_sales = yr_sales_avg.nlargest(5)
    print(yr_top_sales.tolist())
    print(yr_avg_sales.tolist())

    yearly_table.loc['TOTALS'] = yearly_table.sum()
    yearly_totals = yearly_table.loc['TOTALS']


    # Scorecard


    return render_template(
        'home/index.html',
        form=form,
        segment='index',
        fiscal_dates=fiscal_dates,
        values1=values1,
        values2=values2,
        values3=values3,
        values1_ly=values1_ly,
        values2_ly=values2_ly,
        values3_ly=values3_ly,
        daily_table=daily_table,
        daily_totals=daily_totals,
        weekly_table=weekly_table,
        weekly_totals=weekly_totals,
        period_table=period_table,
        period_totals=period_totals,
        yearly_table=yearly_table,
        yearly_totals=yearly_totals,
        dy_top_sales=dy_top_sales,
        dy_avg_sales=dy_avg_sales,
        wk_top_sales=wk_top_sales,
        wk_avg_sales=wk_avg_sales,
        pd_top_sales=pd_top_sales,
        pd_avg_sales=pd_avg_sales
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
