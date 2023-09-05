help:
	@echo "help\t- Print this message"
	@echo "serve\t- Launches web server"
	@echo "depends\t- Downloads all dependencies"

virtual_env:
	virtualenv -p python3 virtual_env
	make depends

depends: virtual_env
	. virtual_env/bin/activate; python -m pip install -r requirements.txt --upgrade

serve: virtual_env
	. virtual_env/bin/activate; virtual_env/bin/gunicorn --bind 127.0.0.1:35795 server-snpshtr:app --preload --workers 2 --threads 3

all: virtual_env
	@echo "Nothing to do here"

devserver: virtual_env
	make all
	. virtual_env/bin/activate; FLASK_ENV=development FLASK_DEBUG=1 virtual_env/bin/flask -A server-snpshtr:app run --host=0.0.0.0 --port=8088 --reload
