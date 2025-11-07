from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, Response, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from app.database import engine, SessionLocal
from app.models import Base, UserDB, CourseDB, ProjectDB
from .schemas import (
    UserCreate, UserRead,
    CourseCreate, CourseRead,
    ProjectCreate, ProjectRead,
    ProjectReadWithOwner, ProjectCreateForUser
)

# Replaces @app.on_event("startup")
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(lifespan=lifespan)

# CORS (dev-friendly; tighten in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # specify domains in prod
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def commit_or_rollback(db: Session, error_msg: str):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=error_msg)

@app.get("/health")
def health():
    return {"status": "ok"}


#Below are all the code from previous lab
# ---------- COURSES ----------
@app.post("/api/courses", response_model=CourseRead, status_code=201)
def create_course(course: CourseCreate, db: Session = Depends(get_db)):
    db_course = CourseDB(**course.model_dump())
    db.add(db_course)
    commit_or_rollback(db, "Course already exists")
    db.refresh(db_course)
    return db_course

@app.get("/api/courses", response_model=list[CourseRead])
def list_courses(limit: int = 10, offset: int = 0, db: Session = Depends(get_db)):
    stmt = select(CourseDB).order_by(CourseDB.id).limit(limit).offset(offset)
    return db.execute(stmt).scalars().all()

# ---------- PROJECTS ----------
@app.post("/api/projects", response_model=ProjectRead, status_code=201)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    user = db.get(UserDB, project.owner_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    proj = ProjectDB(
        name=project.name,
        description=project.description,
        owner_id=project.owner_id,
    )
    db.add(proj)
    commit_or_rollback(db, "Project creation failed")
    db.refresh(proj)
    return proj

@app.put("/api/projects/{project_id}", response_model=ProjectRead)
def replace_project(project_id: int, payload: ProjectCreate, db: Session = Depends(get_db)):
    proj = db.get(ProjectDB, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    owner = db.get(UserDB, payload.owner_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    for field, value in payload.model_dump().items():
        setattr(proj, field, value)
    commit_or_rollback(db, "Project update failed")
    db.refresh(proj)
    return proj

@app.patch("/api/projects/{project_id}", response_model=ProjectRead)
def patch_project(project_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    proj = db.get(ProjectDB, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    for field, value in payload.items():
        if hasattr(proj, field):
            setattr(proj, field, value)
    commit_or_rollback(db, "Project partial update failed")
    db.refresh(proj)
    return proj

@app.get("/api/projects", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)):
    stmt = select(ProjectDB).order_by(ProjectDB.id)
    return db.execute(stmt).scalars().all()

@app.get("/api/projects/{project_id}", response_model=ProjectReadWithOwner)
def get_project_with_owner(project_id: int, db: Session = Depends(get_db)):
    stmt = select(ProjectDB).where(ProjectDB.id == project_id).options(selectinload(ProjectDB.owner))
    proj = db.execute(stmt).scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


# ---------- USERS ----------
@app.get("/api/users", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)):
    stmt = select(UserDB).order_by(UserDB.id)
    return db.execute(stmt).scalars().all()

@app.get("/api/users/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(UserDB, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/api/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def add_user(payload: UserCreate, db: Session = Depends(get_db)):
    user = UserDB(**payload.model_dump())
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="User already exists")
    return user

@app.put("/api/users/{user_id}", response_model=UserRead)
def replace_user(user_id: int, payload: UserCreate, db: Session = Depends(get_db)):
    user = db.get(UserDB, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in payload.model_dump().items():
        setattr(user, field, value)
    commit_or_rollback(db, "User update failed")
    db.refresh(user)
    return user

@app.patch("/api/users/{user_id}", response_model=UserRead)
def patch_user(user_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    user = db.get(UserDB, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in payload.items():
        if hasattr(user, field):
            setattr(user, field, value)
    commit_or_rollback(db, "User partial update failed")
    db.refresh(user)
    return user

@app.delete("/api/users/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db)) -> Response:
    user = db.get(UserDB, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)