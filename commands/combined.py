"""
Combined Number + Calculator command
"""

import os
import json
import re
import logging

DATA_FILE = "gateway_numbers.json"

ACCOUNT_TYPES = {"1": "Personal", "2": "Merchant", "3": "Agent"}

GATEWAY_DISPLAY = {
    "bkash":  "Bᴋᴀsʜ",
    "nagad":  "Nᴀɢᴀᴅ",
    "rocket": "Rᴏᴄᴋᴇᴛ",
    "upay":   "Uᴘᴀʏ",
}

pending = {}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {gw: [] for gw in GATEWAY_DISPLAY}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def add_entry(gateway, number, account_type):
    data = load_data()
    data.setdefault(gateway, []).append({"number": number, "type": account_type})
    save_data(data)

def delete_entry(gateway, number):
    data = load_data()
    original = data.get(gateway, [])
    filtered = [e for e in original if e["number"] != number]
    if len(filtered) == len(original):
        return False
    data[gateway] = filtered
    save_data(data)
    return True

def transform_percentage(expr):
    expr = expr.replace(" ", "")
    if '%' not in expr:
        return expr
    expr = re.sub(r'\*(\d+\.?\d*)%', r'*(\1/100)', expr)
    expr = re.sub(r'/(\d+\.?\d*)%', r'/(\1/100)', expr)
    def replace_pm(match):
        a, op, b = match.group(1), match.group(2), match.group(3)
        return f"{a}{op}({a}*{b}/100)"
    prev = ""
    while prev != expr:
        prev = expr
        expr = re.sub(r'(\d+\.?\d*)([+\-])(\d+\.?\d*)%', replace_pm, expr, count=1)
    expr = re.sub(r'(\d+\.?\d*)%', r'(\1/100)', expr)
    return expr

def safe_calculate(expression):
    expression = expression.replace(" ", "")
    if not expression:
        raise ValueError
    if not re.match(r'^[\d+\-*/().%]+$', expression):
        raise ValueError
    expression = transform_percentage(expression)
    clean = expression.replace('(-', '(0-').replace('--', '+')
    if clean.startswith('-'):
        clean = '0' + clean
    result = eval(clean, {"__builtins__": {}}, {})
    return result

def format_result(result):
    if isinstance(result, float):
        if result.is_integer():
            return "{:,}".format(int(result))
        return "{:,.6f}".format(round(result, 6)).rstrip('0').rstrip('.')
    return "{:,}".format(result)

def register(client, prefix):
    from telethon import events

    ADMIN_IDS = [int(i.strip()) for i in os.getenv("ADMIN_IDS", "").split(",") if i.strip()]

    async def get_allowed():
        me = await client.get_me()
        return set(ADMIN_IDS + [me.id])

    async def is_admin(event):
        try:
            allowed = await get_allowed()
            sender = await event.get_sender()
            return sender and sender.id in allowed
        except:
            return False

    async def is_allowed(event):
        try:
            if event.is_group or event.is_channel:
                allowed = await get_allowed()
                sender = await event.get_sender()
                return sender and sender.id in allowed
            return True
        except:
            return False

    # ── number ────────────────────────────────────────────────────────────────

    @client.on(events.NewMessage(pattern=rf"^{prefix}number$"))
    async def number_handler(event):
        try:
            if not await is_admin(event):
                return
            data = load_data()
            lines = []
            for gw, display in GATEWAY_DISPLAY.items():
                lines.append(display)
                lines.append("━━━━━━━━━━━━━━")
                entries = data.get(gw, [])
                if entries:
                    for e in entries:
                        lines.append(f"➤ `{e['number']}`  [{e['type']}]")
                else:
                    lines.append("➤ Not Set")
                lines.append("")
            await event.respond("\n".join(lines).strip())
        except:
            pass

    # ── set<gateway> ──────────────────────────────────────────────────────────

    async def handle_set(event, gateway):
        try:
            if not await is_admin(event):
                return
            parts = event.raw_text.strip().split(maxsplit=1)
            if len(parts) < 2:
                await event.respond(f"✗ Usage: `{prefix}set{gateway} <number>`")
                return
            sender = await event.get_sender()
            pending[sender.id] = {"gateway": gateway, "number": parts[1].strip(), "step": "type"}
            await event.respond(
                f"📋 **Select type for** `{parts[1].strip()}`:\n\n"
                "1️⃣ Personal\n2️⃣ Merchant\n3️⃣ Agent\n\nReply **1**, **2**, or **3**."
            )
        except:
            pass

    for gw in GATEWAY_DISPLAY:
        _gw = gw
        @client.on(events.NewMessage(pattern=rf"^{prefix}set{_gw}(\s+.*)?$"))
        async def _set(event, _g=_gw):
            await handle_set(event, _g)

    # ── conversation reply ────────────────────────────────────────────────────

    @client.on(events.NewMessage())
    async def conversation_handler(event):
        try:
            sender = await event.get_sender()
            if not sender or sender.id not in pending:
                return
            uid = sender.id
            if pending[uid]["step"] != "type":
                return
            text = event.raw_text.strip()
            if text not in ACCOUNT_TYPES:
                await event.respond("✗ Reply with **1**, **2**, or **3** only.")
                return
            state = pending.pop(uid)
            add_entry(state["gateway"], state["number"], ACCOUNT_TYPES[text])
            await event.respond(
                f"✅ **Saved!**\n\n"
                f"Gateway : {GATEWAY_DISPLAY[state['gateway']]}\n"
                f"Number  : `{state['number']}`\n"
                f"Type    : {ACCOUNT_TYPES[text]}"
            )
        except:
            pass

    # ── del<gateway> ──────────────────────────────────────────────────────────

    async def handle_delete(event, gateway):
        try:
            if not await is_admin(event):
                return
            parts = event.raw_text.strip().split(maxsplit=1)
            if len(parts) < 2:
                await event.respond(f"✗ Usage: `{prefix}del{gateway} <number>`")
                return
            number = parts[1].strip()
            if delete_entry(gateway, number):
                await event.respond(f"🗑️ Deleted `{number}` from {GATEWAY_DISPLAY[gateway]}.")
            else:
                await event.respond(f"✗ `{number}` not found in {GATEWAY_DISPLAY[gateway]}.")
        except:
            pass

    for gw in GATEWAY_DISPLAY:
        _gw = gw
        @client.on(events.NewMessage(pattern=rf"^{prefix}del{_gw}(\s+.*)?$"))
        async def _del(event, _g=_gw):
            await handle_delete(event, _g)

    # ── calculator ────────────────────────────────────────────────────────────

    @client.on(events.NewMessage(pattern=r'^([\d+\-*/().%\s]+)$'))
    async def calc_handler(event):
        try:
            if not await is_allowed(event):
                return
            expr = event.pattern_match.group(1).strip()
            if len(expr) < 3:
                return
            if not any(op in expr for op in ['+', '-', '*', '/', '%']):
                return
            result = safe_calculate(expr)
            await event.respond(
                f"✓ Cᴀʟᴄᴜʟᴀᴛɪᴏɴ Cᴏᴍᴘʟᴇᴛᴇ\n"
                f"➦Iɴᴘᴜᴛ : {expr}\n"
                f"➥Rᴇsᴜʟᴛ: {format_result(result)}\n"
                f"━━━━━━━━━━━━━━━━━━"
            )
        except:
            pass
