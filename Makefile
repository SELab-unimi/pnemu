
TEST_PATH=./tests

init:
	pip3 install -r requirements.txt

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +

install:
	python3 setup.py install

test:
	python3 -m pytest -s $(TEST_PATH)
