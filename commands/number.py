"""
Number command - Shows all payment gateway numbers
Supports: bkash, nagad, rocket, upay
Commands:
  (prefix)number          - Show all gateway numbers
  (prefix)setbkash        - Add a bkash number (interactive)
  (prefix)setnagad        - Add a nagad number (interactive)
  (prefix)setrocket       - Add a rocket number (interactive)
  (prefix)setupay         - Add a upay number (interactive)
  (prefix)delbkash <num>  - Delete a bkash number
  (prefix)delnagad <num>  - Delete a nagad number
  (prefix)delrocket <num> - Delete a rocket number
  (prefix)delupay <num>   - Delete a upay number
"""

import os
import json
import asyncio

# JSON file path for persistent storage
DATA_FILE = "gateway_numbers.json"

# Account type map
ACCOUNT_TYPES = {
    "1": "Personal",
    "2": "Merchant",
    "3": "Agent"
}

# Gateway display names (small caps style)
GATEWAY_DISPLAY = {
    "bkash":  "Bᴋᴀsʜ",
    "nagad":  "Nᴀɢᴀᴅ",
    "rocket": "Rᴏᴄᴋᴇᴛ",
    "upay":   "Uᴘᴀʏ",
}

# ── JSON helpers ──────────────────────────────────────────────────────────────

def load_data() -> dict:
    """Load gateway data from JSON file."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {gw: [] for gw in GATEWAY_DISPLAY}


def save_data(data: dict):
    """Save gateway data to JSON file."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_entry(gateway: str, number: str, account_type: str):
    """Add a number entry to a gateway."""
    data = load_data()
    if gateway not in data:
        data[gateway] = []
    data[gateway].append({"number": number, "type": account_type})
    save_data(data)


def delete_entry(gateway: str, number: str) -> bool:
    """Delete a number from a gateway. Returns True if found and deleted."""
    data = load_data()
    original = data.get(gateway, [])
    filtered = [e for e in original if e["number"] != number]
    if len(filtered) == len(original):
        return False
    data[gateway] = filtered
    save_data(data)
    return True


# ── Conversation state (in-memory per user) ───────────────────────────────────

# { user_id: {"gateway": str, "number": str, "step": "type"} }
pending = {}

# ── Register ──────────────────────────────────────────────────────────────────

def register(client, prefix):
    """Register number command and all gateway set/delete commands."""

    from telethon import events

    ADMIN_IDS = [
        int(i.strip())
        for i in os.getenv("ADMIN_IDS", "").split(",")
        if i.strip()
    ]

    # ── Admin guard ────────────────────────────────────────────────────────────

    async def is_admin(event) -> bool:
        sender = await event.get_sender()
        if sender.id not in ADMIN_IDS:
            await event.respond("✗ Tʜɪs Cᴏᴍᴍᴀɴᴅ Is Oɴʟʏ Fᴏʀ Aᴅᴍɪɴs.")
            await event.delete()
            return False
        return True

    # ── (prefix)number ─────────────────────────────────────────────────────────

    @client.on(events.NewMessage(pattern=rf"^{prefix}number$"))
    async def number_handler(event):
        """Show all gateway numbers."""
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
                        lines.append(f"➤ {e['number']}  [{e['type']}]")
                else:
                    lines.append("➤ Not Set")
                lines.append("")

            await event.respond("\n".join(lines).strip())
            await event.delete()

        except Exception as e:
            await event.respond(f"✗ Eʀʀᴏʀ: {e}")

    # ── (prefix)set<gateway> <number> ─────────────────────────────────────────

    async def handle_set(event, gateway: str):
        """Start the set flow for a gateway."""
        try:
            if not await is_admin(event):
                return

            sender = await event.get_sender()
            parts = event.raw_text.strip().split(maxsplit=1)

            if len(parts) < 2:
                await event.respond(
                    f"✗ Usage: `{prefix}set{gateway} <number>`\n"
                    f"Example: `{prefix}set{gateway} 01XXXXXXXXX`"
                )
                await event.delete()
                return

            number = parts[1].strip()

            # Save state, ask for account type
            pending[sender.id] = {"gateway": gateway, "number": number, "step": "type"}

            await event.respond(
                f"📋 **Select account type for** `{number}`:\n\n"
                "1️⃣ Personal\n"
                "2️⃣ Merchant\n"
                "3️⃣ Agent\n\n"
                "Reply with **1**, **2**, or **3**."
            )
            await event.delete()

        except Exception as e:
            await event.respond(f"✗ Eʀʀᴏʀ: {e}")

    # Register set commands for each gateway
    for gw in GATEWAY_DISPLAY:
        _gw = gw  # capture

        @client.on(events.NewMessage(pattern=rf"^{prefix}set{_gw}(\s+.*)?$"))
        async def _set_handler(event, _gateway=_gw):
            await handle_set(event, _gateway)

    # ── Conversation reply handler (1/2/3) ─────────────────────────────────────

    @client.on(events.NewMessage())
    async def conversation_handler(event):
        """Handle the account-type reply in the set flow."""
        try:
            sender = await event.get_sender()
            uid = sender.id

            if uid not in pending:
                return
            if pending[uid]["step"] != "type":
                return

            text = event.raw_text.strip()
            if text not in ACCOUNT_TYPES:
                await event.respond("✗ Please reply with **1**, **2**, or **3** only.")
                return

            state = pending.pop(uid)
            gateway = state["gateway"]
            number = state["number"]
            account_type = ACCOUNT_TYPES[text]

            add_entry(gateway, number, account_type)

            display = GATEWAY_DISPLAY[gateway]
            await event.respond(
                f"✅ **Saved!**\n\n"
                f"Gateway : {display}\n"
                f"Number  : `{number}`\n"
                f"Type    : {account_type}"
            )

        except Exception as e:
            await event.respond(f"✗ Eʀʀᴏʀ: {e}")

    # ── (prefix)del<gateway> <number> ─────────────────────────────────────────

    async def handle_delete(event, gateway: str):
        """Delete a number from a gateway."""
        try:
            if not await is_admin(event):
                return

            parts = event.raw_text.strip().split(maxsplit=1)
            if len(parts) < 2:
                await event.respond(
                    f"✗ Usage: `{prefix}del{gateway} <number>`\n"
                    f"Example: `{prefix}del{gateway} 01XXXXXXXXX`"
                )
                await event.delete()
                return

            number = parts[1].strip()
            deleted = delete_entry(gateway, number)
            display = GATEWAY_DISPLAY[gateway]

            if deleted:
                await event.respond(f"🗑️ Deleted `{number}` from {display}.")
            else:
                await event.respond(f"✗ `{number}` not found in {display}.")

            await event.delete()

        except Exception as e:
            await event.respond(f"✗ Eʀʀᴏʀ: {e}")

    # Register delete commands for each gateway
    for gw in GATEWAY_DISPLAY:
        _gw = gw  # capture

        @client.on(events.NewMessage(pattern=rf"^{prefix}del{_gw}(\s+.*)?$"))
        async def _del_handler(event, _gateway=_gw):
            await handle_delete(event, _gateway)
