from __future__ import annotations
from typing import Optional
import jwt
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

SECRET_KEY = os.getenv("JWT_SECRET", "supersecretjwtkey")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# OAuth2 scheme — lee el token del header Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def JWTBearer(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Dependencia JWT reutilizable.
    Uso: payload: dict = Depends(JWTBearer)
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autenticado — token requerido",
        )
    return decode_token(token)


async def get_tenant_id(payload: dict = Depends(JWTBearer)) -> str:
    """Extrae tenant_id del payload JWT."""
    tid = payload.get("tenant_id")
    if not tid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id requerido en el token",
        )
    return tid
