from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Boolean, Float, Text, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel
from typing import Optional, List
import os
import uuid
import json

# 生产环境必须设置 ZHITONG_JWT_SECRET 环境变量；默认值仅用于本地开发
SECRET_KEY = os.environ.get("ZHITONG_JWT_SECRET", "dev-secret-change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SQLALCHEMY_DATABASE_URL = "sqlite:///./zhitong.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="user")
    created_at = Column(DateTime, default=datetime.utcnow)
    violations = relationship("ViolationRecord", back_populates="operator")

class ViolationRecord(Base):
    __tablename__ = "violation_records"
    id = Column(Integer, primary_key=True, index=True)
    violation_type = Column(String)
    license_plate = Column(String, index=True)
    confidence = Column(Float)
    image_path = Column(String)
    location = Column(String)
    timestamp = Column(DateTime, index=True)
    operator_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="pending")
    operator = relationship("User", back_populates="violations")

class SystemLog(Base):
    __tablename__ = "system_logs"
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String)
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    source = Column(String)

class ControlCommand(Base):
    __tablename__ = "control_commands"
    id = Column(Integer, primary_key=True, index=True)
    command = Column(String)
    parameters = Column(Text)
    status = Column(String, default="pending")
    user_id = Column(Integer, ForeignKey("users.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    response = Column(Text)

Base.metadata.create_all(bind=engine)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    password: str
    role: Optional[str] = "user"

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime

class ViolationRecordCreate(BaseModel):
    violation_type: str
    license_plate: Optional[str] = None
    confidence: float
    location: Optional[str] = None

class ViolationRecordResponse(BaseModel):
    id: int
    violation_type: str
    license_plate: Optional[str]
    confidence: float
    image_path: Optional[str]
    location: Optional[str]
    timestamp: datetime
    status: str

class ControlCommandCreate(BaseModel):
    command: str
    parameters: Optional[dict] = None

class ControlCommandResponse(BaseModel):
    id: int
    command: str
    status: str
    timestamp: datetime
    response: Optional[str]

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user

app = FastAPI(title="智瞳智慧交管系统API", version="1.0")

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    db_user = get_user(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed_password, role=user.role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.post("/violations/", response_model=ViolationRecordResponse)
async def create_violation_record(
    violation: ViolationRecordCreate = Depends(),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    image_data = await file.read()
    image_filename = f"{uuid.uuid4()}.jpg"
    image_path = f"uploads/{image_filename}"
    
    os.makedirs("uploads", exist_ok=True)
    with open(image_path, "wb") as f:
        f.write(image_data)
    
    new_record = ViolationRecord(
        violation_type=violation.violation_type,
        license_plate=violation.license_plate,
        confidence=violation.confidence,
        image_path=image_path,
        location=violation.location,
        timestamp=datetime.now(),
        operator_id=current_user.id
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return new_record

@app.get("/violations/", response_model=List[ViolationRecordResponse])
async def get_violation_records(
    skip: int = 0,
    limit: int = 100,
    license_plate: Optional[str] = None,
    violation_type: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(ViolationRecord)
    
    if license_plate:
        query = query.filter(ViolationRecord.license_plate.like(f"%{license_plate}%"))
    if violation_type:
        query = query.filter(ViolationRecord.violation_type == violation_type)
    if start_time:
        query = query.filter(ViolationRecord.timestamp >= start_time)
    if end_time:
        query = query.filter(ViolationRecord.timestamp <= end_time)
    
    return query.offset(skip).limit(limit).all()

@app.get("/violations/{record_id}", response_model=ViolationRecordResponse)
async def get_violation_record(record_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    record = db.query(ViolationRecord).filter(ViolationRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return record

@app.put("/violations/{record_id}", response_model=ViolationRecordResponse)
async def update_violation_record(
    record_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    record = db.query(ViolationRecord).filter(ViolationRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    record.status = status
    db.commit()
    db.refresh(record)
    return record

@app.post("/control/", response_model=ControlCommandResponse)
async def send_control_command(
    command: ControlCommandCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="无操作权限")
    
    new_command = ControlCommand(
        command=command.command,
        parameters=json.dumps(command.parameters) if command.parameters else None,
        user_id=current_user.id
    )
    db.add(new_command)
    db.commit()
    db.refresh(new_command)
    return new_command

@app.get("/control/{command_id}", response_model=ControlCommandResponse)
async def get_control_command(command_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    command = db.query(ControlCommand).filter(ControlCommand.id == command_id).first()
    if not command:
        raise HTTPException(status_code=404, detail="命令不存在")
    return command

@app.post("/logs/")
async def create_log(
    level: str,
    message: str,
    source: str = "api",
    db: Session = Depends(get_db)
):
    new_log = SystemLog(level=level, message=message, source=source)
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    return {"status": "ok"}

@app.get("/logs/")
async def get_logs(
    skip: int = 0,
    limit: int = 100,
    level: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    query = db.query(SystemLog)
    if level:
        query = query.filter(SystemLog.level == level)
    return query.order_by(SystemLog.timestamp.desc()).offset(skip).limit(limit).all()

@app.get("/stats/violations")
async def get_violation_stats(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(ViolationRecord)
    if start_time:
        query = query.filter(ViolationRecord.timestamp >= start_time)
    if end_time:
        query = query.filter(ViolationRecord.timestamp <= end_time)
    
    total = query.count()
    by_type = db.query(
        ViolationRecord.violation_type,
        func.count(ViolationRecord.id)
    ).group_by(ViolationRecord.violation_type).all()
    
    return {
        "total": total,
        "by_type": {vt: cnt for vt, cnt in by_type}
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "zhitong-api"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)