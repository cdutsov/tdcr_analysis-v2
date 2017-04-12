#!flask/bin/python
import sys, os
from app import db
from app.models import User
from app.config import UPLOAD_FOLDER

username = sys.argv[1]
password = sys.argv[2]
user = User(username=username, password=password)
if not os.path.exists(os.path.join(UPLOAD_FOLDER, username)):
    os.mkdir(os.path.join(UPLOAD_FOLDER, username))

if not os.path.exists(os.path.join(UPLOAD_FOLDER, username, 'Exports')):
    os.mkdir(os.path.join(UPLOAD_FOLDER, username, 'Exports'))

db.session.add(user)
db.session.commit()
print("user created: ", user.username, " with password: ", password)
