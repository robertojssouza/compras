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

insert into public.app_settings (id, admin_code)
values (true, 'CHANGE-ME-BEFORE-RUN')
on conflict (id) do nothing;

alter table public.shopping_lists enable row level security;
alter table public.shopping_items enable row level security;

drop policy if exists "Anyone can read shopping lists" on public.shopping_lists;
drop policy if exists "Anyone can create shopping lists" on public.shopping_lists;
drop policy if exists "Anyone can read shopping items" on public.shopping_items;
drop policy if exists "Anyone can create shopping items" on public.shopping_items;
drop policy if exists "Anyone can update shopping items" on public.shopping_items;
drop policy if exists "Anyone can delete shopping items" on public.shopping_items;

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
  limit 1
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
  if not exists (select 1 from public.app_settings where app_settings.admin_code = p_admin_code) then
    raise exception 'Código administrativo inválido';
  end if;
  delete from public.shopping_lists where id = target_list_id;
  if not found then raise exception 'Lista não encontrada'; end if;
end;
$$;

revoke all on public.shopping_lists from anon, authenticated;
revoke all on public.shopping_items from anon, authenticated;
revoke all on public.app_settings from anon, authenticated;
grant execute on function public.create_shopping_list(text) to anon, authenticated;
grant execute on function public.get_shopping_list(text) to anon, authenticated;
grant execute on function public.list_shopping_items(text) to anon, authenticated;
grant execute on function public.add_shopping_item(text, text, text, text) to anon, authenticated;
grant execute on function public.set_shopping_item_purchased(text, uuid, boolean) to anon, authenticated;
grant execute on function public.delete_shopping_item(text, uuid) to anon, authenticated;
grant execute on function public.list_all_shopping_lists(text) to anon, authenticated;
grant execute on function public.delete_shopping_list(text, uuid) to anon, authenticated;
