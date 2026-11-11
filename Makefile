PYTHON ?= python3
export PYTHONPATH := src

.PHONY: run test lint demo

run:
	$(PYTHON) -m depgraph $(ARGS)

test:
	$(PYTHON) -m unittest discover -s tests -v

lint:
	$(PYTHON) -m flake8 src tests scripts

demo:
	sh scripts/run_all.sh
