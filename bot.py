import logging
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# Telegram Imports
from telegram import (
    Update, 
    constants, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    InlineQueryResultArticle, 
    InputTextMessageContent,
    InputMediaVideo
)
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes, 
    CallbackQueryHandler, 
    InlineQueryHandler,
    Defaults
)

# Database Imports
from pymongo import MongoClient, errors

# ==========================================
# ⚙️ CONFIGURATION & SETTINGS
# ==========================================

# ⚠️ REPLACE THESE WITH YOUR ACTUAL KEYS
BOT_TOKEN = "8342076756:AAEj8BjB-aDegzv7jPISvGPXl7VgD59R3CU"
MONGO_URI = "mongodb+srv://officaltnvjvalid_db_user:QpOcYNtTqqY7eRrm@cluster0.xbzmis8.mongodb.net/?appName=Cluster0"

# ⚠️ ADMIN & CHANNEL SETTINGS
ADMIN_IDS = [6457348769, 8237070487]  # Add your numeric IDs here
LOG_CHANNEL_ID = -1003710710882       # Channel for logs (Optional)
FORCE_JOIN_CHANNEL = "@YourChannelUsername" # Channel users must join
CONTACT_ADMIN = "@mineheartO"

# ⚠️ PRICING & REFERRAL SETTINGS
PREMIUM_PRICE = "499"
REFERRAL_THRESHOLD = 3                # Invites needed for free trial
TRIAL_DURATION_HOURS = 24             # How long the trial lasts
AUTO_DELETE_SECONDS = 120             # 2 Minutes for trial videos

# ⚠️ UI TEXTS (Edit these to change bot language)
TEXTS = {
    "welcome": (
        "<b>👋 Welcome, {first_name}!</b>\n\n"
        "I am the ultimate course repository bot. "
        "Search for any course or upgrade to Premium for lifetime access."
    ),
    "access_denied": (
        "🚫 <b>Access Denied</b>\n\n"
        "You must join our channel to use this bot.\n"
        "Click the button below to join, then try again."
    ),
    "premium_dashboard": (
        "💎 <b>PREMIUM MEMBER</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "✅ Unlimited Search\n"
        "✅ Permanent Links\n"
        "✅ No Auto-Delete\n"
        "✅ Anti-Ban Support\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "<i>Enjoy your learning journey!</i>"
    ),
    "free_dashboard": (
        "👤 <b>FREE MEMBER</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🔍 <b>Search:</b> Type course name or use inline mode.\n"
        "💎 <b>Premium:</b> ₹{price}/- Lifetime (<code>/buy</code>)\n"
        "🎫 <b>Redeem Code:</b> <code>/redeem [CODE]</code>\n\n"
        "🎁 <b>Free Trial Offer:</b>\n"
        "Invite {threshold} friends to unlock 3 sample videos per course!\n\n"
        "🔗 <b>Your Referral Link:</b>\n<code>{ref_link}</code>\n\n"
        "👥 <b>Stats:</b> {referrals}/{threshold} Referrals {expiry}"
    ),
    "payment_info": (
        "💎 <b>PREMIUM UPGRADE INSTRUCTIONS</b>\n\n"
        "<b>Price:</b> ₹{price}/- (Lifetime Access)\n\n"
        "💳 <b>Payment Methods:</b>\n"
        "• <b>UPI:</b> <code>example@upi</code>\n"
        "• <b>Binance Pay:</b> <code>12345678</code>\n\n"
        "📝 <b>How to Activate:</b>\n"
        "1. Make the payment.\n"
        "2. Take a screenshot of the success screen.\n"
        "3. Send the photo here with the caption: <code>/submit_proof</code>\n\n"
        "<i>Admin will verify and activate your account instantly.</i>"
    ),
    "referral_congrats": (
        "🎉 <b>CONGRATULATIONS!</b>\n\n"
        "You have hit {count} referrals!\n"
        "🎁 <b>Reward:</b> 3 Sample Videos per course unlocked.\n"
        "⏳ <b>Validity:</b> {hours} Hours.\n\n"
        "<i>Search for a course now!</i>"
    )
}

# ==========================================
# 🗄️ DATABASE CONNECTION
# ==========================================

try:
    client = MongoClient(MONGO_URI)
    db = client['course_bot_db']
    courses_col = db['courses']
    users_col = db['users']
    coupons_col = db['coupons']
    
    # Create indexes for faster search
    courses_col.create_index([("name", "text")])
    users_col.create_index("user_id", unique=True)
    
    print("✅ MongoDB Connected Successfully.")
except errors.ConnectionFailure:
    print("❌ FATAL: Could not connect to MongoDB. Check URI.")
    exit(1)

# Logging Setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================

def is_admin(user_id: int) -> bool:
    """Checks if the user is in the ADMIN_IDS list."""
    return user_id in ADMIN_IDS

def get_user_status(user_id: int) -> str:
    """
    Determines user privileges.
    Returns: 'admin', 'premium', 'referral_qualified', or 'free'
    Also handles the 24-hour expiry check logic.
    """
    # 1. Check Admin
    if is_admin(user_id): 
        return 'admin'
    
    user = users_col.find_one({"user_id": user_id})
    if not user: 
        return 'free'
    
    # 2. Check Premium (Authorized)
    if user.get("authorized", False):
        return 'premium'
    
    # 3. Check Referral Expiry Logic
    reset_time = user.get("referral_reset_time")
    
    # If time exists and has passed current time
    if reset_time and datetime.now() > reset_time:
        # Reset the user's progress
        users_col.update_one(
            {"user_id": user_id},
            {
                "$set": {"referral_count": 0},
                "$unset": {"referral_reset_time": ""}
            }
        )
        return 'free'

    # 4. Check Referral Qualification
    if user.get("referral_count", 0) >= REFERRAL_THRESHOLD:
        # If qualified but no timer set (edge case), set it now
        if not reset_time:
             expiry = datetime.now() + timedelta(hours=TRIAL_DURATION_HOURS)
             users_col.update_one(
                 {"user_id": user_id}, 
                 {"$set": {"referral_reset_time": expiry}}
             )
        return 'referral_qualified'
        
    return 'free'

async def check_subscription(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """Verifies if the user is a member of the Force Join Channel."""
    try:
        member = await context.bot.get_chat_member(
            chat_id=FORCE_JOIN_CHANNEL, 
            user_id=user_id
        )
        if member.status in [constants.ChatMemberStatus.LEFT, constants.ChatMemberStatus.BANNED]:
            return False
        return True
    except Exception as e:
        logger.warning(f"Subscription Check Failed (Admin might be restricted): {e}")
        return True # Default to True if bot can't check, to avoid blocking users due to bugs

async def delete_message_job(context: ContextTypes.DEFAULT_TYPE):
    """Job to delete messages after X seconds."""
    job = context.job
    try:
        await context.bot.delete_message(chat_id=job.chat_id, message_id=job.data)
    except Exception as e:
        logger.debug(f"Auto-delete failed (Message likely already deleted): {e}")

# ==========================================
# 🚦 MAIN HANDLERS (START & DASHBOARD)
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles /start command, referrals, and user registration.
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    args = context.args
    
    # 1. Database Registration
    existing_user = users_col.find_one({"user_id": user.id})
    referrer_id = None
    
    # 2. Handle New Referral
    if not existing_user and args:
        try:
            referrer_id = int(args[0])
            if referrer_id != user.id:
                # Update the person who referred this new user
                referrer_data = users_col.find_one({"user_id": referrer_id})
                if referrer_data:
                    # Increment count
                    users_col.update_one(
                        {"user_id": referrer_id}, 
                        {"$inc": {"referral_count": 1}}
                    )
                    
                    # Notify Referrer
                    new_count = referrer_data.get("referral_count", 0) + 1
                    msg = f"🎉 <b>New Referral!</b>\nYou have referred {new_count} users."
                    
                    # Check Threshold
                    if new_count == REFERRAL_THRESHOLD:
                        # Activate Trial Timer
                        expiry_time = datetime.now() + timedelta(hours=TRIAL_DURATION_HOURS)
                        users_col.update_one(
                            {"user_id": referrer_id}, 
                            {"$set": {"referral_reset_time": expiry_time}}
                        )
                        msg = TEXTS["referral_congrats"].format(
                            count=new_count, 
                            hours=TRIAL_DURATION_HOURS
                        )
                    
                    elif new_count < REFERRAL_THRESHOLD:
                        msg += f"\nNeed {REFERRAL_THRESHOLD - new_count} more to unlock videos!"
                    
                    await context.bot.send_message(referrer_id, msg, parse_mode=constants.ParseMode.HTML)
        except ValueError:
            pass # Invalid ID passed
        except Exception as e:
            logger.error(f"Referral Error: {e}")

    # 3. Update Current User Data
    user_data = {
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_active": datetime.now()
    }
    if not existing_user and referrer_id:
        user_data["referred_by"] = referrer_id
        
    users_col.update_one({"user_id": user.id}, {"$set": user_data}, upsert=True)

    # 4. Force Join Check
    if not await check_subscription(context, user.id):
        ref_link_raw = f"https://t.me/{context.bot.username}?start={user.id}"
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{FORCE_JOIN_CHANNEL.replace('@','')}")],
            [InlineKeyboardButton("🔁 Try Again", url=f"https://t.me/{context.bot.username}?start={user.id}")]
        ]
        await update.message.reply_text(
            TEXTS["access_denied"],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=constants.ParseMode.HTML
        )
        return

    # 5. Show Dashboard
    status = get_user_status(user.id)
    ref_link = f"https://t.me/{context.bot.username}?start={user.id}"
    
    if status == 'admin':
        # Admin Panel UI
        dashboard = (
            f"⭐ <b>ADMINISTRATION PANEL</b>\n"
            f"👤 <b>User:</b> {user.first_name}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"➕ <b>Add Content:</b>\n"
            f"<code>/add [Course Name] [Link1] [Link2]</code>\n"
            f"<code>/save [Course Name]</code> (Reply to video)\n\n"
            f"👥 <b>User Mgmt:</b>\n"
            f"<code>/authorize [User ID]</code>\n"
            f"<code>/remove [User ID]</code>\n"
            f"<code>/stats</code>\n\n"
            f"🎫 <b>Marketing:</b>\n"
            f"<code>/create_coupon [CODE]</code>\n"
            f"<code>/broadcast [Message]</code>\n\n"
            f"🗑️ <b>Delete:</b>\n"
            f"<code>/del_course [Name]</code>"
        )
    elif status == 'premium':
        dashboard = TEXTS["premium_dashboard"]
    else:
        # Free/Referral User UI
        user_doc = users_col.find_one({"user_id": user.id})
        current_refs = user_doc.get("referral_count", 0)
        
        # Calculate expiry string
        expiry_info = ""
        if status == 'referral_qualified':
            reset_time = user_doc.get("referral_reset_time")
            if reset_time:
                remaining = reset_time - datetime.now()
                if remaining.total_seconds() > 0:
                    hours = int(remaining.total_seconds() // 3600)
                    mins = int((remaining.total_seconds() % 3600) // 60)
                    expiry_info = f"\n⏳ <b>Expires in:</b> {hours}h {mins}m"
        
        dashboard = TEXTS["free_dashboard"].format(
            price=PREMIUM_PRICE,
            threshold=REFERRAL_THRESHOLD,
            ref_link=ref_link,
            referrals=current_refs,
            expiry=expiry_info
        )
    
    # Send Dashboard
    await update.message.reply_text(
        dashboard, 
        parse_mode=constants.ParseMode.HTML,
        disable_web_page_preview=True
    )

# ==========================================
# 💸 PAYMENT & COUPON SYSTEM
# ==========================================

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends payment details."""
    await update.message.reply_text(
        TEXTS["payment_info"].format(price=PREMIUM_PRICE),
        parse_mode=constants.ParseMode.HTML
    )

async def handle_payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles images sent with caption /submit_proof.
    Forwards to Admin with Approve/Reject buttons.
    """
    user = update.effective_user
    if not update.message.photo:
        await update.message.reply_text("❌ Please attach a screenshot image.")
        return

    photo_file_id = update.message.photo[-1].file_id
    
    # Notify Admins
    keyboard = [[InlineKeyboardButton("✅ Approve Premium Access", callback_data=f"approve_{user.id}")]]
    
    sent_count = 0
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=photo_file_id,
                caption=(
                    f"💸 <b>PAYMENT PROOF RECEIVED</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"👤 <b>Name:</b> {user.first_name}\n"
                    f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
                    f"🔗 <b>Username:</b> @{user.username}\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"<i>Click below to authorize instantly.</i>"
                ),
                parse_mode=constants.ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send proof to admin {admin_id}: {e}")

    if sent_count > 0:
        await update.message.reply_text("✅ <b>Proof Submitted!</b>\nAdmin has been notified. You will receive a message once approved.")
    else:
        await update.message.reply_text("❌ Internal Error: Admins not reachable.")

async def create_coupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Create a coupon code."""
    if not is_admin(update.effective_user.id): return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: <code>/create_coupon [CODE]</code>", parse_mode=constants.ParseMode.HTML)
        return
        
    code = context.args[0].upper()
    coupons_col.insert_one({
        "code": code,
        "active": True,
        "created_at": datetime.now(),
        "created_by": update.effective_user.id
    })
    await update.message.reply_text(f"✅ Coupon <code>{code}</code> Created Successfully!", parse_mode=constants.ParseMode.HTML)

async def redeem_coupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User: Redeem a coupon code."""
    user = update.effective_user
    
    if not context.args:
        await update.message.reply_text("❌ Usage: <code>/redeem [CODE]</code>", parse_mode=constants.ParseMode.HTML)
        return
        
    code = context.args[0].upper()
    coupon = coupons_col.find_one({"code": code, "active": True})
    
    if coupon:
        # Give Premium
        users_col.update_one({"user_id": user.id}, {"$set": {"authorized": True}})
        # Deactivate Coupon (Single use logic, remove this line if you want multi-use)
        coupons_col.update_one({"_id": coupon['_id']}, {"$set": {"active": False, "used_by": user.id}})
        
        await update.message.reply_text(
            "🎉 <b>Code Redeemed Successfully!</b>\n\n"
            "You have been upgraded to <b>Premium</b>.\n"
            "Enjoy lifetime access and unlimited searches!",
            parse_mode=constants.ParseMode.HTML
        )
        
        # Notify Admin
        for admin in ADMIN_IDS:
            await context.bot.send_message(admin, f"ℹ️ Coupon {code} used by {user.first_name} ({user.id})")
    else:
        await update.message.reply_text("❌ <b>Error:</b> Invalid or Expired Coupon Code.", parse_mode=constants.ParseMode.HTML)

# ==========================================
# 📚 COURSE BROWSING (PAGINATION)
# ==========================================

async def get_courses_keyboard(page: int) -> InlineKeyboardMarkup:
    """Generates pagination buttons."""
    courses = list(courses_col.find({}).sort("name", 1)) # Sort alphabetically
    per_page = 5
    start = page * per_page
    end = start + per_page
    current_courses = courses[start:end]
    
    # Course Buttons (Clicking them does nothing/noop - user must type name)
    # Alternatively, you could make them paste the name into chat
    buttons = [
        [InlineKeyboardButton(f"📂 {c['name'].upper()}", switch_inline_query_current_chat=c['name'])] 
        for c in current_courses
    ]
    
    # Navigation Buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page_{page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{((len(courses)-1)//per_page)+1}", callback_data="noop"))
    
    if end < len(courses):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
        
    return InlineKeyboardMarkup(buttons)

async def list_courses_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /courses"""
    if not await check_subscription(context, update.effective_user.id):
        await update.message.reply_text(TEXTS["access_denied"], parse_mode=constants.ParseMode.HTML)
        return

    count = courses_col.count_documents({})
    if count == 0:
        await update.message.reply_text("📭 No courses available yet.")
        return

    await update.message.reply_text(
        "📚 <b>Course Catalog</b>\nClick a course to search for it:",
        reply_markup=await get_courses_keyboard(0),
        parse_mode=constants.ParseMode.HTML
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles button clicks for Pagination and Payment Approval."""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    # 1. Pagination
    if data.startswith("page_"):
        page = int(data.split("_")[1])
        try:
            await query.edit_message_reply_markup(reply_markup=await get_courses_keyboard(page))
        except Exception:
            pass # Message not modified
            
    # 2. Payment Approval
    elif data.startswith("approve_"):
        if not is_admin(update.effective_user.id):
            return # Security check
            
        target_user_id = int(data.split("_")[1])
        
        # Update DB
        users_col.update_one({"user_id": target_user_id}, {"$set": {"authorized": True}}, upsert=True)
        
        # Edit Admin Message
        await query.edit_message_caption(
            caption=f"{query.message.caption}\n\n✅ <b>APPROVED by {update.effective_user.first_name}</b>",
            parse_mode=constants.ParseMode.HTML
        )
        
        # Notify User
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=(
                    "🎉 <b>PAYMENT VERIFIED!</b>\n\n"
                    "Your account has been upgraded to <b>PREMIUM</b>.\n"
                    "You now have unlimited access, permanent links, and no restrictions."
                ),
                parse_mode=constants.ParseMode.HTML
            )
        except Exception as e:
            await context.bot.send_message(update.effective_chat.id, f"⚠️ User authorized, but DM failed: {e}")

# ==========================================
# 🔍 SEARCH & CONTENT DELIVERY (THE CORE)
# ==========================================

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles global inline search (@BotName python)."""
    query = update.inline_query.query.lower()
    if not query: 
        return
    
    # Fuzzy search logic
    courses = list(courses_col.find({"name": {"$regex": query, "$options": "i"}}).limit(10))
    results = []
    
    for c in courses:
        results.append(
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=c['name'].upper(),
                description="Click to request course materials",
                thumbnail_url="https://cdn-icons-png.flaticon.com/512/2436/2436874.png", # Generic icon
                input_message_content=InputTextMessageContent(c['name']) # Sends the exact name to chat
            )
        )
    
    await update.inline_query.answer(results, cache_time=0)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Main Logic: Receives text, searches DB, delivers content based on User Status.
    """
    user = update.effective_user
    if not await check_subscription(context, user.id):
        return # Silent ignore or send join prompt
    
    query = update.message.text.lower().strip()
    status = get_user_status(user.id)
    
    # 1. Search Database
    course = courses_col.find_one({"name": query})
    
    if not course:
        # Optional: Fuzzy search suggestion could go here
        await update.message.reply_text("🔍 Course not found. Please check spelling or use /courses list.")
        return

    # 2. CASE: PREMIUM & ADMIN (Full Access, No Timer)
    if status in ['premium', 'admin']:
        response_text = f"✅ <b>{query.upper()}</b> (Premium Access)\n\n"
        
        if "links" in course and course['links']:
            response_text += "\n".join([f"🔗 {l}" for l in course['links']])
        else: 
            response_text += "📂 No direct links available."
        
        # Send with Content Protection
        await update.message.reply_text(
            response_text,
            parse_mode=constants.ParseMode.HTML,
            disable_web_page_preview=True,
            protect_content=True  # 🛡️ Prevents Forwarding/Saving
        )
        return

    # 3. CASE: REFERRAL QUALIFIED (Limited Access, Auto-Delete)
    elif status == 'referral_qualified':
        videos = course.get('videos', [])
        
        if not videos:
            await update.message.reply_text("😕 No sample videos available for this course yet.\nAsk admin to add some.")
            return
            
        await update.message.reply_text(
            f"🎁 <b>Referral Bonus Active!</b>\n"
            f"Sending 3 sample videos for <b>{query.upper()}</b>...\n"
            f"⚠️ <i>Videos will auto-delete in {AUTO_DELETE_SECONDS//60} mins.</i>",
            parse_mode=constants.ParseMode.HTML
        )
        
        # Send max 3 videos
        for vid_id in videos[:3]:
            try:
                sent_msg = await context.bot.send_video(
                    chat_id=user.id,
                    video=vid_id,
                    caption=f"🎥 {query.upper()} Sample (Trial)",
                    protect_content=True  # 🛡️ Anti-Piracy
                )
                
                # Schedule Auto-Delete
                context.job_queue.run_once(
                    delete_message_job, 
                    AUTO_DELETE_SECONDS, 
                    chat_id=user.id, 
                    data=sent_msg.message_id
                )
            except Exception as e:
                logger.error(f"Failed to send trial video: {e}")
        
        # Upsell Message
        await update.message.reply_text(
            f"💎 <b>Liked the sample?</b>\n"
            f"Get full access + permanent links for <b>₹{PREMIUM_PRICE}/-</b>\n"
            f"Type <code>/buy</code> to purchase.",
            parse_mode=constants.ParseMode.HTML
        )

    # 4. CASE: FREE USER (Paywall)
    else:
        ref_link = f"https://t.me/{context.bot.username}?start={user.id}"
        msg = (
            f"🚫 <b>LOCKED CONTENT: {query.upper()}</b>\n\n"
            f"You need Premium to access this course.\n\n"
            f"💰 <b>Price:</b> ₹{PREMIUM_PRICE}/- (Lifetime)\n"
            f"🛒 <b>To Buy:</b> Type <code>/buy</code>\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔓 <b>GET A FREE TRIAL</b>\n"
            f"Refer {REFERRAL_THRESHOLD} friends to unlock 3 sample videos!\n\n"
            f"👇 <b>Your Referral Link:</b>\n<code>{ref_link}</code>"
        )
        await update.message.reply_text(msg, parse_mode=constants.ParseMode.HTML)

# ==========================================
# ⚙️ ADMIN CONTENT MANAGEMENT
# ==========================================

async def add_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add links to a course."""
    if not is_admin(update.effective_user.id): return
    
    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: <code>/add [name] [link1] [link2]</code>", parse_mode=constants.ParseMode.HTML)
        return
        
    links = [arg for arg in context.args if arg.startswith('http')]
    name_parts = [arg for arg in context.args if not arg.startswith('http')]
    name = " ".join(name_parts).lower()
    
    if not name or not links:
        await update.message.reply_text("❌ Invalid format.")
        return

    result = courses_col.update_one(
        {"name": name}, 
        {"$addToSet": {"links": {"$each": links}}}, 
        upsert=True
    )
    
    action = "Updated" if result.matched_count > 0 else "Created"
    await update.message.reply_text(f"✅ Course <b>{name.upper()}</b> {action} with {len(links)} links.", parse_mode=constants.ParseMode.HTML)
    
    # Optional: Broadcast new course to Premium Users
    # (Commented out to prevent spam, uncomment if needed)
    # await notify_premium_users(context, name)

async def save_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save a video file_id to a course."""
    user = update.effective_user
    if not is_admin(user.id): return

    msg = update.message
    # Check reply or current message
    video = msg.video or (msg.reply_to_message.video if msg.reply_to_message else None)
    
    if not video:
        await msg.reply_text("❌ please reply to a video or upload one with the command.")
        return

    if not context.args:
        await msg.reply_text("❌ Usage: <code>/save [course_name]</code>", parse_mode=constants.ParseMode.HTML)
        return
        
    name = " ".join(context.args).lower()
    file_id = video.file_id
    
    courses_col.update_one({"name": name}, {"$push": {"videos": file_id}}, upsert=True)
    await msg.reply_text(f"✅ Video saved to <b>{name.upper()}</b>!", parse_mode=constants.ParseMode.HTML)

async def del_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a course entirely."""
    if not is_admin(update.effective_user.id): return
    
    if not context.args:
        await update.message.reply_text("Usage: /del_course [name]")
        return
        
    name = " ".join(context.args).lower()
    result = courses_col.delete_one({"name": name})
    
    if result.deleted_count > 0:
        await update.message.reply_text(f"🗑️ <b>{name.upper()}</b> deleted.", parse_mode=constants.ParseMode.HTML)
    else:
        await update.message.reply_text("🔍 Course not found.")

async def authorize_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually give premium."""
    if not is_admin(update.effective_user.id): return
    try:
        target = int(context.args[0])
        users_col.update_one({"user_id": target}, {"$set": {"authorized": True}}, upsert=True)
        await update.message.reply_text(f"✅ User {target} authorized.")
        await context.bot.send_message(target, "🎉 <b>You have been manually upgraded to Premium!</b>", parse_mode=constants.ParseMode.HTML)
    except:
        await update.message.reply_text("Usage: /authorize [user_id]")

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually remove premium."""
    if not is_admin(update.effective_user.id): return
    try:
        target = int(context.args[0])
        users_col.update_one({"user_id": target}, {"$set": {"authorized": False}})
        await update.message.reply_text(f"❌ User {target} revoked.")
    except:
        await update.message.reply_text("Usage: /remove [user_id]")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send message to all users."""
    if not is_admin(update.effective_user.id): return
    
    msg = " ".join(context.args)
    if not msg: return
    
    users = users_col.find({})
    count = 0
    await update.message.reply_text("📣 Broadcasting...")
    
    for u in users:
        try:
            await context.bot.send_message(u['user_id'], f"📢 <b>ANNOUNCEMENT:</b>\n\n{msg}", parse_mode=constants.ParseMode.HTML)
            count += 1
            await asyncio.sleep(0.05) # Flood limit protection
        except Exception:
            pass # User blocked bot
            
    await update.message.reply_text(f"✅ Sent to {count} users.")

async def get_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """System Statistics."""
    if not is_admin(update.effective_user.id): return
    
    total_users = users_col.count_documents({})
    premium_users = users_col.count_documents({"authorized": True})
    total_courses = courses_col.count_documents({})
    
    stats = (
        f"📊 <b>SYSTEM STATISTICS</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 Total Users: {total_users}\n"
        f"👑 Premium Users: {premium_users}\n"
        f"📚 Total Courses: {total_courses}\n"
    )
    await update.message.reply_text(stats, parse_mode=constants.ParseMode.HTML)

# ==========================================
# 🚀 APP STARTUP
# ==========================================

def main():
    """Initializes and runs the bot."""
    print("🚀 Starting Affanoi Enterprise Bot...")
    
    # 1. Build App
    app = Application.builder().token(BOT_TOKEN).build()
    
    # 2. Add Handlers
    
    # Basic Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start)) # reuse start for dashboard
    app.add_handler(CommandHandler("courses", list_courses_command))
    
    # Money & Coupons
    app.add_handler(CommandHandler("buy", buy_command))
    app.add_handler(CommandHandler("redeem", redeem_coupon))
    
    # Admin Commands
    app.add_handler(CommandHandler("add", add_course))
    app.add_handler(CommandHandler("save", save_video))
    app.add_handler(CommandHandler("del_course", del_course))
    app.add_handler(CommandHandler("authorize", authorize_user))
    app.add_handler(CommandHandler("remove", remove_user))
    app.add_handler(CommandHandler("create_coupon", create_coupon))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("stats", get_stats))
    
    # 3. Complex Handlers
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(InlineQueryHandler(inline_query))
    
    # Payment Proof Handler (Photos with caption)
    app.add_handler(MessageHandler(filters.PHOTO & filters.CaptionRegex(r"^/submit_proof"), handle_payment_proof))
    
    # Video Saver (Reply or upload)
    app.add_handler(MessageHandler(filters.VIDEO & filters.CaptionRegex(r"^/save"), save_video))
    
    # Main Search Handler (Text)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # 4. Run
    print("✅ Bot is polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
