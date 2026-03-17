"""Schemas Pydantic para validaÃ§Ã£o de dados."""

from pydantic import BaseModel
from typing import Optional


# ============================================================
# AUTH
# ============================================================

class LoginRequest(BaseModel):
    email: str
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: dict


class AtualizarPerfilRequest(BaseModel):
    nome: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    avatar_url: Optional[str] = None
    senha_atual: Optional[str] = None
    nova_senha: Optional[str] = None


# ============================================================
# SETUP / ADM
# ============================================================

class CriarAdmRequest(BaseModel):
    email: str
    nome: str
    senha: str
    cpf_cnpj: Optional[str] = None   # CNPJ da empresa (14 dÃ­gitos) ou CPF (11 dÃ­gitos), sem formataÃ§Ã£o


class RegistroMasterRequest(BaseModel):
    email: str
    nome: str
    senha: str
    cpf_cnpj: Optional[str] = None
    empresa_razao_social: str
    empresa_cnpj: str
    empresa_nome_fantasia: Optional[str] = None


class CriarGestorRequest(BaseModel):
    email: str
    nome: str
    senha: str
    empresa_id: Optional[str] = None
    cpf_cnpj: Optional[str] = None   # CPF (11 dÃ­gitos) ou CNPJ (14 dÃ­gitos), sem formataÃ§Ã£o


class AtualizarGestorRequest(BaseModel):
    email: Optional[str] = None
    nome: Optional[str] = None
    senha: Optional[str] = None
    empresa_id: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    ativo: Optional[bool] = None


class GestorResponse(BaseModel):
    id: str
    email: str
    nome: str
    ativo: bool
    criado_em: str


class CriarEmpresaRequest(BaseModel):
    razao_social: str
    cnpj: str
    nome_fantasia: Optional[str] = None


class EmpresaResponse(BaseModel):
    id: str
    razao_social: str
    cnpj: str
    nome_fantasia: Optional[str] = None
    ativo: bool
    criado_em: str


# ============================================================
# GESTOR â†’ CLIENTES
# ============================================================

class VinculoClienteRequest(BaseModel):
    tipo_vinculo: str  # socio | responsavel_solidario
    nome: str
    cpf_cnpj: str
    email: Optional[str] = None


class CriarClienteRequest(BaseModel):
    email: str
    nome: str
    cpf_cnpj: str
    vinculos: list[VinculoClienteRequest] = []


class AtualizarClienteRequest(BaseModel):
    email: Optional[str] = None
    nome: Optional[str] = None
    cpf_cnpj: Optional[str] = None


class ClienteResponse(BaseModel):
    id: str
    email: str
    nome: str
    ativo: bool
    criado_em: str


class SocioRequest(BaseModel):
    cpf_cnpj: str
    nome: Optional[str] = None
    email: Optional[str] = None
    tipo_vinculo: Optional[str] = "socio"


class AtualizarSocioRequest(BaseModel):
    cpf_cnpj: Optional[str] = None
    nome: Optional[str] = None
    email: Optional[str] = None
    tipo_vinculo: Optional[str] = None


class SocioResponse(BaseModel):
    id: str
    cliente_id: str
    cpf: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    email: Optional[str] = None
    tipo_vinculo: Optional[str] = None
    nome: Optional[str]
    criado_em: str


# ============================================================
# AUTH POR CERTIFICADO DIGITAL
# ============================================================

class CertificadoDesafioResponse(BaseModel):
    nonce_id: str
    desafio_b64: str    # 32 bytes aleatÃ³rios em base64 para assinar


class CertificadoVerificarRequest(BaseModel):
    nonce_id: str
    assinatura_b64: str  # assinatura RAW (SHA256withRSA) em base64
    cert_pem: str        # certificado pÃºblico em PEM


# ============================================================
# DOCUMENTOS
# ============================================================

class DocumentoResponse(BaseModel):
    id: str
    titulo: str
    nome_arquivo: str
    tamanho_bytes: int
    hash_sha256: str
    status: str
    criado_em: str


class SolicitacaoRequest(BaseModel):
    signatario_email: str
    signatario_nome: Optional[str] = None
    mensagem: Optional[str] = None
    assinatura_obrigatoria_tipo: str
    assinatura_obrigatoria_cpf_cnpj: str
    assinatura_obrigatoria_nome: Optional[str] = None
    assinatura_pagina: Optional[int] = 1
    assinatura_x: Optional[float] = 0.06
    assinatura_y: Optional[float] = 0.06
    assinatura_largura: Optional[float] = 0.44
    assinatura_altura: Optional[float] = 0.12


class SolicitacaoResponse(BaseModel):
    id: str
    token_acesso: str
    signatario_email: str
    status: str
    expira_em: str
    link_assinatura: str


# ============================================================
# ASSINATURA
# ============================================================

class PrepararAssinaturaResponse(BaseModel):
    hash_bytes_b64: str
    hash_hex: str
    algoritmo: str
    documento_id: str
    solicitacao_id: str


class SubmeterAssinaturaRequest(BaseModel):
    token_acesso: str
    assinatura_cms_b64: str
    cert_pem: str
    cert_tipo: Optional[str] = "A1"


class ValidarCertificadoSolicitacaoRequest(BaseModel):
    cpf_cnpj: str


class AssinaturaResponse(BaseModel):
    id: str
    documento_id: str
    cert_subject_cn: str
    cert_subject_cpf: Optional[str]
    cert_issuer_cn: str
    assinado_em: str
    sucesso: bool
    mensagem: str



