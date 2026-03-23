"""ServiÃ§o de acesso ao banco de dados via Supabase."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from supabase import create_client, Client
from config import get_settings

_bucket_inicializado = False


def get_supabase() -> Client:
    """Retorna cliente Supabase com service_role key."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_key)


# ============================================================
# USUÃRIOS
# ============================================================

def criar_usuario(email: str, nome: str, senha_hash: str,
                  tipo_usuario: str = "usuario", gestor_id: str = None,
                  empresa_id: str = None, cpf_cnpj: str = None) -> dict:
    db = get_supabase()
    dados = {
        "email": email,
        "nome": nome,
        "senha_hash": senha_hash,
        "tipo_usuario": tipo_usuario,
    }
    if gestor_id:
        dados["gestor_id"] = gestor_id
    if empresa_id:
        dados["empresa_id"] = empresa_id
    if cpf_cnpj:
        # Armazena apenas dÃ­gitos
        dados["cpf_cnpj"] = "".join(c for c in cpf_cnpj if c.isdigit())
    resultado = db.table("usuarios").insert(dados).execute()
    return resultado.data[0] if resultado.data else None


def buscar_usuario_por_email(email: str) -> Optional[dict]:
    db = get_supabase()
    resultado = db.table("usuarios").select("*").eq("email", email).execute()
    return resultado.data[0] if resultado.data else None


def listar_docs_vinculados_cliente(cliente_id: str) -> list[dict]:
    """Lista documentos de vinculados (socio/responsavel_solidario) de um cliente."""
    db = get_supabase()
    try:
        resultado = (
            db.table("socios")
            .select("cpf, cpf_cnpj, nome, email, tipo_vinculo")
            .eq("cliente_id", cliente_id)
            .execute()
        )
        data = resultado.data or []
        docs = []
        for item in data:
            doc = "".join(
                c for c in str(item.get("cpf_cnpj") or item.get("cpf") or "")
                if c.isdigit()
            )
            if not doc:
                continue
            docs.append({
                "cpf_cnpj": doc,
                "nome": item.get("nome"),
                "email": item.get("email"),
                "tipo_vinculo": item.get("tipo_vinculo") or "socio",
            })
        return docs
    except Exception:
        try:
            legado = db.table("socios").select("cpf, nome").eq("cliente_id", cliente_id).execute()
            data = legado.data or []
            return [
                {
                    "cpf_cnpj": "".join(c for c in str(item.get("cpf") or "") if c.isdigit()),
                    "nome": item.get("nome"),
                    "email": None,
                    "tipo_vinculo": "socio",
                }
                for item in data if item.get("cpf")
            ]
        except Exception:
            return []


def buscar_usuario_por_id(usuario_id: str) -> Optional[dict]:
    db = get_supabase()
    resultado = db.table("usuarios").select("*").eq("id", usuario_id).execute()
    return resultado.data[0] if resultado.data else None


def listar_gestores() -> list:
    db = get_supabase()
    resultado = (
        db.table("usuarios")
        .select("id, email, nome, ativo, criado_em, tipo_usuario, empresa_id, cpf_cnpj")
        .eq("tipo_usuario", "gestor")
        .order("criado_em", desc=True)
        .execute()
    )
    return resultado.data or []

def listar_gestores_por_empresa(empresa_id: str) -> list:
    db = get_supabase()
    resultado = (
        db.table("usuarios")
        .select("id, email, nome, ativo, criado_em, tipo_usuario, empresa_id, cpf_cnpj")
        .eq("tipo_usuario", "gestor")
        .eq("empresa_id", empresa_id)
        .order("criado_em", desc=True)
        .execute()
    )
    return resultado.data or []


def criar_empresa(
    razao_social: str,
    cnpj: str | None = None,
    nome_fantasia: str = None,
    tipo_cadastro: str | None = None,
    documento: str | None = None,
) -> Optional[dict]:
    db = get_supabase()
    dados: dict = {
        "razao_social": razao_social,
    }
    cnpj_digits = "".join(c for c in str(cnpj or "") if c.isdigit())
    if cnpj_digits:
        dados["cnpj"] = cnpj_digits
    if nome_fantasia:
        dados["nome_fantasia"] = nome_fantasia
    if tipo_cadastro:
        dados["tipo_cadastro"] = tipo_cadastro
    documento_digits = "".join(c for c in str(documento or "") if c.isdigit())
    if documento_digits:
        dados["documento"] = documento_digits
    try:
        resultado = db.table("empresas").insert(dados).execute()
    except Exception:
        dados.pop("tipo_cadastro", None)
        dados.pop("documento", None)
        resultado = db.table("empresas").insert(dados).execute()
    return resultado.data[0] if resultado.data else None


def listar_empresas() -> list:
    db = get_supabase()
    resultado = (
        db.table("empresas")
        .select("id, razao_social, cnpj, nome_fantasia, ativo, criado_em")
        .eq("ativo", True)
        .order("razao_social")
        .execute()
    )
    return resultado.data or []


def buscar_empresa_por_id(empresa_id: str) -> Optional[dict]:
    db = get_supabase()
    resultado = db.table("empresas").select("*").eq("id", empresa_id).execute()
    return resultado.data[0] if resultado.data else None


def buscar_empresa_por_cnpj(cnpj: str) -> Optional[dict]:
    db = get_supabase()
    digits = "".join(c for c in cnpj if c.isdigit())
    resultado = db.table("empresas").select("*").eq("cnpj", digits).execute()
    return resultado.data[0] if resultado.data else None


def buscar_empresa_por_documento(documento: str) -> Optional[dict]:
    db = get_supabase()
    digits = "".join(c for c in str(documento or "") if c.isdigit())
    if not digits:
        return None
    try:
        resultado = db.table("empresas").select("*").eq("documento", digits).execute()
        return resultado.data[0] if resultado.data else None
    except Exception:
        return None


def listar_clientes_gestor(empresa_id: str, excluir_usuario_id: str = None) -> list:
    db = get_supabase()
    try:
        query = (
            db.table("usuarios")
            .select("id, email, nome, ativo, criado_em, tipo_usuario, cpf_cnpj, empresa_id")
            .eq("empresa_id", empresa_id)
            .order("criado_em", desc=True)
        )
        if excluir_usuario_id:
            query = query.neq("id", excluir_usuario_id)
        resultado = query.execute()
        return resultado.data or []
    except Exception:
        return []


def desativar_usuario(usuario_id: str) -> Optional[dict]:
    db = get_supabase()
    resultado = (
        db.table("usuarios")
        .update({"ativo": False})
        .eq("id", usuario_id)
        .execute()
    )
    return resultado.data[0] if resultado.data else None


def atualizar_usuario(usuario_id: str, dados: dict) -> Optional[dict]:
    db = get_supabase()
    resultado = db.table("usuarios").update(dados).eq("id", usuario_id).execute()
    return resultado.data[0] if resultado.data else None


def buscar_usuario_por_cpf_cnpj(cpf_cnpj: str) -> Optional[dict]:
    """Busca usuÃ¡rio pelo CPF (11 dÃ­gitos) ou CNPJ (14 dÃ­gitos)."""
    db = get_supabase()
    digits = "".join(c for c in cpf_cnpj if c.isdigit())
    resultado = (
        db.table("usuarios")
        .select("*")
        .eq("cpf_cnpj", digits)
        .eq("ativo", True)
        .execute()
    )
    return resultado.data[0] if resultado.data else None


def buscar_cliente_por_cpf_socio(cpf: str) -> Optional[dict]:
    """Busca o cliente (empresa) ao qual um CPF de sÃ³cio estÃ¡ vinculado."""
    db = get_supabase()
    digits = "".join(c for c in cpf if c.isdigit())
    try:
        resultado = (
            db.table("socios")
            .select("cliente_id")
            .or_(f"cpf.eq.{digits},cpf_cnpj.eq.{digits}")
            .limit(1)
            .execute()
        )
    except Exception:
        resultado = db.table("socios").select("cliente_id").eq("cpf", digits).limit(1).execute()
    if not resultado.data:
        return None
    return buscar_usuario_por_id(resultado.data[0]["cliente_id"])


def tabela_socios_disponivel() -> bool:
    db = get_supabase()
    try:
        db.table("socios").select("id").limit(1).execute()
        return True
    except Exception:
        return False


def criar_socio(cliente_id: str, cpf_cnpj: str, nome: str = None,
               email: str = None, tipo_vinculo: str = "socio") -> Optional[dict]:
    db = get_supabase()
    doc = "".join(c for c in cpf_cnpj if c.isdigit())
    dados: dict = {
        "cliente_id": cliente_id,
        "cpf": doc if len(doc) == 11 else None,
        "cpf_cnpj": doc,
        "tipo_vinculo": tipo_vinculo or "socio",
    }
    if nome:
        dados["nome"] = nome
    if email:
        dados["email"] = email
    try:
        resultado = db.table("socios").insert(dados).execute()
    except Exception:
        # Compatibilidade com schema antigo (somente cpf + nome)
        legado = {"cliente_id": cliente_id, "cpf": doc[:11], "nome": nome}
        resultado = db.table("socios").insert(legado).execute()
    return resultado.data[0] if resultado.data else None


def listar_socios_cliente(cliente_id: str) -> list:
    db = get_supabase()
    resultado = (
        db.table("socios")
        .select("*")
        .eq("cliente_id", cliente_id)
        .order("criado_em")
        .execute()
    )
    return resultado.data or []


def buscar_socio_por_id(socio_id: str) -> Optional[dict]:
    db = get_supabase()
    resultado = db.table("socios").select("*").eq("id", socio_id).execute()
    return resultado.data[0] if resultado.data else None


def atualizar_socio(socio_id: str, dados: dict) -> Optional[dict]:
    db = get_supabase()
    resultado = db.table("socios").update(dados).eq("id", socio_id).execute()
    return resultado.data[0] if resultado.data else None


def remover_socio(socio_id: str) -> bool:
    db = get_supabase()
    resultado = db.table("socios").delete().eq("id", socio_id).execute()
    return bool(resultado.data)


def contar_adms() -> int:
    db = get_supabase()
    resultado = (
        db.table("usuarios")
        .select("id", count="exact")
        .eq("tipo_usuario", "adm")
        .execute()
    )
    return resultado.count or 0


# ============================================================
# DOCUMENTOS
# ============================================================

def criar_documento(titulo: str, nome_arquivo: str, tamanho_bytes: int,
                    hash_sha256: str, storage_path: str, remetente_id: str) -> dict:
    db = get_supabase()
    resultado = db.table("documentos").insert({
        "titulo": titulo,
        "nome_arquivo": nome_arquivo,
        "tamanho_bytes": tamanho_bytes,
        "hash_sha256": hash_sha256,
        "storage_path": storage_path,
        "remetente_id": remetente_id,
    }).execute()
    return resultado.data[0] if resultado.data else None


def buscar_documento(documento_id: str) -> Optional[dict]:
    db = get_supabase()
    resultado = db.table("documentos").select("*").eq("id", documento_id).execute()
    return resultado.data[0] if resultado.data else None


def excluir_documento(documento_id: str) -> None:
    db = get_supabase()
    db.table("documentos").delete().eq("id", documento_id).execute()


def atualizar_documento(documento_id: str, dados: dict) -> Optional[dict]:
    db = get_supabase()
    resultado = db.table("documentos").update(dados).eq("id", documento_id).execute()
    return resultado.data[0] if resultado.data else None


def listar_documentos_remetente(remetente_id: str) -> list:
    db = get_supabase()
    resultado = (
        db.table("documentos")
        .select("*, solicitacoes_assinatura(*)")
        .eq("remetente_id", remetente_id)
        .order("criado_em", desc=True)
        .execute()
    )
    return resultado.data or []


def listar_solicitacoes_documento(documento_id: str) -> list:
    db = get_supabase()
    resultado = (
        db.table("solicitacoes_assinatura")
        .select("*")
        .eq("documento_id", documento_id)
        .order("criado_em")
        .execute()
    )
    return resultado.data or []


def recalcular_status_documento(documento_id: str) -> str:
    """
    Recalcula status do documento com base em todas as solicitações.
    Regras:
      - sem solicitações: pendente
      - todas assinadas: assinado
      - existe pendente/visualizado: aguardando_assinatura
      - sem pendentes e sem assinadas: expirado
    """
    solicitacoes = listar_solicitacoes_documento(documento_id)
    if not solicitacoes:
        status = "pendente"
    else:
        statuses = [s.get("status") for s in solicitacoes]
        if all(s == "assinado" for s in statuses):
            status = "assinado"
        elif any(s in ("pendente", "visualizado") for s in statuses):
            status = "aguardando_assinatura"
        elif any(s == "assinado" for s in statuses):
            status = "aguardando_assinatura"
        else:
            status = "expirado"

    atualizar_documento(documento_id, {"status": status})
    return status


# ============================================================
# SOLICITAÃ‡Ã•ES DE ASSINATURA
# ============================================================

def criar_solicitacao(documento_id: str, signatario_email: str,
                      signatario_nome: str = None, mensagem: str = None,
                      dias_expiracao: int = 7, cliente_id: str = None,
                      assinatura_obrigatoria_tipo: str = None,
                      assinatura_obrigatoria_cpf_cnpj: str = None,
                      assinatura_obrigatoria_nome: str = None,
                      assinatura_pagina: int = 1,
                      assinatura_x: float = 0.06,
                      assinatura_y: float = 0.06,
                      assinatura_largura: float = 0.44,
                      assinatura_altura: float = 0.12) -> dict:
    db = get_supabase()
    expira_em = (datetime.now(timezone.utc) + timedelta(days=dias_expiracao)).isoformat()
    dados = {
        "documento_id": documento_id,
        "signatario_email": signatario_email,
        "signatario_nome": signatario_nome,
        "mensagem": mensagem,
        "expira_em": expira_em,
        "assinatura_pagina": assinatura_pagina,
        "assinatura_x": assinatura_x,
        "assinatura_y": assinatura_y,
        "assinatura_largura": assinatura_largura,
        "assinatura_altura": assinatura_altura,
        "assinatura_obrigatoria_tipo": assinatura_obrigatoria_tipo,
        "assinatura_obrigatoria_cpf_cnpj": (
            "".join(c for c in str(assinatura_obrigatoria_cpf_cnpj or "") if c.isdigit())
            or None
        ),
        "assinatura_obrigatoria_nome": assinatura_obrigatoria_nome,
    }
    if cliente_id:
        dados["cliente_id"] = cliente_id
    try:
        resultado = db.table("solicitacoes_assinatura").insert(dados).execute()
    except Exception:
        # Compatibilidade com schema sem colunas novas
        dados.pop("cliente_id", None)
        dados.pop("assinatura_obrigatoria_tipo", None)
        dados.pop("assinatura_obrigatoria_cpf_cnpj", None)
        dados.pop("assinatura_obrigatoria_nome", None)
        resultado = db.table("solicitacoes_assinatura").insert(dados).execute()
    return resultado.data[0] if resultado.data else None


def buscar_solicitacao_por_token(token: str) -> Optional[dict]:
    db = get_supabase()
    resultado = (
        db.table("solicitacoes_assinatura")
        .select("*, documentos(*)")
        .eq("token_acesso", token)
        .execute()
    )
    return resultado.data[0] if resultado.data else None


def atualizar_solicitacao(solicitacao_id: str, dados: dict) -> Optional[dict]:
    db = get_supabase()
    resultado = (
        db.table("solicitacoes_assinatura")
        .update(dados)
        .eq("id", solicitacao_id)
        .execute()
    )
    return resultado.data[0] if resultado.data else None


def expirar_solicitacoes_pendentes_documento_signatario(documento_id: str, assinatura_doc: str = None) -> int:
    """
    Expira solicitações pendentes/visualizadas do mesmo documento e signatário obrigatório.
    Evita duplicidade de links ativos para a mesma pessoa.
    """
    db = get_supabase()
    assinatura_doc = "".join(c for c in str(assinatura_doc or "") if c.isdigit())
    try:
        query = (
            db.table("solicitacoes_assinatura")
            .update({"status": "expirado"})
            .eq("documento_id", documento_id)
            .in_("status", ["pendente", "visualizado"])
        )
        if assinatura_doc:
            query = query.eq("assinatura_obrigatoria_cpf_cnpj", assinatura_doc)
        resultado = query.execute()
        return len(resultado.data or [])
    except Exception:
        return 0


def listar_solicitacoes_cliente(cliente_id: str) -> list:
    """Lista todas as solicitaÃ§Ãµes de assinatura de um cliente."""
    db = get_supabase()
    resultado = (
        db.table("solicitacoes_assinatura")
        .select("*, documentos(titulo, nome_arquivo, tamanho_bytes, remetente_id, storage_path_assinado)")
        .eq("cliente_id", cliente_id)
        .order("criado_em", desc=True)
        .execute()
    )
    return resultado.data or []


def listar_solicitacoes_recentes(limit: int = 100) -> list:
    db = get_supabase()
    resultado = (
        db.table("solicitacoes_assinatura")
        .select(
            "*, documentos(id, titulo, nome_arquivo, tamanho_bytes, status, storage_path_assinado, criado_em)"
        )
        .order("criado_em", desc=True)
        .limit(limit)
        .execute()
    )
    return resultado.data or []


def listar_solicitacoes_por_bundle_token(bundle_token: str, limit: int = 500) -> list:
    db = get_supabase()
    resultado = (
        db.table("solicitacoes_assinatura")
        .select(
            "*, documentos(id, titulo, nome_arquivo, tamanho_bytes, status, storage_path, storage_path_assinado, criado_em)"
        )
        .like("mensagem", f"%bundle={bundle_token}|%")
        .order("criado_em")
        .limit(limit)
        .execute()
    )
    return resultado.data or []


# ============================================================
# ASSINATURAS
# ============================================================

def criar_assinatura(dados: dict) -> dict:
    db = get_supabase()
    resultado = db.table("assinaturas").insert(dados).execute()
    return resultado.data[0] if resultado.data else None


def buscar_assinaturas_documento(documento_id: str) -> list:
    db = get_supabase()
    resultado = (
        db.table("assinaturas")
        .select("*")
        .eq("documento_id", documento_id)
        .order("criado_em", desc=True)
        .execute()
    )
    return resultado.data or []


# ============================================================
# AUDITORIA
# ============================================================

def registrar_auditoria(tipo_evento: str, descricao: str,
                        documento_id: str = None, solicitacao_id: str = None,
                        usuario_id: str = None, ip_origem: str = None,
                        user_agent: str = None, dados_extras: dict = None):
    db = get_supabase()
    registro = {
        "tipo_evento": tipo_evento,
        "descricao": descricao,
    }
    if documento_id:
        registro["documento_id"] = documento_id
    if solicitacao_id:
        registro["solicitacao_id"] = solicitacao_id
    if usuario_id:
        registro["usuario_id"] = usuario_id
    if ip_origem:
        registro["ip_origem"] = ip_origem
    if user_agent:
        registro["user_agent"] = user_agent
    if dados_extras:
        registro["dados_extras"] = dados_extras

    db.table("auditoria").insert(registro).execute()


# ============================================================
# STORAGE
# ============================================================

def garantir_bucket_storage():
    """Garante que o bucket configurado exista no Storage."""
    global _bucket_inicializado
    if _bucket_inicializado:
        return

    db = get_supabase()
    settings = get_settings()
    bucket_name = settings.supabase_bucket

    try:
        buckets = db.storage.list_buckets() or []
        def bucket_nome(bucket):
            if isinstance(bucket, dict):
                return bucket.get("name")
            return getattr(bucket, "name", None)

        existe = any(bucket_nome(bucket) == bucket_name for bucket in buckets)
        if not existe:
            db.storage.create_bucket(
                id=bucket_name,
                name=bucket_name,
                options={"public": False},
            )
    except Exception as e:
        if "already exists" not in str(e).lower():
            raise

    _bucket_inicializado = True


def upload_arquivo(caminho: str, conteudo: bytes, content_type: str = "application/pdf") -> str:
    garantir_bucket_storage()
    db = get_supabase()
    settings = get_settings()
    db.storage.from_(settings.supabase_bucket).upload(
        path=caminho,
        file=conteudo,
        file_options={
            "content-type": content_type,
            "upsert": "true",
        }
    )
    return caminho


def delete_arquivo(caminho: str) -> None:
    garantir_bucket_storage()
    db = get_supabase()
    settings = get_settings()
    db.storage.from_(settings.supabase_bucket).remove([caminho])


def download_arquivo(caminho: str) -> bytes:
    garantir_bucket_storage()
    db = get_supabase()
    settings = get_settings()
    return db.storage.from_(settings.supabase_bucket).download(caminho)


def gerar_url_assinada(caminho: str, expira_em_segundos: int = 3600) -> str:
    garantir_bucket_storage()
    db = get_supabase()
    settings = get_settings()
    resultado = db.storage.from_(settings.supabase_bucket).create_signed_url(
        caminho, expira_em_segundos
    )
    return resultado.get("signedURL", "")
