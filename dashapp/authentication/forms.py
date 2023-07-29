# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from flask_wtf import FlaskForm
from datetime import datetime
from wtforms import widgets, SubmitField, StringField, PasswordField
from wtforms.fields import DateField
from wtforms_sqlalchemy.fields import QuerySelectMultipleField, QuerySelectField
from wtforms.validators import Email, DataRequired
from dashapp.authentication.models import *

# login and registration


def store_query():
    closed_stores = [
            "91", "21B", "12B", "2B", "17B", "7B", "18", "10", "3B", "28", "8B", "1B", "85B", "15B", "15", "4B", "19", "25B", "14B", "11B", "95", "99", "5B", "10B", "18B" 
            ]
    return location.query.filter(location.locationnumber.notin_(closed_stores)).order_by(location.name).all()


class LoginForm(FlaskForm):
    email = StringField("Email Address", id="email_login", validators=[DataRequired(), Email()])
    password = PasswordField("Password", id="pwd_login", validators=[DataRequired()])


class CreateAccountForm(FlaskForm):
    username = StringField("Username", id="username_create", validators=[DataRequired()])
    email = StringField("Email", id="email_create", validators=[DataRequired(), Email()])
    password = PasswordField("Password", id="pwd_create", validators=[DataRequired()])


class DateForm(FlaskForm):
    selectdate = DateField("", format="%Y-%m-%d")
    submit1 = SubmitField("Submit")


class UpdateForm(FlaskForm):
    selectdate = DateField("Data Update", format="%Y-%m-%d", default=datetime.today())
    submit2 = SubmitField("Submit")


class MultiCheckboxField(QuerySelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class StoreForm(FlaskForm):
    stores = MultiCheckboxField(
        "Select Stores",
        query_factory=store_query,
        get_label="name",
    )
    submit3 = SubmitField("Submit")


class PotatoForm(FlaskForm):
    store = QuerySelectField(
        "",
        query_factory=store_query,
        get_label="name",
        blank_text="Select Store",
    )
    submit4 = SubmitField("Submit")


class LobsterForm(FlaskForm):
    store = QuerySelectField(
        "",
        query_factory=store_query,
        get_label="name",
        blank_text="Select Store",
    )
    submit5 = SubmitField("Submit")


class StoneForm(FlaskForm):
    store = QuerySelectField(
        "",
        query_factory=store_query,
        get_label="name",
        blank_text="Select Store",
    )
    submit6 = SubmitField("Submit")


class UofMForm(FlaskForm):
    submit_uofm = SubmitField("Submit")


class RecipeForm(FlaskForm):
    submit9 = SubmitField("Submit")


class UserForm(FlaskForm):
    submit_user = SubmitField("Submit")
