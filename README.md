# 📝 Assinatura Digital ICP-Brasil

Sistema completo de assinatura digital com validade jurídica no Brasil, baseado em certificados ICP-Brasil (A1 e A3) no padrão PAdES.

## 🏗️ Arquitetura

```
assinatura-digital/
├── backend/          # FastAPI - API principal
├── frontend/         # React - Interface do usuário
├── app/              # Python - Aplicativo local (acessa certificados)
└── banco-de-dados/   # PostgreSQL via Supabase - Schemas e migrations
```

## 🔄 Fluxo de Assinatura

1. **Remetente** faz upload do PDF via frontend
2. **Backend** armazena o PDF e gera um link seguro
3. **Destinatário** acessa o link, visualiza o documento
4. **Frontend** se comunica com o **App Local** (localhost:8765)
5. **App Local** lista certificados ICP-Brasil instalados na máquina
6. **Destinatário** seleciona o certificado e confirma a assinatura
7. **App Local** gera a assinatura CMS/PKCS#7 com a chave privada
8. **Frontend** envia a assinatura ao **Backend**
9. **Backend** incorpora a assinatura ao PDF no padrão PAdES via pyHanko
10. **PDF assinado** é armazenado com metadados de auditoria

## 🚀 Instalação e Execução

### Pré-requisitos
- Python 3.10+
- Node.js 18+
- Conta no Supabase (ou PostgreSQL local)

### Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # Configure suas variáveis
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env  # Configure suas variáveis
npm start
```

### App Local (na máquina do signatário)
```bash
cd app
pip install -r requirements.txt
python main.py
# Inicia em http://localhost:8765
```

### Banco de Dados
```bash
# Execute os scripts SQL no Supabase Dashboard ou via psql
psql -f banco-de-dados/001_schema.sql
psql -f banco-de-dados/002_policies.sql
```

## 🔐 Segurança

- Chave privada **nunca** sai da máquina do signatário
- Links de assinatura com token UUID + expiração
- Assinatura PAdES com selo visível no documento
- Auditoria completa de todas as operações
- CORS configurável para produção
