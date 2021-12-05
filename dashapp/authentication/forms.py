# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from flask_wtf import FlaskForm
from wtforms import SubmitField, EmailField, StringField, PasswordField, DateField
from wtforms.validators import Email, DataRequired

# login and registration


class LoginForm(FlaskForm):
    email = StringField("Email Address", id="email_login", validators=[DataRequired(), Email()])
    password = PasswordField("Password", id="pwd_login", validators=[DataRequired()])


class CreateAccountForm(FlaskForm):
    username = StringField(
        "Username", id="username_create", validators=[DataRequired()]
    )
    email = EmailField("Email", id="email_create", validators=[DataRequired(), Email()])
    password = PasswordField("Password", id="pwd_create", validators=[DataRequired()])


class DateForm(FlaskForm):
    selectdate = DateField("Change Date: ", format="%Y-%m-%d")
    submit = SubmitField("Submit")
