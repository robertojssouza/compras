import os
from typing import Any

import streamlit as st
from streamlit_autorefresh import st_autorefresh
from supabase import Client, create_client


st.set_page_config(page_title="Lista de compras", page_icon="🛒", layout="wide")

st.markdown(
    """
    <style>
    /* Remove topo em branco e esconde o cabeçalho nativo do Streamlit */
    .stAppViewContainer .main .block-container,
    .block-container {
        padding-top: 0rem !important;
    }
    header {
        visibility: hidden !important;
        height: 0vh !important;
    }

    /* Trava os campos 'Quantidade' e 'Unidade' LADO A LADO no celular */
    [data-testid="stForm"] [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 0.5rem !important;
        width: 100% !important;
    }

    [data-testid="stForm"] [data-testid="stColumn"] {
        min-width: 0 !important;
        flex: 1 1 50% !important;
    }

    /* Impede que as colunas da lista empilhem na vertical no celular */
    .st-key-items-table [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        justify-content: space-between !important;
        gap: 0.4rem !important;
        width: 100% !important;
    }

    /* Libera o corte vertical e remove margens internas dos parágrafos */
    .st-key-items-table [data-testid="stColumn"] {
        min-width: 0 !important;
        overflow: visible !important;
    }

    .st-key-items-table p,
    .st-key-items-table [data-testid="stMarkdownContainer"] {
        margin: 0 !important;
        padding: 0 !important;
        line-height: 1.35 !important;
        overflow: visible !important;
        word-break: break-word !important;
    }

    /* Coluna central do texto cresce para ocupar o espaço */
    .st-key-items-table [data-testid="stColumn"]:nth-child(2) {
        flex: 1 1 auto !important;
    }

    /* Coluna do botão X fixada à extrema direita */
    .st-key-items-table [data-testid="stColumn"]:nth-child(3) {
        flex: 0 0 auto !important;
        display: flex !important;
        justify-content: flex-end !important;
    }

    /* Estilização dos botões */
    .st-key-items-table [data-testid="stButton"] button {
        min-height: 1.6rem !important;
        padding: 0.2rem 0.45rem !important;
        font-size: 0.8rem !important;
        white-space: nowrap !important;
    }

    .st-key-items-table [class*="st-key-buy-"] button {
        color: #ffffff !important;
        border-color: #15803d !important;
        background: #16a34a !important;
    }
    .st-key-items-table [class*="st-key-undo-"] button {
        color: #ffffff !important;
        border-color: #c2410c !important;
        background: #ea580c !important;
    }
    .st-key-items-table [class*="st-key-delete-"] button {
        color: #b42318 !important;
        border-color: #fca5a5 !important;
        background: #fef2f2 !important;
        padding: 0.2rem 0.4rem !important;
        font-size: 0.9rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def setting(name: str) -> str:
    value = os.getenv(name, "")
    if not value:
        try:
            value = st.secrets.get(name, "")
        except FileNotFoundError as error:
            raise RuntimeError(
                "Crie `.streamlit/secrets.toml` com SUPABASE_URL e "
                "SUPABASE_ANON_KEY. Veja o README."
            ) from error
    if not value:
        raise RuntimeError(f"Secret ausente: {name}.")
    return str(value)


@st.cache_resource
def get_supabase() -> Client:
    return create_client(setting("SUPABASE_URL"), setting("SUPABASE_ANON_KEY"))


def get_default_list(client: Client) -> dict[str, Any]:
    response = client.rpc("get_default_shopping_list").execute()
    if not response.data:
        raise RuntimeError("Não foi possível carregar a lista de compras.")
    return response.data


def render_items(client: Client, active_list: dict[str, Any]) -> None:
    st.subheader("Adicionar produto")
    with st.form("add_item", clear_on_submit=True):
        name = st.text_input("Produto", placeholder="Ex.: arroz")
        
        # Divisão da quantidade em Número e Unidade na mesma linha
        col_qty, col_unit = st.columns([1, 1])
        with col_qty:
            qty_num = st.text_input("Quantidade", value="1")
        with col_unit:
            units = ["un", "kg", "g", "L", "ml", "pct", "cx", "dz", "lata", "garr"]
            qty_unit = st.selectbox("Unidade", options=units, index=0)

        if st.form_submit_button("Adicionar", type="primary"):
            if not name.strip() or not qty_num.strip():
                st.error("Informe o produto e a quantidade.")
            else:
                full_quantity = f"{qty_num.strip()} {qty_unit}"
                client.rpc("add_shopping_item", {
                    "code": active_list["invite_code"],
                    "item_name": name.strip(),
                    "item_quantity": full_quantity,
                    "creator": "contribuidor",
                }).execute()
                st.rerun()

    response = client.rpc(
        "list_shopping_items", {"code": active_list["invite_code"]}
    ).execute()
    items = response.data or []
    st.subheader(f"Produtos ({len(items)})")
    if not items:
        st.info("A lista está vazia.")
        return

    with st.container(key="items-table"):
        for item in items:
            col_act, col_txt, col_del = st.columns(
                [1.1, 3.8, 0.6], vertical_alignment="center"
            )
            
            with col_act:
                action_label = "Desfazer" if item["is_purchased"] else "Comprar"
                action_key = "undo" if item["is_purchased"] else "buy"
                if st.button(
                    action_label,
                    key=f"{action_key}-{item['id']}",
                    help="Alterar status do produto",
                ):
                    client.rpc("set_shopping_item_purchased", {
                        "code": active_list["invite_code"],
                        "item_id": item["id"],
                        "purchased": not item["is_purchased"],
                    }).execute()
                    st.rerun()

            with col_txt:
                if item["is_purchased"]:
                    label_html = f"<span style='text-decoration: line-through; opacity: 0.6;'>{item['name']}</span> <span style='opacity: 0.65;'>· {item['quantity']}</span>"
                else:
                    label_html = f"<strong>{item['name']}</strong> · {item['quantity']}"
                st.markdown(label_html, unsafe_allow_html=True)

            with col_del:
                if st.button(
                    "✕", key=f"delete-{item['id']}", help="Remover produto"
                ):
                    client.rpc("delete_shopping_item", {
                        "code": active_list["invite_code"],
                        "item_id": item["id"],
                    }).execute()
                    st.rerun()


def render_admin(client: Client) -> None:
    if st.button(
        "Fechar administração"
        if st.session_state.get("admin_open")
        else "Abrir administração",
        key="toggle-admin",
    ):
        st.session_state.admin_open = not st.session_state.get("admin_open", False)
        st.rerun()
    if not st.session_state.get("admin_open"):
        return

    st.subheader("Administração de listas")
    admin_code = st.text_input(
        "Código administrativo",
        type="password",
        value=st.session_state.get("admin_code", ""),
        key="admin-code-input",
    )
    if st.button("Visualizar listas", key="load-admin-lists"):
        response = client.rpc(
            "list_all_shopping_lists", {"p_admin_code": admin_code}
        ).execute()
        st.session_state.admin_lists = response.data or []
        st.session_state.admin_code = admin_code

    lists = st.session_state.get("admin_lists")
    if lists is None:
        return
    if not lists:
        st.info("Nenhuma lista criada.")
        return
    st.warning("Excluir uma lista também exclui todos os seus produtos.")
    for shopping_list in lists:
        st.write(
            f"{shopping_list['name']} · `{shopping_list['invite_code']}`"
        )
        st.caption(f"Criada em: {shopping_list['created_at'][:10]}")
        if st.button(
            "Excluir lista",
            key=f"admin-delete-{shopping_list['id']}",
            use_container_width=True,
        ):
            client.rpc("delete_shopping_list", {
                "p_admin_code": st.session_state.get("admin_code", ""),
                "target_list_id": shopping_list["id"],
            }).execute()
            st.session_state.admin_lists = [
                item for item in lists if item["id"] != shopping_list["id"]
            ]
            if st.session_state.get("active_list", {}).get("id") == shopping_list["id"]:
                st.session_state.pop("active_list")
            st.rerun()


def main() -> None:
    client = get_supabase()
    if "active_list" not in st.session_state:
        st.session_state.active_list = None
    st_autorefresh(interval=5000, key="shopping-list-refresh")
    st.title("🛒 Lista de compras")
    
    active_list = st.session_state.get("active_list")
    if active_list is None:
        st.session_state.active_list = get_default_list(client)
        st.rerun()

    render_items(client, active_list)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        message = str(error)
        if "PGRST205" in message or "Could not find the table" in message:
            st.error(
                "As tabelas do aplicativo ainda não estão disponíveis no Supabase. "
                "Execute novamente o conteúdo de `schema.sql` no SQL Editor do "
                "mesmo projeto configurado nos Secrets e recarregue o app."
            )
        elif "PGRST202" in message or "get_default_shopping_list" in message:
            st.error(
                "O banco ainda não foi atualizado para o modo de lista única. "
                "Execute novamente o conteúdo atualizado de `schema.sql` no "
                "Supabase → SQL Editor e depois reinicie o app."
            )
        else:
            st.error(f"Erro ao acessar o Supabase: {error}")
        st.stop()
