# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import uuid

from flask import current_app, render_template
from flask_admin import Admin
from flask_admin.contrib import sqla
from flask_admin.contrib.sqla.fields import QuerySelectMultipleField
from flask_admin.form import Select2Widget
from flask_mailman import EmailMessage, Mail
from flask_security import current_user, utils
from flask_security.core import (
    RoleMixin,
    Security,
    UserMixin,
)
from flask_security.datastore import SQLAlchemySessionUserDatastore
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column
from wtforms.fields import PasswordField

from dashapp.authentication.util import hash_pass

db = SQLAlchemy()
mail = Mail()
admin = Admin()


# Create a table to support a many-to-many relationship between Users and Roles
roles_users = db.Table(
    "roles_users",
    db.Column("users_id", db.Integer, db.ForeignKey("users.id")),
    db.Column("roles_id", db.Integer, db.ForeignKey("roles.id")),
)

# Create a table to support a many-to-many relationship between Users and Stores
stores_users = db.Table(
    "stores_users",
    db.Column("users_id", db.Integer, db.ForeignKey("users.id")),
    db.Column("restaurants_id", db.Integer, db.ForeignKey("restaurants.id")),
)


# Role class
class Roles(db.Model, RoleMixin):
    __tablename__ = "roles"

    # Our Role has three fields, ID, name and description
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    # __str__ is required by Flask-Admin, so we can have human-readable values for the Role when editing a User.
    # If we were using Python 2.7, this would be __unicode__ instead.
    def __str__(self):
        return self.name

    # __hash__ is required to avoid the exception TypeError: unhashable type: 'Role' when saving a User
    def __hash__(self):
        return hash(self.name)


class Restaurants(db.Model):
    __tablename__ = "restaurants"

    id = db.Column(db.Integer, primary_key=True)
    locationid = db.Column(db.String(64), unique=True)
    name = db.Column(db.String(64), unique=True)
    toast_id = db.Column(db.Integer)
    active = db.Column(db.Boolean())

    # __str__ is required by Flask-Admin, so we can have human-readable values for the Role when editing a User.
    # If we were using Python 2.7, this would be __unicode__ instead.
    def __str__(self):
        return self.name

    # __hash__ is required to avoid the exception TypeError: unhashable type: 'Role' when saving a User
    def __hash__(self):
        return hash(self.name)


class Users(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    fs_uniquifier = db.Column(db.String(64), unique=True)
    confirmed_at = db.Column(db.DateTime())
    last_login_at = db.Column(db.DateTime())
    current_login_at = db.Column(db.DateTime())
    last_login_ip = db.Column(db.String(100))
    current_login_ip = db.Column(db.String(100))
    login_count = db.Column(db.Integer)
    roles = db.relationship("Roles", secondary=roles_users, backref="users", lazy=True)
    stores = db.relationship(
        "Restaurants", secondary=stores_users, backref="users", lazy=True
    )


user_datastore = SQLAlchemySessionUserDatastore(db.session, Users, Roles)
security = Security()


# Customized User model for SQL-Admin
class UserAdmin(sqla.ModelView):
    # Prevent administration of Users unless the currently logged-in user has the "admin" role
    def is_accessible(self):
        return current_user.has_role("admin")

    # Don't display the password on the list of Users
    column_exclude_list = ("password", "fs_uniquifier")

    # Don't include the standard password field when creating or editing a User (but see below)
    form_excluded_columns = (
        "password",
        "fs_uniquifier",
        "last_login_at",
        "current_login_at",
        "last_login_ip",
        "current_login_ip",
        "login_count",
    )

    # Automatically display human-readable names for the current and available Roles when creating or editing a User
    column_auto_select_related = True
    column_searchable_list = ["email", "first_name", "last_name"]
    column_filters = ["active"]
    page_size = 50

    # On the form for creating or editing a User, don't display a field corresponding to the model's password field.
    # There are two reasons for this. First, we want to encrypt the password before storing in the database. Second,
    # we want to use a password field (with the input masked) rather than a regular text field.
    def scaffold_form(self):
        # Start with the standard form as provided by Flask-Admin. We've already told Flask-Admin to exclude the
        # password field from this form.
        form_class = super(UserAdmin, self).scaffold_form()

        # Add a password field, naming it "password2" and labeling it "New Password".
        form_class.password2 = PasswordField("New Password")

        # Add a field for the user's roles
        form_class.roles = QuerySelectMultipleField(
            query_factory=lambda: self.session.query(Roles),
            allow_blank=False,
            blank_text="Select Role",
            widget=Select2Widget(
                multiple=True
            ),  # change this to True if you allow multiple roles
        )
        # Add a filed for the user's store
        form_class.stores = QuerySelectMultipleField(
            query_factory=lambda: self.session.query(Restaurants),
            allow_blank=False,
            blank_text="Select Store(s)",
            widget=Select2Widget(
                multiple=True
            ),  # change this to True if you allow multiple stores
        )
        return form_class

    # This callback executes when the user saves changes to a newly-created or edited User -- before the changes are
    # committed to the database.
    def on_model_change(self, form, model, is_created):
        # If the password field isn't blank...
        if len(model.password2):
            # ... then encrypt the new password prior to storing it in the database. If the password field is blank,
            # the existing password in the database will be retained.
            model.password = hash_pass(model.password2)

        if model.fs_uniquifier is None:
            model.fs_uniquifier = uuid.uuid4().hex

        # if a new user is_created send welcome email to user
        if is_created:
            subject = "CentraArchy Dashboard Registration"
            html_content = render_template(
                "security/email/welcome.html",
                email=model.email,
                password=model.password2,
                fname=model.first_name,
                lname=model.last_name,
            )
            to, cc = model.email, "it@centraarchy.com"
            reply_to = "support@centraarchy.com"
            # headers = {'Message-ID': 'centraarchy.com'}

            msg = EmailMessage(
                subject, html_content, to=[to], cc=[cc], reply_to=[reply_to]
            )
            msg.content_subtype = "html"
            try:
                msg.send()
                print("Email was sent")
            except Exception as e:
                print('Email was not sent', e)


# Customized Role model for SQL-Admin
class RoleAdmin(sqla.ModelView):
    # Prevent administration of Roles unless the currently logged-in user has the "admin" role
    def is_accessible(self):
        return current_user.has_role("admin")


class StoreAdmin(sqla.ModelView):
    # Prevent administration of Roles unless the currently logged-in user has the "admin" role
    def is_accessible(self):
        return current_user.has_role("admin")



# Add Flask-Admin views for Users and Roles
admin.add_view(UserAdmin(Users, db.session))
admin.add_view(RoleAdmin(Roles, db.session))
admin.add_view(StoreAdmin(Restaurants, db.session))


class PotatoLoadTimes(db.Model):
    __tablename__ = "potato_load_times"

    time = db.Column(db.Time(), primary_key=True)
    in_time = db.Column(db.Time())
    start_time = db.Column(db.Time())
    stop_time = db.Column(db.Time())
    out_time = db.Column(db.Time())


class UnitsOfMeasure(db.Model):
    __tablename__ = "unitsofmeasure"

    uofm_id = db.Column(db.String(64), primary_key=True, unique=True)
    name = db.Column(db.String(64))
    equivalent_qty = db.Column(db.Float)
    equivalent_uofm = db.Column(db.String(64))
    measure_type = db.Column(db.String(64))
    base_qty = db.Column(db.Float)
    base_uofm = db.Column(db.String(64))


class Calendar(db.Model):
    __tablename__ = "calendar"

    date = db.Column(db.String(64), primary_key=True, unique=True)
    week = db.Column(db.Integer)
    week_start = db.Column(db.String(64))
    week_end = db.Column(db.String(64))
    period = db.Column(db.Integer)
    period_start = db.Column(db.String(64))
    period_end = db.Column(db.String(64))
    quarter = db.Column(db.Integer)
    quarter_start = db.Column(db.String(64))
    quarter_end = db.Column(db.String(64))
    year = db.Column(db.Integer)
    year_start = db.Column(db.String(64))
    year_end = db.Column(db.String(64))
    dow = db.Column(db.Integer)
    day = db.Column(db.String(64))

    def as_dict(self):
        return {
            "date": self.date,
            "week": self.week,
            "period": self.period,
            "quarter": self.quarter,
            "year": self.year,
            "dow": self.dow,
            "day": self.day,
        }


class Company(db.Model):
    __tablename__ = "company"

    companyid = db.Column(db.String, primary_key=True)
    name = db.Column(db.String)


class GlAccount(db.Model):
    __tablename__ = "glaccount"

    glaccountid = db.Column(db.String, primary_key=True)
    name = db.Column(db.String)
    glaccountnumber = db.Column(db.String)
    gltyp = db.Column(db.String)


class Item(db.Model):
    __tablename__ = "item"

    itemid = db.Column(db.String, primary_key=True)
    name = db.Column(db.String)
    category1 = db.Column(db.String)
    category2 = db.Column(db.String)
    category3 = db.Column(db.String)


class JobTitle(db.Model):
    __tablename__ = "job_title"

    jobtitleid = db.Column(db.String, primary_key=True)
    name = db.Column(db.String)
    jobcode = db.Column(db.String)
    glaccount_id = db.Column(db.String, db.ForeignKey("glaccount.glaccountid"))
    location_id = db.Column(db.String, db.ForeignKey("location.locationid"))


class Location(db.Model):
    __tablename__ = "location"

    locationid = db.Column(db.String, primary_key=True)
    name = db.Column(db.String)
    locationnumber = db.Column(db.String)


class SalesDetail(db.Model):
    __tablename__ = "sales_detail"

    salesdetailid = db.Column(db.Integer, primary_key=True)
    menuitem = db.Column(db.String(256))
    amount = db.Column(db.Float)
    date = db.Column(db.String(64))
    quantity = db.Column(db.Float)
    location = db.Column(db.String(64))
    salesaccount = db.Column(db.String(64))
    category = db.Column(db.String(64))
    dailysalessummaryid = db.Column(db.String(64))


class SalesEmployee(db.Model):
    __tablename__ = "sales_employee"

    salesid = db.Column(db.String, primary_key=True)
    date = db.Column(db.DateTime())
    daypart = db.Column(db.String)
    netsales = db.Column(db.Float)
    numberofguests = db.Column(db.Integer)
    orderhour = db.Column(db.Integer)
    salesamount = db.Column(db.Float)
    location = db.Column(db.String)
    grosssales = db.Column(db.Float)
    dailysalessummaryid = db.Column(db.String)


class LaborDetail(db.Model):
    __tablename__ = "labor_detail"

    laborid = db.Column(db.String, primary_key=True)
    dateworked = db.Column(db.DateTime())
    jobtitle_id = db.Column(db.String)
    jobtitle = db.Column(db.String)
    hours = db.Column(db.Float)
    total = db.Column(db.Float)
    location_id = db.Column(db.String)
    dailylaborsummaryid = db.Column(db.String)


class SalesPayment(db.Model):
    __tablename__ = "sales_payment"

    salespaymentid = db.Column(db.String, primary_key=True)
    name = db.Column(db.String)
    amount = db.Column(db.Float)
    date = db.Column(db.DateTime())
    location = db.Column(db.String)
    paymenttype = db.Column(db.String)
    dailysalessummaryid = db.Column(db.String)


## Table Views


class PotatoSales(db.Model):
    __tablename__ = "potato_sales"

    date = db.Column(db.Date, primary_key=True)
    time = db.Column(db.Time, primary_key=True)
    dow = db.Column(db.Integer)
    name = db.Column(db.String)
    quantity = db.Column(db.Float)


class PotatoChart(db.Model):
    __tablename__ = "potato_chart"

    date = db.Column(db.Date, primary_key=True)
    store = db.Column(db.String, primary_key=True)
    time = db.Column(db.Time, primary_key=True)
    in_time = db.Column(db.Time)
    out_time = db.Column(db.Time)
    quantity = db.Column(db.Float)


class SalesTotals(db.Model):
    __tablename__ = "sales_totals"

    store = db.Column(db.String, primary_key=True)
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, primary_key=True)
    dow = db.Column(db.Integer)
    week = db.Column(db.Integer)
    period = db.Column(db.Integer)
    year = db.Column(db.Integer)
    net_sales = db.Column(db.Float)
    guest_count = db.Column(db.Integer)


class LaborTotals(db.Model):
    __tablename__ = "labor_totals"

    store = db.Column(db.String, primary_key=True)
    id = db.Column(db.Integer, primary_key=True)
    job = db.Column(db.String, primary_key=True)
    category = db.Column(db.String)
    date = db.Column(db.Date)
    dow = db.Column(db.Integer)
    week = db.Column(db.Integer)
    period = db.Column(db.Integer)
    year = db.Column(db.Integer)
    total_hours = db.Column(db.Float)
    total_dollars = db.Column(db.Integer)


class Menuitems(db.Model):
    __tablename__ = "menuitems"

    store = db.Column(db.String, primary_key=True)
    menuitem = db.Column(db.String, primary_key=True)
    date = db.Column(db.Date)
    total_sales = db.Column(db.Float)
    total_count = db.Column(db.Integer)


class Purchases(db.Model):
    __tablename__ = "purchases"

    transactionid = db.Column(db.String, primary_key=True)
    date = db.Column(db.Date, primary_key=True)
    week = db.Column(db.Integer)
    period = db.Column(db.Integer)
    year = db.Column(db.Integer)
    id = db.Column(db.Integer, primary_key=True)
    store = db.Column(db.String)
    item = db.Column(db.String)
    category1 = db.Column(db.String)
    category2 = db.Column(db.String)
    category3 = db.Column(db.String)
    quantity = db.Column(db.Float)
    uofm = db.Column(db.String)
    credit = db.Column(db.Integer)
    debit = db.Column(db.Integer)
    amount = db.Column(db.Integer)
    account = db.Column(db.String)
    company = db.Column(db.String)


class SalesCategory(db.Model):
    __tablename__ = "sales_category"

    store = db.Column(db.String, primary_key=True)
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, primary_key=True)
    dow = db.Column(db.Integer)
    week = db.Column(db.Integer)
    period = db.Column(db.Integer)
    year = db.Column(db.Integer)
    category = db.Column(db.String)
    quantity = db.Column(db.Float)
    amount = db.Column(db.Float)


class SalesDaypart(db.Model):
    __tablename__ = "sales_daypart"

    store = db.Column(db.String, primary_key=True)
    id = db.Column(db.Integer, primary_key=True)
    daypart = db.Column(db.String, primary_key=True)
    date = db.Column(db.Date, primary_key=True)
    dow = db.Column(db.Integer)
    week = db.Column(db.Integer)
    period = db.Column(db.Integer)
    year = db.Column(db.Integer)
    net_sales = db.Column(db.Float)
    guest_count = db.Column(db.Integer)


class SalesHourly(db.Model):
    __tablename__ = "sales_hourly"

    store = db.Column(db.String, primary_key=True)
    id = db.Column(db.Integer, primary_key=True)
    order_hour = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, primary_key=True)
    dow = db.Column(db.Integer)
    week = db.Column(db.Integer)
    period = db.Column(db.Integer)
    year = db.Column(db.Integer)
    net_sales = db.Column(db.Float)
    guest_count = db.Column(db.Integer)


class SalesRecordsDay(db.Model):
    __tablename__ = "sales_records_day"

    store = db.Column(db.String, primary_key=True)
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, primary_key=True)
    dow = db.Column(db.Integer)
    week = db.Column(db.Integer)
    period = db.Column(db.Integer)
    year = db.Column(db.Integer)
    net_sales = db.Column(db.Float)


class SalesRecordsWeek(db.Model):
    __tablename__ = "sales_records_week"

    store = db.Column(db.String, primary_key=True)
    id = db.Column(db.Integer, primary_key=True)
    week = db.Column(db.Integer, primary_key=True)
    period = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    net_sales = db.Column(db.Float)


class SalesRecordsPeriod(db.Model):
    __tablename__ = "sales_records_period"

    store = db.Column(db.String, primary_key=True)
    id = db.Column(db.Integer, primary_key=True)
    period = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    net_sales = db.Column(db.Float)


class SalesRecordsYear(db.Model):
    __tablename__ = "sales_records_year"

    store = db.Column(db.String, primary_key=True)
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    net_sales = db.Column(db.Float)


class TableTurns(db.Model):
    __tablename__ = "table_turns"
    store = db.Column(db.String, primary_key=True)
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, primary_key=True)
    dow = db.Column(db.Integer)
    week = db.Column(db.Integer)
    period = db.Column(db.Integer)
    year = db.Column(db.Integer)
    bar = db.Column(db.Time)
    dining_room = db.Column(db.Time)
    handheld = db.Column(db.Time)
    patio = db.Column(db.Time)
    online_ordering = db.Column(db.Time)


class StockCount(db.Model):
    __tablename__ = "stock_count"

    transactionid = db.Column(db.String, primary_key=True)
    date = db.Column(db.DateTime())
    dow = db.Column(db.Integer)
    week = db.Column(db.Integer)
    period = db.Column(db.Integer)
    year = db.Column(db.Integer)
    id = db.Column(db.String)
    store = db.Column(db.String)
    item = db.Column(db.String)
    category1 = db.Column(db.String)
    category2 = db.Column(db.String)
    category3 = db.Column(db.String)
    quantity = db.Column(db.Float)
    uofm = db.Column(db.String)
    previous_amount = db.Column(db.Float)
    adjustment = db.Column(db.Float)
    amount = db.Column(db.Float)


class GiftCardSales(db.Model):
    __tablename__ = "gift_card_sales"

    store = db.Column(db.String, primary_key=True)
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, primary_key=True)
    dow = db.Column(db.Integer)
    week = db.Column(db.Integer)
    period = db.Column(db.Integer)
    year = db.Column(db.Integer)
    quantity = db.Column(db.Float)
    amount = db.Column(db.Float)


class GiftCardRedeem(db.Model):
    __tablename__ = "gift_card_redeem"

    store = db.Column(db.String, primary_key=True)
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, primary_key=True)
    dow = db.Column(db.Integer)
    week = db.Column(db.Integer)
    period = db.Column(db.Integer)
    year = db.Column(db.Integer)
    amount = db.Column(db.Float)


class SalesCarryout(db.Model):
    __tablename__ = "sales_carryout"
    store = db.Column(db.String, primary_key=True)
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, primary_key=True)
    dow = db.Column(db.Integer)
    week = db.Column(db.Integer)
    period = db.Column(db.Integer)
    year = db.Column(db.Integer)
    category = db.Column(db.String)
    quantity = db.Column(db.Float)
    amount = db.Column(db.Integer)
