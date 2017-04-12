#!/bin/python3.6
import os
import pickle
import re
import uuid
from collections import OrderedDict
from datetime import datetime, date

import pandas as pd
from sqlalchemy.sql import ClauseElement
from werkzeug.utils import secure_filename

from app import app
from app import db
from flask import g
from flask import redirect, url_for
from .models import Measurement as dbMeas


def get_or_create(session, model, defaults=None, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        params = dict((k, v) for k, v in kwargs.items() if not isinstance(v, ClauseElement))
        params.update(defaults or {})
        instance = model(**params)
        session.add(instance)
        print("DEBUG: NEW " + str(instance) + " CREATED")
        return instance


def import_files(user_folder, series_name, files, bulk_tag):
    if not series_name:
        print("Please enter series name!")
        return redirect(url_for('index'))
    if files:
        upload_folder = app.config['UPLOAD_FOLDER']
        serial_number = str(uuid.uuid4())
        par_dir = os.path.join(upload_folder, user_folder, date.today().strftime("%B %Y"))
        udir = series_name
        if not os.path.exists(par_dir):
            os.mkdir(par_dir)
        if not os.path.exists(os.path.join(par_dir, udir)):
            os.mkdir(os.path.join(par_dir, udir))
        all_meas = []
        for file in files:
            if file.filename.split('.')[-1] == 'tdc':
                filename = secure_filename(file.filename)
                file.save(os.path.join(par_dir, udir, filename))
                try:
                    meas = tdc_to_dbmeas(file=open(os.path.join(par_dir, udir, filename)),
                                         series_name=series_name,
                                         serial_number=serial_number,
                                         bulk_tag=bulk_tag)
                    all_meas.append(meas)
                except:
                    print(".tdc file ", filename, ' is corrupted')
        pickle.dump(all_meas, file=open(os.path.join(upload_folder, user_folder) + "/.tmp_pickle", "wb"))
        return all_meas


def tdc_to_dbmeas(file, series_name, bulk_tag, serial_number):
    uploader = g.user.username
    lines = [line for line in file.readlines()]
    tag = lines[0].rsplit(',')
    cocktail = ''
    if not len(tag) == 6 and bulk_tag:
        tag = bulk_tag.rsplit(',')
    if len(tag) > 5:
        radionuclide = tag[4]
        cocktail = tag[5]
    else:
        radionuclide = 'N/A'
        cocktail = 'N/A'

    sample_name = ''

    coinc_window_n = 0
    coinc_window_m = 0
    ext_dt1 = 0
    ext_dt2 = 0

    cps_bundle = dict()
    counters_bundle = dict()
    timers_bundle = dict()
    sect = 0

    start_time = datetime.strptime(lines[1], '%d-%b-%y ,%H:%M:%S\r\n')
    for line in lines[3:]:
        line = line.rsplit(',')
        if line[0] == 'TDCR_CPS':
            sect = 0
        elif line[0] == 'TDCR Counters':
            sect = 1
        elif line[0] == 'TDCR Timers':
            sect = 2
        elif line[0] == 'TDCR Hardware\n':
            sect = 3
        if not 'TDCR' in line[0] and len(line) == 2:
            if sect == 0:
                cps_bundle.update({line[0].replace("ABC", "Triple"): float(line[1])})
            elif sect == 1:
                counters_bundle.update({line[0].replace("ABC", "Triple"): float(line[1])})
            elif sect == 2:
                timers_bundle.update({line[0].replace("ABC", "Triple"): float(line[1])})
            elif sect == 3:
                if 'Window1' in line[0]:
                    coinc_window_n = int(line[1])
                if 'Window2' in line[0]:
                    coinc_window_m = int(line[1])
                if 'Extension1' in line[0]:
                    ext_dt1 = float(line[1]) / 1000
                if 'Extension2' in line[0]:
                    ext_dt2 = float(line[1]) / 1000
    return {"path": file.name,
            "uploader": uploader,
            "serial_number": serial_number,
            "series_name": series_name,
            "filename": os.path.basename(file.name),
            "datetime": start_time,
            "radionuclide": radionuclide,
            "cocktail": cocktail,
            "sample_name": sample_name,
            "coinc_window_n": coinc_window_n,
            "coinc_window_m": coinc_window_m,
            "ext_dt1": ext_dt1,
            "ext_dt2": ext_dt2,
            "cps_bundle": pickle.dumps(cps_bundle),
            "counters_bundle": pickle.dumps(counters_bundle),
            "timers_bundle": pickle.dumps(timers_bundle)
            }


def export_data(**kwargs):
    print(db.session.query(dbMeas).filter_by(kwargs).all())


def extract_bundle(bundle, fields):
    data = pickle.loads(bundle)
    values = OrderedDict()
    for field in fields:
        if field:
            for key, value in data.items():
                if field in key:
                    values.update({re.sub('[^A-Za-z0-9\.]+', ' ', key): value})
    return values


def add_columns(dicts):
    rows = {}
    for d in dicts:
        for k, v in d.items():
            if k:
                rows.setdefault(k, []).append(v)
    return rows


def write_csv(filename, dict):
    with open(filename, 'w') as f:
        pd.DataFrame(dict, columns=dict.keys()).to_csv(filename, header=True, index=False)
        return f
