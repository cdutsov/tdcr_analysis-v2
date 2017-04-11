#!flask/bin/python
from app import db
from app.models import User


def create_user(username, password):
    user = User(username=username, password=password)
    db.session.add(user)
    db.session.commit()
    print("user created:", user.username)
