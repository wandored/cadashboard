# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from flask_wtf import FlaskForm
from datetime import datetime
from wtforms import widgets, SelectField, SubmitField, StringField, PasswordField
from wtforms.fields import DateField
from wtforms_sqlalchemy.fields import QuerySelectMultipleField, QuerySelectField
from wtforms.validators import Email, DataRequired
from dashapp.authentication.models import Restaurants

# login and registration

# TODO pull id's directly from Restaurants table
def store_query():
    closed_stores = [1, 2, 7, 8]
    return Restaurants.query.filter(Restaurants.id.notin_(closed_stores)).order_by(Restaurants.name).all()


class LoginForm(FlaskForm):
    email = StringField("Email Address", id="email_login", validators=[DataRequired(), Email()])
    password = PasswordField("Password", id="pwd_login", validators=[DataRequired()])


class CreateAccountForm(FlaskForm):
    username = StringField("Username", id="username_create", validators=[DataRequired()])
    email = StringField("Email", id="email_create", validators=[DataRequired(), Email()])
    password = PasswordField("Password", id="pwd_create", validators=[DataRequired()])


class DateForm(FlaskForm):
    selectdate = DateField("", format="%Y-%m-%d", default=datetime.today())
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


class RecipeForm(FlaskForm):
    submit5 = SubmitField("Submit")


class PageForm(FlaskForm):
    page = SelectField(
        "Page",
        choices=["Beef", "Dairy", "Food Other", "Pork", "Poultry", "Produce", "Seafood"],
    )
    submit6 = SubmitField("Submit")
