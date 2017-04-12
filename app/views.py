import os
import pickle
import re
from datetime import datetime

from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.fileadmin import FileAdmin
from flask_admin.contrib.sqla import ModelView
from flask_login import login_required
from flask_login import login_user
from flask_login import logout_user, current_user
from sqlalchemy import and_
from sqlalchemy import func

from app import app, db, login_manager
from flask import g
from flask import make_response, jsonify
from flask import render_template, request, redirect, url_for
from .db_management import extract_bundle, add_columns, write_csv, import_files, get_or_create
from .forms import UploadForm, ExportForm, LoginForm
from .models import Measurement, Cocktail, User
from collections import OrderedDict

ALLOWED_EXTENSIONS = {'tdc'}


class MeasView(ModelView):
    column_exclude_list = ('cps_bundle', 'timers_bundle', 'counters_bundle', 'path', 'serial_number')

    def create_form(self, **kwargs):
        return self._use_filtered_parent(super(MeasView, self).create_form())

    def get_query(self):
        return super(MeasView, self).get_query().join(User).filter(User.username == current_user.username)

    def get_count_query(self):
        """
            Return a the count query for the model type

            A ``query(self.model).count()`` approach produces an excessive
            subquery, so ``query(func.count('*'))`` should be used instead.

            See commit ``#45a2723`` for details.
        """
        return self.session.query(func.count('*')).select_from(self.model).join(User).filter(
            User.username == current_user.username)

    def edit_form(self, obj):
        return self._use_filtered_parent(super(MeasView, self).edit_form(obj))

    def _use_filtered_parent(self, form):
        form.uploader.query_factory = self._get_parent_list
        return form

    def _get_parent_list(self):
        return self.session.query(User).filter_by(username='test-account').all()

    def is_accessible(self):
        return current_user.is_authenticated


class AnyView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated


class UserView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.username == "admin"


class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login', next=request.url))


class MyFileAdmin(FileAdmin):
    def get_base_path(self):
        path = FileAdmin.get_base_path(self)
        if not current_user.is_anonymous:
            return os.path.join(path, current_user.username)
        else:
            return path


if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.mkdir(app.config['UPLOAD_FOLDER'])

admin = Admin(app, name='TDCR database', index_view=MyAdminIndexView(),
              base_template='admin-layout.html', template_mode='bootstrap3')
admin.add_view(MeasView(Measurement, db.session))
admin.add_view(AnyView(Cocktail, db.session))
admin.add_view(UserView(User, db.session))
admin.add_view(MyFileAdmin(base_path=app.config['UPLOAD_FOLDER'], name='Files'))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    form = UploadForm()
    g.user = current_user
    export_form = ExportForm().new(user=current_user.username)
    try:
        session_committed = request.args['session_committed']
    except:
        session_committed = False
    try:
        commit_canceled = request.args['commit_canceled']
    except:
        commit_canceled = False

    if export_form.validate_on_submit():
        return redirect(url_for('export'))
    return render_template('index.html',
                           import_form=form,
                           export_form=export_form,
                           session_committed=session_committed,
                           commit_canceled=commit_canceled)


login_manager.login_view = "login"


@login_manager.user_loader
def load_user(userid):
    return User.query.filter(User.id == userid).first()


@app.before_request
def before_request():
    g.user = current_user


@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user is not None and g.user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first_or_404()
        if user.is_correct_password(form.password.data):
            login_user(user)
            return redirect(url_for('index'))
        else:
            return redirect(url_for('login'))
    return render_template('login.html', form=form)


@app.route('/logout')
def signout():
    logout_user()

    return redirect(url_for('index'))


@app.route('/commit-session')
def commit():
    upload_folder = app.config['UPLOAD_FOLDER']
    path = upload_folder + current_user.username + "/.tmp_pickle"
    if os.path.isfile(path=path):
        with open(path, "rb") as f:
            all_meas = pickle.load(f)
            os.remove(path)
        for meas in all_meas:
            meas["cocktail"] = \
                get_or_create(db.session, Cocktail, cocktail_name=re.sub('[^A-Za-z0-9]+', '', meas["cocktail"]))
            meas["uploader"] = \
                get_or_create(db.session, User, username=meas["uploader"])
            db.session.add(Measurement(**meas))
            db.session.commit()
            g.session_commited = True
        return redirect(url_for("index", session_committed=True))
    else:
        return redirect(url_for("index", session_not_committed=True))


@app.route('/_clear_pickle')
def clear():
    return redirect(url_for("index", commit_canceled=True))


@app.route('/uploadajax', methods=['GET', 'POST'])
def session():
    files = request.files.getlist("files")
    series_name = request.form['series_name_field']
    bulk_tag = request.form['serial_tag_field']
    results = import_files(user_folder=current_user.username, files=files, series_name=series_name, bulk_tag=bulk_tag)
    list_of_dicts = []

    for result in results:
        d = OrderedDict(
            [('File name', result["filename"]),
             ('Start time', result["datetime"]),
             ('Real time', extract_bundle(result["timers_bundle"], fields=["Real_Time"])["Real Time"]),
             ('Series name', result["series_name"]),
             ('Radionuclide', result["radionuclide"]),
             ('LS cocktail', result["cocktail"]),
             ('Coincidence window N', result["coinc_window_n"]),
             ('Coincidence window M', result["coinc_window_m"]),
             ('EXT DT 1', result["ext_dt1"]),
             ('EXT DT 2', result["ext_dt2"])])
        d.update(extract_bundle(result["cps_bundle"], fields=['N1', 'N2', 'M1', 'M2']))
        list_of_dicts.append(d)
    return jsonify({'template': render_template('upload_table.html', table=list_of_dicts)})


@app.route("/export", methods=['GET', 'POST'])
def export():
    show_raw_cps = False
    series_name = request.form['series_name']
    coinc_window_n = request.form['coinc_window_n']
    coinc_window_m = request.form['coinc_window_m']
    ext_dt1 = request.form['ext_dt1']
    ext_dt2 = request.form['ext_dt2']
    radionuclide = request.form['radionuclide']
    results = db.session.query(Measurement).join(User).filter(
        and_(Measurement.series_name == series_name if series_name else True,
             Measurement.radionuclide == radionuclide if radionuclide else True,
             Measurement.coinc_window_n == coinc_window_n if coinc_window_n and not coinc_window_n == '0' else True,
             Measurement.coinc_window_m == coinc_window_m if coinc_window_m and not coinc_window_m == '0' else True,
             Measurement.ext_dt1 == ext_dt1 if ext_dt1 and not ext_dt1 == '0' else True,
             Measurement.ext_dt2 == ext_dt2 if ext_dt2 and not ext_dt2 == '0' else True
             )).filter(User.username == g.user.username).all()
    l = []
    for result in results:
        d = OrderedDict(
            [('File name', result.filename),
             ('Start time', result.datetime),
             ('Real time', extract_bundle(result.timers_bundle, fields=["Real_Time"])["Real Time"]),
             ('Series name', result.series_name),
             ('Radionuclide', result.radionuclide),
             ('LS cocktail', result.cocktail.cocktail_name),
             ('Coincidence window N' if not coinc_window_n == '0' else False, result.coinc_window_n),
             ('Coincidence window M' if not coinc_window_m == '0' else False, result.coinc_window_m),
             ('EXT DT 1' if not ext_dt1 == '0' else False, result.ext_dt1),
             ('EXT DT 2' if not ext_dt2 == '0' else False, result.ext_dt2)])
        fields = ['RAW' if show_raw_cps else '',
                  ('N1' if not coinc_window_n == '0' else '') if not ext_dt1 == '0' else '',
                  ('N2' if not coinc_window_n == '0' else '') if not ext_dt2 == '0' else '',
                  ('M1' if not coinc_window_m == '0' else '') if not ext_dt1 == '0' else '',
                  ('M2' if not coinc_window_m == '0' else '') if not ext_dt2 == '0' else ''
                  ]
        d.update(extract_bundle(result.cps_bundle, fields=fields))
        l.append(d)
    rows = add_columns(l)
    filename = app.config['UPLOAD_FOLDER'] + current_user.username + "/Exports/Export_" \
               + datetime.now().strftime("%a_%d_%b_%Y_%H:%M:%S") + ".csv "
    write_csv(filename=filename, dict=rows)
    response = make_response(open(filename, 'r').read())
    cd = 'attachment; filename=' + filename
    response.headers['Content-Disposition'] = cd
    response.mimetype = 'text/csv'
    return response


@app.route("/_series_exists")
def series_exists():
    series_name = request.args.get('series_name', '', type=str)
    results = db.session.query(Measurement).join(User).filter(Measurement.series_name == series_name) \
        .filter(User.username == current_user.username).all()
    return jsonify(response=len(results))


@app.route("/_export_form_data")
def form_data():
    coinc_window_n_vals, coinc_window_m_vals, radionuclide_vals, series_name_vals, ext_dt1_vals, ext_dt2_vals = \
        'undefined', 'undefined', 'undefined', 'undefined', 'undefined', 'undefined'
    series_name = request.args.get('series_name', '', type=str)
    radionuclide = request.args.get('radionuclide', '', type=str)
    coinc_window_n = request.args.get('coinc_window_n', '', type=int)
    coinc_window_m = request.args.get('coinc_window_m', '', type=int)
    ext_dt1 = request.args.get('ext_dt1', '', type=float)
    ext_dt2 = request.args.get('ext_dt2', '', type=float)
    results = db.session.query(Measurement).join(User).filter(
        and_((Measurement.series_name == series_name if series_name else True),
             Measurement.radionuclide == radionuclide if radionuclide else True,
             Measurement.coinc_window_n == coinc_window_n if coinc_window_n else True,
             Measurement.coinc_window_m == coinc_window_m if coinc_window_m else True,
             Measurement.ext_dt1 == ext_dt1 if ext_dt1 else True,
             Measurement.ext_dt2 == ext_dt2 if ext_dt2 else True,
             )).filter(User.username == g.user.username).all()
    number_results = len(results)
    if not coinc_window_n:
        coinc_window_n_vals = sorted(set([result.coinc_window_n for result in results]))
    if not coinc_window_m:
        coinc_window_m_vals = sorted(set([result.coinc_window_m for result in results]))
    if not ext_dt1:
        ext_dt1_vals = sorted(set([result.ext_dt1 for result in results]))
    if not ext_dt2:
        ext_dt2_vals = sorted(set([result.ext_dt2 for result in results]))
    if not series_name:
        series_name_vals = sorted(set([result.series_name for result in results]))
    if not radionuclide:
        radionuclide_vals = sorted(set([result.radionuclide for result in results]))
    return jsonify(coinc_window_n_vals=coinc_window_n_vals,
                   coinc_window_m_vals=coinc_window_m_vals,
                   series_name_vals=series_name_vals,
                   radionuclide_vals=radionuclide_vals,
                   ext_dt1_vals=ext_dt1_vals,
                   ext_dt2_vals=ext_dt2_vals,
                   number_results=number_results)
