#!flask/bin/python
import os
os.environ['DATABASE_URL'] = 'mysql+pymysql://tdcr:tdcr-samolet2@localhost/tdcr'

from flipflop import WSGIServer
from app import app

if __name__ == '__main__':
    WSGIServer(app).run()
