"""
Aplicativo Local de Assinatura Digital - ICP-Brasil

Serviço HTTP local (localhost:8765) que:
- Lista certificados digitais instalados na máquina
- Integra com tokens A3 via PKCS#11
- Gera assinaturas CMS/PKCS#7 com a chave privada local
- A chave privada NUNCA sai da máquina do usuário

Suporta:
- Certificados A1 (arquivo .pfx/.p12 no keystore do SO)
- Certificados A3 (token/smartcard via PKCS#11)
"""

import base64
import json
import platform
import subprocess
import sys
import os
import traceback
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS

from certificate_manager import CertificateManager

app = Flask(__name__)
# Aceita requisições de qualquer origem — o serviço só ouve localhost,
# portanto não há risco de acesso externo.
CORS(app, origins="*")

cert_manager = CertificateManager()


@app.route("/api/status", methods=["GET"])
def status():
    """Verifica se o aplicativo local está rodando."""
    return jsonify({
        "status": "online",
        "versao": "1.0.0",
        "sistema_operacional": platform.system(),
        "python_versao": platform.python_version(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.route("/api/certificados", methods=["GET"])
def listar_certificados():
    """
    Lista todos os certificados digitais disponíveis na máquina.
    Retorna informações públicas (CN, emissor, validade, tipo).
    A chave privada permanece na máquina.
    """
    try:
        certificados = cert_manager.listar_certificados()
        return jsonify({
            "sucesso": True,
            "certificados": certificados,
            "total": len(certificados),
        })
    except Exception as e:
        return jsonify({
            "sucesso": False,
            "erro": str(e),
            "certificados": [],
        }), 500


@app.route("/api/assinar", methods=["POST"])
def assinar():
    """
    Assina o hash recebido usando o certificado selecionado.
    
    Recebe:
        - cert_id: ID do certificado selecionado
        - hash_b64: Hash do conteúdo a ser assinado (base64)
        - algoritmo: Algoritmo de hash (default: SHA-256)
    
    Retorna:
        - assinatura_cms_b64: Assinatura CMS/PKCS#7 em base64
        - cert_pem: Certificado público em PEM
        - cert_tipo: Tipo do certificado (A1 ou A3)
    """
    dados = request.get_json()

    if not dados:
        return jsonify({"sucesso": False, "erro": "JSON inválido"}), 400

    cert_id = dados.get("cert_id")
    hash_b64 = dados.get("hash_b64")
    algoritmo = dados.get("algoritmo", "SHA-256")

    if not cert_id or not hash_b64:
        return jsonify({
            "sucesso": False,
            "erro": "cert_id e hash_b64 são obrigatórios",
        }), 400

    try:
        resultado = cert_manager.assinar(cert_id, hash_b64, algoritmo)
        return jsonify({
            "sucesso": True,
            **resultado,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "sucesso": False,
            "erro": str(e),
        }), 500


@app.route("/api/assinar-desafio", methods=["POST"])
def assinar_desafio():
    """
    Assina um desafio (nonce) para autenticação por certificado digital.

    Recebe:
        - cert_id: ID do certificado selecionado
        - desafio_b64: Bytes aleatórios do desafio em base64

    Retorna:
        - assinatura_b64: Assinatura RAW (SHA256withRSA) em base64
        - cert_pem: Certificado público em PEM
        - cert_info: Informações do certificado (inclui cpf_cnpj)
    """
    dados = request.get_json()

    if not dados:
        return jsonify({"sucesso": False, "erro": "JSON inválido"}), 400

    cert_id = dados.get("cert_id")
    desafio_b64 = dados.get("desafio_b64")

    if not cert_id or not desafio_b64:
        return jsonify({
            "sucesso": False,
            "erro": "cert_id e desafio_b64 são obrigatórios",
        }), 400

    try:
        resultado = cert_manager.assinar_desafio(cert_id, desafio_b64)
        return jsonify({"sucesso": True, **resultado})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"sucesso": False, "erro": str(e)}), 500


@app.route("/api/verificar-certificado", methods=["POST"])
def verificar_certificado():
    """Verifica validade e cadeia de confiança de um certificado."""
    dados = request.get_json()
    cert_id = dados.get("cert_id")

    if not cert_id:
        return jsonify({"sucesso": False, "erro": "cert_id obrigatório"}), 400

    try:
        info = cert_manager.verificar_certificado(cert_id)
        return jsonify({"sucesso": True, **info})
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500


if __name__ == "__main__":
    print("=" * 60)
    print("  Gold Credit · Assinatura Digital ICP-Brasil")
    print("  Rodando em: http://localhost:8765")
    print("  Sistema: " + platform.system())
    print("=" * 60)
    app.run(host="127.0.0.1", port=8765, debug=False)
