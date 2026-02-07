"""
AFFANOI COURSES BOT - ENTERPRISE EDITION
Version: 3.0.0 (Architecture: Monolithic Class-Based)
Author: Professional Python Developer
Platform: Render / VPS
"""

import logging
import asyncio
import uuid
import os
import sys
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union, Tuple

# Web Server Imports (For Render Keep-Alive)
from flask import Flask

# Telegram Imports
from telegram import (
    Update, 
    constants, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    InlineQueryResultArticle, 
    InputTextMessageContent,
    InputMediaVideo,
    User,
    Message
)
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes, 
    CallbackQueryHandler, 
    InlineQueryHandler,
    Defaults,
    JobQueue
)
from telegram.error import TelegramError, BadRequest, Forbidden

# Database Imports
from pymongo import MongoClient, errors
from pymongo.collection import Collection
from pymongo.database import Database

# ==============================================================================
# ⚙️ CLASS: CONFIGURATION & SETTINGS
# ==============================================================================

class Config:
    """
    Central configuration class. 
    Loads environment variables and defines static constants.
    """
    
    # --------------------------------------------------------------------------
    # SECURITY & API KEYS
    # --------------------------------------------------------------------------
    # Attempt to load from Environment, fallback to hardcoded strings (Not recommended for Prod)
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8342076756:AAEj8BjB-aDegzv7jPISvGPXl7VgD59R3CU")
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb+srv://officaltnvjvalid_db_user:QpOcYNtTqqY7eRrm@cluster0.xbzmis8.mongodb.net/?appName=Cluster0")
    
    # --------------------------------------------------------------------------
    # ADMIN CONFIGURATION
    # --------------------------------------------------------------------------
    # Parse comma-separated admin IDs from env
    _admin_env = os.getenv("ADMIN_IDS", "6457348769,8237070487")
    ADMIN_IDS: List[int] = [int(x.strip()) for x in _admin_env.split(",") if x.strip().isdigit()]
    
    CONTACT_ADMIN: str = "@mineheartO"
    LOG_CHANNEL_ID: int = -1003710710882 
    FORCE_JOIN_CHANNEL: str = "@courselist88"
    
    # --------------------------------------------------------------------------
    # BUSINESS LOGIC SETTINGS
    # --------------------------------------------------------------------------
    PREMIUM_PRICE: str = "499"
    REFERRAL_THRESHOLD: int = 3
    TRIAL_DURATION_HOURS: int = 24
    AUTO_DELETE_SECONDS: int = 120  # 2 Minutes
    PAGINATION_LIMIT: int = 5
    
    # --------------------------------------------------------------------------
    # FLASK SERVER SETTINGS
    # --------------------------------------------------------------------------
    PORT: int = int(os.environ.get("PORT", 8080))


# ==============================================================================
# 📝 CLASS: TEXT RESOURCES
# ==============================================================================

class Texts:
    """
    Repository for all text strings used in the bot.
    Supports HTML formatting.
    """
    
    WELCOME = (
        "<b>👋 Welcome to Affanoi Courses, {first_name}!</b>\n\n"
        "I am your premium gateway to advanced learning materials.\n"
        "Search for courses, watch samples, or upgrade for lifetime access."
    )
    
    ACCESS_DENIED = (
        "🚫 <b>ACCESS DENIED</b>\n\n"
        "To protect our community, you must join our official channel to use this bot.\n\n"
        "<i>Please join below and click 'Try Again'.</i>"
    )
    
    PREMIUM_DASHBOARD = (
        "💎 <b>PREMIUM DASHBOARD</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ <b>Status:</b> Lifetime Active\n"
        "✅ <b>Access:</b> Unlimited\n"
        "✅ <b>Links:</b> Permanent (No Auto-Delete)\n"
        "✅ <b>Protection:</b> Anti-Ban Enabled\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Type any course name to search instantly.</i>"
    )
    
    FREE_DASHBOARD = (
        "👤 <b>MEMBER DASHBOARD</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔍 <b>Search:</b> Type course name or use inline mode.\n"
        "💎 <b>Premium:</b> ₹{price}/- Lifetime\n"
        "🛒 <b>Purchase:</b> <code>/buy</code>\n"
        "🎫 <b>Redeem:</b> <code>/redeem [CODE]</code>\n\n"
        "🎁 <b>FREE TRIAL CHALLENGE:</b>\n"
        "Refer {threshold} friends to unlock 3 sample videos per course!\n\n"
        "🔗 <b>Your Referral Link:</b>\n<code>{ref_link}</code>\n\n"
        "📊 <b>Your Progress:</b>\n"
        "👥 Referrals: {referrals}/{threshold}\n"
        "{expiry_info}"
    )
    
    PAYMENT_INSTRUCTIONS = (
        "💎 <b>UPGRADE TO PREMIUM</b>\n\n"
        "<b>Price:</b> ₹{price}/- (One-time Payment)\n"
        "<b>Validity:</b> Lifetime Access\n\n"
        "💳 <b>Payment Methods:</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔸 <b>UPI ID:</b> <code>example@upi</code>\n"
        "🔸 <b>Binance Pay:</b> <code>12345678</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📝 <b>Verification Steps:</b>\n"
        "1. Complete the payment.\n"
        "2. Take a clear screenshot of the transaction.\n"
        "3. Send the photo here with caption: <code>/submit_proof</code>\n\n"
        "<i>Our admins will verify and authorize you shortly.</i>"
    )
    
    REFERRAL_SUCCESS = (
        "🎉 <b>NEW REFERRAL!</b>\n\n"
        "You have referred {count} users.\n\n"
        "{status_msg}"
    )
    
    REFERRAL_UNLOCKED = (
        "🎁 <b>CONGRATULATIONS!</b>\n"
        "You have unlocked the <b>24-Hour Trial!</b>\n\n"
        "✅ 3 Sample Videos per course unlocked.\n"
        "⏳ Expires in 24 Hours.\n"
        "<i>Start searching now!</i>"
    )
    
    ADMIN_PANEL = (
        "⭐ <b>ADMINISTRATION CONSOLE</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "<b>📦 Content Management:</b>\n"
        "• Add Links: <code>/add [Name] [URL]</code>\n"
        "• Add Video: Reply video with <code>/save [Name]</code>\n"
        "• Delete: <code>/del_course [Name]</code>\n\n"
        "<b>👥 User Management:</b>\n"
        "• Auth: <code>/authorize [ID]</code>\n"
        "• Revoke: <code>/remove [ID]</code>\n"
        "• Stats: <code>/stats</code>\n\n"
        "<b>📢 Marketing:</b>\n"
        "• Coupon: <code>/create_coupon [CODE]</code>\n"
        "• Broadcast: <code>/broadcast [Msg]</code>"
    )
    
    BROADCAST_HEADER = "📢 <b>OFFICIAL ANNOUNCEMENT</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n{msg}"


# ==============================================================================
# 🗄️ CLASS: DATABASE MANAGER
# ==============================================================================

class DatabaseManager:
    """
    Handles all interactions with MongoDB.
    Abstracts the pymongo library calls into safe methods.
    """
    
    def __init__(self, uri: str):
        self.uri = uri
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        self.users: Optional[Collection] = None
        self.courses: Optional[Collection] = None
        self.coupons: Optional[Collection] = None
        
        self.connect()

    def connect(self):
        """Establishes connection to MongoDB with error handling."""
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            # Trigger a connection check
            self.client.server_info()
            
            self.db = self.client['course_bot_db']
            self.users = self.db['users']
            self.courses = self.db['courses']
            self.coupons = self.db['coupons']
            
            # Create Indexes for Performance
            self.users.create_index("user_id", unique=True)
            self.courses.create_index([("name", "text")])
            self.coupons.create_index("code", unique=True)
            
            logging.info("✅ Database Manager: Connected successfully.")
            
        except errors.ServerSelectionTimeoutError:
            logging.critical("❌ Database Manager: Connection Timeout! Check URI/IP Whitelist.")
        except Exception as e:
            logging.critical(f"❌ Database Manager: Fatal Error - {e}")

    # --- USER METHODS ---

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Retrieves a user document."""
        return self.users.find_one({"user_id": user_id})

    def register_user(self, user: User, referrer_id: Optional[int] = None) -> bool:
        """
        Registers a new user. Returns True if new, False if existed.
        Handles referral logic internally if referrer_id is provided.
        """
        if self.get_user(user.id):
            return False

        user_data = {
            "user_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "joined_at": datetime.now(),
            "referral_count": 0,
            "authorized": False
        }
        
        if referrer_id and referrer_id != user.id:
            user_data["referred_by"] = referrer_id
            self._increment_referral(referrer_id)
            
        self.users.insert_one(user_data)
        return True

    def _increment_referral(self, referrer_id: int):
        """Internal method to increment referrer count safely."""
        self.users.update_one(
            {"user_id": referrer_id},
            {"$inc": {"referral_count": 1}}
        )

    def set_referral_expiry(self, user_id: int, expiry_date: datetime):
        """Sets the expiry time for a user's trial."""
        self.users.update_one(
            {"user_id": user_id},
            {"$set": {"referral_reset_time": expiry_date}}
        )

    def reset_referral_status(self, user_id: int):
        """Resets referral stats after expiry."""
        self.users.update_one(
            {"user_id": user_id},
            {
                "$set": {"referral_count": 0},
                "$unset": {"referral_reset_time": ""}
            }
        )

    def authorize_user(self, user_id: int, status: bool = True):
        """Sets the premium authorization status."""
        self.users.update_one(
            {"user_id": user_id}, 
            {"$set": {"authorized": status}},
            upsert=True
        )

    # --- COURSE METHODS ---

    def add_course_links(self, name: str, links: List[str]) -> str:
        """Adds links to a course."""
        result = self.courses.update_one(
            {"name": name},
            {"$addToSet": {"links": {"$each": links}}},
            upsert=True
        )
        return "updated" if result.matched_count > 0 else "created"

    def add_course_video(self, name: str, file_id: str):
        """Adds a video file_id to a course."""
        self.courses.update_one(
            {"name": name},
            {"$push": {"videos": file_id}},
            upsert=True
        )

    def delete_course(self, name: str) -> bool:
        """Deletes a course."""
        result = self.courses.delete_one({"name": name})
        return result.deleted_count > 0

    def find_course(self, query: str) -> Optional[Dict]:
        """Exact match search."""
        return self.courses.find_one({"name": query})

    def search_courses(self, query: str, limit: int = 10) -> List[Dict]:
        """Fuzzy search for inline mode."""
        return list(self.courses.find(
            {"name": {"$regex": query, "$options": "i"}}
        ).limit(limit))

    def get_all_courses_sorted(self) -> List[Dict]:
        """Returns all courses sorted alphabetically."""
        return list(self.courses.find({}).sort("name", 1))

    # --- COUPON METHODS ---

    def create_coupon(self, code: str, creator_id: int):
        """Creates a new coupon."""
        self.coupons.insert_one({
            "code": code,
            "active": True,
            "created_by": creator_id,
            "created_at": datetime.now()
        })

    def redeem_coupon(self, code: str, user_id: int) -> bool:
        """Attempts to redeem a coupon. Returns Success/Fail."""
        coupon = self.coupons.find_one({"code": code, "active": True})
        if coupon:
            self.coupons.update_one(
                {"_id": coupon['_id']},
                {"$set": {"active": False, "redeemed_by": user_id, "redeemed_at": datetime.now()}}
            )
            return True
        return False

    # --- STATS ---
    def get_system_stats(self) -> Dict[str, int]:
        return {
            "users": self.users.count_documents({}),
            "premium": self.users.count_documents({"authorized": True}),
            "courses": self.courses.count_documents({}),
            "coupons": self.coupons.count_documents({})
        }


# Initialize DB Global Instance
db_manager = DatabaseManager(Config.MONGO_URI)


# ==============================================================================
# 🌐 CLASS: WEB SERVER (KEEP ALIVE FOR RENDER)
# ==============================================================================

class WebServer:
    """
    Runs a minimal Flask server in a separate thread.
    This satisfies Render's requirement for a web service to bind to a port.
    """
    
    app = Flask(__name__)

    @app.route('/')
    def health_check():
        return "Affanoi Bot Status: ONLINE (Healthy)", 200

    @classmethod
    def run(cls):
        """Starts the Flask app on the configured port."""
        try:
            cls.app.run(host='0.0.0.0', port=Config.PORT, debug=False, use_reloader=False)
        except Exception as e:
            logging.error(f"WebServer Error: {e}")

    @classmethod
    def start_in_thread(cls):
        """Spawns the server in a daemon thread."""
        t = threading.Thread(target=cls.run, daemon=True)
        t.start()
        logging.info(f"✅ WebServer: Started on port {Config.PORT}")


# ==============================================================================
# 🤖 CLASS: BOT LOGIC & HANDLERS
# ==============================================================================

class BotHandlers:
    """
    Container for all Telegram Event Handlers.
    Separating logic from configuration and data.
    """

    # --------------------------------------------------------------------------
    # UTILITY METHODS
    # --------------------------------------------------------------------------

    @staticmethod
    def get_user_status(user_id: int) -> str:
        """
        Determines user permission level.
        Returns: 'admin', 'premium', 'referral_qualified', 'free'
        """
        if user_id in Config.ADMIN_IDS:
            return 'admin'
        
        user = db_manager.get_user(user_id)
        if not user:
            return 'free'
        
        # Priority 1: Premium
        if user.get("authorized", False):
            return 'premium'
        
        # Priority 2: Referral Expiry Check
        reset_time = user.get("referral_reset_time")
        if reset_time and datetime.now() > reset_time:
            db_manager.reset_referral_status(user_id)
            return 'free'

        # Priority 3: Referral Qualified
        if user.get("referral_count", 0) >= Config.REFERRAL_THRESHOLD:
            # Fix legacy data missing timer
            if not reset_time:
                expiry = datetime.now() + timedelta(hours=Config.TRIAL_DURATION_HOURS)
                db_manager.set_referral_expiry(user_id, expiry)
            return 'referral_qualified'
            
        return 'free'

    @staticmethod
    async def check_subscription(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
        """
        Verifies Force Join.
        Returns True if subscribed or if check fails (fail-open).
        """
        try:
            member = await context.bot.get_chat_member(
                chat_id=Config.FORCE_JOIN_CHANNEL, 
                user_id=user_id
            )
            if member.status in [constants.ChatMemberStatus.LEFT, constants.ChatMemberStatus.BANNED]:
                return False
            return True
        except Exception as e:
            logging.warning(f"⚠️ Sub Check Failed: {e}")
            return True # Fail open to prevent locking users if bot is admin-restricted

    @staticmethod
    async def auto_delete_task(context: ContextTypes.DEFAULT_TYPE):
        """Background task to delete temporary messages."""
        job = context.job
        try:
            await context.bot.delete_message(chat_id=job.chat_id, message_id=job.data)
        except BadRequest:
            pass # Message likely already deleted
        except Exception as e:
            logging.error(f"Auto-delete error: {e}")

    # --------------------------------------------------------------------------
    # COMMAND HANDLERS
    # --------------------------------------------------------------------------

    @classmethod
    async def start(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/start command handler."""
        user = update.effective_user
        args = context.args
        
        # Registration & Referral
        is_new = db_manager.register_user(user)
        
        # Logic: If user is new AND has args, process referral
        if is_new and args:
            try:
                referrer_id = int(args[0])
                # We already handled DB increment in register_user, now just notify
                if referrer_id != user.id:
                    ref_data = db_manager.get_user(referrer_id)
                    if ref_data:
                        count = ref_data.get("referral_count", 0)
                        
                        # Notify Referrer
                        msg_text = Texts.REFERRAL_SUCCESS.format(
                            count=count, 
                            status_msg=""
                        )
                        
                        if count == Config.REFERRAL_THRESHOLD:
                            # Activate Trial
                            expiry = datetime.now() + timedelta(hours=Config.TRIAL_DURATION_HOURS)
                            db_manager.set_referral_expiry(referrer_id, expiry)
                            msg_text = Texts.REFERRAL_UNLOCKED
                        elif count < Config.REFERRAL_THRESHOLD:
                            msg_text += f"\nNeed {Config.REFERRAL_THRESHOLD - count} more."
                        
                        await context.bot.send_message(referrer_id, msg_text, parse_mode=constants.ParseMode.HTML)
            except Exception as e:
                logging.error(f"Referral Notification Error: {e}")

        # Subscription Gate
        if not await cls.check_subscription(context, user.id):
            keyboard = [[InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{Config.FORCE_JOIN_CHANNEL.replace('@','')}")]]
            await update.message.reply_text(Texts.ACCESS_DENIED, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=constants.ParseMode.HTML)
            return

        # Dashboard Routing
        status = cls.get_user_status(user.id)
        
        if status == 'admin':
            await update.message.reply_text(Texts.ADMIN_PANEL, parse_mode=constants.ParseMode.HTML)
            
        elif status == 'premium':
            await update.message.reply_text(Texts.PREMIUM_DASHBOARD, parse_mode=constants.ParseMode.HTML)
            
        else:
            # Free / Referral User
            user_doc = db_manager.get_user(user.id)
            expiry_str = ""
            
            if status == 'referral_qualified':
                rt = user_doc.get("referral_reset_time")
                if rt:
                    delta = rt - datetime.now()
                    if delta.total_seconds() > 0:
                        h = int(delta.total_seconds() // 3600)
                        expiry_str = f"\n⏳ <b>Expires in:</b> {h} Hours"

            ref_link = f"https://t.me/{context.bot.username}?start={user.id}"
            
            await update.message.reply_text(
                Texts.FREE_DASHBOARD.format(
                    first_name=user.first_name,
                    price=Config.PREMIUM_PRICE,
                    threshold=Config.REFERRAL_THRESHOLD,
                    ref_link=ref_link,
                    referrals=user_doc.get("referral_count", 0),
                    expiry_info=expiry_str
                ),
                parse_mode=constants.ParseMode.HTML,
                disable_web_page_preview=True
            )

    @classmethod
    async def buy(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/buy command."""
        await update.message.reply_text(
            Texts.PAYMENT_INSTRUCTIONS.format(price=Config.PREMIUM_PRICE),
            parse_mode=constants.ParseMode.HTML
        )

    @classmethod
    async def submit_proof(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handles photos sent with /submit_proof."""
        user = update.effective_user
        if not update.message.photo:
            await update.message.reply_text("❌ Error: Please attach a screenshot.")
            return

        file_id = update.message.photo[-1].file_id
        
        # Create Verification Keyboard for Admin
        keyboard = [[InlineKeyboardButton("✅ Approve / Authorize", callback_data=f"auth_{user.id}")]]
        
        sent = 0
        for admin_id in Config.ADMIN_IDS:
            try:
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=file_id,
                    caption=f"💸 <b>PAYMENT PROOF</b>\nFrom: {user.first_name} ({user.id})",
                    parse_mode=constants.ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                sent += 1
            except Exception: pass
            
        if sent > 0:
            await update.message.reply_text("✅ <b>Proof Submitted!</b> Admin has been notified.")
        else:
            await update.message.reply_text("⚠️ System Error: Admins unreachable.")

    # --------------------------------------------------------------------------
    # COURSE & SEARCH LOGIC
    # --------------------------------------------------------------------------

    @classmethod
    async def search_message(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Main text handler for searching courses."""
        user = update.effective_user
        
        # Gatekeeper
        if not await cls.check_subscription(context, user.id):
            return

        query = update.message.text.lower().strip()
        status = cls.get_user_status(user.id)
        
        course = db_manager.find_course(query)
        
        if not course:
            await update.message.reply_text("🔍 Course not found. Use /courses to see available list.")
            return

        # 1. PREMIUM / ADMIN EXPERIENCE
        if status in ['premium', 'admin']:
            links = course.get('links', [])
            txt = f"✅ <b>{course['name'].upper()}</b> (Premium)\n\n"
            
            if links:
                txt += "\n".join([f"🔗 {link}" for link in links])
            else:
                txt += "📂 No direct links found."
            
            # NO AUTO DELETE, PROTECT CONTENT ENABLED
            await update.message.reply_text(
                txt,
                parse_mode=constants.ParseMode.HTML,
                disable_web_page_preview=True,
                protect_content=True
            )
            return

        # 2. REFERRAL QUALIFIED EXPERIENCE (TRIAL)
        elif status == 'referral_qualified':
            videos = course.get('videos', [])
            if not videos:
                await update.message.reply_text("😕 No sample videos available for this course.")
                return

            await update.message.reply_text(
                f"🎁 <b>Trial Active!</b> Sending 3 samples...\n"
                f"⚠️ <i>Auto-delete in {Config.AUTO_DELETE_SECONDS // 60} mins.</i>",
                parse_mode=constants.ParseMode.HTML
            )

            # Send max 3 videos with Auto-Delete
            for vid in videos[:3]:
                try:
                    msg = await context.bot.send_video(
                        chat_id=user.id,
                        video=vid,
                        caption=f"🎥 {course['name'].upper()} (Trial)",
                        protect_content=True
                    )
                    # Schedule Deletion
                    context.job_queue.run_once(
                        cls.auto_delete_task,
                        Config.AUTO_DELETE_SECONDS,
                        chat_id=user.id,
                        data=msg.message_id
                    )
                except Exception as e:
                    logging.error(f"Video Send Fail: {e}")
            
            # Upsell
            await update.message.reply_text(f"💎 Unlock Full Access: /buy")

        # 3. FREE USER EXPERIENCE
        else:
            await update.message.reply_text(
                f"🚫 <b>LOCKED: {course['name'].upper()}</b>\n\n"
                f"💰 Price: ₹{Config.PREMIUM_PRICE}/-\n"
                f"🔓 <b>Get Free Trial:</b> Refer {Config.REFERRAL_THRESHOLD} friends.\n"
                f"🔗 Link: <code>https://t.me/{context.bot.username}?start={user.id}</code>",
                parse_mode=constants.ParseMode.HTML
            )

    @classmethod
    async def inline_query(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Global search handler."""
        query = update.inline_query.query.lower()
        if not query: return
        
        results = []
        courses = db_manager.search_courses(query)
        
        for c in courses:
            results.append(
                InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title=c['name'].upper(),
                    description="Click to retrieve course content",
                    thumbnail_url="https://cdn-icons-png.flaticon.com/512/2436/2436874.png",
                    input_message_content=InputTextMessageContent(c['name']) # Sends name as text message
                )
            )
        
        await update.inline_query.answer(results, cache_time=0)

    # --------------------------------------------------------------------------
    # ADMIN COMMANDS
    # --------------------------------------------------------------------------

    @classmethod
    async def add_course(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/add [name] [link]"""
        if update.effective_user.id not in Config.ADMIN_IDS: return
        
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("Usage: /add [name] [link]")
            return
            
        links = [x for x in args if x.startswith("http")]
        name_parts = [x for x in args if not x.startswith("http")]
        name = " ".join(name_parts).lower()
        
        status = db_manager.add_course_links(name, links)
        await update.message.reply_text(f"✅ Course <b>{name}</b> {status}.", parse_mode=constants.ParseMode.HTML)

    @classmethod
    async def save_video(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/save [name] (Reply to video)"""
        if update.effective_user.id not in Config.ADMIN_IDS: return
        
        msg = update.message
        video = msg.video or (msg.reply_to_message.video if msg.reply_to_message else None)
        
        if not video or not context.args:
            await update.message.reply_text("Usage: Reply to video with /save [name]")
            return
            
        name = " ".join(context.args).lower()
        db_manager.add_course_video(name, video.file_id)
        await update.message.reply_text(f"✅ Video saved to {name}")

    @classmethod
    async def del_course(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in Config.ADMIN_IDS: return
        if not context.args: return
        
        name = " ".join(context.args).lower()
        if db_manager.delete_course(name):
            await update.message.reply_text(f"🗑️ {name} deleted.")
        else:
            await update.message.reply_text("❌ Not found.")

    @classmethod
    async def authorize(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in Config.ADMIN_IDS: return
        try:
            target = int(context.args[0])
            db_manager.authorize_user(target, True)
            await update.message.reply_text(f"✅ User {target} is now Premium.")
            await context.bot.send_message(target, "🎉 <b>You have been upgraded to Premium!</b>", parse_mode=constants.ParseMode.HTML)
        except:
            await update.message.reply_text("Usage: /authorize [ID]")

    @classmethod
    async def remove_user(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in Config.ADMIN_IDS: return
        try:
            target = int(context.args[0])
            db_manager.authorize_user(target, False)
            await update.message.reply_text(f"❌ User {target} revoked.")
        except: pass

    @classmethod
    async def create_coupon(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in Config.ADMIN_IDS: return
        if not context.args: return
        
        code = context.args[0].upper()
        db_manager.create_coupon(code, update.effective_user.id)
        await update.message.reply_text(f"✅ Coupon <code>{code}</code> created.", parse_mode=constants.ParseMode.HTML)

    @classmethod
    async def redeem_coupon(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/redeem [CODE]"""
        if not context.args:
            await update.message.reply_text("Usage: /redeem [CODE]")
            return
        
        code = context.args[0].upper()
        if db_manager.redeem_coupon(code, update.effective_user.id):
            db_manager.authorize_user(update.effective_user.id, True)
            await update.message.reply_text("🎉 <b>Success!</b> You are now Premium.", parse_mode=constants.ParseMode.HTML)
            
            # Notify Admin
            for admin in Config.ADMIN_IDS:
                await context.bot.send_message(admin, f"ℹ️ Coupon {code} used by {update.effective_user.first_name}")
        else:
            await update.message.reply_text("❌ Invalid/Expired Coupon.")

    @classmethod
    async def stats(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in Config.ADMIN_IDS: return
        
        s = db_manager.get_system_stats()
        msg = (
            f"📊 <b>STATS</b>\n"
            f"Users: {s['users']}\n"
            f"Premium: {s['premium']}\n"
            f"Courses: {s['courses']}\n"
            f"Coupons: {s['coupons']}"
        )
        await update.message.reply_text(msg, parse_mode=constants.ParseMode.HTML)

    @classmethod
    async def broadcast(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in Config.ADMIN_IDS: return
        
        msg = " ".join(context.args)
        if not msg: return
        
        users = db_manager.users.find({})
        await update.message.reply_text("📣 Sending...")
        count = 0
        
        for u in users:
            try:
                await context.bot.send_message(
                    u['user_id'], 
                    Texts.BROADCAST_HEADER.format(msg=msg),
                    parse_mode=constants.ParseMode.HTML
                )
                count += 1
                await asyncio.sleep(0.05)
            except Exception: pass
        
        await update.message.reply_text(f"✅ Sent to {count} users.")

    # --------------------------------------------------------------------------
    # CALLBACK QUERY HANDLER (BUTTONS)
    # --------------------------------------------------------------------------

    @classmethod
    async def handle_callback(cls, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        
        # Admin Payment Authorization
        if data.startswith("auth_"):
            if update.effective_user.id not in Config.ADMIN_IDS: return
            
            target_id = int(data.split("_")[1])
            db_manager.authorize_user(target_id, True)
            
            await query.edit_message_caption(
                caption=f"{query.message.caption}\n\n✅ <b>AUTHORIZED by {update.effective_user.first_name}</b>",
                parse_mode=constants.ParseMode.HTML
            )
            try:
                await context.bot.send_message(target_id, "🎉 <b>Payment Approved!</b> You are now Premium.")
            except: pass
            
        # Pagination
        elif data.startswith("page_"):
            page = int(data.split("_")[1])
            await cls.list_courses(update, context, page_num=page)

    @classmethod
    async def list_courses(cls, update: Update, context: ContextTypes.DEFAULT_TYPE, page_num: int = 0):
        """Handles /courses and pagination."""
        if isinstance(update, Update) and update.message:
            # Command Trigger
            if not await cls.check_subscription(context, update.effective_user.id):
                await update.message.reply_text(Texts.ACCESS_DENIED, parse_mode=constants.ParseMode.HTML)
                return
        
        all_courses = db_manager.get_all_courses_sorted()
        total = len(all_courses)
        
        if total == 0:
            if update.message: await update.message.reply_text("📭 Empty.")
            return

        # Pagination Logic
        start = page_num * Config.PAGINATION_LIMIT
        end = start + Config.PAGINATION_LIMIT
        page_items = all_courses[start:end]
        
        # Build Keyboard
        buttons = []
        for c in page_items:
            buttons.append([InlineKeyboardButton(
                f"📂 {c['name'].upper()}", 
                switch_inline_query_current_chat=c['name']
            )])
            
        nav = []
        if page_num > 0:
            nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page_{page_num-1}"))
        
        nav.append(InlineKeyboardButton(f"📄 {page_num+1}/{((total-1)//Config.PAGINATION_LIMIT)+1}", callback_data="noop"))
        
        if end < total:
            nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{page_num+1}"))
            
        if nav: buttons.append(nav)
        
        markup = InlineKeyboardMarkup(buttons)
        text = "📚 <b>COURSE LIBRARY</b>\nClick a button to select:"
        
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode=constants.ParseMode.HTML)
            except BadRequest: pass
        else:
            await update.message.reply_text(text, reply_markup=markup, parse_mode=constants.ParseMode.HTML)


# ==============================================================================
# 🚀 MAIN EXECUTOR
# ==============================================================================

def main():
    """
    Application Entry Point.
    Initializes Logger, Database, WebServer, and Telegram Bot.
    """
    
    # 1. Start Logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logger = logging.getLogger("AffanoiBot")
    logger.info("🚀 Initializing Affanoi Enterprise Bot...")

    # 2. Check Database Connection
    if not db_manager.client:
        logger.critical("❌ Failed to connect to DB. Exiting.")
        return

    # 3. Start Web Server (Daemon Thread)
    WebServer.start_in_thread()

    # 4. Build Telegram Application
    try:
        app = Application.builder().token(Config.BOT_TOKEN).build()
        
        # --- COMMANDS ---
        app.add_handler(CommandHandler("start", BotHandlers.start))
        app.add_handler(CommandHandler("help", BotHandlers.start))
        app.add_handler(CommandHandler("courses", BotHandlers.list_courses))
        app.add_handler(CommandHandler("buy", BotHandlers.buy))
        app.add_handler(CommandHandler("redeem", BotHandlers.redeem_coupon))
        
        # --- ADMIN ---
        app.add_handler(CommandHandler("add", BotHandlers.add_course))
        app.add_handler(CommandHandler("save", BotHandlers.save_video))
        app.add_handler(CommandHandler("del_course", BotHandlers.del_course))
        app.add_handler(CommandHandler("authorize", BotHandlers.authorize))
        app.add_handler(CommandHandler("remove", BotHandlers.remove_user))
        app.add_handler(CommandHandler("create_coupon", BotHandlers.create_coupon))
        app.add_handler(CommandHandler("broadcast", BotHandlers.broadcast))
        app.add_handler(CommandHandler("stats", BotHandlers.stats))
        
        # --- MESSAGE & QUERY HANDLERS ---
        app.add_handler(CallbackQueryHandler(BotHandlers.handle_callback))
        app.add_handler(InlineQueryHandler(BotHandlers.inline_query))
        
        # Payment Proofs
        app.add_handler(MessageHandler(
            filters.PHOTO & filters.CaptionRegex(r"^/submit_proof"), 
            BotHandlers.submit_proof
        ))
        
        # Video Saving (Admin)
        app.add_handler(MessageHandler(
            filters.VIDEO & filters.CaptionRegex(r"^/save"), 
            BotHandlers.save_video
        ))
        
        # Main Text Search
        app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            BotHandlers.search_message
        ))

        # 5. Run Polling
        logger.info("✅ Bot Handlers Registered. Starting Polling...")
        app.run_polling(drop_pending_updates=True)

    except Exception as e:
        logger.critical(f"❌ Application Crash: {e}")

if __name__ == "__main__":
    main()
