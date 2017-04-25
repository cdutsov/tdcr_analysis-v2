import os

from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.fileadmin import FileAdmin
from flask_admin.contrib.sqla import ModelView
from .models import Measurement, Cocktail, User
from flask_login import current_user
from sqlalchemy import func
from app import app, db, login_manager
from flask import redirect, url_for, request


class MeasView(ModelView):
    column_exclude_list = ('cps_bundle', 'timers_bundle', 'counters_bundle', 'path', 'serial_number', 'hardware_bundle',
                           'comment', 'preset_timer_name')
    page_size = 20
    can_set_page_size = True

    # can_export = True

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
        return self.session.query(User).filter_by(username=current_user.username).all()

    def is_accessible(self):
        return current_user.is_authenticated


class CocktailView(ModelView):
    def create_form(self, **kwargs):
        return self._use_filtered_parent(super(CocktailView, self).create_form())

    def get_query(self):
        return super(CocktailView, self).get_query().join(User).filter(User.username == current_user.username)

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
        return self._use_filtered_parent(super(CocktailView, self).edit_form(obj))

    def _use_filtered_parent(self, form):
        form.uploader.query_factory = self._get_parent_list
        return form

    def _get_parent_list(self):
        return self.session.query(User).filter_by(username=current_user.username).all()

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
admin.add_view(CocktailView(Cocktail, db.session))
admin.add_view(UserView(User, db.session))
admin.add_view(MyFileAdmin(base_path=app.config['UPLOAD_FOLDER'], name='Files'))
