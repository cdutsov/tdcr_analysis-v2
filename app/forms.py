import re

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import SelectField, StringField, PasswordField
from wtforms.validators import DataRequired

from app import db
from .models import Measurement, User


class UploadForm(FlaskForm):
    series_name = StringField('series_name', validators=[DataRequired()])
    bulk_tag = StringField('bulk_tag')
    files = FileField('', validators=[
        FileRequired(message='There was no file!'),
    ])


class LoginForm(FlaskForm):
    username = StringField('username', validators=[DataRequired()])
    password = PasswordField('password', validators=[DataRequired()])
    # remember_me = BooleanField('remember_me', default=False)


def get_choices(column):
    coinc_choices = []
    if column == Measurement.radionuclide:
        coinc_choices = [('', 'Any')]
    else:
        coinc_choices = [('', 'Any'), ('0', 'Do not show')]
    coinc_choices.extend(
        sorted([(value[0], str(value[0])) for value in
                db.session.query(column).distinct()],
               key=lambda tup: int(re.findall(r'\d+', str(tup))[0]) if len(re.findall(r'\d+', str(tup))) else 0))
    return coinc_choices


class ExportForm(FlaskForm):
    series_name = StringField('series_name', id='series_name')
    radionuclides = get_choices(Measurement.radionuclide)
    radionuclide = SelectField(choices=radionuclides, id="radionuclide")
    coinc_choices_n = get_choices(Measurement.coinc_window_n)
    coinc_window_n = SelectField(choices=coinc_choices_n, id="coinc_window_n")
    coinc_choices_m = get_choices(Measurement.coinc_window_m)
    coinc_window_m = SelectField(choices=coinc_choices_m, id="coinc_window_m")
    ext_dt1_choices = get_choices(Measurement.ext_dt1)
    ext_dt1 = SelectField(choices=ext_dt1_choices, id="ext_dt1")
    ext_dt2_choices = get_choices(Measurement.ext_dt2)
    ext_dt2 = SelectField(choices=ext_dt2_choices, id="ext_dt2")

    @classmethod
    def new(cls, user):
        form = cls()
        form.radionuclides = get_choices(Measurement.radionuclide)
        form.coinc_choices_n = get_choices(Measurement.coinc_window_n)
        form.coinc_choices_m = get_choices(Measurement.coinc_window_m)
        form.ext_dt1_choices = get_choices(Measurement.ext_dt1)
        form.ext_dt2_choices = get_choices(Measurement.ext_dt2)
        form.series_choices = [str(value[0]) for value in db.session.query(Measurement.series_name).join(User).filter(
            User.username == user).distinct()]
        return form


class DeleteForm(FlaskForm):
    series_name = StringField('series_name', id='series_name')

    @classmethod
    def new(cls, user):
        form = cls()
        form.series_choices = [str(value[0]) for value in db.session.query(Measurement.series_name).join(User).filter(
            User.username == user).distinct()]

        return form
