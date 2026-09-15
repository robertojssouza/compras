create extension if not exists pgcrypto;

create table if not exists public.shopping_lists (
  id uuid primary key default gen_random_uuid(),
  name text not null default 'Lista de compras',
  invite_code text not null unique,
  created_at timestamptz not null default now()
);

create table if not exists public.shopping_items (
  id uuid primary key default gen_random_uuid(),
  list_id uuid not null references public.shopping_lists(id) on delete cascade,
  name text not null check (char_length(trim(name)) between 1 and 200),
  quantity text not null default '1' check (char_length(trim(quantity)) between 1 and 50),
  is_purchased boolean not null default false,
  created_by text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists shopping_items_list_id_idx
  on public.shopping_items(list_id);

create table if not exists public.app_settings (
  id boolean primary key default true check (id),
  admin_code text not null
);

create table if not exists public.authorized_accounts (
  id uuid primary key default gen_random_uuid(),
  email text not null unique check (email = lower(trim(email))),
  username text,
  active boolean not null default true,
  note text,
  created_at timestamptz not null default now()
);

alter table public.authorized_accounts
  add column if not exists username text;
update public.authorized_accounts
set username = lower(split_part(email, '@', 1))
where username is null;
create unique index if not exists authorized_accounts_username_idx
  on public.authorized_accounts(username)
  where username is not null;

insert into public.app_settings (id, admin_code)
values (true, 'CHANGE-ME-BEFORE-RUN')
on conflict (id) do nothing;

-- Substitua o e-mail abaixo pelo primeiro administrador antes de executar.
insert into public.authorized_accounts (email, username, note)
values (
  'first-admin@example.com',
  lower(split_part('first-admin@example.com', '@', 1)),
  'Substitua este nome pelo primeiro usuário'
)
on conflict (email) do nothing;

alter table public.shopping_lists enable row level security;
alter table public.shopping_items enable row level security;
alter table public.authorized_accounts enable row level security;

drop policy if exists "Anyone can read shopping lists" on public.shopping_lists;
drop policy if exists "Anyone can create shopping lists" on public.shopping_lists;
drop policy if exists "Anyone can read shopping items" on public.shopping_items;
drop policy if exists "Anyone can create shopping items" on public.shopping_items;
drop policy if exists "Anyone can update shopping items" on public.shopping_items;
drop policy if exists "Anyone can delete shopping items" on public.shopping_items;

create or replace function public.is_authorized_account()
returns boolean
language sql
security definer
stable
set search_path = public
as $$
  select exists (
    select 1
    from public.authorized_accounts
    where username = lower(split_part(
      trim(coalesce(auth.jwt() ->> 'email', '')), '@', 1
    ))
      and active
  )
$$;

create or replace function public.require_authorized_account()
returns void
language plpgsql
security definer
stable
set search_path = public
as $$
begin
  if auth.uid() is null or not public.is_authorized_account() then
    raise exception 'Conta não autorizada';
  end if;
end;
$$;

-- As tabelas não são acessadas diretamente pelo cliente. As funções abaixo
-- validam o código da lista antes de executar cada operação.
create or replace function public.create_shopping_list(list_name text)
returns public.shopping_lists
language plpgsql
security definer
set search_path = public
as $$
declare
  new_list public.shopping_lists;
begin
  perform public.require_authorized_account();
  insert into public.shopping_lists (name, invite_code)
  values (
    coalesce(nullif(trim(list_name), ''), 'Lista de compras'),
    upper(substr(replace(gen_random_uuid()::text, '-', ''), 1, 8))
  )
  returning * into new_list;
  return new_list;
end;
$$;

create or replace function public.get_shopping_list(code text)
returns public.shopping_lists
language sql
security definer
set search_path = public
as $$
  select * from public.shopping_lists
  where invite_code = upper(trim(code))
    and public.is_authorized_account()
  limit 1
$$;

create or replace function public.get_default_shopping_list()
returns public.shopping_lists
language plpgsql
security definer
set search_path = public
as $$
declare
  default_list public.shopping_lists;
begin
  perform public.require_authorized_account();
  select * into default_list
  from public.shopping_lists
  order by created_at asc
  limit 1;
  if default_list.id is null then
    insert into public.shopping_lists (name, invite_code)
    values ('Lista de compras', upper(substr(replace(gen_random_uuid()::text, '-', ''), 1, 8)))
    returning * into default_list;
  end if;
  return default_list;
end;
$$;

create or replace function public.list_shopping_items(code text)
returns setof public.shopping_items
language sql
security definer
set search_path = public
as $$
  select item.*
  from public.shopping_items item
  join public.shopping_lists list on list.id = item.list_id
  where list.invite_code = upper(trim(code))
    and public.is_authorized_account()
  order by item.is_purchased asc, item.created_at asc
$$;

create or replace function public.add_shopping_item(
  code text, item_name text, item_quantity text, creator text
)
returns public.shopping_items
language plpgsql
security definer
set search_path = public
as $$
declare
  target_list_id uuid;
  new_item public.shopping_items;
begin
  perform public.require_authorized_account();
  select id into target_list_id from public.shopping_lists
  where invite_code = upper(trim(code));
  if target_list_id is null then raise exception 'Código de convite inválido'; end if;
  insert into public.shopping_items (list_id, name, quantity, created_by)
  values (target_list_id, trim(item_name), trim(item_quantity), trim(creator))
  returning * into new_item;
  return new_item;
end;
$$;

create or replace function public.set_shopping_item_purchased(
  code text, item_id uuid, purchased boolean
)
returns public.shopping_items
language plpgsql
security definer
set search_path = public
as $$
declare
  updated_item public.shopping_items;
begin
  perform public.require_authorized_account();
  update public.shopping_items item
  set is_purchased = purchased, updated_at = now()
  where item.id = item_id
    and item.list_id = (select id from public.shopping_lists
                        where invite_code = upper(trim(code)))
  returning * into updated_item;
  if updated_item.id is null then raise exception 'Item não encontrado'; end if;
  return updated_item;
end;
$$;

create or replace function public.delete_shopping_item(code text, item_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  perform public.require_authorized_account();
  delete from public.shopping_items item
  where item.id = item_id
    and item.list_id = (select id from public.shopping_lists
                        where invite_code = upper(trim(code)));
  if not found then raise exception 'Item não encontrado'; end if;
end;
$$;

create or replace function public.list_all_shopping_lists(p_admin_code text)
returns setof public.shopping_lists
language plpgsql
security definer
set search_path = public
as $$
begin
  perform public.require_authorized_account();
  if not exists (select 1 from public.app_settings where app_settings.admin_code = p_admin_code) then
    raise exception 'Código administrativo inválido';
  end if;
  return query select * from public.shopping_lists order by created_at desc;
end;
$$;

create or replace function public.delete_shopping_list(p_admin_code text, target_list_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  perform public.require_authorized_account();
  if not exists (select 1 from public.app_settings where app_settings.admin_code = p_admin_code) then
    raise exception 'Código administrativo inválido';
  end if;
  delete from public.shopping_lists where id = target_list_id;
  if not found then raise exception 'Lista não encontrada'; end if;
end;
$$;

create or replace function public.list_authorized_accounts(p_admin_code text)
returns setof public.authorized_accounts
language plpgsql
security definer
set search_path = public
as $$
begin
  perform public.require_authorized_account();
  if not exists (select 1 from public.app_settings where admin_code = p_admin_code) then
    raise exception 'Código administrativo inválido';
  end if;
  return query select * from public.authorized_accounts order by username;
end;
$$;

create or replace function public.add_authorized_account(
  p_admin_code text, account_username text, account_note text default null
)
returns public.authorized_accounts
language plpgsql
security definer
set search_path = public
as $$
declare
  new_account public.authorized_accounts;
  normalized_username text := lower(trim(account_username));
begin
  perform public.require_authorized_account();
  if not exists (select 1 from public.app_settings where admin_code = p_admin_code) then
    raise exception 'Código administrativo inválido';
  end if;
  if normalized_username !~ '^[a-z0-9][a-z0-9._-]{2,29}$' then
    raise exception 'Nome de usuário inválido';
  end if;
  insert into public.authorized_accounts (email, username, note)
  values (
    normalized_username || '@users.local',
    normalized_username,
    nullif(trim(account_note), '')
  )
  returning * into new_account;
  return new_account;
exception
  when unique_violation then
    raise exception 'E-mail já cadastrado';
end;
$$;

create or replace function public.set_authorized_account_active(
  p_admin_code text, account_id uuid, is_active boolean
)
returns public.authorized_accounts
language plpgsql
security definer
set search_path = public
as $$
declare
  updated_account public.authorized_accounts;
begin
  perform public.require_authorized_account();
  if not exists (select 1 from public.app_settings where admin_code = p_admin_code) then
    raise exception 'Código administrativo inválido';
  end if;
  update public.authorized_accounts
  set active = is_active
  where id = account_id
  returning * into updated_account;
  if updated_account.id is null then
    raise exception 'Conta não encontrada';
  end if;
  return updated_account;
end;
$$;

create or replace function public.delete_authorized_account(
  p_admin_code text, account_id uuid
)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  perform public.require_authorized_account();
  if not exists (select 1 from public.app_settings where admin_code = p_admin_code) then
    raise exception 'Código administrativo inválido';
  end if;
  delete from public.authorized_accounts where id = account_id;
  if not found then
    raise exception 'Conta não encontrada';
  end if;
end;
$$;

revoke all on public.shopping_lists from anon, authenticated;
revoke all on public.shopping_items from anon, authenticated;
revoke all on public.app_settings from anon, authenticated;
revoke all on public.authorized_accounts from anon, authenticated;
grant execute on function public.is_authorized_account() to anon, authenticated;
grant execute on function public.require_authorized_account() to anon, authenticated;
grant execute on function public.create_shopping_list(text) to anon, authenticated;
grant execute on function public.get_shopping_list(text) to anon, authenticated;
grant execute on function public.get_default_shopping_list() to anon, authenticated;
grant execute on function public.list_shopping_items(text) to anon, authenticated;
grant execute on function public.add_shopping_item(text, text, text, text) to anon, authenticated;
grant execute on function public.set_shopping_item_purchased(text, uuid, boolean) to anon, authenticated;
grant execute on function public.delete_shopping_item(text, uuid) to anon, authenticated;
grant execute on function public.list_all_shopping_lists(text) to anon, authenticated;
grant execute on function public.delete_shopping_list(text, uuid) to anon, authenticated;
grant execute on function public.list_authorized_accounts(text) to anon, authenticated;
grant execute on function public.add_authorized_account(text, text, text) to anon, authenticated;
grant execute on function public.set_authorized_account_active(text, uuid, boolean) to anon, authenticated;
grant execute on function public.delete_authorized_account(text, uuid) to anon, authenticated;
revoke execute on function public.create_shopping_list(text) from anon, authenticated;
