import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import UserNotParticipant, FloodWait
from motor.motor_asyncio import AsyncIOMotorClient

# --- CONFIGURATION ---
API_ID = 37668346
API_HASH = "699f2bddd2fc4952c32b37753d5cf419"
BOT_TOKEN = "8875765734:AAHR4UsKAwFDlgdIq8B2TNMyl7xEqI5kmuI"
SESSION_STRING = "AQI-xfoAskfk0WaA3XrHm93yVoRAyZd2uKhKGOlyigEGilzbqYi0Ci03zydxZYnHIJCf5--XbRojqVkoWQu2wfg0YMUFFxR-WuGCP6_H_qeWMINOpmRP6qMnRlIf6QyKDxkh0dPOa6T6uAUt6fEXXh_oQsz36P2UgAedk3chjM_GEKJJLkh_bnEFP3cg7YnDgBxoAH4-AG-uPeyr2a45-dU7DkMzcv9tdiojIjG-rtppciVMCWKYQpmDeFGvJ7t1TLsJ6p-faF9Wgcdv4RTqAnpSZRugTAp7TTPS6MKbuG2u3GxNFAA4MaTyTGdg2gcQkVwNAHOjR60bfuCkwYwRlEofF61nhwAAAAIFinEKAA"

DATABASE_URL = "mongodb+srv://sanatanigojoyt_db_user:xLRL1I7hC1qsg7NT@cluster00.6n6tt6a.mongodb.net/?appName=Cluster00"

FORCE_SUB_CHANNEL = "rushbots"
USERBOT_USERNAME = "@Recoverbott"
TARGET_BOT = "@EURegulation"
ADMIN_IDS = [8924549820, 8306853454]

# --- INITIALIZATION ---
app = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
userbot = Client("userbot_session", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# --- DATABASE SETUP ---
db_client = AsyncIOMotorClient(DATABASE_URL)
db = db_client["telegram_bot_db"]
users_collection = db["users"]

user_state = {}

# --- AUTOMATED APPEALS ---
CHANNEL_APPEAL = "Hello Telegram Support, my channel has been wrongly flagged. Recently, my primary device was compromised, and unauthorized access was gained to my account. The prohibited content was uploaded by an intruder during this breach, not by me. I have now secured my account with 2FA and terminated all other sessions. Please review the login logs and restore my channel, as I am the rightful owner and committed to following all guidelines."

GROUP_APPEAL = "Hello Telegram Team, My group was temporarily suspended. I have completely cleared the entire chat history and removed all the offending content. I pledge to take reasonable care of moderation in the future. Kindly review and restore my group. Thank you"

# --- HELPER FUNCTIONS ---
async def check_force_sub(client, user_id):
    try:
        await client.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        return True
    except UserNotParticipant:
        return False
    except Exception:
        return True

async def add_user_to_db(user_id):
    user = await users_collection.find_one({"user_id": user_id})
    if not user:
        await users_collection.insert_one({"user_id": user_id})

# --- COMMANDS ---
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    user_id = message.from_user.id
    await add_user_to_db(user_id)
    
    is_joined = await check_force_sub(client, user_id)
    if not is_joined:
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("Join Channel", url=f"https://t.me/{FORCE_SUB_CHANNEL}")]])
        await message.reply_text("Please join our update channel first to use this bot.", reply_markup=btn)
        return
    await message.reply_text("Welcome! Send /appeal to start the process.")

@app.on_message(filters.command("broadcast") & filters.private & filters.user(ADMIN_IDS))
async def broadcast_cmd(client, message):
    if not message.reply_to_message:
        await message.reply_text("Please reply to a message with /broadcast to send it to all users.")
        return

    msg = await message.reply_text("Broadcast starting...")
    users = await users_collection.find().to_list(length=None)
    
    success = 0
    failed = 0
    
    for user in users:
        try:
            await message.reply_to_message.copy(user["user_id"])
            success += 1
            await asyncio.sleep(0.1)  # Anti-flood sleep
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await message.reply_to_message.copy(user["user_id"])
            success += 1
        except Exception:
            failed += 1

    await msg.edit_text(f"Broadcast completed!\n\n✅ Success: {success}\n❌ Failed: {failed}")

@app.on_message(filters.command("appeal") & filters.private)
async def appeal_cmd(client, message):
    user_id = message.from_user.id
    await add_user_to_db(user_id)
    
    is_joined = await check_force_sub(client, user_id)
    if not is_joined:
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("Join Channel", url=f"https://t.me/{FORCE_SUB_CHANNEL}")]])
        await message.reply_text("Please join our update channel first.", reply_markup=btn)
        return

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("Why did this happen?", callback_data="btn_info")],
        [InlineKeyboardButton("Public", callback_data="btn_public"), InlineKeyboardButton("Private", callback_data="btn_private")]
    ])
    await message.reply_text("Select the type of your chat to appeal:", reply_markup=buttons)

# --- CALLBACKS ---
@app.on_callback_query()
async def callback_handler(client, callback_query):
    user_id = callback_query.from_user.id
    data = callback_query.data

    if data == "btn_info":
        await callback_query.answer("To learn why this might happen, or to report incorrectly applied limitations, please contact @rushunfrozenbot using the restricted account.", show_alert=True)
    
    elif data in ["btn_public", "btn_private"]:
        chat_type = "Public" if data == "btn_public" else "Private"
        user_state[user_id] = {"step": "waiting_for_link", "type": chat_type}
        
        # Userbot sends /dsa_appeal to EU bot
        await userbot.send_message(TARGET_BOT, "/dsa_appeal")
        await asyncio.sleep(1.5)
        # Userbot mimics the chat type selection
        await userbot.send_message(TARGET_BOT, chat_type)

        await callback_query.message.reply_text(f"You selected {chat_type}. Please send the link of your chat.")
        await callback_query.answer()
    
    elif data == "check_admin":
        if user_id not in user_state or "chat_id" not in user_state[user_id]:
            await callback_query.answer("Session expired. Please restart using /appeal.", show_alert=True)
            return
        
        chat_id = user_state[user_id]["chat_id"]
        try:
            member = await userbot.get_chat_member(chat_id, userbot.me.id)
            if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                user_state[user_id]["step"] = "waiting_for_name"
                await callback_query.message.reply_text("Admin verified! ✅\n\nAccording to our Custom T&C verification process, please provide your **Full Name**.")
                await callback_query.answer()
            else:
                await callback_query.answer("Abhi admin nhi bnaya h! Please make the userbot an admin first.", show_alert=True)
        except Exception as e:
            await callback_query.answer("Userbot is not in the chat or not an admin yet. Please check.", show_alert=True)

# --- MESSAGE HANDLER (Form steps) ---
@app.on_message(filters.text & filters.private & ~filters.command(["start", "appeal", "broadcast"]))
async def message_handler(client, message):
    user_id = message.from_user.id
    if user_id not in user_state:
        return

    step = user_state[user_id].get("step")

    if step == "waiting_for_link":
        link = message.text
        user_state[user_id]["link"] = link
        await message.reply_text("Attempting to join the chat with the userbot...")

        try:
            chat = await userbot.join_chat(link)
            user_state[user_id]["chat_id"] = chat.id
            
            # Userbot forwards the link to the EU bot
            await userbot.send_message(TARGET_BOT, link)
            
            btn = InlineKeyboardMarkup([[InlineKeyboardButton("Done ✅", callback_data="check_admin")]])
            await message.reply_text(
                f"{USERBOT_USERNAME} ye id join ho chuki h tumhare group/channel me. Admin bnao ise full power ke saath.",
                reply_markup=btn
            )
            user_state[user_id]["step"] = "waiting_for_admin_done"
        except Exception as e:
            await message.reply_text(f"Failed to join the chat. Ensure the link is valid and bot is not banned. Error: {e}")

    elif step == "waiting_for_name":
        user_state[user_id]["name"] = message.text
        await userbot.send_message(TARGET_BOT, message.text)
        
        user_state[user_id]["step"] = "waiting_for_phone"
        await message.reply_text("Please provide your **Phone Number**.")

    elif step == "waiting_for_phone":
        user_state[user_id]["phone"] = message.text
        await userbot.send_message(TARGET_BOT, message.text)
        
        user_state[user_id]["step"] = "waiting_for_email"
        await message.reply_text("Please provide your **Email ID**.")

    elif step == "waiting_for_email":
        user_state[user_id]["email"] = message.text
        await userbot.send_message(TARGET_BOT, message.text)
        
        await message.reply_text("Thank you. All information has been gathered and submitted for verification under our Custom Guidelines.")
        
        # --- AUTOMATED APPEAL INJECTION ---
        chat_id = user_state[user_id].get("chat_id")
        try:
            chat_info = await userbot.get_chat(chat_id)
            if str(chat_info.type) == "ChatType.CHANNEL":
                await userbot.send_message(TARGET_BOT, CHANNEL_APPEAL)
            else:
                await userbot.send_message(TARGET_BOT, GROUP_APPEAL)
        except Exception:
            await userbot.send_message(TARGET_BOT, GROUP_APPEAL)

        del user_state[user_id]

async def main():
    await app.start()
    await userbot.start()
    print("Bot and Userbot are both running!")
    import pyrogram
    await pyrogram.idle()

if __name__ == "__main__":
    app.run(main())

                                                          
