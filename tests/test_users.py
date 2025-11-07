import pytest 
from fastapi.testclient import TestClient 
from sqlalchemy import create_engine 
from sqlalchemy.orm import sessionmaker 
 
from app.main import app, get_db 
from app.models import Base 
from sqlalchemy.pool import StaticPool
 
TEST_DB_URL = "sqlite+pysqlite:///:memory:" 
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False}, poolclass = StaticPool) 
TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False) 
Base.metadata.create_all(bind=engine)

@pytest.fixture 
def client(): 
    def override_get_db(): 
        db = TestingSessionLocal() 
        try: 
            yield db 
        finally: 
            db.close() 
    app.dependency_overrides[get_db] = override_get_db 
    with TestClient(app) as c: 
        # hand the client to the test 
        yield c 
        # --- teardown happens when the 'with' block exits --- 
 
def test_create_user(client): 
    r = client.post("/api/users", 
    json={"name":"Paul","email":"pl@atu.ie","age":25,"student_id":"S1234567"}) 
    assert r.status_code == 201     

#Tests user full replace
def test_put_user(client):
    client.post("/api/users", json = {"name":"Paul","email":"pl@atu.ie","age":25,"student_id":"S1234567"})
    r = client.put("/api/users/1", json = {"name":"Yz","email":"yz@atu.ie","age":35,"student_id":"S2234567"})
    assert r.status_code == 200

#Test user partial replace by changing the age
def test_patch_user(client):
    client.post("/api/users", json = {"name":"Paul","email":"pl@atu.ie","age":25,"student_id":"S1234567"})
    r = client.patch("api/users/1", json = {"age": 30})
    assert r.status_code == 200

#Tests Project full replace, first create a project and a user as it is needed for the owner_id
def test_put_project(client):
    client.post("/api/users", json = {"name":"Paul","email":"pl@atu.ie","age":25,"student_id":"S1234567"})
    client.post("/api/projects", json = {"name": "project 1","description": "project","owner_id": 1})
    r = client.put("/api/projects/1", json = {"name": "project 2","description": "project 2","owner_id": 1})
    assert r.status_code == 200

#Test project partial replace by changing the project name
def test_patch_project(client):
    client.post("/api/projects", json = {"name":"Paul","email":"pl@atu.ie","age":25,"student_id":"S1234567"})
    client.post("/api/projects", json = {"name": "project 1","description": "project","owner_id": 1})
    r = client.patch("api/projects/1", json = {"name": "project 2"})
    assert r.status_code == 200