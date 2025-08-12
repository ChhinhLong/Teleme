import asyncio
import os
import re
import time
import json
import logging
from datetime import datetime
from urllib.parse import urlparse
import aiohttp
import yt_dlp
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    InputMediaVideo,
    InputMediaPhoto,
    InputMediaAudio
)
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode, ChatAction

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
BOT_USERNAME = "@DownloaderKhmerBot"
DEVELOPER = "@ChhinhLong"
TIMEOUT = 3600  # 1 hour timeout

# User statistics
user_stats = {}

class MediaDownloaderBot:
    def __init__(self):
        self.download_progress = {}
        
    def get_user_stats(self, user_id):
        """Get user download statistics"""
        if user_id not in user_stats:
            user_stats[user_id] = {
                'downloads': 0,
                'videos': 0,
                'audios': 0,
                'photos': 0,
                'joined': datetime.now().strftime('%Y-%m-%d')
            }
        return user_stats[user_id]
    
    def update_user_stats(self, user_id, media_type):
        """Update user statistics"""
        stats = self.get_user_stats(user_id)
        stats['downloads'] += 1
        if media_type == 'video':
            stats['videos'] += 1
        elif media_type == 'audio':
            stats['audios'] += 1
        elif media_type == 'photo':
            stats['photos'] += 1
    
    def get_main_keyboard(self):
        """Create main inline keyboard"""
        keyboard = [
            [
                InlineKeyboardButton("📹 វីដេអូ", callback_data="help_video"),
                InlineKeyboardButton("🎵 អូឌីយ៉ូ", callback_data="help_audio")
            ],
            [
                InlineKeyboardButton("📸 រូបភាព", callback_data="help_photo"),
                InlineKeyboardButton("📖 ការបង្រៀន", callback_data="tutorial")
            ],
            [
                InlineKeyboardButton("⚙️ ការកំណត់", callback_data="settings"),
                InlineKeyboardButton("📊 ស្ថិតិ", callback_data="stats")
            ],
            [
                InlineKeyboardButton("❌ បោះបង់", callback_data="abort"),
                InlineKeyboardButton("ℹ️ អំពីបត់", callback_data="about")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def is_supported_url(self, url):
        """Check if URL is from supported platforms"""
        supported_domains = [
            'tiktok.com', 'vm.tiktok.com',
            'youtube.com', 'youtu.be', 'm.youtube.com',
            'facebook.com', 'fb.watch', 'm.facebook.com',
            'instagram.com', 'instagr.am'
        ]
        
        try:
            parsed_url = urlparse(url.lower())
            domain = parsed_url.netloc.replace('www.', '')
            return any(supported in domain for supported in supported_domains)
        except:
            return False
    
    def get_platform_name(self, url):
        """Get platform name from URL"""
        url = url.lower()
        if 'tiktok' in url:
            return 'TikTok'
        elif 'youtube' in url or 'youtu.be' in url:
            return 'YouTube'
        elif 'facebook' in url or 'fb.watch' in url:
            return 'Facebook'
        elif 'instagram' in url:
            return 'Instagram'
        return 'Unknown'

# Initialize bot
bot = MediaDownloaderBot()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    user_id = user.id
    
    # Update user stats
    bot.get_user_stats(user_id)
    
    welcome_text = f"""
🎉 **ស្វាគមន៍មកកាន់ {BOT_USERNAME}!** 🎉

សួស្តី {user.first_name}! 👋

🤖 **ខ្ញុំជាបត់ទាញយកមេឌៀ** ដែលអាចជួយអ្នក:

📱 **គាំទ្រវេទិកា:**
• TikTok (វីដេអូ/រូបភាព)
• YouTube (វីដេអូ/អូឌីយ៉ូ)
• Facebook (វីដេអូ/រូបភាព)
• Instagram (វីដេអូ/រូបភាព/Story)

✨ **លក្ខណៈពិសេស:**
• ទាញយកលឿន ⚡
• គុណភាពខ្ពស់ 🎯
• មិនមានវាកយសម្ព័ន្ធ 🚫
• បង្ហាញភាគរយ % 📊

📝 **របៀបប្រើ:**
1. ផ្ញើតំណភ្ជាប់ពីវេទិកាគាំទ្រ
2. ជ្រើសរើសប្រភេទទាញយក
3. រង់ចាំការទាញយក

👨‍💻 **អ្នកបង្កើត:** {DEVELOPER}
🤖 **ឥណទានបត់:** {BOT_USERNAME}
"""
    
    # Send welcome message with keyboard
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=bot.get_main_keyboard()
    )
    
    # Send tutorial video (placeholder)
    tutorial_text = """
🎬 **វីដេអូបង្រៀន**

នេះគឺជាវីដេអូបង្រៀនពីរបៀបប្រើប្រាស់បត់:

1. ចម្លងតំណភ្ជាប់ពី TikTok, YouTube, Facebook ឬ Instagram
2. ផ្ញើតំណភ្ជាប់មកកាន់បត់
3. ជ្រើសរើសប្រភេទទាញយក (វីដេអូ/អូឌីយ៉ូ/រូបភាព)
4. រង់ចាំការទាញយក

💡 **គន្លឹះ:** បត់នឹងបញ្ជាក់ភ្លាមៗនៅពេលទទួលបានតំណភ្ជាប់!
"""
    
    await update.message.reply_text(tutorial_text, parse_mode=ParseMode.MARKDOWN)

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle URL messages"""
    user_id = update.effective_user.id
    url = update.message.text.strip()
    
    # React with eyes emoji
    try:
        await context.bot.set_message_reaction(
            chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
            reaction="👀"
        )
    except:
        pass  # Reaction might not be supported
    
    # Show typing
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING
    )
    
    if not bot.is_supported_url(url):
        await update.message.reply_text(
            "❌ **តំណភ្ជាប់មិនត្រឹមត្រូវ!**\n\n"
            "សូមផ្ញើតំណភ្ជាប់ពី:\n"
            "• TikTok\n"
            "• YouTube\n"
            "• Facebook\n"
            "• Instagram",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    platform = bot.get_platform_name(url)
    
    # Create download options keyboard
    keyboard = [
        [
            InlineKeyboardButton("📹 ទាញយកវីដេអូ", callback_data=f"download_video_{user_id}"),
            InlineKeyboardButton("🎵 ទាញយកអូឌីយ៉ូ", callback_data=f"download_audio_{user_id}")
        ],
        [
            InlineKeyboardButton("📸 ទាញយករូបភាព", callback_data=f"download_photo_{user_id}"),
            InlineKeyboardButton("ℹ️ ព័ត៌មានវីដេអូ", callback_data=f"info_{user_id}")
        ],
        [InlineKeyboardButton("❌ បោះបង់", callback_data="abort")]
    ]
    
    # Store URL in context
    context.user_data['current_url'] = url
    context.user_data['platform'] = platform
    
    await update.message.reply_text(
        f"🔗 **រកឃើញតំណភ្ជាប់ {platform}!**\n\n"
        f"📱 **វេទិកា:** {platform}\n"
        f"🔗 **តំណភ្ជាប់:** `{url[:50]}...`\n\n"
        "🤖 **ជ្រើសរើសមុខងារ:**",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    if data == "abort":
        await query.edit_message_text("❌ **ការប្រតិបត្តិត្រូវបានបោះបង់**")
        return
    
    elif data == "tutorial":
        tutorial_text = """
🎬 **ការបង្រៀនលម្អិត**

**១. ការទាញយកវីដេអូ:**
• ចម្លងតំណភ្ជាប់វីដេអូ
• ផ្ញើមកកាន់បត់
• ចុច "📹 ទាញយកវីដេអូ"

**២. ការទាញយកអូឌីយ៉ូ:**
• ចម្លងតំណភ្ជាប់វីដេអូ
• ចុច "🎵 ទាញយកអូឌីយ៉ូ"

**៣. ការទាញយករូបភាព:**
• ចម្លងតំណភ្ជាប់ពីប្រកាស
• ចុច "📸 ទាញយករូបភាព"

**៤. គាំទ្រវេទិកា:**
• TikTok ✅
• YouTube ✅
• Facebook ✅
• Instagram ✅

💡 **ចំណាំ:** បត់មានកំណត់ពេលវេលា ៣៦០០ វិនាទី
"""
        await query.edit_message_text(tutorial_text, parse_mode=ParseMode.MARKDOWN)
    
    elif data == "stats":
        stats = bot.get_user_stats(user_id)
        stats_text = f"""
📊 **ស្ថិតិរបស់អ្នក**

👤 **អ្នកប្រើ:** {update.effective_user.first_name}
📅 **ចូលរួមពី:** {stats['joined']}

📈 **ការទាញយក:**
• សរុប: {stats['downloads']}
• វីដេអូ: {stats['videos']} 📹
• អូឌីយ៉ូ: {stats['audios']} 🎵  
• រូបភាព: {stats['photos']} 📸

🤖 **ឥណទានបត់:** {BOT_USERNAME}
👨‍💻 **អ្នកបង្កើត:** {DEVELOPER}
"""
        await query.edit_message_text(stats_text, parse_mode=ParseMode.MARKDOWN)
    
    elif data == "about":
        about_text = f"""
ℹ️ **អំពី {BOT_USERNAME}**

🤖 **ឈ្មោះ:** Khmer Media Downloader Bot
📱 **កំណែ:** v2.0
👨‍💻 **អ្នកបង្កើត:** {DEVELOPER}

✨ **លក្ខណៈពិសេស:**
• ទាញយកលឿន ⚡
• គុណភាពខ្ពស់ 🎯
• ឥតគិតថ្លៃ ✅
• ពេញលេញខ្មែរ 🇰🇭

🛡️ **ការពារភាពឯកជន:**
• មិនរក្សាទុកតំណភ្ជាប់
• មិនរក្សាទុកឯកសារ
• ការពារអ្នកប្រើ ១០០%

📞 **ទំនាក់ទំនង:** {DEVELOPER}
🤖 **បត់:** {BOT_USERNAME}
"""
        await query.edit_message_text(about_text, parse_mode=ParseMode.MARKDOWN)
    
    elif data.startswith("download_"):
        await handle_download(update, context, query)

async def handle_download(update: Update, context: ContextTypes.DEFAULT_TYPE, query):
    """Handle download requests"""
    data = query.data
    action = data.split('_')[1]  # video, audio, or photo
    user_id = update.effective_user.id
    
    if 'current_url' not in context.user_data:
        await query.edit_message_text("❌ **មិនរកឃើញតំណភ្ជាប់! សូមផ្ញើតំណភ្ជាប់ម្តងទៀត**")
        return
    
    url = context.user_data['current_url']
    platform = context.user_data.get('platform', 'Unknown')
    
    # Update loading message
    loading_msg = await query.edit_message_text(
        f"⏳ **កំពុងដំណើរការ...**\n\n"
        f"📱 **វេទិកា:** {platform}\n"
        f"🎯 **ប្រភេទ:** {action.title()}\n"
        f"📊 **ភាគរយ:** 0%\n\n"
        f"🤖 **ឥណទានបត់:** {BOT_USERNAME}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        # Configure yt-dlp options
        if action == 'video':
            ydl_opts = {
                'format': 'best[height<=720]',
                'outtmpl': f'downloads/{user_id}_%(title)s.%(ext)s',
                'timeout': TIMEOUT,
            }
        elif action == 'audio':
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': f'downloads/{user_id}_%(title)s.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'timeout': TIMEOUT,
            }
        else:  # photo
            ydl_opts = {
                'writesubtitles': False,
                'writeautomaticsub': False,
                'outtmpl': f'downloads/{user_id}_%(title)s.%(ext)s',
                'timeout': TIMEOUT,
            }
        
        # Create downloads directory
        os.makedirs('downloads', exist_ok=True)
        
        # Progress hook
        async def progress_hook(d):
            if d['status'] == 'downloading':
                try:
                    percent = d.get('_percent_str', '0%').replace('%', '')
                    await loading_msg.edit_text(
                        f"⬇️ **កំពុងទាញយក...**\n\n"
                        f"📱 **វេទិកា:** {platform}\n"
                        f"🎯 **ប្រភេទ:** {action.title()}\n"
                        f"📊 **ភាគរយ:** {percent}%\n"
                        f"⚡ **ល្បឿន:** {d.get('_speed_str', 'N/A')}\n\n"
                        f"🤖 **ឥណទានបត់:** {BOT_USERNAME}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
        
        # Simulate progress updates
        for i in range(0, 101, 20):
            try:
                await loading_msg.edit_text(
                    f"⬇️ **កំពុងទាញយក...**\n\n"
                    f"📱 **វេទិកា:** {platform}\n"
                    f"🎯 **ប្រភេទ:** {action.title()}\n"
                    f"📊 **ភាគរយ:** {i}%\n"
                    f"⚡ **ល្បឿន:** {'█' * (i//10)}{'░' * (10-i//10)}\n\n"
                    f"🤖 **ឥណទានបត់:** {BOT_USERNAME}",
                    parse_mode=ParseMode.MARKDOWN
                )
                await asyncio.sleep(0.5)
            except:
                pass
        
        # Download with yt-dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            description = info.get('description', 'មិនមានការពិពណ៌នា')[:200] + "..." if info.get('description') else "មិនមានការពិពណ៌នា"
            
            # Download the file
            ydl.download([url])
        
        # Find downloaded file
        download_dir = 'downloads'
        files = [f for f in os.listdir(download_dir) if f.startswith(str(user_id))]
        
        if not files:
            await loading_msg.edit_text("❌ **ការទាញយកបរាជ័យ! សូមព្យាយាមម្តងទៀត**")
            return
        
        file_path = os.path.join(download_dir, files[0])
        
        # Update user stats
        bot.update_user_stats(user_id, action)
        
        # Prepare caption
        caption = f"""
🎉 **ទាញយកបានជោគជ័យ!**

📝 **ចំណងជើង:** {title}

📖 **ការពិពណ៌នា:** {description}

🤖 **ឥណទានបត់:** {BOT_USERNAME}
👨‍💻 **អ្នកបង្កើត:** {DEVELOPER}
"""
        
        # Send file
        await loading_msg.edit_text("📤 **កំពុងផ្ញើឯកសារ...**")
        
        if action == 'video':
            with open(file_path, 'rb') as video_file:
                await context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=video_file,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                    timeout=TIMEOUT
                )
        elif action == 'audio':
            with open(file_path, 'rb') as audio_file:
                await context.bot.send_audio(
                    chat_id=update.effective_chat.id,
                    audio=audio_file,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                    timeout=TIMEOUT
                )
        else:  # photo
            with open(file_path, 'rb') as photo_file:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=photo_file,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                    timeout=TIMEOUT
                )
        
        # Delete loading message
        await loading_msg.delete()
        
        # Clean up file
        try:
            os.remove(file_path)
        except:
            pass
            
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        await loading_msg.edit_text(
            f"❌ **ការទាញយកបរាជ័យ!**\n\n"
            f"🚫 **កំហុស:** {str(e)[:100]}\n\n"
            f"💡 **សូមព្យាយាម:**\n"
            f"• ពិនិត្យតំណភ្ជាប់\n"
            f"• ព្យាយាមម្តងទៀតក្រោយពេល\n"
            f"• ប្រាកដថាវីដេអូមិនឯកជន",
            parse_mode=ParseMode.MARKDOWN
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
🆘 **ជំនួយការប្រើប្រាស់**

**📋 ពាក្យបញ្ជា:**
• /start - ចាប់ផ្តើមបត់
• /help - បង្ហាញជំនួយ
• /stats - បង្ហាញស្ថិតិ
• /about - អំពីបត់

**🔗 គាំទ្រតំណភ្ជាប់:**
• TikTok: https://tiktok.com/@username/video/xxx
• YouTube: https://youtube.com/watch?v=xxx
• Facebook: https://facebook.com/xxx/videos/xxx
• Instagram: https://instagram.com/p/xxx

**💡 គន្លឹះប្រើប្រាស់:**
• ផ្ញើតំណភ្ជាប់ទៅបត់
• ជ្រើសរើសប្រភេទទាញយក
• រង់ចាំការដំណើរការ

🤖 **ទំនាក់ទំនង:** {DEVELOPER}
"""
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

def main():
    """Start the bot"""
    print(f"🤖 Starting {BOT_USERNAME}...")
    print(f"👨‍💻 Developer: {DEVELOPER}")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    
    # Start the bot
    print("✅ Bot started successfully!")
    application.run_polling()

if __name__ == '__main__':
    main()