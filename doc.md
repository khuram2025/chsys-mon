sudo -u postgres psql << EOF
CREATE DATABASE readdb;
CREATE USER read WITH PASSWORD 'Read@123';
ALTER ROLE read SET client_encoding TO 'utf8';
ALTER ROLE read SET default_transaction_isolation TO read committed';
ALTER ROLE read SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE readdb TO read;
\q
EOF


cd
source venv/bin/activate
cd chsys_mon


python manage.py runserver 0.0.0.0:8000

python manage.py makemigrations
python manage.py migrate
