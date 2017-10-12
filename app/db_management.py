#!/bin/python3.6
import os
import pickle
import re
import uuid
from collections import OrderedDict
from datetime import datetime, date, timedelta

import pandas as pd
from sqlalchemy.sql import ClauseElement
from werkzeug.utils import secure_filename

from app import app
from app import db
from flask import g
from flask import redirect, url_for
from .models import Measurement, User, Cocktail
from collections import OrderedDict


def get_or_create(session, model, defaults=None, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        params = dict((k, v) for k, v in kwargs.items() if not isinstance(v, ClauseElement))
        params.update(defaults or {})
        instance = model(**params)
        session.add(instance)
        session.commit()
        print("DEBUG: NEW " + str(instance) + " ADDED")
        return instance


def import_files(user_folder, series_name, files):
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
                meas = tdc_to_dbmeas_ver34(file=open(os.path.join(par_dir, udir, filename)),
                                           series_name=series_name,
                                           serial_number=serial_number)
                all_meas.extend(meas)
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
        cocktail = re.sub('[^A-Za-z0-9]+', '', tag[5])
    else:
        radionuclide = 'N/A'
        cocktail = 'N/A'

    sample_name = ''

    coinc_window_n = 0
    coinc_window_m = 0
    ext_dt1 = 0
    ext_dt2 = 0

    cps_bundle = OrderedDict()
    counters_bundle = OrderedDict()
    timers_bundle = OrderedDict()
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


def tdc_to_dbmeas_ver34(file, series_name, serial_number):
    uploader = g.user.username
    lines = [line for line in file.readlines()]
    sample_name = ''

    hardware_bundle = OrderedDict()
    cps_bundle = OrderedDict()
    counters_bundle = OrderedDict()
    timers_bundle = OrderedDict()

    measurements = []

    # add hardware data
    for line in lines[1:3]:
        key, value = line.split(',', 1)
        hardware_bundle.update({key: value})

    settings = OrderedDict()
    for line in lines[5:21]:
        key, value = [x.strip() for x in line.split(',', 1) if x]
        settings.update({key: value})

    threshold_a = float(settings['Threshold A [mV]'])
    threshold_b = float(settings['Threshold B [mV]'])
    threshold_c = float(settings['Threshold C [mV]'])
    high_voltage = int(''.join(x for x in str(settings['High Voltage']) if x.isdigit()) or 0)
    coinc_window_n = int(settings['Coincidence Window N [ns]'])
    coinc_window_m = int(settings['Coincidence Window M [ns]'])
    ext_dt1 = float(settings['Dead Time Extension 1 [us]'])
    ext_dt2 = float(settings['Dead Time Extension 2 [us]'])
    preset_time = int(settings['Preset Time per Run [s]'])
    cocktail = settings['LS Coctail']
    radionuclide = settings['Nuclides']
    operator = settings['Operator']
    comment = settings['Measurement Tag']
    number_of_runs = settings['Preset Sequential Runs']
    stop_timer_name = settings['Stop Timer']

    start_time = datetime.now()

    start_line_number = 20
    run_number = 0

    for line in lines[start_line_number:]:
        run = line.split(':', 1)
        if len(run) == 2:
            if 'START TIME' in run[1]:
                run_number = int(''.join(i for i in re.findall(r'\d+', run[0])))
                if run_number > 1:
                    measurements.append({"path": file.name,
                                         "uploader": uploader,
                                         "serial_number": serial_number,
                                         "series_name": series_name,
                                         "filename": os.path.basename(file.name),
                                         "datetime": start_time,
                                         "stop_timer_name": stop_timer_name,
                                         "run_number": str(run_number - 1),
                                         "total_runs": str(number_of_runs),
                                         "radionuclide": radionuclide,
                                         "cocktail": cocktail,
                                         "sample_name": sample_name,
                                         "comment": comment,
                                         "operator": operator,
                                         "preset_time": preset_time,
                                         "threshold_a": threshold_a,
                                         "threshold_b": threshold_b,
                                         "threshold_c": threshold_c,
                                         "high_voltage": high_voltage,
                                         "coinc_window_n": coinc_window_n,
                                         "coinc_window_m": coinc_window_m,
                                         "ext_dt1": ext_dt1,
                                         "ext_dt2": ext_dt2,
                                         "hardware_bundle": pickle.dumps(hardware_bundle),
                                         "cps_bundle": pickle.dumps(cps_bundle),
                                         "counters_bundle": pickle.dumps(counters_bundle),
                                         "timers_bundle": pickle.dumps(timers_bundle)
                                         })
                time_row = run[1].split(':', 1)
                time = time_row[1].split(',', 1)
                stop_timer_name = time[0].strip()
                start_time = datetime.strptime(time[1].strip(), '%d/%m/%Y  %H:%M:%S.%f')
            else:
                line = run[1].rsplit(',')
                key, value = line[0], line[1]

            if "[cps]" in key:
                cps_bundle.update({key: float(value)})
            elif "[counts]" in key:
                counters_bundle.update({key: float(value)})
            elif "[s]" in key:
                timers_bundle.update({key: float(value)})
    measurements.append({"path": file.name,
                         "uploader": uploader,
                         "serial_number": serial_number,
                         "series_name": series_name,
                         "filename": os.path.basename(file.name),
                         "datetime": start_time,
                         "stop_timer_name": stop_timer_name,
                         "run_number": str(run_number),
                         "total_runs": str(number_of_runs),
                         "radionuclide": radionuclide,
                         "cocktail": cocktail,
                         "sample_name": sample_name,
                         "comment": comment,
                         "operator": operator,
                         "preset_time": preset_time,
                         "threshold_a": threshold_a,
                         "threshold_b": threshold_b,
                         "threshold_c": threshold_c,
                         "high_voltage": high_voltage,
                         "coinc_window_n": coinc_window_n,
                         "coinc_window_m": coinc_window_m,
                         "ext_dt1": ext_dt1,
                         "ext_dt2": ext_dt2,
                         "hardware_bundle": pickle.dumps(hardware_bundle),
                         "cps_bundle": pickle.dumps(cps_bundle),
                         "counters_bundle": pickle.dumps(counters_bundle),
                         "timers_bundle": pickle.dumps(timers_bundle)
                         })

    return measurements


def export_data(**kwargs):
    print(db.session.query(Measurement).filter_by(kwargs).all())


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
    rows = OrderedDict()
    for d in dicts:
        for k, v in d.items():
            if k:
                rows.setdefault(k, []).append(v)
    return rows


def write_csv(filename, d):
    with open(filename, 'w') as f:
        pd.DataFrame(d, columns=d.keys()).to_csv(filename, header=True, index=False)
        return f


def check_warnings(user, d):
    new_cocktail = d['LS cocktail']
    new_radionuclide = d['Radionuclide']
    cocktails = db.session.query(Cocktail).join(User).filter(User.username == user.username).distinct()
    cocktail_names = [cocktail.cocktail_name for cocktail in cocktails]
    measurements = db.session.query(Measurement).join(User).filter(User.username == user.username).distinct()
    radionuclides = [measurement.radionuclide for measurement in measurements]
    warnings = {}
    if not new_cocktail in cocktail_names:
        warnings.update({'cocktail': new_cocktail})
    if not new_radionuclide in radionuclides:
        warnings.update({'radionuclide': new_radionuclide})
    return warnings
