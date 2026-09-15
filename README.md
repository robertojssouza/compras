# Lista de compras colaborativa

Aplicação em Python/Streamlit com dados persistentes no Supabase PostgreSQL. O app usa uma única lista compartilhada, carregada automaticamente, sem exigir login, nome ou código de convite.

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

**Importante após remover a autenticação:** se aparecer `Conta não autorizada`, o banco ainda está usando as RPCs antigas. Execute novamente todo o `schema.sql` no SQL Editor, clique em **Run** e depois execute:

```sql
notify pgrst, 'reload schema';
```

Por fim, use **Reboot app** no Streamlit Cloud. Isso atualiza as funções do banco para aceitar contribuições sem login.

O app usa funções RPC que recebem o código da lista. As tabelas não ficam expostas diretamente ao cliente.

O app cria a lista padrão automaticamente apenas se ainda não existir. Não há opção de criar ou trocar de lista na interface.

Se aparecer o erro `PGRST202` mencionando `get_default_shopping_list`, execute novamente o `schema.sql` atualizado no SQL Editor do Supabase e use **Reboot app** no Streamlit Cloud.

Na primeira execução do SQL, altere `CHANGE-ME-BEFORE-RUN` para um código administrativo secreto antes de clicar em **Run**. Esse código aparece no painel **Administração de listas** do app e permite visualizar e excluir listas. A exclusão remove também todos os produtos da lista.

## Publicar no Streamlit Community Cloud

1. Publique o projeto em um repositório GitHub.
2. Crie um app no Streamlit Community Cloud apontando para `app.py`.
3. Em **Settings > Secrets**, adicione:

```toml
SUPABASE_URL = "https://seu-projeto.supabase.co"
SUPABASE_ANON_KEY = "sua-chave-publica"
```

O arquivo local `.streamlit/secrets.toml` está protegido pelo `.gitignore`.
