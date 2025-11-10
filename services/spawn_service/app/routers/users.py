import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import get_current_principal
from ..database import get_db
from ..models import Tenant, User
from ..schemas import Principal, UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> list[User]:
    query = select(User)
    if principal.tenant_id:
        query = query.where(User.tenant_id == principal.tenant_id)
    users = db.execute(query).scalars().all()
    return users


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> User:
    if principal.tenant_id and principal.tenant_id != user_in.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    tenant = db.get(Tenant, user_in.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    user = User(**user_in.model_dump())
    try:
        db.add(user)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="User already exists for tenant") from exc
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if principal.tenant_id and principal.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return user


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if principal.tenant_id and principal.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    for field, value in user_in.model_dump(exclude_unset=True).items():
        setattr(user, field, value)

    try:
        db.add(user)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="User already exists for tenant") from exc

    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> None:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if principal.tenant_id and principal.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    db.delete(user)
    db.commit()
