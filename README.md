# DashFlow 📊

> **Interface atual:** o aplicativo React/Vite está em `my-app`. Consulte [execução local e validação da repaginação](docs/glassy-redesign.md). A documentação Streamlit abaixo descreve a versão inicial.

Sistema automatizado de relatórios de marketing digital com IA.

## Stack

- **Backend:** FastAPI + SQLAlchemy + PostgreSQL
- **Frontend:** Streamlit
- **Auth:** JWT
- **APIs:** Google Ads, Meta Ads
- **IA:** Google Gemini

## Setup - Backend

```bash
cd Backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

Criar `.env`:
```bash
DATABASE_URL=sqlite:///./dashflow.db
SECRET_KEY=sua-chave-aqui
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
```

Rodar:
```bash
python -m uvicorn app.main:app --reload
```

API disponível em: http://localhost:8000  
Docs: http://localhost:8000/docs

## Setup - Frontend

```bash
cd Frontend
pip install -r requirements.txt
streamlit run Home.py
```

## Progresso

- [x] Setup inicial
- [x] Sistema de autenticação (register/login/JWT)
- [x] Banco de dados
- [ ] CRUD de clientes
- [ ] Integração Google Ads API
- [ ] Integração Meta Ads API
- [ ] Dashboard Streamlit
- [ ] Geração de relatórios PDF
- [ ] Insights com IA

## Autor

Desenvolvido por Duffes - 2025