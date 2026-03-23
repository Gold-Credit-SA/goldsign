"""
Gerenciador de Certificados Digitais ICP-Brasil.

Responsável por:
- Listar certificados do keystore do SO (Windows/Linux/macOS)
- Integrar com tokens PKCS#11 (A3)
- Gerar assinaturas CMS/PKCS#7
- Manter a chave privada segura na máquina local
"""

import base64
import hashlib
import platform
import subprocess
import uuid
import tempfile
from datetime import datetime, timezone
from typing import List, Optional, Dict

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa, ec
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID


class CertificateInfo:
    """Informações públicas de um certificado."""

    def __init__(self, cert_id: str, cert_obj, private_key=None,
                 source: str = "system", cert_tipo: str = "A1",
                 pkcs11_session=None, pkcs11_key_handle=None):
        self.cert_id = cert_id
        self.cert = cert_obj
        self.private_key = private_key
        self.source = source
        self.cert_tipo = cert_tipo
        self.pkcs11_session = pkcs11_session
        self.pkcs11_key_handle = pkcs11_key_handle

    def to_dict(self) -> dict:
        cn = self._get_attr(self.cert.subject, NameOID.COMMON_NAME)
        issuer_cn = self._get_attr(self.cert.issuer, NameOID.COMMON_NAME)
        org = self._get_attr(self.cert.issuer, NameOID.ORGANIZATION_NAME)

        # Extrair CPF do certificado ICP-Brasil
        cpf = self._extrair_cpf()
        cnpj = self._extrair_cnpj()
        cpf_cnpj = cnpj or cpf

        not_before = self._get_not_valid_before()
        not_after = self._get_not_valid_after()

        return {
            "cert_id": self.cert_id,
            "subject_cn": cn,
            "cpf": cpf,
            "cnpj": cnpj,
            "cpf_cnpj": cpf_cnpj,
            "issuer_cn": issuer_cn,
            "issuer_org": org,
            "serial_number": str(self.cert.serial_number),
            "not_before": not_before.isoformat(),
            "not_after": not_after.isoformat(),
            "valido": self._esta_valido(),
            "tipo": self.cert_tipo,
            "source": self.source,
        }

    def _get_attr(self, name, oid) -> str:
        try:
            return name.get_attributes_for_oid(oid)[0].value
        except (IndexError, Exception):
            return ""

    @staticmethod
    def _parse_asn1_string(raw: bytes) -> str:
        """Extrai conteúdo de uma string ASN.1 (IA5String/UTF8String/etc.)."""
        if not raw:
            return ""
        if len(raw) >= 2:
            length = raw[1]
            if length < 0x80 and len(raw) >= 2 + length:
                return raw[2: 2 + length].decode("latin-1", errors="ignore")
        return raw.decode("latin-1", errors="ignore")

    def _extrair_cpf(self) -> str:
        """Tenta extrair CPF do certificado ICP-Brasil (OtherName no SubjectAltName)."""
        from cryptography.x509 import OtherName
        from cryptography.x509.oid import ExtensionOID
        try:
            san = self.cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            for entry in san.value:
                if isinstance(entry, OtherName) and entry.type_id.dotted_string == "2.16.76.1.3.1":
                    valor = self._parse_asn1_string(entry.value)
                    digits = "".join(c for c in valor if c.isdigit())
                    if digits:
                        return digits[:11]
        except Exception:
            pass

        # Fallback: CN no formato "NOME:CPF"
        cn = self._get_attr(self.cert.subject, NameOID.COMMON_NAME)
        if ":" in cn:
            for part in cn.split(":"):
                cleaned = "".join(c for c in part if c.isdigit())
                if len(cleaned) == 11:
                    return cleaned
        return ""

    def _extrair_cnpj(self) -> str:
        """Tenta extrair CNPJ do certificado ICP-Brasil (OtherName no SubjectAltName)."""
        from cryptography.x509 import OtherName
        from cryptography.x509.oid import ExtensionOID
        try:
            san = self.cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            for entry in san.value:
                if isinstance(entry, OtherName) and entry.type_id.dotted_string == "2.16.76.1.3.3":
                    valor = self._parse_asn1_string(entry.value)
                    digits = "".join(c for c in valor if c.isdigit())
                    if digits:
                        return digits[:14]
        except Exception:
            pass
        return ""

    def extrair_cpf_cnpj(self) -> str:
        """Retorna CNPJ (PJ) ou CPF (PF) extraído do certificado, apenas dígitos."""
        cnpj = self._extrair_cnpj()
        if cnpj:
            return cnpj
        return self._extrair_cpf()

    def _esta_valido(self) -> bool:
        agora = datetime.now(timezone.utc)
        return self._get_not_valid_before() <= agora <= self._get_not_valid_after()

    def _get_not_valid_before(self):
        dt = getattr(self.cert, "not_valid_before_utc", None)
        if dt is None:
            dt = self.cert.not_valid_before.replace(tzinfo=timezone.utc)
        return dt

    def _get_not_valid_after(self):
        dt = getattr(self.cert, "not_valid_after_utc", None)
        if dt is None:
            dt = self.cert.not_valid_after.replace(tzinfo=timezone.utc)
        return dt


class CertificateManager:
    """Gerenciador principal de certificados."""

    def __init__(self):
        self._certificados: Dict[str, CertificateInfo] = {}
        self._pkcs11_libs = [
            # Caminhos comuns para drivers PKCS#11 de tokens no Brasil
            "/usr/lib/libaetpkss.so",       # Safenet / Gemalto
            "/usr/lib/libgdpkcs11.so",       # GD Burti
            "/usr/lib/watchdata/ICP/lib/libwdpkcs.so",  # Watchdata
            "/usr/lib/libeTPkcs11.so",       # Safenet eToken
            "/usr/lib/libneaborern.so",      # Neoborg
            "C:\\Windows\\System32\\eTPKCS11.dll",  # Windows Safenet
            "C:\\Windows\\System32\\aetpkss1.dll",  # Windows Safenet alt
            "C:\\Windows\\System32\\dkck201.dll",   # Windows Datakey
        ]

    def _run_powershell_hidden(self, ps_script: str, timeout: int = 30):
        """Executa PowerShell sem abrir janela de terminal no Windows."""
        kwargs = {
            "capture_output": True,
            "text": True,
            "timeout": timeout,
        }
        if platform.system() == "Windows" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        return subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            **kwargs,
        )

    def listar_certificados(self) -> List[dict]:
        """Lista todos os certificados disponíveis."""
        self._certificados.clear()
        certificados = []

        # 1. Certificados do sistema operacional (A1)
        certs_so = self._listar_certificados_so()
        certificados.extend(certs_so)

        # 2. Certificados de tokens PKCS#11 (A3)
        certs_pkcs11 = self._listar_certificados_pkcs11()
        certificados.extend(certs_pkcs11)

        return certificados

    def assinar(self, cert_id: str, hash_b64: str, algoritmo: str = "SHA-256") -> dict:
        """
        Assina o hash usando a chave privada do certificado selecionado.
        A chave privada nunca sai da máquina.
        """
        cert_info = self._certificados.get(cert_id)
        if not cert_info:
            # O app local pode perder o cache entre chamadas.
            # Recarrega automaticamente para evitar erro intermitente.
            self.listar_certificados()
            cert_info = self._certificados.get(cert_id)
        if not cert_info:
            raise ValueError(f"Certificado '{cert_id}' não encontrado. Liste novamente.")

        # Decodificar conteúdo a ser assinado (byte range preparado pelo backend)
        conteudo_bytes = base64.b64decode(hash_b64)

        # Gerar assinatura conforme o tipo
        if cert_info.cert_tipo == "A3" and cert_info.pkcs11_session:
            raise ValueError(
                "Assinatura juridica PAdES com A3 ainda nao implementada neste prototipo. "
                "Use certificado A1 no Windows Store."
            )
        elif cert_info.source == "windows_store":
            assinatura = self._assinar_windows_store_cms(cert_info, conteudo_bytes)
        elif cert_info.private_key:
            assinatura = self._assinar_cms_chave_local(cert_info, conteudo_bytes)
        else:
            raise ValueError("Chave privada não disponível para este certificado")

        # Certificado em PEM
        cert_pem = cert_info.cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")

        return {
            "assinatura_cms_b64": base64.b64encode(assinatura).decode("ascii"),
            "cert_pem": cert_pem,
            "cert_tipo": cert_info.cert_tipo,
            "cert_info": cert_info.to_dict(),
        }

    def assinar_desafio(self, cert_id: str, desafio_b64: str) -> dict:
        """
        Assina um desafio (nonce) com a chave privada do certificado.
        Usado no fluxo de autenticação por certificado digital.
        Retorna assinatura RAW (não CMS) para verificação no backend.
        """
        cert_info = self._certificados.get(cert_id)
        if not cert_info:
            self.listar_certificados()
            cert_info = self._certificados.get(cert_id)
        if not cert_info:
            raise ValueError(f"Certificado '{cert_id}' não encontrado")

        desafio_bytes = base64.b64decode(desafio_b64)

        if cert_info.source == "windows_store":
            assinatura = self._assinar_windows_store(cert_info, desafio_bytes)
        elif cert_info.private_key:
            assinatura = self._assinar_chave_local(cert_info, desafio_bytes)
        else:
            raise ValueError("Chave privada não disponível para este certificado")

        cert_pem = cert_info.cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
        info = cert_info.to_dict()
        info["cpf_cnpj"] = cert_info.extrair_cpf_cnpj()

        return {
            "assinatura_b64": base64.b64encode(assinatura).decode("ascii"),
            "cert_pem": cert_pem,
            "cert_info": info,
        }

    def verificar_certificado(self, cert_id: str) -> dict:
        """Verifica validade do certificado."""
        cert_info = self._certificados.get(cert_id)
        if not cert_info:
            raise ValueError("Certificado não encontrado")

        info = cert_info.to_dict()
        info["cadeia_confianca"] = "Verificação de cadeia ICP-Brasil requer AC raiz"
        return info

    # ============================================================
    # CERTIFICADOS DO SISTEMA OPERACIONAL (A1)
    # ============================================================

    def _listar_certificados_so(self) -> List[dict]:
        """Lista certificados do keystore do SO."""
        sistema = platform.system()
        certs = []

        if sistema == "Windows":
            certs = self._listar_windows_store()
        elif sistema == "Linux":
            certs = self._listar_linux_store()
        elif sistema == "Darwin":
            certs = self._listar_macos_keychain()

        return certs

    def _listar_windows_store(self) -> List[dict]:
        """Lista certificados do Windows Certificate Store."""
        certificados = []
        try:
            import ssl
            import ctypes
            from ctypes import wintypes

            # Usar wincertstore ou certifi para acessar o store
            # Abordagem via PowerShell para listar certs pessoais
            resultado = self._run_powershell_hidden(
                "$stores = @('Cert:\\CurrentUser\\My','Cert:\\LocalMachine\\My'); "
                "$items = foreach ($s in $stores) { "
                "  if (Test-Path $s) { "
                "    Get-ChildItem -Path $s | "
                "    Where-Object { $_.HasPrivateKey } | "
                "    Select-Object *, @{Name='StorePath';Expression={$s}} "
                "  } "
                "}; "
                "$items | "
                "ForEach-Object { "
                "  [PSCustomObject]@{"
                "    Thumbprint=$_.Thumbprint; "
                "    Subject=$_.Subject; "
                "    Issuer=$_.Issuer; "
                "    StorePath=$_.StorePath; "
                "    NotBefore=$_.NotBefore.ToString('o'); "
                "    NotAfter=$_.NotAfter.ToString('o'); "
                "    Cert=[Convert]::ToBase64String($_.RawData)"
                "  }"
                "} | ConvertTo-Json -Compress",
                timeout=30,
            )

            if resultado.returncode == 0 and resultado.stdout.strip():
                import json
                raw = resultado.stdout.strip()
                try:
                    dados = json.loads(raw)
                except json.JSONDecodeError:
                    # Alguns ambientes adicionam mensagens extras ao stdout.
                    # Tentamos extrair o trecho JSON bruto.
                    inicio_obj = raw.find("{")
                    inicio_arr = raw.find("[")
                    candidatos = [i for i in [inicio_obj, inicio_arr] if i >= 0]
                    if not candidatos:
                        raise
                    dados = json.loads(raw[min(candidatos):])
                if isinstance(dados, dict):
                    dados = [dados]

                for item in dados:
                    try:
                        cert_bytes = base64.b64decode(item["Cert"])
                        cert = x509.load_der_x509_certificate(cert_bytes, default_backend())
                        cert_id = f"win_{item['Thumbprint']}"

                        info = CertificateInfo(
                            cert_id=cert_id,
                            cert_obj=cert,
                            source="windows_store",
                            cert_tipo="A1",
                        )
                        self._certificados[cert_id] = info
                        certificados.append(info.to_dict())
                    except Exception:
                        continue

            elif resultado.stderr:
                print(f"Erro PowerShell ao listar certificados: {resultado.stderr.strip()}")

        except Exception as e:
            print(f"Erro ao listar certificados Windows: {e}")

        return certificados

    def _listar_linux_store(self) -> List[dict]:
        """
        Lista certificados A1 em Linux.
        Procura em diretórios comuns de certificados pessoais.
        """
        certificados = []
        import glob

        # Diretórios comuns para certificados pessoais
        paths_pfx = glob.glob(os.path.expanduser("~/.certs/*.pfx")) + \
                     glob.glob(os.path.expanduser("~/.certs/*.p12")) + \
                     glob.glob("/etc/ssl/certs/pessoal/*.pfx")

        for pfx_path in paths_pfx:
            try:
                # Para PFX/P12, precisaria da senha - solicitar via frontend
                cert_id = f"linux_{hashlib.md5(pfx_path.encode()).hexdigest()[:12]}"
                # Nota: em produção, listar o certificado público sem a chave
                # e solicitar a senha quando for assinar
                certificados.append({
                    "cert_id": cert_id,
                    "subject_cn": os.path.basename(pfx_path),
                    "tipo": "A1",
                    "source": "linux_file",
                    "arquivo": pfx_path,
                    "requer_senha": True,
                })
            except Exception:
                continue

        return certificados

    def _listar_macos_keychain(self) -> List[dict]:
        """Lista certificados do macOS Keychain."""
        certificados = []
        try:
            resultado = subprocess.run(
                ["security", "find-identity", "-v", "-p", "codesigning"],
                capture_output=True, text=True, timeout=30
            )
            # Parse output para extrair certificados
            for line in resultado.stdout.split("\n"):
                line = line.strip()
                if line and ")" in line and '"' in line:
                    parts = line.split('"')
                    if len(parts) >= 2:
                        cn = parts[1]
                        hash_val = line.split(")")[0].split()[-1] if ")" in line else ""
                        cert_id = f"mac_{hash_val[:12]}"
                        certificados.append({
                            "cert_id": cert_id,
                            "subject_cn": cn,
                            "tipo": "A1",
                            "source": "macos_keychain",
                        })
        except Exception as e:
            print(f"Erro ao listar certificados macOS: {e}")

        return certificados

    # ============================================================
    # CERTIFICADOS PKCS#11 (A3 - Tokens/Smartcards)
    # ============================================================

    def _listar_certificados_pkcs11(self) -> List[dict]:
        """Lista certificados de tokens PKCS#11."""
        certificados = []

        try:
            import PyKCS11
        except ImportError:
            return certificados

        for lib_path in self._pkcs11_libs:
            if not os.path.exists(lib_path):
                continue

            try:
                pkcs11 = PyKCS11.PyKCS11Lib()
                pkcs11.load(lib_path)

                slots = pkcs11.getSlotList(tokenPresent=True)
                for slot in slots:
                    try:
                        session = pkcs11.openSession(
                            slot, PyKCS11.CKF_SERIAL_SESSION
                        )

                        # Listar certificados no token
                        objetos = session.findObjects([
                            (PyKCS11.CKA_CLASS, PyKCS11.CKO_CERTIFICATE),
                        ])

                        for obj in objetos:
                            attrs = session.getAttributeValue(obj, [
                                PyKCS11.CKA_VALUE,
                                PyKCS11.CKA_LABEL,
                                PyKCS11.CKA_ID,
                            ])

                            cert_der = bytes(attrs[0])
                            label = bytes(attrs[1]).decode("utf-8", errors="ignore")
                            obj_id = bytes(attrs[2]).hex()

                            cert = x509.load_der_x509_certificate(
                                cert_der, default_backend()
                            )

                            cert_id = f"pkcs11_{slot}_{obj_id}"

                            info = CertificateInfo(
                                cert_id=cert_id,
                                cert_obj=cert,
                                source="pkcs11",
                                cert_tipo="A3",
                                pkcs11_session=session,
                            )

                            # Buscar handle da chave privada correspondente
                            priv_keys = session.findObjects([
                                (PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY),
                                (PyKCS11.CKA_ID, attrs[2]),
                            ])
                            if priv_keys:
                                info.pkcs11_key_handle = priv_keys[0]

                            self._certificados[cert_id] = info
                            certificados.append(info.to_dict())

                    except Exception as e:
                        print(f"Erro ao acessar slot {slot}: {e}")
                        continue

            except Exception as e:
                print(f"Erro ao carregar PKCS#11 lib {lib_path}: {e}")
                continue

        return certificados

    # ============================================================
    # ASSINATURA DIGITAL
    # ============================================================

    def _assinar_chave_local(self, cert_info: CertificateInfo,
                              hash_bytes: bytes) -> bytes:
        """Assina usando chave privada local (A1)."""
        private_key = cert_info.private_key

        if isinstance(private_key, rsa.RSAPrivateKey):
            assinatura = private_key.sign(
                hash_bytes,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
        elif isinstance(private_key, ec.EllipticCurvePrivateKey):
            assinatura = private_key.sign(
                hash_bytes,
                ec.ECDSA(hashes.SHA256())
            )
        else:
            raise ValueError("Tipo de chave privada não suportado")

        return assinatura

    def _assinar_windows_store(self, cert_info: CertificateInfo, hash_bytes: bytes) -> bytes:
        """Assina usando a chave privada vinculada ao certificado no Windows Store."""
        if not cert_info.cert_id.startswith("win_"):
            raise ValueError("Certificado Windows inválido")

        thumbprint = cert_info.cert_id.removeprefix("win_")
        payload_b64 = base64.b64encode(hash_bytes).decode("ascii")

        ps_script = (
            "Add-Type -AssemblyName System.Security; "
            f"$thumb = '{thumbprint}'; "
            "$stores = @('Cert:\\CurrentUser\\My','Cert:\\LocalMachine\\My'); "
            "$cert = $null; "
            "foreach ($s in $stores) { "
            "  $p = Join-Path $s $thumb; "
            "  if (Test-Path $p) { $cert = Get-Item $p; break } "
            "}; "
            "if (-not $cert) { throw 'Certificado nao encontrado no Windows Store' }; "
            f"$data = [Convert]::FromBase64String('{payload_b64}'); "
            "$rsa = [System.Security.Cryptography.X509Certificates.RSACertificateExtensions]::GetRSAPrivateKey($cert); "
            "if ($rsa) { "
            "  $sig = $rsa.SignData($data, [System.Security.Cryptography.HashAlgorithmName]::SHA256, [System.Security.Cryptography.RSASignaturePadding]::Pkcs1); "
            "  [Convert]::ToBase64String($sig); "
            "  exit 0 "
            "}; "
            "$ecdsa = [System.Security.Cryptography.X509Certificates.ECDsaCertificateExtensions]::GetECDsaPrivateKey($cert); "
            "if ($ecdsa) { "
            "  $sig = $ecdsa.SignData($data, [System.Security.Cryptography.HashAlgorithmName]::SHA256); "
            "  [Convert]::ToBase64String($sig); "
            "  exit 0 "
            "}; "
            "throw 'Chave privada nao acessivel para assinatura'"
        )

        resultado = self._run_powershell_hidden(ps_script, timeout=30)

        if resultado.returncode != 0:
            erro = (resultado.stderr or resultado.stdout or "").strip()
            raise ValueError(f"Falha ao assinar com certificado do Windows: {erro}")

        assinatura_b64 = (resultado.stdout or "").strip()
        if not assinatura_b64:
            raise ValueError("Assinatura vazia retornada pelo Windows Store")

        return base64.b64decode(assinatura_b64)

    def _assinar_windows_store_cms(self, cert_info: CertificateInfo, conteudo_bytes: bytes) -> bytes:
        """Gera CMS detached (PKCS#7) usando certificado do Windows Store."""
        if not cert_info.cert_id.startswith("win_"):
            raise ValueError("Certificado Windows inválido")

        thumbprint = cert_info.cert_id.removeprefix("win_")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
            tmp.write(conteudo_bytes)
            tmp_path = tmp.name
        tmp_path_ps = tmp_path.replace("'", "''")

        ps_script = (
            "Add-Type -AssemblyName System.Security; "
            f"$thumb = '{thumbprint}'; "
            "$stores = @('Cert:\\CurrentUser\\My','Cert:\\LocalMachine\\My'); "
            "$cert = $null; "
            "foreach ($s in $stores) { "
            "  $p = Join-Path $s $thumb; "
            "  if (Test-Path $p) { $cert = Get-Item $p; break } "
            "}; "
            "if (-not $cert) { throw 'Certificado nao encontrado no Windows Store' }; "
            f"$data = [System.IO.File]::ReadAllBytes('{tmp_path_ps}'); "
            "$contentInfo = New-Object System.Security.Cryptography.Pkcs.ContentInfo -ArgumentList (, $data); "
            "$signedCms = New-Object System.Security.Cryptography.Pkcs.SignedCms -ArgumentList $contentInfo, $true; "
            "$cmsSigner = New-Object System.Security.Cryptography.Pkcs.CmsSigner -ArgumentList $cert; "
            "$cmsSigner.IncludeOption = [System.Security.Cryptography.X509Certificates.X509IncludeOption]::WholeChain; "
            "$cmsSigner.DigestAlgorithm = New-Object System.Security.Cryptography.Oid('2.16.840.1.101.3.4.2.1'); "
            "$signedCms.ComputeSignature($cmsSigner, $false); "
            "[Convert]::ToBase64String($signedCms.Encode())"
        )

        try:
            resultado = self._run_powershell_hidden(ps_script, timeout=45)
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

        if resultado.returncode != 0:
            erro = (resultado.stderr or resultado.stdout or "").strip()
            raise ValueError(f"Falha ao gerar CMS no Windows Store: {erro}")

        cms_b64 = (resultado.stdout or "").strip()
        if not cms_b64:
            raise ValueError("CMS vazio retornado pelo Windows Store")

        return base64.b64decode(cms_b64)

    def _assinar_cms_chave_local(self, cert_info: CertificateInfo, conteudo_bytes: bytes) -> bytes:
        """Gera CMS detached com chave privada local carregada em memória."""
        from cryptography.hazmat.primitives.serialization import pkcs7

        if not cert_info.private_key:
            raise ValueError("Chave privada local indisponível")

        builder = pkcs7.PKCS7SignatureBuilder().set_data(conteudo_bytes).add_signer(
            cert_info.cert,
            cert_info.private_key,
            hashes.SHA256(),
        )
        return builder.sign(
            serialization.Encoding.DER,
            [pkcs7.PKCS7Options.DetachedSignature],
        )

    def _assinar_pkcs11(self, cert_info: CertificateInfo,
                        hash_bytes: bytes) -> bytes:
        """Assina usando token PKCS#11 (A3)."""
        import PyKCS11

        session = cert_info.pkcs11_session
        key_handle = cert_info.pkcs11_key_handle

        if not session or not key_handle:
            raise ValueError("Sessão PKCS#11 ou chave não disponível")

        # Mecanismo RSA PKCS#1 v1.5 com SHA-256
        mechanism = PyKCS11.Mechanism(PyKCS11.CKM_SHA256_RSA_PKCS, None)

        assinatura = session.sign(key_handle, hash_bytes, mechanism)
        return bytes(assinatura)


# Necessário para os imports de os
import os
