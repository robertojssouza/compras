# Lista de compras colaborativa

Aplicação em Python/Streamlit com dados persistentes no Supabase PostgreSQL. O app usa uma única lista compartilhada, carregada automaticamente, com login por nome de usuário e senha e usuários autorizados pelo administrador.

## Configuração local

Crie o arquivo `.streamlit/secrets.toml`:

```toml
SUPABASE_URL = "https://seu-projeto.supabase.co"
SUPABASE_ANON_KEY = "sua-chave-publica"
```

Use a URL e a chave pública `anon`/`publishable` em **Project Settings > API**. Nunca use a chave `service_role`.

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

Antes da primeira execução do SQL, altere `CHANGE-ME-BEFORE-RUN` para um código administrativo secreto e substitua o usuário inicial no `schema.sql`. O código permite abrir a aba **Administração**, onde é possível adicionar, ativar, desativar e remover usuários autorizados, além de visualizar e excluir listas.

## Configurar o login direto

No Supabase, abra **Authentication → Sign In / Providers → Email** e mantenha o provedor de e-mail ativado. Como o app usa um identificador interno (`nome@users.local`), desative **Confirm email** em **Authentication → Configuration → Sign In / Providers → Email**. O app oferece as abas **Entrar** e **Criar conta**; o usuário informa apenas nome e senha. Após o cadastro, o administrador precisa autorizar o nome de usuário na aba **Administração** antes que a pessoa consiga usar a lista.

## Publicar no Streamlit Community Cloud

1. Publique o projeto em um repositório GitHub.
2. Crie um app no Streamlit Community Cloud apontando para `app.py`.
3. Em **Settings > Secrets**, adicione:

```toml
SUPABASE_URL = "https://seu-projeto.supabase.co"
SUPABASE_ANON_KEY = "sua-chave-publica"
```

O arquivo local `.streamlit/secrets.toml` está protegido pelo `.gitignore`.
