# Lista de compras colaborativa

Aplicação em Python/Streamlit com dados persistentes no Supabase PostgreSQL. O app usa uma única lista compartilhada, carregada automaticamente, com login Google e contas autorizadas pelo administrador.

## Configuração local

Crie o arquivo `.streamlit/secrets.toml`:

```toml
SUPABASE_URL = "https://seu-projeto.supabase.co"
SUPABASE_ANON_KEY = "sua-chave-publica"
SUPABASE_REDIRECT_URL = "https://seu-app.streamlit.app"
```

Use a URL e a chave pública `anon`/`publishable` em **Project Settings > API**. Nunca use a chave `service_role`. `SUPABASE_REDIRECT_URL` deve ser a URL pública exata do app Streamlit.

Instale e execute:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Configurar o banco

Execute o conteúdo de [`schema.sql`](./schema.sql) em **Supabase > SQL Editor > New query**. Se você já executou uma versão anterior, execute o arquivo novamente para atualizar as funções e bloquear o acesso direto às tabelas.

O app usa funções RPC que validam a sessão do Supabase Auth e a conta autorizada. As tabelas não ficam expostas diretamente ao cliente.

O app cria a lista padrão automaticamente apenas se ainda não existir. Não há opção de criar ou trocar de lista na interface.

Se aparecer o erro `PGRST202` mencionando `get_default_shopping_list`, execute novamente o `schema.sql` atualizado no SQL Editor do Supabase e use **Reboot app** no Streamlit Cloud.

Antes da primeira execução do SQL, altere `CHANGE-ME-BEFORE-RUN` para um código administrativo secreto e substitua `first-admin@example.com` pelo primeiro e-mail Google autorizado. O código permite abrir a aba **Administração**, onde é possível adicionar, ativar, desativar e remover contas autorizadas, além de visualizar e excluir listas.

## Configurar o login Google

1. No Supabase, abra **Authentication > Providers > Google** e ative o provedor.
2. Crie um OAuth Client ID do tipo **Web application** no Google Cloud.
3. Use como callback autorizado a URL exibida pelo Supabase em **Authentication > URL Configuration**, normalmente:
   `https://SEU-PROJETO.supabase.co/auth/v1/callback`.
4. Cadastre o Client ID e o Client Secret no provedor Google do Supabase.
5. Em **Authentication > URL Configuration**, adicione também a URL do app Streamlit em **Redirect URLs**.
6. Configure `SUPABASE_REDIRECT_URL` com essa mesma URL no Streamlit Cloud e localmente.

Depois de executar o SQL e configurar o primeiro e-mail, abra o app, entre com a conta Google autorizada e use a aba **Administração** com o código administrativo.

## Publicar no Streamlit Community Cloud

1. Publique o projeto em um repositório GitHub.
2. Crie um app no Streamlit Community Cloud apontando para `app.py`.
3. Em **Settings > Secrets**, adicione:

```toml
SUPABASE_URL = "https://seu-projeto.supabase.co"
SUPABASE_ANON_KEY = "sua-chave-publica"
SUPABASE_REDIRECT_URL = "https://seu-app.streamlit.app"
```

O arquivo local `.streamlit/secrets.toml` está protegido pelo `.gitignore`.
