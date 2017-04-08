WTF_CSRF_ENABLED = True
SECRET_KEY = 'n49RtlwUYxYmhqW8OhM6c67nIAlI63Su'
UPLOAD_FOLDER = 'data/'

import os

basedir = os.path.abspath(os.path.dirname(__file__))
if os.environ.get('DATABASE_URL') is None:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'tdcr_database.db')
else:
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
# SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'tdcr_database.db')
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'tdcr_db_repository')
SQLALCHEMY_TRACK_MODIFICATIONS = False
