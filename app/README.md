# App Local - Assinatura Digital ICP-Brasil

## Sobre

Aplicativo Python/Flask que roda **na máquina do signatário** (localhost:8765).

Responsável por:
- Listar certificados digitais ICP-Brasil instalados (A1 e A3)
- Gerar assinaturas CMS/PKCS#7 usando a chave privada local
- A chave privada **nunca** sai da máquina

## Requisitos

- Python 3.10+
- Certificado digital ICP-Brasil instalado no sistema
- Para A3: driver PKCS#11 do token/smartcard

## Instalação

```bash
cd app
pip install -r requirements.txt
python main.py
```

O aplicativo inicia em `http://localhost:8765`.

## Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/status` | Verifica se está rodando |
| GET | `/api/certificados` | Lista certificados disponíveis |
| POST | `/api/assinar` | Gera assinatura CMS/PKCS#7 |
| POST | `/api/verificar-certificado` | Verifica validade |

## Certificados Suportados

### A1 (Arquivo)
- Windows: Certificate Store (CurrentUser\My)
- Linux: ~/.certs/*.pfx, ~/.certs/*.p12
- macOS: Keychain

### A3 (Token/Smartcard)
- Safenet/Gemalto (eToken)
- GD Burti
- Watchdata
- Outros via PKCS#11

## Segurança

- Roda apenas em `127.0.0.1` (não aceita conexões externas)
- CORS restrito a `localhost:3000`
- Chave privada usada apenas para assinar, nunca exportada
- Comunicação com o frontend via HTTP local
