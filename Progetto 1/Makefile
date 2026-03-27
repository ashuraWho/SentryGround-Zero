# Makefile for Secure EO Pipeline

.PHONY: install run test clean

install:
	pip install -r requirements.txt
	pip install pytest

run:
	python main.py

test:
	PYTHONPATH=. pytest tests/ -v

clean:
	rm -rf simulation_data
	rm -rf __pycache__
	rm -rf secure_eo_pipeline/__pycache__
	rm -rf secure_eo_pipeline/components/__pycache__
	rm -rf secure_eo_pipeline/utils/__pycache__
	rm -rf secure_eo_pipeline/resilience/__pycache__
	rm -rf tests/__pycache__
	rm -f audit.log
	@echo "Cleaned up runtime data and logs."

lint:
	# Stop the build if there are Python syntax errors or undefined names
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	# Exit-zero treats all errors as warnings. The GitHub editor is 127 chars wide
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
