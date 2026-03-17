"""
Assinatura Digital ICP-Brasil - Backend FastAPI

PapÃ©is de usuÃ¡rio:
  - adm:    cria gestores, acesso total
  - master: conta principal da empresa (SaaS), cadastra empresa e gestores
  - gestor: cria clientes, faz upload e envia contratos
  - cliente: visualiza e assina contratos
"""

import uuid
import asyncio
import base64
import os
import time
from datetime import datetime, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, ec
from cryptography.exceptions import InvalidSignature

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import io

from config import get_settings
from auth import (
    hash_senha, verificar_senha, criar_token,
    get_usuario_atual, get_adm_atual, get_gestor_atual, get_cliente_atual,
)
import database as db
from signature_service import (
    calcular_hash_pdf,
    preparar_documento_pades_externo,
    aplicar_cms_em_pdf_preparado,
    extrair_info_certificado,
)
from schemas import (
    LoginRequest, TokenResponse, AtualizarPerfilRequest,
    CriarAdmRequest, RegistroMasterRequest, CriarEmpresaRequest, CriarGestorRequest, AtualizarGestorRequest, CriarClienteRequest, AtualizarClienteRequest,
    SolicitacaoRequest,
    PrepararAssinaturaResponse, SubmeterAssinaturaRequest, AssinaturaResponse, ValidarCertificadoSolicitacaoRequest,
    CertificadoDesafioResponse, CertificadoVerificarRequest,
    SocioRequest, AtualizarSocioRequest, SocioResponse,
)

settings = get_settings()
_assinaturas_pendentes: dict[str, dict] = {}
# Rastreia qual token está no meio do fluxo preparar→submeter por documento.
# Impede que dois signatários preparem simultaneamente o mesmo PDF,
# o que causaria corrida e perda de assinatura anterior.
_documentos_em_preparacao: dict[str, str] = {}  # documento_id → token

# Desafios de autenticaÃ§Ã£o por certificado: {nonce_id: {"desafio": bytes, "expira_em": float}}
_desafios_pendentes: dict[str, dict] = {}

app = FastAPI(
    title=settings.app_name,
    description="API de assinatura digital com certificados ICP-Brasil no padrÃ£o PAdES",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HELPERS
# ============================================================

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _usuario_response(usuario: dict) -> dict:
    return {
        "id": usuario["id"],
        "email": usuario["email"],
        "nome": usuario["nome"],
        "tipo_usuario": usuario["tipo_usuario"],
        "cpf_cnpj": usuario.get("cpf_cnpj"),
        "empresa_id": usuario.get("empresa_id"),
        "avatar_url": usuario.get("avatar_url"),
        "criado_em": usuario.get("criado_em"),
    }


def _clamp_float(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, float(valor)))


def _validar_certificado_signatario(solicitacao: dict, info_cert: dict):
    """
    Garante que o certificado usado para assinar pertence ao cliente da solicitação
    (CPF/CNPJ do cliente ou CPF de sócio vinculado).
    """
    cert_doc = "".join(c for c in str(info_cert.get("cpf_cnpj") or info_cert.get("cpf") or info_cert.get("cnpj") or "") if c.isdigit())

    if not cert_doc:
        raise HTTPException(
            status_code=403,
            detail="Não foi possível identificar CPF/CNPJ no certificado digital.",
        )

    docs_permitidos, _, _ = _obter_docs_permitidos_solicitacao(solicitacao)
    assinatura_obrigatoria = "".join(
        c for c in str(solicitacao.get("assinatura_obrigatoria_cpf_cnpj") or "")
        if c.isdigit()
    )

    if assinatura_obrigatoria and cert_doc != assinatura_obrigatoria:
        raise HTTPException(
            status_code=403,
            detail="Este documento exige assinatura de um signatário específico.",
        )

    if cert_doc not in docs_permitidos:
        raise HTTPException(
            status_code=403,
            detail="Certificado não autorizado para este cliente (CPF/CNPJ divergente).",
        )


def _obter_docs_permitidos_solicitacao(solicitacao: dict) -> tuple[set[str], dict, dict]:
    """Retorna documentos permitidos (cliente + sócios) para uma solicitação."""
    doc = solicitacao.get("documentos", {}) or {}
    remetente_id = doc.get("remetente_id")
    signatario_email = (solicitacao.get("signatario_email") or "").strip().lower()

    remetente = db.buscar_usuario_por_id(remetente_id) if remetente_id else None
    cliente = db.buscar_usuario_por_email(signatario_email) if signatario_email else None
    if not remetente or not cliente:
        raise HTTPException(
            status_code=403,
            detail="Signatário não vinculado. O cliente precisa estar cadastrado no sistema.",
        )
    if remetente.get("empresa_id") != cliente.get("empresa_id"):
        raise HTTPException(
            status_code=403,
            detail="Cliente não pertence à mesma empresa do solicitante.",
        )

    docs_permitidos = set()
    cliente_doc = "".join(c for c in str(cliente.get("cpf_cnpj") or "") if c.isdigit())
    if cliente_doc:
        docs_permitidos.add(cliente_doc)
    for vinculo in db.listar_docs_vinculados_cliente(cliente.get("id")):
        digits = "".join(c for c in str(vinculo.get("cpf_cnpj") or "") if c.isdigit())
        if digits:
            docs_permitidos.add(digits)
    return docs_permitidos, cliente, remetente


# ============================================================
# SETUP â€” CRIAR PRIMEIRO ADMIN
# ============================================================

@app.post("/api/setup/primeiro-admin", response_model=TokenResponse)
async def criar_primeiro_admin(dados: CriarAdmRequest):
    """
    Cria o primeiro administrador do sistema.
    SÃ³ funciona enquanto nÃ£o existir nenhum adm no banco.
    """
    if db.contar_adms() > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="JÃ¡ existe um administrador cadastrado.",
        )

    existente = db.buscar_usuario_por_email(dados.email)
    if existente:
        raise HTTPException(status_code=400, detail="Email jÃ¡ cadastrado")

    senha_aleatoria = uuid.uuid4().hex
    senha_h = hash_senha(senha_aleatoria)
    cpf_cnpj = ''.join(filter(str.isdigit, dados.cpf_cnpj)) if dados.cpf_cnpj else None
    usuario = db.criar_usuario(dados.email, dados.nome, senha_h, tipo_usuario="adm", cpf_cnpj=cpf_cnpj)
    if not usuario:
        raise HTTPException(status_code=500, detail="Erro ao criar administrador")

    token = criar_token(usuario["id"], usuario["email"], usuario["tipo_usuario"])
    return TokenResponse(access_token=token, usuario=_usuario_response(usuario))


# ============================================================
# AUTH
# ============================================================

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(dados: LoginRequest):
    """Autenticar usuÃ¡rio (adm, gestor ou cliente)."""
    usuario = db.buscar_usuario_por_email(dados.email)
    if not usuario or not verificar_senha(dados.senha, usuario["senha_hash"]):
        raise HTTPException(status_code=401, detail="Credenciais invÃ¡lidas")
    if not usuario.get("ativo"):
        raise HTTPException(status_code=403, detail="Conta desativada")

    token = criar_token(usuario["id"], usuario["email"], usuario["tipo_usuario"])
    return TokenResponse(access_token=token, usuario=_usuario_response(usuario))


@app.post("/api/auth/registro-master", response_model=TokenResponse)
async def registrar_master(dados: RegistroMasterRequest):
    """Cadastro SaaS (compat): cria usuário e empresa vinculada em uma única operação."""
    existente = db.buscar_usuario_por_email(dados.email)
    if existente:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    cnpj_digits = "".join(c for c in dados.empresa_cnpj if c.isdigit())
    if len(cnpj_digits) != 14:
        raise HTTPException(status_code=400, detail="CNPJ da empresa deve ter 14 dígitos")
    empresa_existente = db.buscar_empresa_por_cnpj(cnpj_digits)
    if empresa_existente:
        raise HTTPException(status_code=400, detail="Empresa com este CNPJ já cadastrada")

    empresa = db.criar_empresa(
        razao_social=dados.empresa_razao_social,
        cnpj=cnpj_digits,
        nome_fantasia=dados.empresa_nome_fantasia,
    )
    if not empresa:
        raise HTTPException(status_code=500, detail="Erro ao criar empresa")

    senha_aleatoria = uuid.uuid4().hex
    senha_h = hash_senha(senha_aleatoria)
    cpf_cnpj = "".join(c for c in (dados.cpf_cnpj or "") if c.isdigit()) or None
    usuario = db.criar_usuario(
        dados.email,
        dados.nome,
        senha_h,
        tipo_usuario="usuario",
        empresa_id=empresa["id"],
        cpf_cnpj=cpf_cnpj,
    )
    if not usuario:
        raise HTTPException(status_code=500, detail="Erro ao criar usuário")

    token = criar_token(usuario["id"], usuario["email"], usuario["tipo_usuario"])
    return TokenResponse(access_token=token, usuario=_usuario_response(usuario))


@app.get("/api/auth/me")
async def perfil(usuario: dict = Depends(get_usuario_atual)):
    """Retorna dados do usuÃ¡rio autenticado."""
    return _usuario_response(usuario)


@app.put("/api/auth/me")
async def atualizar_perfil(dados: AtualizarPerfilRequest, usuario: dict = Depends(get_usuario_atual)):
    """Atualiza perfil do usuário autenticado (nome, foto, cpf/cnpj e senha)."""
    payload = dados.model_dump(exclude_unset=True, exclude_none=True)
    update_data: dict = {}

    if "nome" in payload:
        update_data["nome"] = payload["nome"].strip()

    if "cpf_cnpj" in payload:
        update_data["cpf_cnpj"] = "".join(c for c in payload["cpf_cnpj"] if c.isdigit())

    if "avatar_url" in payload:
        avatar = payload["avatar_url"].strip()
        if avatar and len(avatar) > 2_000_000:
            raise HTTPException(status_code=400, detail="Imagem muito grande")
        update_data["avatar_url"] = avatar or None

    if "nova_senha" in payload:
        senha_atual = payload.get("senha_atual")
        if not senha_atual:
            raise HTTPException(status_code=400, detail="Informe a senha atual para alterar a senha")
        if not verificar_senha(senha_atual, usuario["senha_hash"]):
            raise HTTPException(status_code=400, detail="Senha atual incorreta")
        if len(payload["nova_senha"]) < 6:
            raise HTTPException(status_code=400, detail="Nova senha deve ter ao menos 6 caracteres")
        update_data["senha_hash"] = hash_senha(payload["nova_senha"])

    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhum dado para atualizar")

    atualizado = db.atualizar_usuario(usuario["id"], update_data)
    if not atualizado:
        raise HTTPException(status_code=500, detail="Erro ao atualizar perfil")
    return _usuario_response(atualizado)


# ============================================================
# AUTH POR CERTIFICADO DIGITAL (Challenge-Response)
# ============================================================

@app.post("/api/auth/certificado/desafio", response_model=CertificadoDesafioResponse)
async def gerar_desafio_certificado():
    """
    Gera um desafio (nonce) para autenticaÃ§Ã£o por certificado digital.
    O frontend deve assinar o desafio com a chave privada via app local.
    O desafio expira em 60 segundos.
    """
    # Limpar desafios expirados
    agora = time.time()
    expirados = [k for k, v in _desafios_pendentes.items() if v["expira_em"] < agora]
    for k in expirados:
        _desafios_pendentes.pop(k, None)

    nonce_id = str(uuid.uuid4())
    desafio_bytes = os.urandom(32)  # 256 bits aleatÃ³rios
    _desafios_pendentes[nonce_id] = {
        "desafio": desafio_bytes,
        "expira_em": agora + 60,  # 60 segundos
    }
    return CertificadoDesafioResponse(
        nonce_id=nonce_id,
        desafio_b64=base64.b64encode(desafio_bytes).decode("ascii"),
    )


@app.post("/api/auth/certificado/verificar", response_model=TokenResponse)
async def verificar_certificado_auth(dados: CertificadoVerificarRequest):
    """
    Verifica a assinatura do desafio e autentica o usuÃ¡rio pelo CPF/CNPJ do certificado.
    """
    # 1. Verificar se o desafio existe e nÃ£o expirou
    ctx = _desafios_pendentes.pop(dados.nonce_id, None)
    if not ctx:
        raise HTTPException(status_code=400, detail="Desafio invÃ¡lido ou expirado")
    if time.time() > ctx["expira_em"]:
        raise HTTPException(status_code=400, detail="Desafio expirado. Tente novamente.")

    desafio_bytes = ctx["desafio"]

    # 2. Carregar certificado e verificar a assinatura
    try:
        cert = x509.load_pem_x509_certificate(dados.cert_pem.encode())
        pub_key = cert.public_key()
        sig_bytes = base64.b64decode(dados.assinatura_b64)

        try:
            if hasattr(pub_key, "verify"):
                from cryptography.hazmat.primitives.asymmetric import rsa as _rsa
                if isinstance(pub_key, _rsa.RSAPublicKey):
                    pub_key.verify(sig_bytes, desafio_bytes, padding.PKCS1v15(), hashes.SHA256())
                else:
                    pub_key.verify(sig_bytes, desafio_bytes, ec.ECDSA(hashes.SHA256()))
        except InvalidSignature:
            raise HTTPException(status_code=401, detail="Assinatura invÃ¡lida. Certificado nÃ£o reconhecido.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Erro ao processar certificado")

    # 3. Extrair CPF ou CNPJ do certificado
    cpf_cnpj = _extrair_cpf_cnpj_do_cert(cert)
    if not cpf_cnpj:
        raise HTTPException(
            status_code=422,
            detail="CPF/CNPJ nÃ£o encontrado no certificado. Verifique se Ã© um certificado ICP-Brasil vÃ¡lido.",
        )

    # 4. Buscar usuÃ¡rio pelo CPF/CNPJ
    # Tentativa 1: usuÃ¡rio com esse CNPJ/CPF cadastrado diretamente
    usuario = db.buscar_usuario_por_cpf_cnpj(cpf_cnpj)
    # Tentativa 2: CPF de sÃ³cio vinculado a um cliente empresa
    if not usuario:
        usuario = db.buscar_cliente_por_cpf_socio(cpf_cnpj)
    if not usuario:
        raise HTTPException(
            status_code=404,
            detail=f"UsuÃ¡rio com CPF/CNPJ {_formatar_cpf_cnpj(cpf_cnpj)} nÃ£o cadastrado no sistema. "
                   "Solicite ao administrador ou gestor que cadastre seu acesso.",
        )

    token = criar_token(usuario["id"], usuario["email"], usuario["tipo_usuario"])
    return TokenResponse(access_token=token, usuario=_usuario_response(usuario))


def _extrair_cpf_cnpj_do_cert(cert) -> str:
    """Extrai CPF (PF) ou CNPJ (PJ) de um certificado ICP-Brasil.

    ICP-Brasil armazena CPF/CNPJ como OtherName dentro do SubjectAltName
    (RFC 5280), nÃ£o como extensÃµes de nÃ­vel superior.
    OIDs: CNPJ = 2.16.76.1.3.3 | CPF = 2.16.76.1.3.1
    """
    from cryptography.x509 import SubjectAlternativeName, OtherName
    from cryptography.x509.oid import ExtensionOID

    def _parse_asn1_string(raw: bytes) -> str:
        """Extrai conteÃºdo de uma string ASN.1 (IA5String/UTF8String/etc.)."""
        if not raw:
            return ""
        # tag(1) + length(1) + value  â€” suporta length < 128
        if len(raw) >= 2:
            length = raw[1]
            if length < 0x80 and len(raw) >= 2 + length:
                return raw[2: 2 + length].decode("latin-1", errors="ignore")
        return raw.decode("latin-1", errors="ignore")

    # â”€â”€ MÃ©todo correto: OtherName dentro do SubjectAltName â”€â”€
    try:
        san = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
        for entry in san.value:
            if not isinstance(entry, OtherName):
                continue
            oid_str = entry.type_id.dotted_string
            # CNPJ (PJ)
            if oid_str == "2.16.76.1.3.3":
                valor = _parse_asn1_string(entry.value)
                digits = "".join(c for c in valor if c.isdigit())
                if digits:
                    return digits[:14]
            # CPF (PF)
            elif oid_str == "2.16.76.1.3.1":
                valor = _parse_asn1_string(entry.value)
                digits = "".join(c for c in valor if c.isdigit())
                if digits:
                    return digits[:11]
    except Exception:
        pass

    # â”€â”€ Fallback: CN no formato "NOME:CPF" â”€â”€
    try:
        from cryptography.x509.oid import NameOID
        cn_attrs = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        if cn_attrs:
            cn = cn_attrs[0].value
            if ":" in cn:
                for part in cn.split(":"):
                    digits = "".join(c for c in part if c.isdigit())
                    if len(digits) in (11, 14):
                        return digits
    except Exception:
        pass

    return ""


def _formatar_cpf_cnpj(valor: str) -> str:
    if len(valor) == 11:
        return f"{valor[:3]}.{valor[3:6]}.{valor[6:9]}-{valor[9:]}"
    if len(valor) == 14:
        return f"{valor[:2]}.{valor[2:5]}.{valor[5:8]}/{valor[8:12]}-{valor[12:]}"
    return valor


# ============================================================
# ADM â€” GESTORES
# ============================================================


@app.post("/api/adm/empresas")
async def criar_empresa(dados: CriarEmpresaRequest, adm: dict = Depends(get_adm_atual)):
    """Cria empresa (adm cria qualquer; master cria apenas a própria)."""
    cnpj_digits = "".join(c for c in dados.cnpj if c.isdigit())
    if len(cnpj_digits) != 14:
        raise HTTPException(status_code=400, detail="CNPJ deve ter exatamente 14 dígitos")

    existente = db.buscar_empresa_por_cnpj(cnpj_digits)
    if existente:
        raise HTTPException(status_code=400, detail="Empresa com este CNPJ já cadastrada")

    if adm.get("tipo_usuario") == "master" and adm.get("empresa_id"):
        raise HTTPException(status_code=400, detail="Master já possui empresa vinculada")

    empresa = db.criar_empresa(
        razao_social=dados.razao_social,
        cnpj=cnpj_digits,
        nome_fantasia=dados.nome_fantasia,
    )
    if not empresa:
        raise HTTPException(status_code=500, detail="Erro ao criar empresa")

    db.registrar_auditoria(
        tipo_evento="EMPRESA_CRIADA",
        descricao=f"Empresa '{dados.razao_social}' criada por {adm.get('tipo_usuario')}",
        usuario_id=adm["id"],
    )

    if adm.get("tipo_usuario") == "master":
        db.atualizar_usuario(adm["id"], {"empresa_id": empresa["id"]})

    return empresa


@app.get("/api/adm/empresas")
async def listar_empresas(adm: dict = Depends(get_adm_atual)):
    """Lista empresas (adm vê todas; master vê apenas a sua)."""
    if adm.get("tipo_usuario") == "master":
        if not adm.get("empresa_id"):
            return []
        empresa = db.buscar_empresa_por_id(adm["empresa_id"])
        return [empresa] if empresa else []
    return db.listar_empresas()
@app.post("/api/adm/gestores")
async def criar_gestor(dados: CriarGestorRequest, adm: dict = Depends(get_adm_atual)):
    """Cria gestor (adm por empresa escolhida; master na própria empresa)."""
    existente = db.buscar_usuario_por_email(dados.email)
    if existente:
        raise HTTPException(status_code=400, detail="Email jÃ¡ cadastrado")

    empresa_id = dados.empresa_id
    if adm.get("tipo_usuario") == "master":
        empresa_id = adm.get("empresa_id")
        if not empresa_id:
            raise HTTPException(status_code=400, detail="Cadastre sua empresa antes de criar gestores")
    if not empresa_id:
        raise HTTPException(status_code=400, detail="empresa_id é obrigatório")

    empresa = db.buscar_empresa_por_id(empresa_id)
    if not empresa or not empresa.get("ativo", True):
        raise HTTPException(status_code=400, detail="Empresa inválida ou inativa")

    senha_aleatoria = uuid.uuid4().hex
    senha_h = hash_senha(senha_aleatoria)
    gestor = db.criar_usuario(dados.email, dados.nome, senha_h, tipo_usuario="gestor",
                              empresa_id=empresa_id,
                              cpf_cnpj=dados.cpf_cnpj)
    if not gestor:
        raise HTTPException(status_code=500, detail="Erro ao criar gestor")

    db.registrar_auditoria(
        tipo_evento="GESTOR_CRIADO",
        descricao=f"Gestor '{dados.nome}' ({dados.email}) criado pelo adm",
        usuario_id=adm["id"],
    )
    return {
        "id": gestor["id"],
        "email": gestor["email"],
        "nome": gestor["nome"],
        "ativo": gestor["ativo"],
        "empresa_id": gestor.get("empresa_id"),
    }


@app.get("/api/adm/gestores")
async def listar_gestores(adm: dict = Depends(get_adm_atual)):
    """Lista gestores (adm vê todos; master vê apenas os da sua empresa)."""
    if adm.get("tipo_usuario") == "master":
        if not adm.get("empresa_id"):
            return []
        return db.listar_gestores_por_empresa(adm["empresa_id"])
    return db.listar_gestores()


@app.put("/api/adm/gestores/{gestor_id}")
async def editar_gestor(gestor_id: str, dados: AtualizarGestorRequest, adm: dict = Depends(get_adm_atual)):
    """Edita gestor e permite re-vincular a empresa."""
    gestor = db.buscar_usuario_por_id(gestor_id)
    if not gestor or gestor.get("tipo_usuario") != "gestor":
        raise HTTPException(status_code=404, detail="Gestor não encontrado")
    if adm.get("tipo_usuario") == "master" and gestor.get("empresa_id") != adm.get("empresa_id"):
        raise HTTPException(status_code=403, detail="Acesso negado")

    payload = dados.model_dump(exclude_unset=True, exclude_none=True)
    update_data: dict = {}

    if "email" in payload:
        existente = db.buscar_usuario_por_email(payload["email"])
        if existente and existente.get("id") != gestor_id:
            raise HTTPException(status_code=400, detail="Email já cadastrado")
        update_data["email"] = payload["email"]

    if "nome" in payload:
        update_data["nome"] = payload["nome"]

    if "cpf_cnpj" in payload:
        update_data["cpf_cnpj"] = "".join(c for c in payload["cpf_cnpj"] if c.isdigit())

    if "senha" in payload:
        if len(payload["senha"]) < 6:
            raise HTTPException(status_code=400, detail="Senha deve ter ao menos 6 caracteres")
        update_data["senha_hash"] = hash_senha(payload["senha"])

    if "ativo" in payload:
        update_data["ativo"] = bool(payload["ativo"])

    if "empresa_id" in payload:
        if adm.get("tipo_usuario") == "master":
            raise HTTPException(status_code=403, detail="Master não pode trocar empresa de gestor")
        empresa = db.buscar_empresa_por_id(payload["empresa_id"])
        if not empresa or not empresa.get("ativo", True):
            raise HTTPException(status_code=400, detail="Empresa inválida ou inativa")
        update_data["empresa_id"] = payload["empresa_id"]

    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhum dado para atualizar")

    atualizado = db.atualizar_usuario(gestor_id, update_data)
    if not atualizado:
        raise HTTPException(status_code=500, detail="Erro ao atualizar gestor")

    db.registrar_auditoria(
        tipo_evento="GESTOR_ATUALIZADO",
        descricao=f"Gestor '{atualizado['nome']}' atualizado",
        usuario_id=adm["id"],
        dados_extras={"gestor_id": gestor_id},
    )

    return {
        "id": atualizado["id"],
        "email": atualizado["email"],
        "nome": atualizado["nome"],
        "ativo": atualizado["ativo"],
        "empresa_id": atualizado.get("empresa_id"),
    }


@app.delete("/api/adm/gestores/{gestor_id}")
async def desativar_gestor(gestor_id: str, adm: dict = Depends(get_adm_atual)):
    """Desativa um gestor."""
    gestor = db.buscar_usuario_por_id(gestor_id)
    if not gestor or gestor.get("tipo_usuario") != "gestor":
        raise HTTPException(status_code=404, detail="Gestor nÃ£o encontrado")
    if adm.get("tipo_usuario") == "master" and gestor.get("empresa_id") != adm.get("empresa_id"):
        raise HTTPException(status_code=403, detail="Acesso negado")

    db.desativar_usuario(gestor_id)
    db.registrar_auditoria(
        tipo_evento="GESTOR_DESATIVADO",
        descricao=f"Gestor '{gestor['nome']}' desativado",
        usuario_id=adm["id"],
    )
    return {"mensagem": "Gestor desativado com sucesso"}


# ============================================================
# GESTOR â€” CLIENTES
# ============================================================

@app.post("/api/gestor/clientes")
async def criar_cliente(dados: CriarClienteRequest, gestor: dict = Depends(get_gestor_atual)):
    """Gestor cria uma conta de cliente."""
    if not gestor.get("empresa_id"):
        raise HTTPException(status_code=400, detail="Usuário sem empresa vinculada")
    existente = db.buscar_usuario_por_email(dados.email)
    if existente:
        raise HTTPException(status_code=400, detail="Email jÃ¡ cadastrado")

    cpf_cnpj_cliente = "".join(c for c in str(dados.cpf_cnpj or "") if c.isdigit())
    if len(cpf_cnpj_cliente) not in (11, 14):
        raise HTTPException(status_code=400, detail="CPF/CNPJ do cliente deve ter 11 ou 14 dígitos")

    vinculos_normalizados = []
    for vinculo in (dados.vinculos or []):
        doc = "".join(c for c in str(vinculo.cpf_cnpj or "") if c.isdigit())
        if len(doc) not in (11, 14):
            raise HTTPException(status_code=400, detail="CPF/CNPJ de vinculo deve ter 11 ou 14 dígitos")
        tipo = (vinculo.tipo_vinculo or "").strip().lower()
        if tipo not in ("socio", "responsavel_solidario"):
            raise HTTPException(status_code=400, detail="tipo_vinculo inválido")
        existente_vinculo = db.buscar_cliente_por_cpf_socio(doc)
        if existente_vinculo:
            raise HTTPException(status_code=400, detail=f"CPF/CNPJ {doc} já vinculado a outro cliente")
        vinculos_normalizados.append({
            "doc": doc,
            "tipo": tipo,
            "nome": vinculo.nome,
            "email": vinculo.email,
        })

    senha_aleatoria = uuid.uuid4().hex
    senha_h = hash_senha(senha_aleatoria)
    cliente = db.criar_usuario(
        dados.email, dados.nome, senha_h,
        tipo_usuario="usuario",
        empresa_id=gestor.get("empresa_id"),
        cpf_cnpj=cpf_cnpj_cliente,
    )
    if not cliente:
        raise HTTPException(status_code=500, detail="Erro ao criar cliente")

    for vinculo in vinculos_normalizados:
        db.criar_socio(
            cliente_id=cliente["id"],
            cpf_cnpj=vinculo["doc"],
            nome=vinculo["nome"],
            email=vinculo["email"],
            tipo_vinculo=vinculo["tipo"],
        )

    db.registrar_auditoria(
        tipo_evento="CLIENTE_CRIADO",
        descricao=f"Cliente '{dados.nome}' ({dados.email}) criado pelo gestor",
        usuario_id=gestor["id"],
    )
    return {"id": cliente["id"], "email": cliente["email"], "nome": cliente["nome"], "ativo": cliente["ativo"]}


@app.get("/api/gestor/clientes")
async def listar_clientes(gestor: dict = Depends(get_gestor_atual)):
    """Lista clientes criados pelo gestor autenticado."""
    if not gestor.get("empresa_id"):
        return []
    return db.listar_clientes_gestor(gestor["empresa_id"], excluir_usuario_id=gestor["id"])


@app.delete("/api/gestor/clientes/{cliente_id}")
async def desativar_cliente(cliente_id: str, gestor: dict = Depends(get_gestor_atual)):
    """Desativa um cliente do gestor."""
    cliente = db.buscar_usuario_por_id(cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente nÃ£o encontrado")
    if not gestor.get("empresa_id") or cliente.get("empresa_id") != gestor.get("empresa_id"):
        raise HTTPException(status_code=403, detail="Acesso negado")
    if cliente.get("id") == gestor.get("id"):
        raise HTTPException(status_code=400, detail="Você não pode desativar o próprio usuário")

    db.desativar_usuario(cliente_id)
    db.registrar_auditoria(
        tipo_evento="CLIENTE_DESATIVADO",
        descricao=f"Cliente '{cliente['nome']}' desativado",
        usuario_id=gestor["id"],
    )
    return {"mensagem": "Cliente desativado com sucesso"}


@app.put("/api/gestor/clientes/{cliente_id}")
async def editar_cliente(cliente_id: str, dados: AtualizarClienteRequest, gestor: dict = Depends(get_gestor_atual)):
    """Edita dados principais do cliente (nome, email, CPF/CNPJ)."""
    cliente = db.buscar_usuario_por_id(cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    if not gestor.get("empresa_id") or cliente.get("empresa_id") != gestor.get("empresa_id"):
        raise HTTPException(status_code=403, detail="Acesso negado")
    if cliente.get("id") == gestor.get("id"):
        raise HTTPException(status_code=400, detail="Você não pode editar o próprio usuário aqui")

    payload = dados.model_dump(exclude_unset=True, exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="Nenhum dado para atualizar")

    update_data = {}
    if "nome" in payload:
        update_data["nome"] = payload["nome"].strip()
    if "email" in payload:
        email = payload["email"].strip().lower()
        existente = db.buscar_usuario_por_email(email)
        if existente and existente.get("id") != cliente_id:
            raise HTTPException(status_code=400, detail="Email já cadastrado")
        update_data["email"] = email
    if "cpf_cnpj" in payload:
        doc = "".join(c for c in str(payload["cpf_cnpj"]) if c.isdigit())
        if len(doc) not in (11, 14):
            raise HTTPException(status_code=400, detail="CPF/CNPJ deve ter 11 ou 14 dígitos")
        update_data["cpf_cnpj"] = doc

    atualizado = db.atualizar_usuario(cliente_id, update_data)
    if not atualizado:
        raise HTTPException(status_code=500, detail="Erro ao atualizar cliente")

    return {"id": atualizado["id"], "email": atualizado["email"], "nome": atualizado["nome"], "ativo": atualizado["ativo"], "cpf_cnpj": atualizado.get("cpf_cnpj")}


# ============================================================
# SÃ“CIOS (gestor gerencia CPFs dos sÃ³cios dos clientes)
# ============================================================

def _verificar_cliente_do_gestor(cliente_id: str, gestor_id: str):
    """Garante que o cliente pertence ao gestor. LanÃ§a 403/404 se nÃ£o."""
    gestor = db.buscar_usuario_por_id(gestor_id)
    if not gestor:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    cliente = db.buscar_usuario_por_id(cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente nÃ£o encontrado")
    if cliente.get("empresa_id") != gestor.get("empresa_id"):
        raise HTTPException(status_code=403, detail="Acesso negado")
    return cliente


@app.get("/api/gestor/clientes/{cliente_id}/socios", response_model=list[SocioResponse])
async def listar_socios(cliente_id: str, gestor: dict = Depends(get_gestor_atual)):
    """Lista os sÃ³cios (CPFs) vinculados a um cliente."""
    if not db.tabela_socios_disponivel():
        return []
    _verificar_cliente_do_gestor(cliente_id, gestor["id"])
    return db.listar_socios_cliente(cliente_id)


@app.post("/api/gestor/clientes/{cliente_id}/socios", response_model=SocioResponse)
async def adicionar_socio(cliente_id: str, dados: SocioRequest,
                          gestor: dict = Depends(get_gestor_atual)):
    """Vincula um CPF de sÃ³cio a um cliente empresa."""
    if not db.tabela_socios_disponivel():
        raise HTTPException(status_code=400, detail="Tabela de sócios indisponível. Execute a migration de sócios.")
    cliente = _verificar_cliente_do_gestor(cliente_id, gestor["id"])
    doc = "".join(c for c in str(dados.cpf_cnpj or "") if c.isdigit())
    if len(doc) not in (11, 14):
        raise HTTPException(status_code=400, detail="CPF/CNPJ deve ter 11 ou 14 dígitos")
    tipo_vinculo = (dados.tipo_vinculo or "socio").strip().lower()
    if tipo_vinculo not in ("socio", "responsavel_solidario"):
        raise HTTPException(status_code=400, detail="tipo_vinculo inválido")
    # Verificar duplicata
    existente = db.buscar_cliente_por_cpf_socio(doc)
    if existente:
        raise HTTPException(status_code=400, detail=f"CPF/CNPJ {doc} jÃ¡ estÃ¡ vinculado a outro cliente")
    socio = db.criar_socio(cliente_id, doc, dados.nome, dados.email, tipo_vinculo)
    if not socio:
        raise HTTPException(status_code=500, detail="Erro ao adicionar sÃ³cio")
    db.registrar_auditoria(
        tipo_evento="SOCIO_ADICIONADO",
        descricao=f"CPF/CNPJ {doc} ({dados.nome or 'sem nome'}) vinculado ao cliente '{cliente['nome']}'",
        usuario_id=gestor["id"],
    )
    return socio


@app.delete("/api/gestor/clientes/{cliente_id}/socios/{socio_id}")
async def remover_socio(cliente_id: str, socio_id: str,
                        gestor: dict = Depends(get_gestor_atual)):
    """Remove um CPF de sÃ³cio vinculado a um cliente."""
    if not db.tabela_socios_disponivel():
        raise HTTPException(status_code=400, detail="Tabela de sócios indisponível. Execute a migration de sócios.")
    _verificar_cliente_do_gestor(cliente_id, gestor["id"])
    removido = db.remover_socio(socio_id)
    if not removido:
        raise HTTPException(status_code=404, detail="SÃ³cio nÃ£o encontrado")
    return {"mensagem": "SÃ³cio removido com sucesso"}


@app.put("/api/gestor/clientes/{cliente_id}/socios/{socio_id}", response_model=SocioResponse)
async def editar_socio(cliente_id: str, socio_id: str, dados: AtualizarSocioRequest,
                       gestor: dict = Depends(get_gestor_atual)):
    """Edita vínculo (sócio/responsável solidário) de um cliente."""
    if not db.tabela_socios_disponivel():
        raise HTTPException(status_code=400, detail="Tabela de sócios indisponível. Execute a migration de sócios.")
    _verificar_cliente_do_gestor(cliente_id, gestor["id"])
    socio_atual = db.buscar_socio_por_id(socio_id)
    if not socio_atual:
        raise HTTPException(status_code=404, detail="Vínculo não encontrado")
    if socio_atual.get("cliente_id") != cliente_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    payload = dados.model_dump(exclude_unset=True, exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="Nenhum dado para atualizar")

    update_data = {}
    if "nome" in payload:
        update_data["nome"] = payload["nome"].strip()
    if "email" in payload:
        update_data["email"] = payload["email"].strip() or None
    if "tipo_vinculo" in payload:
        tipo = payload["tipo_vinculo"].strip().lower()
        if tipo not in ("socio", "responsavel_solidario"):
            raise HTTPException(status_code=400, detail="tipo_vinculo inválido")
        update_data["tipo_vinculo"] = tipo

    if "cpf_cnpj" in payload:
        doc = "".join(c for c in str(payload["cpf_cnpj"]) if c.isdigit())
        if len(doc) not in (11, 14):
            raise HTTPException(status_code=400, detail="CPF/CNPJ deve ter 11 ou 14 dígitos")
        existente = db.buscar_cliente_por_cpf_socio(doc)
        if existente and existente.get("id") != cliente_id:
            raise HTTPException(status_code=400, detail=f"CPF/CNPJ {doc} já está vinculado a outro cliente")
        update_data["cpf_cnpj"] = doc
        update_data["cpf"] = doc if len(doc) == 11 else None

    atualizado = db.atualizar_socio(socio_id, update_data)
    if not atualizado:
        raise HTTPException(status_code=500, detail="Erro ao atualizar vínculo")

    return atualizado


# ============================================================
# DOCUMENTOS (apenas gestores)
# ============================================================

@app.post("/api/documentos/upload")
async def upload_documento(
    request: Request,
    arquivo: UploadFile = File(...),
    titulo: str = Form(...),
    gestor: dict = Depends(get_gestor_atual),
):
    """Upload de documento PDF para assinatura."""
    if not arquivo.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF sÃ£o aceitos")

    conteudo = await arquivo.read()
    if len(conteudo) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Arquivo excede 50MB")

    hash_sha256 = calcular_hash_pdf(conteudo)
    storage_path = f"documentos/{gestor['id']}/{uuid.uuid4()}/{arquivo.filename}"
    db.upload_arquivo(storage_path, conteudo)

    documento = db.criar_documento(
        titulo=titulo,
        nome_arquivo=arquivo.filename,
        tamanho_bytes=len(conteudo),
        hash_sha256=hash_sha256,
        storage_path=storage_path,
        remetente_id=gestor["id"],
    )

    db.registrar_auditoria(
        tipo_evento="DOCUMENTO_UPLOAD",
        descricao=f"Upload do documento '{titulo}' ({arquivo.filename})",
        documento_id=documento["id"],
        usuario_id=gestor["id"],
        ip_origem=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return documento


@app.get("/api/documentos")
async def listar_documentos(gestor: dict = Depends(get_gestor_atual)):
    """Lista documentos do gestor autenticado."""
    return db.listar_documentos_remetente(gestor["id"])


@app.get("/api/documentos/{documento_id}")
async def obter_documento(documento_id: str, gestor: dict = Depends(get_gestor_atual)):
    """ObtÃ©m detalhes de um documento."""
    documento = db.buscar_documento(documento_id)
    if not documento:
        raise HTTPException(status_code=404, detail="Documento nÃ£o encontrado")
    if documento["remetente_id"] != gestor["id"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return documento


@app.delete("/api/documentos/{documento_id}")
async def excluir_documento(documento_id: str, gestor: dict = Depends(get_gestor_atual)):
    """Exclui um documento pendente do gestor."""
    documento = db.buscar_documento(documento_id)
    if not documento:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    if documento["remetente_id"] != gestor["id"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    if documento.get("status") == "aguardando_assinatura":
        raise HTTPException(status_code=400, detail="Não é possível excluir um documento que está aguardando assinatura")
    try:
        db.delete_arquivo(documento["storage_path"])
    except Exception:
        pass
    db.excluir_documento(documento_id)
    return {"ok": True}


@app.get("/api/documentos/{documento_id}/download")
async def download_documento(documento_id: str, gestor: dict = Depends(get_gestor_atual)):
    """Download do PDF original."""
    documento = db.buscar_documento(documento_id)
    if not documento:
        raise HTTPException(status_code=404, detail="Documento nÃ£o encontrado")
    if documento["remetente_id"] != gestor["id"]:
        raise HTTPException(status_code=403, detail="Acesso negado")

    conteudo = db.download_arquivo(documento["storage_path"])
    return StreamingResponse(
        io.BytesIO(conteudo),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={documento['nome_arquivo']}"},
    )


@app.get("/api/documentos/{documento_id}/download-assinado")
async def download_documento_assinado(documento_id: str, gestor: dict = Depends(get_gestor_atual)):
    """Download do PDF assinado (apenas para o gestor dono do documento)."""
    documento = db.buscar_documento(documento_id)
    if not documento:
        raise HTTPException(status_code=404, detail="Documento nÃ£o encontrado")
    if documento["remetente_id"] != gestor["id"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    if not documento.get("storage_path_assinado"):
        raise HTTPException(status_code=404, detail="Documento ainda nÃ£o foi assinado")

    conteudo = db.download_arquivo(documento["storage_path_assinado"])
    nome_assinado = documento["nome_arquivo"].replace(".pdf", "_assinado.pdf")
    return StreamingResponse(
        io.BytesIO(conteudo),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={nome_assinado}"},
    )


# ============================================================
# SOLICITAÃ‡Ã•ES DE ASSINATURA (gestores criam)
# ============================================================

@app.post("/api/documentos/{documento_id}/solicitar-assinatura")
async def solicitar_assinatura(
    documento_id: str,
    dados: SolicitacaoRequest,
    request: Request,
    gestor: dict = Depends(get_gestor_atual),
):
    """Cria solicitaÃ§Ã£o de assinatura e gera link seguro."""
    documento = db.buscar_documento(documento_id)
    if not documento:
        raise HTTPException(status_code=404, detail="Documento nÃ£o encontrado")
    if documento["remetente_id"] != gestor["id"]:
        raise HTTPException(status_code=403, detail="Acesso negado")

    # Vincular ao cliente cadastrado na mesma empresa (se existir)
    cliente_id = None
    cliente = db.buscar_usuario_por_email(dados.signatario_email)
    if (cliente and cliente.get("empresa_id") == gestor.get("empresa_id")):
        cliente_id = cliente["id"]
        if not dados.signatario_nome:
            dados.signatario_nome = cliente["nome"]

    if not cliente_id:
        raise HTTPException(status_code=400, detail="Cliente da solicitação deve estar previamente cadastrado")

    assinatura_obrigatoria_doc = "".join(
        c for c in str(dados.assinatura_obrigatoria_cpf_cnpj or "")
        if c.isdigit()
    )
    if len(assinatura_obrigatoria_doc) not in (11, 14):
        raise HTTPException(status_code=400, detail="Assinante obrigatório deve ter CPF/CNPJ válido")

    assinatura_obrigatoria_tipo = (dados.assinatura_obrigatoria_tipo or "").strip().lower()
    if assinatura_obrigatoria_tipo not in ("cliente_cpf", "cliente_cnpj", "socio", "responsavel_solidario"):
        raise HTTPException(status_code=400, detail="Tipo de assinante obrigatório inválido")

    docs_permitidos, _, _ = _obter_docs_permitidos_solicitacao({
        "documentos": {"remetente_id": gestor["id"]},
        "signatario_email": dados.signatario_email,
    })
    if assinatura_obrigatoria_doc not in docs_permitidos:
        raise HTTPException(
            status_code=400,
            detail="Assinante obrigatório não está vinculado ao cliente selecionado",
        )

    db.expirar_solicitacoes_pendentes_documento_signatario(
        documento_id=documento_id,
        assinatura_doc=assinatura_obrigatoria_doc,
    )

    pagina = max(1, int(dados.assinatura_pagina or 1))
    pos_x = _clamp_float(dados.assinatura_x or 0.06, 0.0, 0.95)
    pos_y = _clamp_float(dados.assinatura_y or 0.06, 0.0, 0.95)
    largura = _clamp_float(dados.assinatura_largura or 0.44, 0.05, 1.0)
    altura = _clamp_float(dados.assinatura_altura or 0.12, 0.05, 1.0)

    solicitacao = db.criar_solicitacao(
        documento_id=documento_id,
        signatario_email=dados.signatario_email,
        signatario_nome=dados.signatario_nome,
        mensagem=dados.mensagem,
        dias_expiracao=settings.signing_link_expiration_days,
        cliente_id=cliente_id,
        assinatura_obrigatoria_tipo=assinatura_obrigatoria_tipo,
        assinatura_obrigatoria_cpf_cnpj=assinatura_obrigatoria_doc,
        assinatura_obrigatoria_nome=dados.assinatura_obrigatoria_nome,
        assinatura_pagina=pagina,
        assinatura_x=pos_x,
        assinatura_y=pos_y,
        assinatura_largura=largura,
        assinatura_altura=altura,
    )

    db.recalcular_status_documento(documento_id)
    link = f"{settings.frontend_url}/assinar/{solicitacao['token_acesso']}"

    db.registrar_auditoria(
        tipo_evento="SOLICITACAO_CRIADA",
        descricao=f"SolicitaÃ§Ã£o de assinatura enviada para {dados.signatario_email}",
        documento_id=documento_id,
        solicitacao_id=solicitacao["id"],
        usuario_id=gestor["id"],
        ip_origem=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    return {**solicitacao, "link_assinatura": link}


# ============================================================
# CLIENTE â€” VISUALIZAÃ‡ÃƒO DE CONTRATOS
# ============================================================

@app.get("/api/cliente/solicitacoes")
async def listar_solicitacoes_cliente(cliente: dict = Depends(get_cliente_atual)):
    """Lista todos os contratos (pendentes e assinados) do cliente autenticado."""
    solicitacoes = db.listar_solicitacoes_cliente(cliente["id"])
    resultado = []
    for sol in solicitacoes:
        doc = sol.get("documentos", {}) or {}
        resultado.append({
            "id": sol["id"],
            "token_acesso": sol["token_acesso"],
            "titulo": doc.get("titulo", ""),
            "nome_arquivo": doc.get("nome_arquivo", ""),
            "tamanho_bytes": doc.get("tamanho_bytes", 0),
            "status": sol["status"],
            "mensagem": sol.get("mensagem"),
            "expira_em": sol.get("expira_em"),
            "assinado_em": sol.get("assinado_em"),
            "criado_em": sol["criado_em"],
            "tem_assinado": bool(doc.get("storage_path_assinado")),
        })
    return resultado


# ============================================================
# ENDPOINTS PÃšBLICOS (ACESSO VIA TOKEN DE ASSINATURA)
# ============================================================

@app.get("/api/assinatura/{token}")
async def obter_solicitacao_por_token(token: str, request: Request):
    """Acesso pÃºblico ao documento via token seguro."""
    solicitacao = db.buscar_solicitacao_por_token(token)
    if not solicitacao:
        raise HTTPException(status_code=404, detail="SolicitaÃ§Ã£o nÃ£o encontrada")

    expira_em = datetime.fromisoformat(solicitacao["expira_em"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expira_em:
        db.atualizar_solicitacao(solicitacao["id"], {"status": "expirado"})
        db.recalcular_status_documento(solicitacao["documento_id"])
        raise HTTPException(status_code=410, detail="Link de assinatura expirado")

    if solicitacao["status"] == "assinado":
        raise HTTPException(status_code=400, detail="Documento jÃ¡ foi assinado")

    if solicitacao["status"] == "pendente":
        db.atualizar_solicitacao(solicitacao["id"], {
            "status": "visualizado",
            "visualizado_em": datetime.now(timezone.utc).isoformat(),
        })
        db.registrar_auditoria(
            tipo_evento="DOCUMENTO_VISUALIZADO",
            descricao="Documento visualizado pelo signatÃ¡rio",
            documento_id=solicitacao["documento_id"],
            solicitacao_id=solicitacao["id"],
            ip_origem=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )

    doc = solicitacao.get("documentos", {})
    return {
        "solicitacao_id": solicitacao["id"],
        "documento_id": solicitacao["documento_id"],
        "titulo": doc.get("titulo", ""),
        "nome_arquivo": doc.get("nome_arquivo", ""),
        "signatario_nome": solicitacao.get("signatario_nome"),
        "signatario_email": solicitacao.get("signatario_email"),
        "mensagem": solicitacao.get("mensagem"),
        "assinatura_obrigatoria_tipo": solicitacao.get("assinatura_obrigatoria_tipo"),
        "assinatura_obrigatoria_cpf_cnpj": solicitacao.get("assinatura_obrigatoria_cpf_cnpj"),
        "assinatura_obrigatoria_nome": solicitacao.get("assinatura_obrigatoria_nome"),
        "status": solicitacao["status"],
        "expira_em": solicitacao["expira_em"],
    }


@app.post("/api/assinatura/{token}/validar-certificado")
async def validar_certificado_para_solicitacao(token: str, dados: ValidarCertificadoSolicitacaoRequest):
    """Valida se o CPF/CNPJ do certificado é permitido para a solicitação."""
    solicitacao = db.buscar_solicitacao_por_token(token)
    if not solicitacao:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    if solicitacao["status"] == "assinado":
        raise HTTPException(status_code=400, detail="Documento já foi assinado")

    cert_doc = "".join(c for c in str(dados.cpf_cnpj or "") if c.isdigit())
    if not cert_doc:
        raise HTTPException(status_code=400, detail="CPF/CNPJ inválido no certificado")

    docs_permitidos, cliente, _ = _obter_docs_permitidos_solicitacao(solicitacao)
    assinatura_obrigatoria = "".join(
        c for c in str(solicitacao.get("assinatura_obrigatoria_cpf_cnpj") or "")
        if c.isdigit()
    )
    autorizado = cert_doc in docs_permitidos
    if assinatura_obrigatoria:
        autorizado = autorizado and cert_doc == assinatura_obrigatoria
    return {
        "autorizado": autorizado,
        "cert_doc": cert_doc,
        "cliente_nome": cliente.get("nome"),
        "assinatura_obrigatoria_cpf_cnpj": assinatura_obrigatoria or None,
        "assinatura_obrigatoria_nome": solicitacao.get("assinatura_obrigatoria_nome"),
        "mensagem": (
            "Certificado autorizado para assinatura."
            if autorizado
            else "Certificado não autorizado para este contrato."
        ),
    }


@app.get("/api/assinatura/{token}/pdf")
async def visualizar_pdf_por_token(token: str):
    """Download do PDF para visualizaÃ§Ã£o (acesso via token)."""
    solicitacao = db.buscar_solicitacao_por_token(token)
    if not solicitacao:
        raise HTTPException(status_code=404, detail="SolicitaÃ§Ã£o nÃ£o encontrada")

    doc = solicitacao.get("documentos", {})
    storage_path_fonte = doc.get("storage_path_assinado") or doc["storage_path"]
    conteudo = db.download_arquivo(storage_path_fonte)

    return StreamingResponse(
        io.BytesIO(conteudo),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={doc['nome_arquivo']}"},
    )


@app.post("/api/assinatura/{token}/preparar")
async def preparar_assinatura(token: str, request: Request):
    """Prepara o conteÃºdo (hash) a ser assinado."""
    solicitacao = db.buscar_solicitacao_por_token(token)
    if not solicitacao:
        raise HTTPException(status_code=404, detail="SolicitaÃ§Ã£o nÃ£o encontrada")

    if solicitacao["status"] == "assinado":
        raise HTTPException(status_code=400, detail="Documento jÃ¡ foi assinado")

    doc_id = solicitacao["documento_id"]
    token_em_uso = _documentos_em_preparacao.get(doc_id)
    if token_em_uso and token_em_uso != token:
        raise HTTPException(
            status_code=409,
            detail="Outro signatário está finalizando a assinatura deste documento. Aguarde alguns segundos e tente novamente.",
        )

    doc = solicitacao.get("documentos", {})
    storage_path_fonte = doc.get("storage_path_assinado") or doc["storage_path"]
    pdf_bytes = db.download_arquivo(storage_path_fonte)

    conteudo_assinatura = await asyncio.to_thread(
        preparar_documento_pades_externo,
        pdf_bytes,
        int(solicitacao.get("assinatura_pagina") or 1),
        float(solicitacao.get("assinatura_x") or 0.06),
        float(solicitacao.get("assinatura_y") or 0.06),
        float(solicitacao.get("assinatura_largura") or 0.44),
        float(solicitacao.get("assinatura_altura") or 0.12),
    )
    _assinaturas_pendentes[token] = {
        "prepared_pdf_b64": conteudo_assinatura["prepared_pdf_b64"],
        "document_digest_hex": conteudo_assinatura["document_digest_hex"],
        "reserved_region_start": conteudo_assinatura["reserved_region_start"],
        "reserved_region_end": conteudo_assinatura["reserved_region_end"],
        "documento_id": solicitacao["documento_id"],
        "solicitacao_id": solicitacao["id"],
    }
    _documentos_em_preparacao[doc_id] = token

    db.registrar_auditoria(
        tipo_evento="ASSINATURA_PREPARADA",
        descricao="Hash do documento preparado para assinatura",
        documento_id=solicitacao["documento_id"],
        solicitacao_id=solicitacao["id"],
        ip_origem=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    return PrepararAssinaturaResponse(
        hash_bytes_b64=conteudo_assinatura["bytes_para_assinar_b64"],
        hash_hex=conteudo_assinatura["document_digest_hex"],
        algoritmo=conteudo_assinatura["algoritmo"],
        documento_id=solicitacao["documento_id"],
        solicitacao_id=solicitacao["id"],
    )


@app.post("/api/assinatura/submeter", response_model=AssinaturaResponse)
async def submeter_assinatura(dados: SubmeterAssinaturaRequest, request: Request):
    """Recebe a assinatura CMS/PKCS#7 e incorpora ao PDF no padrÃ£o PAdES."""
    solicitacao = db.buscar_solicitacao_por_token(dados.token_acesso)
    if not solicitacao:
        raise HTTPException(status_code=404, detail="SolicitaÃ§Ã£o nÃ£o encontrada")

    if solicitacao["status"] == "assinado":
        raise HTTPException(status_code=400, detail="Documento jÃ¡ foi assinado")

    doc = solicitacao.get("documentos", {})
    info_cert = extrair_info_certificado(dados.cert_pem)
    _validar_certificado_signatario(solicitacao, info_cert)

    contexto_assinatura = _assinaturas_pendentes.pop(dados.token_acesso, None)
    _documentos_em_preparacao.pop(solicitacao["documento_id"], None)
    if not contexto_assinatura:
        raise HTTPException(
            status_code=400,
            detail="PreparaÃ§Ã£o de assinatura nÃ£o encontrada. Execute /preparar novamente.",
        )

    pdf_assinado = await asyncio.to_thread(
        aplicar_cms_em_pdf_preparado,
        contexto_assinatura["prepared_pdf_b64"],
        dados.assinatura_cms_b64,
        contexto_assinatura["document_digest_hex"],
        contexto_assinatura["reserved_region_start"],
        contexto_assinatura["reserved_region_end"],
    )

    storage_path_assinado = doc.get("storage_path_assinado") or doc["storage_path"].replace(".pdf", "_assinado.pdf")
    db.upload_arquivo(storage_path_assinado, pdf_assinado)

    agora = datetime.now(timezone.utc).isoformat()
    assinatura_registro = db.criar_assinatura({
        "solicitacao_id": solicitacao["id"],
        "documento_id": solicitacao["documento_id"],
        "cert_subject_cn": info_cert.get("subject_cn"),
        "cert_subject_cpf": info_cert.get("cpf"),
        "cert_issuer_cn": info_cert.get("issuer_cn"),
        "cert_serial_number": info_cert.get("serial_number"),
        "cert_not_before": info_cert.get("not_before"),
        "cert_not_after": info_cert.get("not_after"),
        "cert_tipo": dados.cert_tipo,
        "cert_pem": dados.cert_pem,
        "hash_conteudo_assinado": contexto_assinatura["document_digest_hex"],
        "algoritmo_assinatura": "SHA256withRSA",
        "ip_signatario": get_client_ip(request),
        "user_agent": request.headers.get("user-agent"),
    })

    db.atualizar_solicitacao(solicitacao["id"], {"status": "assinado", "assinado_em": agora})
    db.atualizar_documento(solicitacao["documento_id"], {"storage_path_assinado": storage_path_assinado})
    db.recalcular_status_documento(solicitacao["documento_id"])

    db.registrar_auditoria(
        tipo_evento="DOCUMENTO_ASSINADO",
        descricao=f"Documento assinado por {info_cert.get('subject_cn')}",
        documento_id=solicitacao["documento_id"],
        solicitacao_id=solicitacao["id"],
        ip_origem=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        dados_extras={
            "cert_cn": info_cert.get("subject_cn"),
            "cert_cpf": info_cert.get("cpf"),
            "cert_issuer": info_cert.get("issuer_cn"),
            "cert_tipo": dados.cert_tipo,
        },
    )

    return AssinaturaResponse(
        id=assinatura_registro["id"],
        documento_id=solicitacao["documento_id"],
        cert_subject_cn=info_cert.get("subject_cn", ""),
        cert_subject_cpf=info_cert.get("cpf"),
        cert_issuer_cn=info_cert.get("issuer_cn", ""),
        assinado_em=agora,
        sucesso=True,
        mensagem="Documento assinado com sucesso no padrÃ£o PAdES",
    )


@app.get("/api/assinatura/{token}/download-assinado")
async def download_pdf_assinado(token: str):
    """Download do PDF assinado."""
    solicitacao = db.buscar_solicitacao_por_token(token)
    if not solicitacao or solicitacao["status"] != "assinado":
        raise HTTPException(status_code=404, detail="Documento assinado nÃ£o encontrado")

    doc = solicitacao.get("documentos", {})
    if not doc.get("storage_path_assinado"):
        raise HTTPException(status_code=404, detail="PDF assinado nÃ£o disponÃ­vel")

    conteudo = db.download_arquivo(doc["storage_path_assinado"])
    nome = doc["nome_arquivo"].replace(".pdf", "_assinado.pdf")

    return StreamingResponse(
        io.BytesIO(conteudo),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={nome}"},
    )


# ============================================================
# PROGRESSO DE ASSINATURA EM GRUPO
# ============================================================

@app.get("/api/documentos/{documento_id}/solicitacoes")
async def listar_solicitacoes_por_documento(
    documento_id: str,
    gestor: dict = Depends(get_gestor_atual),
):
    """Retorna todas as solicitações de assinatura de um documento com status individual."""
    documento = db.buscar_documento(documento_id)
    if not documento:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    if documento["remetente_id"] != gestor["id"]:
        raise HTTPException(status_code=403, detail="Acesso negado")

    solicitacoes = db.listar_solicitacoes_documento(documento_id)
    agora = datetime.now(timezone.utc)
    resultado = []
    for s in solicitacoes:
        expira_em = s.get("expira_em")
        expirou = False
        if expira_em:
            try:
                expira_dt = datetime.fromisoformat(expira_em.replace("Z", "+00:00"))
                expirou = agora > expira_dt
            except Exception:
                pass
        status_efetivo = s.get("status")
        if status_efetivo in ("pendente", "visualizado") and expirou:
            status_efetivo = "expirado"
        token = s.get("token_acesso")
        resultado.append({
            "id": s["id"],
            "signatario_nome": s.get("signatario_nome"),
            "signatario_email": s.get("signatario_email"),
            "assinatura_obrigatoria_cpf_cnpj": s.get("assinatura_obrigatoria_cpf_cnpj"),
            "assinatura_obrigatoria_nome": s.get("assinatura_obrigatoria_nome"),
            "assinatura_obrigatoria_tipo": s.get("assinatura_obrigatoria_tipo"),
            "status": status_efetivo,
            "criado_em": s.get("criado_em"),
            "assinado_em": s.get("assinado_em"),
            "expira_em": expira_em,
            "link_assinatura": f"{settings.frontend_url}/assinar/{token}" if token else None,
        })
    return resultado


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "servico": settings.app_name, "versao": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)






