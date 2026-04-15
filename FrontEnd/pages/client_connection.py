import streamlit as st
import requests

# Config
st.set_page_config(page_title="ConexÃ£o do Cliente - DashFlow", page_icon="🔌", layout="wide")

API_URL = "http://localhost:8000"

# Verificar login
if "token" not in st.session_state or st.session_state.token is None:
    st.warning("âš ï¸ VocÃª precisa fazer login primeiro!")
    st.info("ðŸ‘ˆ VÃ¡ para a pÃ¡gina inicial e faÃ§a login na barra lateral")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}"}

def _get_client_id():
    client_id = st.session_state.get("selected_client_id")
    if client_id:
        return client_id

    if hasattr(st, "query_params"):
        value = st.query_params.get("client_id")
        if isinstance(value, list):
            return value[0] if value else None
        return value

    query_params = st.experimental_get_query_params()
    value = query_params.get("client_id")
    if isinstance(value, list):
        return value[0] if value else None
    return value

def _get_client(client_id: str):
    try:
        response = requests.get(f"{API_URL}/clients/{client_id}", headers=headers)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None

st.title("🔌 PÃ¡gina de ConexÃ£o do Cliente")

col_left, col_right = st.columns([1, 3])
with col_left:
    if st.button("â¬…ï¸ Voltar para Clientes", use_container_width=True):
        st.switch_page("pages/clients.py")

client_id = _get_client_id()
if not client_id:
    st.info("Selecione um cliente primeiro para abrir esta pÃ¡gina.")
    st.stop()

client = _get_client(client_id)
if not client:
    st.error("Cliente nÃ£o encontrado ou sem permissÃ£o.")
    st.stop()

st.subheader(f"Cliente: {client['name']}")
info_parts = []
if client.get("company"):
    info_parts.append(f"ðŸ¢ {client['company']}")
if client.get("email"):
    info_parts.append(f"ðŸ“§ {client['email']}")
if client.get("phone"):
    info_parts.append(f"ðŸ“± {client['phone']}")
if info_parts:
    st.markdown(" | ".join(info_parts))

st.caption(f"ID: {client['id']} | Criado em: {client['created_at'][:10]}")

st.markdown("---")

# ConexÃµes
st.subheader("ðŸ”— ConexÃµes")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**Google Ads**")
    if st.button("Conectar Google Ads", key="connect_google", use_container_width=True):
        st.info("ðŸš§ Em desenvolvimento. Aqui entraremos com o OAuth e salvar tokens por cliente.")

with col2:
    st.markdown("**Meta Ads**")
    if st.button("Conectar Meta Ads", key="connect_meta", use_container_width=True):
        st.info("ðŸš§ Em desenvolvimento. Aqui entraremos com o OAuth e salvar tokens por cliente.")

st.markdown("---")

# Campanhas
st.subheader("ðŸ“£ Campanhas")
st.info("Nenhuma campanha por enquanto. Conecte uma integraÃ§Ã£o para visualizar as campanhas deste cliente.")

