#!flask/bin/python
import sys
from app import db
from app.models import User

user = User(username=sys.argv[1], password=sys.argv[2])
db.session.add(user)
db.session.commit()
print("user created: ", user.username, " with password: ", sys.argv[2])
