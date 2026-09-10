import asyncio
import os
import sys
from telethon import TelegramClient, events, functions
from telethon.errors import FloodWaitError
from telethon.sessions import MemorySession, StringSession
from telethon.tl.types import InputUserEmpty

# --- CONFIGURATION ---
API_ID = 34612667
API_HASH = "2d3847194413eb15597238d7b51c4221"

BOT_TOKEN = os.getenv(
    "BOT_TOKEN", "8963158555:AAHObgPdHeafE8m4TYtkk6FfBl6jgjljefo"
)
USER_STRING_SESSION = os.getenv("STRING_SESSION", "1AZWarzwBu7y6UXeXwVyP1V3F1IdO_hPYOYJY_laq8V38be_Zg_TBEB4TWGhE7Sng-eQX9sh4V4bIrqOLBMK8o-6Ih7_bT74Unz4nBqUp-llTmKu7-URm8pxG13nJJRKH_OxvOTpgGLC9g82b7y10fUZ7NVSbOG7Ip2JLTvWIaXZvHj3kNKh4WEh-bH8NswdePqX8bajWz8G9QAt4KiPUoe7aRSk4LjWFbL2WFIMJj67F45Z7MrWz5h4lIn76p-MVYbOEWYymspb9Hfs55Oy5SDM8NyWpiNfK5VqfOzJdSx7sekA9gdV4c7qcoo6sUqWiBDS-wR6OLGsf7KTbtvihvM2jqmzL9lM=")

user_client = TelegramClient(
    StringSession(USER_STRING_SESSION), API_ID, API_HASH
)
bot_client = TelegramClient(MemorySession(), API_ID, API_HASH)

is_running = False
target_channel = None
saved_messages = []
processed_users = set()

# ==========================================
#           TELEGRAM BOT COMMANDS
# ==========================================


@bot_client.on(events.NewMessage(pattern="/start"))
async def start_cmd(event):
    help_text = (
        "🤖 **Auto Realtime DM Controller Bot**\n\n"
        "**Features:**\n"
        "✅ Purane Pending Ignore, Sirf Nayi Request Par DM!\n\n"
        "**Commands:**\n"
        "🔹 Reply + `/setmsg` : Message save karein (Max 5)\n"
        "🔹 `/clear_msgs` : Saved messages clear karein\n"
        "🔹 `/setchannel -100XXXXXX` : Target channel set karein\n"
        "🔹 `/status` : Status check karein\n"
        "🔹 `/run` | `/stop` : Start ya Stop karein"
    )
    await event.respond(help_text, parse_mode="md")


@bot_client.on(events.NewMessage(pattern=r"/setchannel (.+)"))
async def set_channel_cmd(event):
    global target_channel, processed_users
    channel_input = event.pattern_match.group(1).strip()

    try:
        chat_id = (
            int(channel_input)
            if channel_input.startswith("-") or channel_input.isdigit()
            else channel_input
        )
        entity = await user_client.get_entity(chat_id)
        target_channel = entity
        channel_name = getattr(entity, "title", "Private Channel")

        # Purane pending requests ko cache karke ignore karne ka setup
        processed_users.clear()
        try:
            old_requests = await user_client(
                functions.messages.GetChatInviteImportersRequest(
                    peer=target_channel,
                    offset_date=0,
                    offset_user=InputUserEmpty(),
                    limit=100,
                    requested=True,
                )
            )
            for imp in old_requests.importers:
                processed_users.add(imp.user_id)
        except Exception:
            pass

        await event.respond(
            f"✅ **Channel Set!**\n📌 Name: `{channel_name}`\n"
            f"⚡ Purane {len(processed_users)} pending requests ignore list me daal diye hain."
        )
    except Exception as e:
        await event.respond(f"❌ Channel Error: {e}")


@bot_client.on(events.NewMessage(pattern="/setmsg"))
async def set_msg_cmd(event):
    global saved_messages

    if not event.is_reply:
        await event.respond(
            "⚠️ **Galti!** Target message par Reply karke `/setmsg` likho."
        )
        return

    if len(saved_messages) >= 5:
        await event.respond(
            "⚠️ **Limit Full!** Maximum 5 messages allow hain. Pehle `/clear_msgs` karein."
        )
        return

    reply_msg = await event.get_reply_message()
    saved_messages.append(reply_msg)

    await event.respond(
        f"✅ **Message #{len(saved_messages)} Saved!**\nTotal Saved: {len(saved_messages)}/5",
        reply_to=reply_msg.id,
    )


@bot_client.on(events.NewMessage(pattern="/clear_msgs"))
async def clear_msgs_cmd(event):
    global saved_messages
    saved_messages.clear()
    await event.respond("🗑️ **All Saved Messages Deleted!**")


@bot_client.on(events.NewMessage(pattern="/status"))
async def status_cmd(event):
    ch_name = (
        getattr(target_channel, "title", "Not Set")
        if target_channel
        else "Not Set"
    )
    status_str = "🟢 RUNNING" if is_running else "🔴 STOPPED"

    status_msg = (
        f"📊 **System Status:** {status_str}\n\n"
        f"📌 **Target Channel:** {ch_name}\n"
        f"💬 **Saved Messages:** {len(saved_messages)}/5"
    )
    await event.respond(status_msg, parse_mode="md")


@bot_client.on(events.NewMessage(pattern="/run"))
async def run_cmd(event):
    global is_running
    if not target_channel:
        await event.respond("❌ Pehle `/setchannel` karein!")
        return
    if not saved_messages:
        await event.respond("❌ Pehle `/setmsg` se message set karein!")
        return

    is_running = True
    await event.respond(
        "🚀 **Realtime DM Active! Purane ignore hain, sirf NAYI requests ko jayega.**"
    )


@bot_client.on(events.NewMessage(pattern="/stop"))
async def stop_cmd(event):
    global is_running
    is_running = False
    await event.respond("🛑 **Auto DM Sender Stopped.**")


# ==========================================
#     ONLY NEW REALTIME REQUEST DM WORKER
# ==========================================


async def dm_worker():
    global is_running, target_channel, saved_messages, processed_users

    while True:
        if is_running and target_channel and saved_messages:
            try:
                requests = await user_client(
                    functions.messages.GetChatInviteImportersRequest(
                        peer=target_channel,
                        offset_date=0,
                        offset_user=InputUserEmpty(),
                        limit=20,
                        requested=True,
                    )
                )

                for importer in requests.importers:
                    user_id = importer.user_id

                    # Purane log ignore rahenge, sirf live new user aate hi execute hoga
                    if user_id not in processed_users:
                        # Pehle hi array me add kar do taaki retry issue na aaye
                        processed_users.add(user_id)
                        try:
                            user_entity = await user_client.get_entity(user_id)

                            for msg_obj in saved_messages:
                                await user_client.send_message(
                                    user_entity, msg_obj
                                )
                                await asyncio.sleep(1)

                            print(
                                f"[✓] Realtime New Request DM Sent -> User ID: {user_id}"
                            )
                        except Exception as send_err:
                            print(
                                f"[X] Error sending DM to {user_id}: {send_err}"
                            )

            except Exception as scan_err:
                print(f"[!] Worker Scan Error: {scan_err}")

        await asyncio.sleep(1)


# ==========================================
#          HOSTING ENTRY POINT
# ==========================================


async def main():
    try:
        await user_client.start()
        await bot_client.start(bot_token=BOT_TOKEN)

        print("==========================================")
        print("   REALTIME ONLY AUTO DM BOT ONLINE       ")
        print("==========================================")

        asyncio.create_task(dm_worker())
        await bot_client.run_until_disconnected()

    except FloodWaitError as e:
        print(f"❌ Telegram Ban/FloodWait: Wait {e.seconds} seconds.")
    except Exception as e:
        print(f"❌ Hosting Critical Error: {e}")
    finally:
        if user_client.is_connected():
            await user_client.disconnect()
        if bot_client.is_connected():
            await bot_client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot Stopped.")
