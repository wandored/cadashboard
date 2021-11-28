# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from flask_login import UserMixin
from dashapp import db, login_manager
from dashapp.authentication.util import hash_pass


class Users(db.Model, UserMixin):

    __tablename__ = "Users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True)
    email = db.Column(db.String(64), unique=True)
    password = db.Column(db.LargeBinary)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            # depending on whether value is an iterable or not, we must
            # unpack it's value (when **kwargs is request.form, some values
            # will be a 1-element list)
            if hasattr(value, "__iter__") and not isinstance(value, str):
                # the ,= unpack of a singleton fails PEP8 (travis flake8 test)
                value = value[0]

            if property == "password":
                value = hash_pass(value)  # we need bytes here (not plain str)

            setattr(self, property, value)

    def __repr__(self):
        return str(self.username)


class Restaurants(db.Model):

    __tablename__ = "Restaurants"

    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(64), unique=True)
    name = db.Column(db.String(64), unique=True)


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
    job = db.Column(db.String(64))
    name = db.Column(db.String(64))
    hours = db.Column(db.Integer)
    dollars = db.Column(db.Integer)


@login_manager.user_loader
def user_loader(id):
    return Users.query.filter_by(id=id).first()


@login_manager.request_loader
def request_loader(request):
    username = request.form.get("username")
    user = Users.query.filter_by(username=username).first()
    return user if user else None
