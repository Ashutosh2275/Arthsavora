from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from ..db.mongodb import get_database
from ..core.security import get_password_hash, verify_password, create_access_token
from ..core.limiter import limiter # New
from ..models.user import UserCreate, UserOut, Token
from datetime import datetime

router = APIRouter()

@router.post("/signup", response_model=UserOut)
async def signup(user_in: UserCreate):
    db = get_database()
    existing_user = await db.users.find_one({"email": user_in.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    user_dict = user_in.model_dump()
    user_dict["hashed_password"] = get_password_hash(user_dict.pop("password"))
    user_dict["created_at"] = datetime.utcnow()
    
    new_user = await db.users.insert_one(user_dict)
    user_dict["_id"] = str(new_user.inserted_id)
    return user_dict

@router.post("/login", response_model=Token)
@limiter.limit("5/minute") # Only 5 login attempts allowed per minute
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    db = get_database()
    user = await db.users.find_one({"email": form_data.username})
    
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(subject=user["email"])
    return {"access_token": access_token, "token_type": "bearer"}