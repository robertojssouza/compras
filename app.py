import os
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import streamlit as st
from streamlit_autorefresh import st_autorefresh
from supabase import Client, create_client
from supabase_auth.helpers import generate_pkce_challenge, generate_pkce_verifier


st.set_page_config(page_title="Lista de compras", page_icon="🛒", layout="centered")

st.markdown(
    """
    <style>
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


def get_redirect_url() -> str:
    configured_url = os.getenv("SUPABASE_REDIRECT_URL", "")
    if not configured_url:
        try:
            configured_url = str(st.secrets.get("SUPABASE_REDIRECT_URL", ""))
        except FileNotFoundError:
            configured_url = ""
    if configured_url:
        return configured_url.rstrip("/")

    headers = st.context.headers
    host = headers.get("X-Forwarded-Host") or headers.get("Host")
    if host:
        protocol = headers.get("X-Forwarded-Proto", "https").split(",")[0].strip()
        return f"{protocol}://{host}".rstrip("/")
    return "http://localhost:8501"


def get_oauth_redirect_url(verifier: str | None = None) -> str:
    redirect_url = get_redirect_url()
    if not verifier:
        return redirect_url
    parts = urlsplit(redirect_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["oauth_verifier"] = verifier
    return urlunsplit((
        parts.scheme,
        parts.netloc,
        parts.path,
        urlencode(query),
        parts.fragment,
    ))


def get_supabase() -> Client:
    return create_client(setting("SUPABASE_URL"), setting("SUPABASE_ANON_KEY"))


def restore_auth_session(client: Client) -> dict[str, Any] | None:
    access_token = st.session_state.get("access_token")
    refresh_token = st.session_state.get("refresh_token")
    if access_token and refresh_token:
        client.auth.set_session(access_token, refresh_token)

    auth_code = st.query_params.get("code")
    if auth_code:
        code_verifier = st.query_params.get("oauth_verifier")
        if not code_verifier:
            st.query_params.clear()
            st.session_state.auth_error = (
                "A sessão de login expirou antes de ser concluída. "
                "Clique novamente em Entrar com Google."
            )
            st.rerun()
        response = client.auth.exchange_code_for_session({
            "auth_code": auth_code,
            "code_verifier": code_verifier,
            "redirect_to": get_oauth_redirect_url(code_verifier),
        })
        if response.session is None or response.user is None:
            raise RuntimeError("Não foi possível concluir o login Google.")
        st.session_state.access_token = response.session.access_token
        st.session_state.refresh_token = response.session.refresh_token
        st.session_state.user_email = response.user.email
        st.query_params.clear()
        st.rerun()

    if not st.session_state.get("user_email"):
        return None
    authorized = client.rpc("is_authorized_account").execute().data
    if not authorized:
        return {"email": st.session_state.user_email, "authorized": False}
    return {"email": st.session_state.user_email, "authorized": True}


def render_login(client: Client) -> None:
    st.title("🛒 Lista de compras")
    st.subheader("Entrar")
    auth_error = st.session_state.pop("auth_error", None)
    if auth_error:
        st.warning(auth_error)
    st.write("Use sua conta Google para acessar a lista compartilhada.")
    verifier = generate_pkce_verifier()
    challenge = generate_pkce_challenge(verifier)
    redirect_url = get_oauth_redirect_url(verifier)
    oauth_url = f"{client.auth._url}/authorize?" + urlencode({
        "provider": "google",
        "redirect_to": redirect_url,
        "code_challenge": challenge,
        "code_challenge_method": "s256",
    })
    st.link_button("Entrar com Google", oauth_url, type="primary")


def render_account_blocked(email: str) -> None:
    st.title("Acesso pendente")
    st.warning(
        f"A conta `{email}` ainda não foi autorizada pelo administrador."
    )
    st.info("Peça ao administrador para adicionar seu e-mail ao sistema.")
    if st.button("Sair", key="blocked-logout"):
        st.session_state.clear()
        st.rerun()


def render_user_bar(client: Client, email: str) -> None:
    st.caption(f"Conectado como {email}")
    if st.button("Sair", key="logout"):
        client.auth.sign_out()
        st.session_state.clear()
        st.rerun()


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
    st.subheader("Administração")
    admin_code = st.text_input(
        "Senha administrativa",
        type="password",
        value=st.session_state.get("admin_code", ""),
        key="admin-code-input",
    )
    if st.button("Entrar na administração", key="load-admin"):
        st.session_state.admin_code = admin_code
        st.session_state.admin_authenticated = False
        try:
            accounts_response = client.rpc(
                "list_authorized_accounts", {"p_admin_code": admin_code}
            ).execute()
            st.session_state.admin_accounts = accounts_response.data or []
            st.session_state.admin_authenticated = True
        except Exception as error:
            st.error(f"Não foi possível abrir a administração: {error}")
    if not st.session_state.get("admin_authenticated"):
        return
    admin_code = st.session_state["admin_code"]

    account_tab, list_tab = st.tabs(["Contas autorizadas", "Listas"])
    with account_tab:
        st.write("Somente e-mails cadastrados e ativos podem usar o sistema.")
        with st.form("add-authorized-account", clear_on_submit=True):
            account_email = st.text_input("E-mail Google")
            account_note = st.text_input("Observação (opcional)")
            if st.form_submit_button("Adicionar conta"):
                try:
                    response = client.rpc(
                        "add_authorized_account",
                        {
                            "p_admin_code": admin_code,
                            "account_email": account_email,
                            "account_note": account_note,
                        },
                    ).execute()
                    st.session_state.admin_accounts.append(response.data)
                    st.success("Conta autorizada.")
                except Exception as error:
                    st.error(f"Não foi possível adicionar a conta: {error}")

        for account in st.session_state.admin_accounts:
            state = "Ativa" if account["active"] else "Inativa"
            st.write(f"**{account['email']}** · {state}")
            if account.get("note"):
                st.caption(account["note"])
            action = "Desativar" if account["active"] else "Ativar"
            if st.button(action, key=f"toggle-account-{account['id']}"):
                try:
                    response = client.rpc(
                        "set_authorized_account_active",
                        {
                            "p_admin_code": admin_code,
                            "account_id": account["id"],
                            "is_active": not account["active"],
                        },
                    ).execute()
                    account.update(response.data)
                    st.rerun()
                except Exception as error:
                    st.error(f"Não foi possível alterar a conta: {error}")
            if st.button("Remover", key=f"remove-account-{account['id']}"):
                try:
                    client.rpc(
                        "delete_authorized_account",
                        {
                            "p_admin_code": admin_code,
                            "account_id": account["id"],
                        },
                    ).execute()
                    st.session_state.admin_accounts = [
                        item for item in st.session_state.admin_accounts
                        if item["id"] != account["id"]
                    ]
                    st.rerun()
                except Exception as error:
                    st.error(f"Não foi possível remover a conta: {error}")

    with list_tab:
        try:
            response = client.rpc(
                "list_all_shopping_lists", {"p_admin_code": admin_code}
            ).execute()
            lists = response.data or []
        except Exception as error:
            st.error(f"Não foi possível carregar as listas: {error}")
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
                    "p_admin_code": admin_code,
                    "target_list_id": shopping_list["id"],
                }).execute()
                if st.session_state.get("active_list", {}).get("id") == shopping_list["id"]:
                    st.session_state.pop("active_list")
                st.rerun()


def main() -> None:
    client = get_supabase()
    user = restore_auth_session(client)
    if user is None:
        render_login(client)
        return
    if not user["authorized"]:
        render_account_blocked(user["email"])
        return

    if "active_list" not in st.session_state:
        st.session_state.active_list = None
    st_autorefresh(interval=5000, key="shopping-list-refresh")
    st.title("🛒 Lista de compras")
    st.caption("Dados persistidos no Supabase · atualização automática a cada 5 segundos")
    render_user_bar(client, user["email"])
    active_list = st.session_state.get("active_list")
    if active_list is None:
        st.session_state.active_list = get_default_list(client)
        st.rerun()

    list_tab, admin_tab = st.tabs(["Lista de compras", "Administração"])
    with list_tab:
        render_items(client, active_list)
    with admin_tab:
        render_admin(client)


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
