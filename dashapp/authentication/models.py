# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

# from flask_login import LoginManager
from flask_security import (
    UserMixin,
    current_user,
    RoleMixin,
    Security,
    SQLAlchemySessionUserDatastore,
)
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib import sqla
from dashapp.authentication.util import hash_pass
from wtforms.fields import PasswordField
from flask_mail import Mail
import uuid


db = SQLAlchemy()
mail = Mail()
admin = Admin()


# Create a table to support a many-to-many relationship between Users and Roles
roles_users = db.Table(
    "roles_users",
    db.Column("users_id", db.Integer, db.ForeignKey("Users.id")),
    db.Column("roles_id", db.Integer, db.ForeignKey("Roles.id")),
)


# Role class
class Roles(db.Model, RoleMixin):
    __tablename__ = "Roles"

    # Our Role has three fields, ID, name and description
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    # __str__ is required by Flask-Admin, so we can have human-readable values for the Role when editing a User.
    # If we were using Python 2.7, this would be __unicode__ instead.
    def __str__(self):
        return self.name

    # __hash__ is required to avoid the exception TypeError: unhashable type: 'Role' when saving a User
    def __hash__(self):
        return hash(self.name)


class Users(db.Model, UserMixin):
    __tablename__ = "Users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    fs_uniquifier = db.Column(db.String(64), unique=True)
    roles = db.relationship("Roles", secondary=roles_users, backref="users", lazy=True)
    confirmed_at = db.Column(db.DateTime())
    last_login_at = db.Column(db.DateTime())
    current_login_at = db.Column(db.DateTime())
    last_login_ip = db.Column(db.String(100))
    current_login_ip = db.Column(db.String(100))
    login_count = db.Column(db.Integer)


#    def __init__(self, **kwargs):
#        for property, value in kwargs.items():
#            # depending on whether value is an iterable or not, we must
#            # unpack it's value (when **kwargs is request.form, some values
#            # will be a 1-element list)
#            if hasattr(value, "__iter__") and not isinstance(value, str):
#                # the ,= unpack of a singleton fails PEP8 (travis flake8 test)
#                value = value[0]
#
#            if property == "password":
#                value = hash_pass(value)  # we need bytes here (not plain str)
#
#            setattr(self, property, value)
#
#    def __repr__(self):
#        return str(self.username)


user_datastore = SQLAlchemySessionUserDatastore(db.session, Users, Roles)
security = Security()


# Customized User model for SQL-Admin
class UserAdmin(sqla.ModelView):
    # Don't display the password on the list of Users
    column_exclude_list = ("password", "fs_uniquifier")

    # Don't include the standard password field when creating or editing a User (but see below)
    form_excluded_columns = ("password",
                             "fs_uniquifier",
                             "last_login_at",
                             "current_login_at",
                             "last_login_ip",
                             "current_login_ip",
                             "login_count")

    # Automatically display human-readable names for the current and available Roles when creating or editing a User
    column_auto_select_related = True
    column_searchable_list = ["email"]
    column_filters = ["active"]
    page_size = 50

    # Prevent administration of Users unless the currently logged-in user has the "admin" role
    def is_accessible(self):
        return current_user.has_role("admin")

    # On the form for creating or editing a User, don't display a field corresponding to the model's password field.
    # There are two reasons for this. First, we want to encrypt the password before storing in the database. Second,
    # we want to use a password field (with the input masked) rather than a regular text field.
    def scaffold_form(self):
        # Start with the standard form as provided by Flask-Admin. We've already told Flask-Admin to exclude the
        # password field from this form.
        form_class = super(UserAdmin, self).scaffold_form()

        # Add a password field, naming it "password2" and labeling it "New Password".
        form_class.password2 = PasswordField("New Password")
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


# Customized Role model for SQL-Admin
class RoleAdmin(sqla.ModelView):
    # Prevent administration of Roles unless the currently logged-in user has the "admin" role
    def is_accessible(self):
        return current_user.has_role("admin")


# Add Flask-Admin views for Users and Roles
admin.add_view(UserAdmin(Users, db.session))
admin.add_view(RoleAdmin(Roles, db.session))


class Restaurants(db.Model):
    __tablename__ = "Restaurants"

    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(64), unique=True)
    name = db.Column(db.String(64), unique=True)
    payment = db.relationship("Payments", backref="payment_types", lazy=True)

    def as_dict(self):
        return {"id": self.id, "name": self.name, "location": self.location}


class Calendar(db.Model):
    __tablename__ = "Calendar"

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


class Sales(db.Model):
    __tablename__ = "Sales"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(64))
    daypart = db.Column(db.String(64))
    name = db.Column(db.String(64))
    sales = db.Column(db.Float)
    guests = db.Column(db.Integer)


class Labor(db.Model):
    __tablename__ = "Labor"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(64))
    category = db.Column(db.String(64))
    job = db.Column(db.String(64))
    name = db.Column(db.String(64))
    hours = db.Column(db.Float)
    dollars = db.Column(db.Float)


class Menuitems(db.Model):
    __tablename__ = "Menuitems"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(64))
    menuitem = db.Column(db.String(64))
    name = db.Column(db.String(64))
    menu_category = db.Column(db.String(64))
    category = db.Column(db.String(64))
    amount = db.Column(db.Float)
    quantity = db.Column(db.Integer)


class Transactions(db.Model):
    __tablename__ = "Transactions"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(64))
    trans_id = db.Column(db.String(64))
    store_id = db.Column(db.Integer)
    name = db.Column(db.String(64))
    item = db.Column(db.String(256))
    category1 = db.Column(db.String(64))
    category2 = db.Column(db.String(64))
    category3 = db.Column(db.String(64))
    quantity = db.Column(db.Float)
    UofM = db.Column(db.String(64))
    credit = db.Column(db.Float)
    debit = db.Column(db.Float)
    amount = db.Column(db.Float)
    type = db.Column(db.String(64))
    modified = db.Column(db.String(64))
    companyid = db.Column(db.String(64))
    company = db.Column(db.String(64))
    account = db.Column(db.String(64))


class Budgets(db.Model):
    __tablename__ = "Budgets"

    id = db.Column(db.Integer, primary_key=True)
    period = db.Column(db.Integer)
    name = db.Column(db.String(64))
    year = db.Column(db.Integer)
    lunch_food_sales = db.Column(db.Integer)
    dinner_food_sales = db.Column(db.Integer)
    to_go_sales = db.Column(db.Integer)
    catering_sales = db.Column(db.Integer)
    total_food_sales = db.Column(db.Integer)
    liquor_sales = db.Column(db.Integer)
    beer_sales = db.Column(db.Integer)
    wine_sales = db.Column(db.Integer)
    total_alcohol_sales = db.Column(db.Integer)
    total_sales = db.Column(db.Integer)
    beef = db.Column(db.Integer)
    pork = db.Column(db.Integer)
    poultry = db.Column(db.Integer)
    fish = db.Column(db.Integer)
    produce = db.Column(db.Integer)
    dairy = db.Column(db.Integer)
    food_other = db.Column(db.Integer)
    total_food_cost = db.Column(db.Integer)
    liquor = db.Column(db.Integer)
    beer = db.Column(db.Integer)
    wine = db.Column(db.Integer)
    total_alcohol_cost = db.Column(db.Integer)
    total_cost_of_sales = db.Column(db.Integer)
    gross_profit = db.Column(db.Integer)
    total_crew_training = db.Column(db.Integer)
    kitchen = db.Column(db.Integer)
    restaurant = db.Column(db.Integer)
    host = db.Column(db.Integer)
    bar = db.Column(db.Integer)
    catering = db.Column(db.Integer)
    total_crew = db.Column(db.Integer)
    total_crew_all = db.Column(db.Integer)
    total_management = db.Column(db.Integer)
    total_labor = db.Column(db.Integer)
    total_labor_benefits = db.Column(db.Integer)
    food_comp = db.Column(db.Integer)
    drink_comp = db.Column(db.Integer)
    serv_atm_comp = db.Column(db.Integer)
    high_time_comp = db.Column(db.Integer)
    comp_certificates_pr = db.Column(db.Integer)
    outside_delivery_service = db.Column(db.Integer)
    total_comps = db.Column(db.Integer)
    kitchen_supplies = db.Column(db.Integer)
    restaurant_supplies = db.Column(db.Integer)
    bar_supplies = db.Column(db.Integer)
    catering_supplies_expense = db.Column(db.Integer)
    cleaning_supplies = db.Column(db.Integer)
    office_supplies = db.Column(db.Integer)
    total_supplies = db.Column(db.Integer)
    china = db.Column(db.Integer)
    glassware = db.Column(db.Integer)
    silverware = db.Column(db.Integer)
    smallware = db.Column(db.Integer)
    total_smallwares = db.Column(db.Integer)
    total_repair_maint = db.Column(db.Integer)
    total_advertising_coupons = db.Column(db.Integer)
    total_other_op_expense = db.Column(db.Integer)
    gift_card_income = db.Column(db.Integer)
    gift_card_expense = db.Column(db.Integer)
    total_income_expense = db.Column(db.Integer)
    total_operating_expense = db.Column(db.Integer)
    total_labor_and_operating_expense = db.Column(db.Integer)
    gross_operating_profit = db.Column(db.Integer)
    net_profit = db.Column(db.Integer)


class Potatoes(db.Model):
    __tablename__ = "Potatoes"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(64))
    time = db.Column(db.String(64))
    name = db.Column(db.String(64))
    in_time = db.Column(db.String(64))
    out_time = db.Column(db.String(64))
    quantity = db.Column(db.Integer)


class Unitsofmeasure(db.Model):
    __tablename__ = "Unitsofmeasure"

    uofm_id = db.Column(db.String(64), primary_key=True, unique=True)
    name = db.Column(db.String(64))
    equivalent_qty = db.Column(db.Float)
    equivalent_uofm = db.Column(db.String(64))
    measure_type = db.Column(db.String(64))
    base_qty = db.Column(db.Float)
    base_uofm = db.Column(db.String(64))


class Ingredients(db.Model):
    __tablename__ = "Ingredients"

    id = db.Column(db.Integer, primary_key=True)
    item = db.Column(db.String(256))
    recipe = db.Column(db.String(256))
    qty = db.Column(db.Float)
    uofm = db.Column(db.String(64))


class Recipes(db.Model):
    __tablename__ = "Recipes"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    menuitem = db.Column(db.String(256))
    cost = db.Column(db.Float)
    recipe = db.Column(db.String(256))
    category1 = db.Column(db.String(64))
    category2 = db.Column(db.String(64))
    posid = db.Column(db.Integer)
    recipeid = db.Column(db.String(64))
    menuitemid = db.Column(db.String(64))


class Payments(db.Model):
    __tablename__ = "Payments"

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float)
    date = db.Column(db.String(64))
    location = db.Column(db.String(64))
    paymenttype = db.Column(db.String(64))
    restaurant_id = db.Column(db.Integer, db.ForeignKey("Restaurants.id"))
