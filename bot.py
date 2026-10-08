import telebot
import requests
import os
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from server import keep_alive

# جلب توكن البوت من متغيرات ريندر
BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# قائمة المنصات للرادار السريع
PLATFORMS = {
    "تيك توك": "https://www.tiktok.com/@{}",
    "إنستغرام": "https://www.instagram.com/{}/",
    "فيسبوك": "https://www.facebook.com/{}",
    "سناب شات": "https://www.snapchat.com/add/{}",
    "تليجرام": "https://t.me/{}",
    "إكس (تويتر)": "https://twitter.com/{}",
    "جيت هاب": "https://github.com/{}"
}

# دالة حساب تاريخ الإنشاء من الآيدي (تيك توك)
def parse_tiktok_creation_date(user_id: int):
    try:
        timestamp = user_id >> 32
        creation_date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        age_days = (now - creation_date).days
        return creation_date.strftime("%Y-%m-%d"), age_days
    except:
        return "غير معروف", 0

# دالة فحص وجود اليوزر في المنصات (الرادار)
def check_platform(platform, username):
    url = PLATFORMS[platform].format(username)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            # فلترة خاصة لتليجرام وتيك توك لأنهم يرجعون 200 حتى لو الحساب محذوف
            if platform == "تليجرام" and "tgme_page_extra" not in response.text:
                return f"🔹 {platform}: ❌ غير موجود"
            if platform == "تيك توك" and "tiktok-meta-tags" not in response.text:
                 return f"🔹 {platform}: ❌ غير موجود"
                 
            return f"🔹 {platform}: ✅ [موجود - اضغط للزيارة]({url})"
        elif response.status_code == 404:
            return f"🔹 {platform}: ❌ غير موجود (متاح)"
        else:
            return f"🔹 {platform}: ⚠️ محمي/غير معروف"
    except:
        return f"🔹 {platform}: ⚠️ خطأ بالاتصال"

# دالة سحب التفاصيل العميقة (حالياً تيك توك)
def get_tiktok_details(username):
    try:
        api_url = f"https://www.tikwm.com/api/user/info?unique_id={username}"
        response = requests.get(api_url, timeout=5).json()
        
        if response.get('code') == -1 or 'data' not in response:
            return None
            
        data = response['data']
        user_info = data.get('user', {})
        stats = data.get('stats', {})
        
        user_id = int(user_info.get('id', 0))
        date_str, age = parse_tiktok_creation_date(user_id)
        
        followers = stats.get('followerCount', 0)
        likes = stats.get('heartCount', 0)
        bio = user_info.get('signature', 'لا يوجد').strip()
        if not bio: bio = "لا يوجد"
        name = user_info.get('nickname', 'غير معروف')
        
        details = f"🎵 **تيك توك:**\n"
        details += f"- الاسم: {name}\n"
        details += f"- تاريخ الإنشاء: {date_str} (العمر: {age} يوم)\n"
        details += f"- المتابعين: {followers:,} | الإعجابات: {likes:,}\n"
        details += f"- البايو: {bio}\n"
        
        return details
    except:
        return None

@bot.message_handler(commands=['start'])
def send_welcome(message):
    text = "أهلاً بك في رادار الحسابات الشامل 🕵️‍♂️\n\nأرسل لي أي (يوزر) وسأجلب لك تفاصيله وأفحصه في جميع المنصات في ثوانٍ معدودة."
    bot.reply_to(message, text)

@bot.message_handler(func=lambda m: True)
def handle_username(message):
    username = message.text.replace('@', '').strip()
    
    if " " in username or not username:
        bot.reply_to(message, "❌ يرجى إرسال يوزر صحيح بدون مسافات.")
        return
        
    msg = bot.reply_to(message, f"⏳ جاري فحص اليوزر: `{username}` ...\nيرجى الانتظار ثواني.")
    
    # 1. محاولة جلب التفاصيل العميقة
    tiktok_details = get_tiktok_details(username)
    
    # 2. تشغيل رادار المنصات بنفس الوقت (سريع جداً)
    radar_results = []
    with ThreadPoolExecutor(max_workers=7) as executor:
        futures = {executor.submit(check_platform, name, username): name for name in PLATFORMS}
        for future in futures:
            radar_results.append(future.result())
            
    # 3. تجميع الرسالة النهائية وتنسيقها
    final_text = f"🕵️‍♂️ **تقرير الفحص الشامل لليوزر:** `{username}`\n\n"
    
    final_text += "📋 **1. تفاصيل الحساب:**\n"
    final_text += "======================\n"
    if tiktok_details:
        final_text += tiktok_details
    else:
        final_text += "⚠️ لم أتمكن من سحب التفاصيل العميقة (قد يكون الحساب غير موجود أو محمي).\n"
        
    final_text += "\n🌐 **2. رادار المنصات (حالة اليوزر):**\n"
    final_text += "======================\n"
    final_text += "\n".join(radar_results)
    
    final_text += "\n\n💡 *ملاحظة:* اضغط على كلمة (موجود) لفتح الحساب مباشرة."
    
    # تعديل الرسالة
    bot.edit_message_text(final_text, message.chat.id, msg.message_id, parse_mode="Markdown", disable_web_page_preview=True)

# تشغيل البوت والسيرفر الوهمي
keep_alive()
bot.infinity_polling(skip_pending=True)
