APP = app.main:app 
PID_FILE = .uvicorn.pid 

install: 
	pip install -r requirements.txt

run:
	python -m uvicorn $(APP) --host localhost --port 8000 --reload 

test: 
	python -m pytest -q