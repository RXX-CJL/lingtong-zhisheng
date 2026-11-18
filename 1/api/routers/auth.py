"""
用户认证路由模块
提供 JWT 登录、用户管理等功能
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
import os

from database import get_db
from models import User
from schemas import ApiResponse

router = APIRouter(prefix="/api/auth", tags=["认证"])

# 安全配置
# 生产环境必须设置 ZHITONG_JWT_SECRET 环境变量；默认值仅用于本地开发
SECRET_KEY = os.environ.get("ZHITONG_JWT_SECRET", "dev-secret-change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

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
        detail="无法验证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="用户未激活")
    return current_user

async def get_current_admin(current_user: User = Depends(get_current_active_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user

@router.post("/login")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """用户登录，获取 JWT Token"""
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="用户未激活")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "role": user.role
        }
    }

@router.get("/me", response_model=ApiResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return ApiResponse(
        success=True,
        message="获取成功",
        data={
            "id": current_user.id,
            "username": current_user.username,
            "name": current_user.name,
            "role": current_user.role,
            "email": current_user.email
        }
    )

@router.post("/register", response_model=ApiResponse)
async def register_user(
    username: str,
    password: str,
    name: Optional[str] = None,
    email: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """管理员创建新用户"""
    if db.query(User).filter(User.username == username).first():
        return ApiResponse(
            success=False,
            message="用户名已存在"
        )
    
    hashed_password = get_password_hash(password)
    new_user = User(
        username=username,
        password_hash=hashed_password,
        name=name or username,
        email=email,
        role="user"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return ApiResponse(
        success=True,
        message="用户创建成功",
        data={"user_id": new_user.id, "username": new_user.username}
    )

@router.get("/users", response_model=ApiResponse)
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """管理员获取用户列表"""
    users = db.query(User).all()
    user_list = [
        {
            "id": u.id,
            "username": u.username,
            "name": u.name,
            "role": u.role,
            "email": u.email,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None
        }
        for u in users
    ]
    
    return ApiResponse(
        success=True,
        message="获取成功",
        data={"users": user_list}
    )

@router.put("/users/{user_id}", response_model=ApiResponse)
async def update_user(
    user_id: int,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    name: Optional[str] = None,
    email: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """管理员更新用户信息"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return ApiResponse(
            success=False,
            message="用户不存在"
        )
    
    if role is not None:
        user.role = role
    if is_active is not None:
        user.is_active = is_active
    if name is not None:
        user.name = name
    if email is not None:
        user.email = email
    
    db.commit()
    db.refresh(user)
    
    return ApiResponse(
        success=True,
        message="更新成功",
        data={"user_id": user.id}
    )

@router.delete("/users/{user_id}", response_model=ApiResponse)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """管理员删除用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return ApiResponse(
            success=False,
            message="用户不存在"
        )
    
    if user.role == "admin" and user.id == current_user.id:
        return ApiResponse(
            success=False,
            message="不能删除自己"
        )
    
    db.delete(user)
    db.commit()
    
    return ApiResponse(
        success=True,
        message="删除成功"
    )

def init_default_user(db: Session):
    """初始化默认管理员用户"""
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        admin = User(
            username="admin",
            password_hash=get_password_hash("admin123"),
            name="系统管理员",
            role="admin",
            is_active=True
        )
        db.add(admin)
        db.commit()
        print("✓ 默认管理员用户已创建 (admin/admin123)")
    else:
        print("✓ 默认管理员用户已存在")