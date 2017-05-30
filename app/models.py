from sqlalchemy.ext.hybrid import hybrid_property

from app import db, bcrypt


class Measurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    serial_number = db.Column(db.String)
    series_name = db.Column(db.String)
    path = db.Column(db.String(300))
    filename = db.Column(db.String(50))
    datetime = db.Column(db.DateTime)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    operator = db.Column(db.String(50))

    sample_name = db.Column(db.String(50))
    cocktail_id = db.Column(db.Integer, db.ForeignKey('cocktail.id'))
    radionuclide = db.Column(db.String(50))
    comment = db.Column(db.String(200))
    preset_time = db.Column(db.Integer)
    stop_timer_name = db.Column(db.String(20))
    run_number = db.Column(db.String(15))
    total_runs = db.Column(db.String(10))

    threshold_a = db.Column(db.Float)
    threshold_b = db.Column(db.Float)
    threshold_c = db.Column(db.Float)
    high_voltage = db.Column(db.Integer)
    coinc_window_n = db.Column(db.Integer)
    coinc_window_m = db.Column(db.Integer)
    ext_dt1 = db.Column(db.Float)
    ext_dt2 = db.Column(db.Float)

    # Bundles
    hardware_bundle = db.Column(db.PickleType)
    cps_bundle = db.Column(db.PickleType)
    counters_bundle = db.Column(db.PickleType)
    timers_bundle = db.Column(db.PickleType)

    def __repr__(self):
        return '<Measurement %r>' % self.filename


class Cocktail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cocktail_name = db.Column(db.String(50))
    cocktail_density = db.Column(db.Float)
    cocktail_ratio = db.Column(db.Float)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    cocktail = db.relationship('Measurement', backref='cocktail')

    def __repr__(self):
        return '<Cocktail %r>' % self.cocktail_name


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    _password = db.Column(db.String(120))
    uploader = db.relationship('Measurement', backref='uploader')
    cocktail_uploader = db.relationship('Cocktail', backref='cocktail_uploader')

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @hybrid_property
    def password(self):
        return self._password

    @password.setter
    def _set_password(self, plaintext):
        self._password = bcrypt.generate_password_hash(plaintext)

    def is_correct_password(self, plaintext):
        return bcrypt.check_password_hash(self._password, plaintext)

    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return '<User %r>' % self.username
