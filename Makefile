.PHONY: install test migrate run build up down logs clean

install:
	pip install -r requirements.txt

test:
	python manage.py test hiring.tests

migrate:
	python manage.py migrate

run:
	python manage.py runserver

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f web

clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

superuser:
	python manage.py createsuperuser

collectstatic:
	python manage.py collectstatic --noinput