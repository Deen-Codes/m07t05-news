# News Application

Django news site with role-based users (Reader / Editor / Journalist),
publishers, articles and newsletters. The REST API uses Django REST
framework with token authentication. When an editor approves an
article, a `post_save` signal emails subscribers and POSTs the
article to `/api/approved/`.

## Requirements

- Python 3.10+
- MariaDB / MySQL (or use Docker, see below)
- The packages in `requirements.txt`

## Run with venv

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Set up the database (MariaDB on macOS using Homebrew):

```
sudo mariadb <<EOF
CREATE DATABASE news_db CHARACTER SET utf8mb4;
CREATE USER 'newsapp'@'localhost' IDENTIFIED BY 'newspass';
GRANT ALL PRIVILEGES ON news_db.* TO 'newsapp'@'localhost';
GRANT ALL PRIVILEGES ON test_news_db.* TO 'newsapp'@'localhost';
FLUSH PRIVILEGES;
EOF
```

Then run:

```
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/.

## Run with Docker

```
docker compose up --build
```

Migrations and group seeding run automatically on container start.
To create a superuser inside the running container:

```
docker compose exec web python manage.py createsuperuser
```

## Run the tests

```
python manage.py test news
```

## Build the Sphinx documentation

```
cd docs
make html
open _build/html/index.html
```

## Project structure

```
M07T05_news/
  manage.py
  requirements.txt
  Dockerfile
  docker-compose.yml
  docs/                  Sphinx source
  news_project/          Django project package
  news/                  app
    models.py
    views.py
    api_views.py
    serializers.py
    permissions.py
    signals.py
    forms.py
    urls.py
    tests.py
    migrations/
    management/commands/seed_groups.py
    templates/
```

## Environment variables

`SECRETS.txt` (gitignored) has the local dev credentials.
`news_project/settings.py` has the same values as fallback defaults,
so the project will start without exporting any env vars.

## Roles

| Role        | Can do                                          |
| ----------- | ------------------------------------------------ |
| Reader      | View articles + newsletters, manage own subs    |
| Editor      | Above + edit/delete/approve articles + newsletters |
| Journalist  | Above + create articles + newsletters           |
