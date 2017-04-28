WTF_CSRF_ENABLED = True
import os

SECRET_KEY = os.environ.get('TDCR_SECRET_KEY') or 'enter-key-as-os-environmental-variable'
basedir = os.path.abspath(os.path.dirname(__file__))
if os.environ.get('DATABASE_URL') is None:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'tdcr_database.db')
else:
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'tdcr_db_repository')
SQLALCHEMY_TRACK_MODIFICATIONS = False
UPLOAD_FOLDER = os.path.join(basedir, 'data/')
