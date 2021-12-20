# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from flask import render_template, redirect, session, request, url_for
from flask_login.utils import login_required
from flask_security import current_user
from flask_security.decorators import auth_required, roles_accepted
from dashapp.authentication import blueprint
from dashapp.authentication.forms import LoginForm, CreateAccountForm
from dashapp.authentication.models import Users, db, user_datastore, security
from dashapp.authentication.util import verify_pass
from datetime import datetime, timedelta




# Login & Registration


#@blueprint.route("/login", methods=["GET", "POST"])
#def login():
#    login_form = LoginForm(request.form)
#    if "login" in request.form:

#        # read form data
#        email = request.form.get('email')
#        username = request.form.get("username")
#        password = request.form.get("password")
#
#        # Locate user
#        user_datastore.find_user(email=email)
##        user = Users.query.filter_by(username=username).first()
#
#        # Check the password
#        if user and verify_pass(password, user.password):
#
#            login_user(user)
#            return redirect(url_for("authentication_blueprint.route_default"))
#
#        # Something (user or pass) is not ok
#        return render_template(
#            "security/login_user.html", msg="Wrong user or password", form=login_form
#        )
#
#    if not current_user:
#        print('not current user')
#        return render_template("security/login_user.html", form=login_form)

#    print(" LOGIN ")
#    if current_user:
#        TODAY = datetime.date(datetime.now())
#        print(TODAY)
#        YSTDAY = TODAY - timedelta(days=1)
#        session["targetdate"] = YSTDAY.strftime("%Y-%m-%d")
#        return redirect(url_for("home_blueprint.index"))


@blueprint.route("/register/", methods=["GET", "POST"])
@login_required
@roles_accepted('admin')
def register():
    create_account_form = CreateAccountForm(request.form)
    if "register" in request.form:

        email = request.form["email"]

        # Check usename exists
#        user = Users.query.filter_by(username=username).first()
#        if user:
#            return render_template(
#                "security/register.html",
#                msg="Username already registered",
#                success=False,
#                form=create_account_form,
#            )

        # Check email exists
        user = Users.query.filter_by(email=email).first()
        if user:
            return render_template(
                "security/register.html",
                msg="Email already registered",
                success=False,
                form=create_account_form,
            )

        # else we can create the user
        user = Users(**request.form)
        db.session.add(user)
        db.session.commit()

        return render_template(
            "accounts/register.html",
            msg='User created please <a href="/login">login</a>',
            success=True,
            form=create_account_form,
        )

    else:
        return render_template("accounts/register.html", form=create_account_form)


#@blueprint.route("/logout")
#def logout():
#    logout_user()
#    return redirect(url_for("authentication_blueprint.login"))


# Errors


#@login_manager.unauthorized_handler
#def unauthorized_handler():
#    return render_template("home/page-403.html"), 403


@blueprint.errorhandler(403)
def access_forbidden(error):
    return render_template("home/page-403.html"), 403


@blueprint.errorhandler(404)
def not_found_error(error):
    return render_template("home/page-404.html"), 404


@blueprint.errorhandler(500)
def internal_error(error):
    return render_template("home/page-500.html"), 500
