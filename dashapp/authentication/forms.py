# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, PasswordField
from wtforms.fields.html5 import DateField  # wftforms 2.3.3 is necessary until bug fix
from wtforms_sqlalchemy.fields import QuerySelectField
from wtforms.validators import Email, DataRequired
from dashapp.authentication.models import Restaurants
from sqlalchemy import or_

# login and registration


def store_query():
    filters = {
        or_(
            Restaurants.id == 3,
            Restaurants.id == 4,
            Restaurants.id == 5,
            Restaurants.id == 6,
            Restaurants.id == 9,
            Restaurants.id == 10,
            Restaurants.id == 11,
            Restaurants.id == 12,
            Restaurants.id == 13,
            Restaurants.id == 14,
            Restaurants.id == 15,
            Restaurants.id == 16,
            Restaurants.id == 17,
            Restaurants.id == 18,
        )
    }
    stores = Restaurants.query.filter(*filters).order_by(Restaurants.name)
    return stores


class LoginForm(FlaskForm):
    email = StringField(
        "Email Address", id="email_login", validators=[DataRequired(), Email()]
    )
    password = PasswordField("Password", id="pwd_login", validators=[DataRequired()])


class CreateAccountForm(FlaskForm):
    username = StringField(
        "Username", id="username_create", validators=[DataRequired()]
    )
    email = StringField(
        "Email", id="email_create", validators=[DataRequired(), Email()]
    )
    password = PasswordField("Password", id="pwd_create", validators=[DataRequired()])


class DateForm(FlaskForm):
    selectdate = DateField("", format="%Y-%m-%d")
    submit1 = SubmitField("Submit")


class UpdateForm(FlaskForm):
    selectdate = DateField("Data Update", format="%Y-%m-%d")
    submit2 = SubmitField("Submit")


class StoreForm(FlaskForm):
    store = QuerySelectField(
        "",
        query_factory=store_query,
        allow_blank=True,
        get_label="name",
        blank_text="Select Store",
    )
    submit3 = SubmitField("Submit")


class PotatoForm(FlaskForm):
    submit4 = SubmitField("Submit")
