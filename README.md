# tdcr_analysis-v2

1. If using mysql as a database, login as a root like:
```bash
mysql -u root -p
CREATE DATABASE <database-name>;
quit;
```
Set DATABASE_URL as environmental variable. DATABASE_URL should have the following format:
```bash
DATABASE_URL=mysql+pymysql://<database-name>:<database-password>@localhost/<database-name>
```

2. Create virtual environment
```bash
virtualenv -p python3 flask
```

3. Enter virtual environment
```bash
 . flask/bin/activate
```
4. Install requirements
```bash
pip install -r requirements.txt
pip install pymysql
```

5. Create databse and make first migration (on the last line in the file __init__.py in the app/ folder delete views module, fix pending)
```bash
python manage.py db init
pyhton manage.py db migrate
python manage.py db upgrade
```
return views module in __init__.py

6. Using create_user.py script create users like:
```bash
python create_user.py <username> <password>
```
7. Start apache or whatever server

8. Enjoy :)
