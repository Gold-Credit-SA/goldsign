"""ServiÃ§o de autenticaÃ§Ã£o JWT com suporte a roles (adm, gestor, cliente)."""

from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from config import get_settings
import database as db

pwd_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")
security = HTTPBearer()


def hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)


def verificar_senha(senha: str, hash: str) -> bool:
    try:
        return pwd_context.verify(senha, hash)
    except (ValueError, AttributeError):
        return False


def criar_token(usuario_id: str, email: str, tipo_usuario: str) -> str:
    settings = get_settings()
    payload = {
        "sub": usuario_id,
        "email": email,
        "tipo_usuario": tipo_usuario,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiration_minutes),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decodificar_token(token: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invÃ¡lido ou expirado",
        )


async def get_usuario_atual(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """DependÃªncia FastAPI para obter o usuÃ¡rio autenticado (qualquer role)."""
    payload = decodificar_token(credentials.credentials)
    usuario = db.buscar_usuario_por_id(payload["sub"])
    if not usuario or not usuario.get("ativo"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="UsuÃ¡rio nÃ£o encontrado ou inativo",
        )
    return usuario


async def get_adm_atual(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """DependÃªncia FastAPI para obter o usuÃ¡rio autenticado com role=adm."""
    payload = decodificar_token(credentials.credentials)
    usuario = db.buscar_usuario_por_id(payload["sub"])
    if not usuario or not usuario.get("ativo"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="UsuÃ¡rio nÃ£o encontrado ou inativo",
        )
    if usuario.get("tipo_usuario") not in ("adm", "master"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores e masters",
        )
    return usuario


async def get_gestor_atual(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Dependência FastAPI para obter usuário operacional (gestor/usuario)."""
    payload = decodificar_token(credentials.credentials)
    usuario = db.buscar_usuario_por_id(payload["sub"])
    if not usuario or not usuario.get("ativo"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="UsuÃ¡rio nÃ£o encontrado ou inativo",
        )
    if usuario.get("tipo_usuario") not in ("gestor", "usuario"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a usuários operacionais",
        )
    return usuario


async def get_cliente_atual(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """DependÃªncia FastAPI para obter o usuÃ¡rio autenticado com role=cliente."""
    payload = decodificar_token(credentials.credentials)
    usuario = db.buscar_usuario_por_id(payload["sub"])
    if not usuario or not usuario.get("ativo"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="UsuÃ¡rio nÃ£o encontrado ou inativo",
        )
    if usuario.get("tipo_usuario") != "cliente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a clientes",
        )
    return usuario

