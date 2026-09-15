# Concatena o número digitado com a unidade selecionada
full_quantity = f"{qty_num.strip()} {qty_unit}"

# Envia o valor já formatado para o Supabase (ex: "2 kg", "500 g", "3 cx")
client.rpc("add_shopping_item", {
    "code": active_list["invite_code"],
    "item_name": name.strip(),
    "item_quantity": full_quantity,
    "creator": "contribuidor",
}).execute()
