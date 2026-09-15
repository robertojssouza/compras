import os
from typing import Any

import streamlit as st
from streamlit_autorefresh import st_autorefresh
from supabase import Client, create_client


st.set_page_config(page_title="Lista de compras", page_icon="🛒", layout="wide")

st.markdown(
    """
    <style>
    .stAppViewContainer .main .block-container {
        padding-top: 0rem;
    }
    header {
            visibility: hidden;
            height: 0vh;
        }
        .block-container {
            padding-top: 0rem;
        }
        
    @media (max-width: 640px) {
        .stAppViewContainer .main .block-container {
            padding-top: 0 !important;
        }
        .stAppViewContainer .main .block-container > div:first-child {
            margin-top: 0 !important;
        }
    }
    div[data-testid="stHorizontalBlock"] {
        gap: 0.35rem;
        align-items: center;
    }
    div[data-testid="stHorizontalBlock"]:has(input[type="checkbox"]) {
        background: #f5f7f5;
        border: 1px solid #dce5dc;
        border-radius: 0;
        padding: 0 0.2rem;
        margin-bottom: 0;
        margin-top: 0;
        min-height: 0;
        align-items: center;
    }
    .st-key-items-table [data-testid="stVerticalBlock"] {
        gap: 0;
        margin: 0;
        padding: 0;
    }
    .st-key-items-table [data-testid="stHorizontalBlock"] {
        margin: 0;
        gap: 0.25rem !important;
        flex-wrap: nowrap !important;
    }
    .st-key-items-table [class*="st-key-item-row-"] {
        display: flex;
        align-items: center;
        gap: 0.25rem !important;
        flex-wrap: nowrap !important;
    }
    .st-key-items-table [class*="st-key-item-action-"] {
        flex: 0 0 auto !important;
        width: auto !important;
    }
    .st-key-items-table [class*="st-key-item-name-"] {
        flex: 1 1 auto !important;
        min-width: 0 !important;
        width: auto !important;
    }
    .st-key-items-table [class*="st-key-item-delete-"] {
        flex: 0 0 36px !important;
        width: 36px !important;
    }
    @media (max-width: 640px) {
        .st-key-items-table [class*="st-key-item-row-"] {
            gap: 0 !important;
        }
        .st-key-items-table [class*="st-key-item-action-"] {
            margin-right: 0 !important;
        }
        .st-key-items-table [class*="st-key-item-name-"] {
            flex: 1 1 0 !important;
            margin: 0 !important;
        }
        .st-key-items-table [class*="st-key-item-delete-"] {
            flex: 0 0 30px !important;
            width: 30px !important;
            position: relative;
            left: 0.6rem;
        }
    }
    .st-key-items-table [data-testid="stMarkdownContainer"] {
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
    }
    div[data-testid="stHorizontalBlock"]:has(input[type="checkbox"])
    div[data-testid="column"] > div:first-child {
        margin-top: 0;
        margin-bottom: 0;
    }
    div[data-testid="stHorizontalBlock"]:has(input[type="checkbox"])
    div[data-testid="stCheckbox"] {
        min-height: 1.4rem;
        padding: 0;
    }
    .st-key-items-table [data-testid="stButton"] button {
        min-height: 1.4rem;
        padding: 0.15rem 0.45rem;
        font-size: 0.8rem;
        white-space: nowrap;
    }
    @media (max-width: 640px) {
        .st-key-items-table [class*="st-key-item-action-"] button {
            padding: 0.1rem 0.2rem !important;
            font-size: 0.7rem !important;
        }
        .st-key-items-table [class*="st-key-item-delete-"] button {
            padding: 0 !important;
            font-size: 0.9rem !important;
        }
    }
    .st-key-items-table [class*="st-key-buy-"] button {
        color: #ffffff;
        border-color: #15803d;
        background: #16a34a;
    }
    .st-key-items-table [class*="st-key-undo-"] button {
        color: #ffffff;
        border-color: #c2410c;
        background: #ea580c;
    }
    .st-key-items-table [class*="st-key-delete-"] button {
        color: #b42318;
        border-color: #fca5a5;
        background: #fef2f2;
    }
    div[data-testid="stHorizontalBlock"]:has(input[type="checkbox"]) p {
        margin: 0;
        line-height: 1.4rem;
    }
    div[data-testid="stHorizontalBlock"]:has(input[type="checkbox"])
    div[data-testid="stMarkdownContainer"] {
        padding: 0;
        margin: 0;
    }
    div[data-testid="stHorizontalBlock"]:has(input[type="checkbox"]) button {
        padding: 0;
        min-height: 0;
        height: 1.4rem;
        border: 0;
        background: transparent;
        color: #b42318;
        font-size: 1rem;
        line-height: 1;
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
    list_id = active_list["id"]
    st.subheader("Adicionar produto")
    with st.form("add_item", clear_on_submit=True):
        name = st.text_input("Produto", placeholder="Ex.: arroz")
        quantity = st.text_input("Quantidade", value="1")
        if st.form_submit_button("Adicionar", type="primary"):
            if not name.strip() or not quantity.strip():
                st.error("Informe o produto e a quantidade.")
            else:
                client.rpc("add_shopping_item", {
                    "code": active_list["invite_code"],
                    "item_name": name.strip(),
                    "item_quantity": quantity.strip(),
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
            with st.container(
                horizontal=True,
                horizontal_alignment="left",
                vertical_alignment="center",
                gap="small",
                key=f"item-row-{item['id']}",
            ):
                action_label = "Desfazer" if item["is_purchased"] else "Comprar"
                action_key = "undo" if item["is_purchased"] else "buy"
                with st.container(key=f"item-action-{item['id']}"):                             
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
                label = (
                    f"~~{item['name']} · {item['quantity']}~~"
                    if item["is_purchased"]
                    else f"**{item['name']}** · {item['quantity']}"
                )
                with st.container(key=f"item-name-{item['id']}"):                
                    st.markdown(label)
                with st.container(key=f"item-delete-{item['id']}"):                
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
    #st.caption("Dados persistidos no Supabase · atualização automática a cada 5 segundos")
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
