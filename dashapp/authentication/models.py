# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

# from flask_login import LoginManager
from flask_security import UserMixin, current_user, RoleMixin, Security, SQLAlchemySessionUserDatastore
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib import sqla
from dashapp.authentication.util import hash_pass
from wtforms.fields import PasswordField
from flask_mail import Mail


db = SQLAlchemy()
mail = Mail()
admin = Admin()


# Create a table to support a many-to-many relationship between Users and Roles
roles_users = db.Table(
    'roles_users',
    db.Column('users_id', db.Integer, db.ForeignKey('Users.id')),
    db.Column('roles_id', db.Integer, db.ForeignKey('Roles.id'))
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
    roles = db.relationship('Roles',
                            secondary=roles_users,
                            backref='users', lazy=True)

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
    column_exclude_list = ('password', 'fs_uniquifier')

    # Don't include the standard password field when creating or editing a User (but see below)
    form_excluded_columns = ('password',)

    # Automatically display human-readable names for the current and available Roles when creating or editing a User
    column_auto_select_related = True

    # Prevent administration of Users unless the currently logged-in user has the "admin" role
    def is_accessible(self):
        return  current_user.has_role('admin')

    # On the form for creating or editing a User, don't display a field corresponding to the model's password field.
    # There are two reasons for this. First, we want to encrypt the password before storing in the database. Second,
    # we want to use a password field (with the input masked) rather than a regular text field.
    def scaffold_form(self):

        # Start with the standard form as provided by Flask-Admin. We've already told Flask-Admin to exclude the
        # password field from this form.
        form_class = super(UserAdmin, self).scaffold_form()

        # Add a password field, naming it "password2" and labeling it "New Password".
        form_class.password2 = PasswordField('New Password')
        return form_class

    # This callback executes when the user saves changes to a newly-created or edited User -- before the changes are
    # committed to the database.
#    def on_model_change(self, form, model, is_created):
#
#        # If the password field isn't blank...
#        if len(model.password2):
#
#            # ... then encrypt the new password prior to storing it in the database. If the password field is blank,
#            # the existing password in the database will be retained.
#            model.password = hash_pass(model.password2)


# Customized Role model for SQL-Admin
class RoleAdmin(sqla.ModelView):

    # Prevent administration of Roles unless the currently logged-in user has the "admin" role
    def is_accessible(self):
        return current_user.has_role('admin')

# Add Flask-Admin views for Users and Roles
admin.add_view(UserAdmin(Users, db.session))
admin.add_view(RoleAdmin(Roles, db.session))



class Restaurants(db.Model):

    __tablename__ = "Restaurants"

    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(64), unique=True)
    name = db.Column(db.String(64), unique=True)

    def as_dict(self):
        return {'id': self.id, 'name': self.name, 'location': self.location}


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
        return {'date': self.date, 'week': self.week, 'period': self.period, 'quarter': self.quarter, 'year': self.year, 'dow': self.dow, 'day': self.day}


class Sales(db.Model):

    __tablename__ = "Sales"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(64))
    daypart = db.Column(db.String(64))
    name = db.Column(db.String(64))
    sales = db.Column(db.Integer)
    guests = db.Column(db.Integer)


class Labor(db.Model):

    __tablename__ = "Labor"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(64))
    category = db.Column(db.String(64))
    job = db.Column(db.String(64))
    name = db.Column(db.String(64))
    hours = db.Column(db.Integer)
    dollars = db.Column(db.Integer)


class Categories(db.Model):

    __tablename__ = "Categories"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(64))
    category = db.Column(db.String(64))
    name = db.Column(db.String(64))
    amount = db.Column(db.Integer)


class Menuitems(db.Model):

    __tablename__ = "Menuitems"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(64))
    menuitem = db.Column(db.String(64))
    name = db.Column(db.String(64))
    category = db.Column(db.String(64))
    amount = db.Column(db.Integer)
    quantity = db.Column(db.Integer)


class Budgets(db.Model):

    __tablename__ = "Budgets"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    period = db.Column(db.Integer)
    year = db.Column(db.Integer)
    alcohol_cost = db.Column(db.Integer)
    alcohol_sales = db.Column(db.Integer)
    food_cost = db.Column(db.Integer)
    food_sales = db.Column(db.Integer)
    gross_operating_profit = db.Column(db.Integer)
    gross_profit = db.Column(db.Integer)
    labor_benefits = db.Column(db.Integer)
    net_profit = db.Column(db.Integer)
    operating_expense = db.Column(db.Integer)
    total_cost_of_sales = db.Column(db.Integer)
    total_labor_and_operating_expense = db.Column(db.Integer)
    total_sales = db.Column(db.Integer)


#@login_manager.user_loader
#def user_loader(id):
#    return Users.query.filter_by(id=id).first()
#
#
#@login_manager.request_loader
#def request_loader(request):
#    username = request.form.get("username")
#    user = Users.query.filter_by(username=username).first()
#    return user if user else None
