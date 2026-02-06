import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, constants, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from pymongo import MongoClient

# --- CONFIGURATION ---
# ⚠️ REPLACE THESE WITH YOUR ACTUAL KEYS
BOT_TOKEN = "8342076756:AAEj8BjB-aDegzv7jPISvGPXl7VgD59R3CU"
MONGO_URI = "mongodb+srv://officaltnvjvalid_db_user:QpOcYNtTqqY7eRrm@cluster0.xbzmis8.mongodb.net/?appName=Cluster0"

# Update with your IDs
ADMIN_IDS = [6457348769, 8237070487]
LOG_CHANNEL_ID = -1003710710882
FORCE_JOIN_CHANNEL = "@courselist88"
CONTACT_ADMIN = "@mineheartO"
PREMIUM_PRICE = "499"

# --- DATABASE SETUP ---
client = MongoClient(MONGO_URI)
db = client['course_bot_db']
courses_col = db['courses']
users_col = db['users']

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- HELPERS ---

def is_admin(user_id):
    return user_id in ADMIN_IDS

def get_user_status(user_id):
    """
    Returns: 'admin', 'premium', 'referral_qualified', or 'free'
    Handles 24-hour expiration for referrals.
    """
    if is_admin(user_id): return 'admin'
    
    user = users_col.find_one({"user_id": user_id})
    if not user: return 'free'
    
    if user.get("authorized", False):
        return 'premium'
    
    # --- REFERRAL EXPIRATION LOGIC ---
    # Check if referral qualification has expired
    reset_time = user.get("referral_reset_time")
    
    if reset_time and datetime.now() > reset_time:
        # Expired! Reset count and remove timer
        users_col.update_one(
            {"user_id": user_id},
            {
                "$set": {"referral_count": 0},
                "$unset": {"referral_reset_time": ""}
            }
        )
        return 'free'

    # Check referrals (Threshold: 3)
    if user.get("referral_count", 0) >= 3:
        # If they qualify but don't have an expiration time set (legacy/edge case), set it now
        if not reset_time:
             # This sets the timer starting NOW if they somehow have 3 refs but no timer
             expiry = datetime.now() + timedelta(hours=24)
             users_col.update_one({"user_id": user_id}, {"$set": {"referral_reset_time": expiry}})
        
        return 'referral_qualified'
        
    return 'free'

async def is_subscribed(context, user_id):
    try:
        member = await context.bot.get_chat_member(chat_id=FORCE_JOIN_CHANNEL, user_id=user_id)
        return member.status not in [constants.ChatMemberStatus.LEFT, constants.ChatMemberStatus.BANNED]
    except:
        return True 

async def delete_message_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.delete_message(chat_id=context.job.chat_id, message_id=context.job.data)
    except: pass

# --- HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    referrer_id = None
    
    # Check if existing user
    existing_user = users_col.find_one({"user_id": user.id})
    
    # --- REFERRAL LOGIC (Only for new users) ---
    if not existing_user and args:
        try:
            referrer_id = int(args[0])
            if referrer_id != user.id:
                # Update Referrer
                referrer_data = users_col.find_one({"user_id": referrer_id})
                
                if referrer_data:
                    # Increment count
                    users_col.update_one(
                        {"user_id": referrer_id},
                        {"$inc": {"referral_count": 1}}
                    )
                    
                    # Fetch updated count
                    new_count = referrer_data.get("referral_count", 0) + 1
                    msg = f"🎉 <b>New Referral!</b>\nYou have referred {new_count} users."
                    
                    # Check if they just hit the threshold
                    if new_count == 3:
                        # SET EXPIRATION TIMER (24 Hours from now)
                        expiry_time = datetime.now() + timedelta(hours=24)
                        users_col.update_one(
                            {"user_id": referrer_id},
                            {"$set": {"referral_reset_time": expiry_time}}
                        )
                        msg += "\n\n🎁 <b>Congratulations!</b> You unlocked 3 sample videos per course!\n⏳ <b>Valid for 24 Hours only.</b>"
                    
                    elif new_count < 3:
                        msg += f"\nNeed {3 - new_count} more to unlock videos!"
                    
                    elif new_count > 3:
                         msg += "\n(You remain qualified for the 24h period)"

                    await context.bot.send_message(referrer_id, msg, parse_mode=constants.ParseMode.HTML)
        except Exception as e:
            logging.error(f"Referral error: {e}")

    # Register/Update User
    user_data = {
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name
    }
    # Only set referred_by if new
    if not existing_user and referrer_id:
        user_data["referred_by"] = referrer_id
        
    users_col.update_one({"user_id": user.id}, {"$set": user_data}, upsert=True)

    # --- FORCE JOIN CHECK ---
    ref_link = f"https://t.me/{context.bot.username}?start={user.id}"
    
    if not await is_subscribed(context, user.id):
        keyboard = [
            [InlineKeyboardButton("Join Channel 📢", url=f"https://t.me/{FORCE_JOIN_CHANNEL.replace('@','')}")],
            [InlineKeyboardButton("Invite Friends (Get Free Trial) 🎁", url=f"https://t.me/share/url?url={ref_link}&text=Get%20Free%20Premium%20Courses%20Here!")]
        ]
        await update.message.reply_text(
            f"❌ <b>Access Denied!</b>\n\nAapko bot use karne ke liye hamara channel join karna hoga.",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=constants.ParseMode.HTML
        )
        return

    # --- WELCOME MESSAGE ---
    status = get_user_status(user.id) # Re-check status to handle expiration
    
    msg = f"<b>👋 Welcome {user.first_name}!</b>\n\n"
    
    if status == 'admin':
        msg += (
            "⭐ <b>ADMIN PANEL ACTIVE</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "➕ <code>/add [Name] [Links]</code>\n"
            "📹 <b>To Add Videos:</b> Reply to video with <code>/save [Name]</code>\n"
            "🗑️ <code>/del_course [Name]</code>\n"
            "🔓 <code>/authorize [ID]</code>\n"
            "❌ <code>/remove [ID]</code>\n"
            "👑 <code>/premium_list</code>\n"
            "📢 <code>/broadcast [Msg]</code>\n"
            "📊 <code>/stats</code>\n"
        )
    else:
        # User Dashboard
        user_doc = users_col.find_one({"user_id": user.id})
        current_refs = user_doc.get("referral_count", 0)
        
        # Calculate time remaining if qualified
        expiry_info = ""
        if status == 'referral_qualified':
            reset_time = user_doc.get("referral_reset_time")
            if reset_time:
                remaining = reset_time - datetime.now()
                if remaining.total_seconds() > 0:
                    hours = int(remaining.total_seconds() // 3600)
                    mins = int((remaining.total_seconds() % 3600) // 60)
                    expiry_info = f"\n⏳ <b>Expires in:</b> {hours}h {mins}m"

        msg += (
            f"🔍 <b>Search Course:</b> Just type the name.\n\n"
            f"💎 <b>Premium Access:</b> {PREMIUM_PRICE}/- Lifetime\n"
            f"🚀 <b>Features:</b> Unlimited Links & Full Access\n"
            f"👤 <b>Contact:</b> {CONTACT_ADMIN}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🎁 <b>Free Trial (Referral):</b>\n"
            f"Invite 3 friends to get <b>3 Sample Videos</b> for any course!\n"
            f"<i>(Access lasts 24 hours after unlocking)</i>\n\n"
            f"🔗 <b>Your Link:</b>\n<code>{ref_link}</code>\n\n"
            f"👥 <b>Your Referrals:</b> {current_refs}/3 {expiry_info}"
        )
        
    await update.message.reply_text(msg, parse_mode=constants.ParseMode.HTML)

# --- COURSE & VIDEO MANAGEMENT ---

async def add_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        if len(context.args) < 2:
            await update.message.reply_text("❌ <b>Format:</b> /add [Name] [Links]")
            return
        
        links = [arg for arg in context.args if arg.startswith('http')]
        name = " ".join([arg for arg in context.args if not arg.startswith('http')]).lower()

        courses_col.update_one({"name": name}, {"$addToSet": {"links": {"$each": links}}}, upsert=True)
        await update.message.reply_text(f"✅ <b>{name.upper()}</b> Links Saved!")
        
        # Notify Premium Users
        await notify_users(context, name)
        
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def save_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id): return

    msg = update.message
    video = msg.video or (msg.reply_to_message.video if msg.reply_to_message else None)
    
    if not video:
        await msg.reply_text("❌ Reply to a video or send a video.")
        return

    args = context.args
    if not args:
        await msg.reply_text("❌ <b>Format:</b> /save [course_name]")
        return
        
    name = " ".join(args).lower()
    file_id = video.file_id
    
    courses_col.update_one({"name": name}, {"$push": {"videos": file_id}}, upsert=True)
    await msg.reply_text(f"✅ Video saved to <b>{name.upper()}</b>!", parse_mode=constants.ParseMode.HTML)

async def notify_users(context, course_name):
    premium_users = users_col.find({"authorized": True})
    for p_user in premium_users:
        try:
            if p_user['user_id'] in ADMIN_IDS: continue
            await context.bot.send_message(
                chat_id=p_user['user_id'],
                text=f"🔔 <b>New Course Added!</b>\n\n📚 Name: <code>{course_name.upper()}</code>\n✨ Search now!",
                parse_mode=constants.ParseMode.HTML
            )
            await asyncio.sleep(0.05)
        except: continue

async def del_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    name = " ".join(context.args).lower()
    if not name:
        await update.message.reply_text("❌ Name toh likho! <code>/del_course python</code>", parse_mode=constants.ParseMode.HTML)
        return
    
    result = courses_col.delete_one({"name": name})
    if result.deleted_count > 0:
        await update.message.reply_text(f"🗑️ <b>{name.upper()}</b> deleted.", parse_mode=constants.ParseMode.HTML)
    else:
        await update.message.reply_text("🔍 Course not found.")

# --- USER MANAGEMENT ---

async def authorize_user(update, context):
    if not is_admin(update.effective_user.id): return
    try:
        target = int(context.args[0])
        users_col.update_one({"user_id": target}, {"$set": {"authorized": True}}, upsert=True)
        await update.message.reply_text(f"✅ User {target} Authorized.")
        await context.bot.send_message(target, f"🎉 <b>Premium Activated!</b>\nYou now have full access.\nPrice Paid: {PREMIUM_PRICE}", parse_mode=constants.ParseMode.HTML)
    except: pass

async def remove_user(update, context):
    if not is_admin(update.effective_user.id): return
    try:
        target = int(context.args[0])
        users_col.update_one({"user_id": target}, {"$set": {"authorized": False}})
        await update.message.reply_text(f"❌ User {target} Access Revoked.")
    except: pass

async def premium_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    p_users = list(users_col.find({"authorized": True}))
    msg = "👑 <b>Premium Users</b>\n\n"
    for i, u in enumerate(p_users, 1):
        msg += f"{i}. <code>{u['user_id']}</code> (@{u.get('username')})\n"
    await update.message.reply_text(msg, parse_mode=constants.ParseMode.HTML)

# --- CORE LOGIC (SEARCH) ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_subscribed(context, user.id): return
    
    query = update.message.text.lower().strip()
    status = get_user_status(user.id) # Handles expiration logic internally
    
    # 1. Check if course exists
    course = courses_col.find_one({"name": query})
    
    if not course:
        await update.message.reply_text("🔍 Course not found. Try /courses or check spelling.")
        return

    # 2. Logic based on Status
    
    # CASE A: PREMIUM USER (Links + Videos)
    if status in ['premium', 'admin']:
        response_text = f"✅ <b>{query.upper()}</b> (Premium)\n\n"
        
        if "links" in course and course['links']:
            response_text += "\n".join([f"🔗 {l}" for l in course['links']])
        else:
            response_text += "No links available."
            
        sent = await update.message.reply_text(
            response_text + "\n\n⚠️ <i>Auto-delete in 2 mins</i>", 
            parse_mode=constants.ParseMode.HTML, disable_web_page_preview=True
        )
        context.job_queue.run_once(delete_message_job, 120, chat_id=update.effective_chat.id, data=sent.message_id)
        return

    # CASE B: REFERRAL QUALIFIED (Videos Only - Max 3)
    elif status == 'referral_qualified':
        videos = course.get('videos', [])
        
        if not videos:
            await update.message.reply_text("😕 Sorry, no videos uploaded for this course yet.\nAsk admin to add videos.")
            return
            
        await update.message.reply_text(f"🎁 <b>Referral Bonus Active!</b>\nSending 3 sample videos for {query.upper()}...")
        
        for vid_id in videos[:3]: # Limit to 3
            try:
                await context.bot.send_video(chat_id=user.id, video=vid_id, caption=f"🎥 {query.upper()} Sample")
            except Exception as e:
                logging.error(f"Failed to send video: {e}")
        
        await update.message.reply_text(f"💎 Want full access & links?\nBuy Premium: <b>{PREMIUM_PRICE}/-</b>\nContact: {CONTACT_ADMIN}", parse_mode=constants.ParseMode.HTML)

    # CASE C: FREE USER (Restriction Message)
    else:
        ref_link = f"https://t.me/{context.bot.username}?start={user.id}"
        await update.message.reply_text(
            f"🚫 <b>Premium Required for {query.upper()}</b>\n\n"
            f"💰 <b>Price:</b> {PREMIUM_PRICE}/-\n"
            f"👤 <b>Buy Here:</b> {CONTACT_ADMIN}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔓 <b>Want Free Access?</b>\n"
            f"Refer 3 friends to get 3 sample videos for this course!\n"
            f"<i>(Trial access expires 24 hours after unlocking)</i>\n\n"
            f"👇 <b>Your Referral Link:</b>\n<code>{ref_link}</code>",
            parse_mode=constants.ParseMode.HTML
        )

async def list_courses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    courses = list(courses_col.find({}))
    text = "📚 <b>Available Courses:</b>\n\n" + "\n".join([f"• <code>{c['name'].upper()}</code>" for c in courses])
    await update.message.reply_text(text, parse_mode=constants.ParseMode.HTML)

# --- STANDARD ADMIN TOOLS ---
async def broadcast(update, context):
    if not is_admin(update.effective_user.id): return
    msg_text = " ".join(context.args)
    if not msg_text: return
    is_pin = update.message.text.startswith('/pin')
    users = users_col.find({})
    for u in users:
        try:
            s = await context.bot.send_message(u['user_id'], f"📢 <b>UPDATE:</b>\n\n{msg_text}", parse_mode=constants.ParseMode.HTML)
            if is_pin: await context.bot.pin_chat_message(u['user_id'], s.message_id)
        except: pass

async def get_stats(update, context):
    if not is_admin(update.effective_user.id): return
    u = users_col.count_documents({})
    c = courses_col.count_documents({})
    p = users_col.count_documents({"authorized": True})
    await update.message.reply_text(f"📊 <b>Stats</b>\nUsers: {u}\nPremium: {p}\nCourses: {c}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_course))
    app.add_handler(CommandHandler("save", save_video))
    app.add_handler(CommandHandler("del_course", del_course))
    app.add_handler(CommandHandler("authorize", authorize_user))
    app.add_handler(CommandHandler("remove", remove_user))
    app.add_handler(CommandHandler("premium_list", premium_list))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("pin_broadcast", broadcast))
    app.add_handler(CommandHandler("courses", list_courses))
    app.add_handler(CommandHandler("stats", get_stats))
    
    # Message Handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VIDEO & filters.CaptionRegex(r"^/save"), save_video))
    
    print("🚀 Affanoi Courses Bot 2.0 (With 24h Expiry) is LIVE...")
    app.run_polling()

if __name__ == "__main__":
    main()
    
