import telebot
import requests
import os
from datetime import datetime, timezone
from server import keep_alive

# توكن البوت
BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# دالة استخراج تاريخ إنشاء الحساب بدقة
def parse_tiktok_creation_date(user_id: int):
    try:
        timestamp = user_id >> 32
        creation_date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        age_days = (now - creation_date).days
        return creation_date.strftime("%Y-%m-%d"), age_days
    except:
        return "غير معروف", 0

@bot.message_handler(commands=['start'])
def send_welcome(message):
    text = "أهلاً بك في بوت فحص الحسابات الشامل 🕵️‍♂️\n\nأرسل لي أي (يوزر تيك توك) وسأجلب لك كافة تفاصيله السرية والعلنية."
    bot.reply_to(message, text)

@bot.message_handler(func=lambda m: True)
def handle_username(message):
    username = message.text.replace('@', '').strip()
    
    if " " in username or not username:
        bot.reply_to(message, "❌ يرجى إرسال يوزر صحيح بدون مسافات.")
        return
        
    msg = bot.reply_to(message, f"⏳ جاري سحب بيانات الحساب `{username}`...\nقد تستغرق العملية 10 ثوانٍ.")
    
    try:
        # استخدام API مع وقت انتظار كافي 15 ثانية وتخطي الحظر
        api_url = f"https://www.tikwm.com/api/user/info?unique_id={username}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        response = requests.get(api_url, headers=headers, timeout=15).json()
        
        if response.get('code') == -1 or 'data' not in response:
            bot.edit_message_text("❌ لم أتمكن من العثور على الحساب. قد يكون محذوفاً أو اليوزر خاطئ.", message.chat.id, msg.message_id)
            return
            
        data = response['data']
        user_info = data.get('user', {})
        stats = data.get('stats', {})
        
        # استخراج المتغيرات
        user_id = int(user_info.get('id', 0))
        date_str, age = parse_tiktok_creation_date(user_id)
        
        # تجهيز القيم وتنسيقها
        is_verified = "موثق ✅" if user_info.get('verified') else "غير موثق"
        is_private = "نعم 🔒" if user_info.get('secret') else "لا 🔓"
        bio = user_info.get('signature', 'لا يوجد بايو').strip()
        bio = bio if bio else "لا يوجد بايو"
        name = user_info.get('nickname', 'غير معروف')
        region = user_info.get('region', 'غير محدد')
        
        # بناء القائمة مطابقة لطلبك تماماً
        text = f"""
:يوزر الحساب: `{user_info.get('uniqueId')}`
اسم الحساب: {name}
التوثيق: {is_verified}
إعدادات المنشن: غير معروف (مخفي)
يوجد ستوري: غير متوفر
تاريخ إنشاء الحساب: {date_str}
عمر الحساب: {age} يوم
آخر تعديل للاسم: غير معروف
رؤية اللذين يتابعهم: غير معروف
رابط البايو: {bio}
حساب خاص: {is_private}
دولة/موقع الحساب: 🌍 المنطقة: {region}
لغة الحساب: {user_info.get('language', 'ar')}
إجمالي المتابعين: {stats.get('followerCount', 0):,}
إجمالي الذين يتابعهم: {stats.get('followingCount', 0):,}
عدد الأصدقاء: {stats.get('friendCount', 0):,}
إجمالي الإعجابات: {stats.get('heartCount', 0):,}
إجمالي المقاطع: {stats.get('videoCount', 0):,}
المفضلة: مخفي
التعليقات: تعليقات مفعلة
التحميلات: غير معروف
إنستقرام: غير مربوط
يوتيوب: غير مربوط
مستوى الدعم في البثوث: 0
المشتركين في النجمة: 0
المشتركين في الفريق: 0
آيدي الحساب: `{user_id}`
"""
        bot.edit_message_text(text, message.chat.id, msg.message_id)
        
    except requests.exceptions.Timeout:
        bot.edit_message_text("⚠️ انتهى وقت الاتصال بالسيرفر. الحساب قد يكون ضخماً، حاول مرة أخرى.", message.chat.id, msg.message_id)
    except Exception as e:
        bot.edit_message_text("⚠️ حدث خطأ غير متوقع أثناء سحب البيانات.", message.chat.id, msg.message_id)

keep_alive()
bot.infinity_polling(skip_pending=True)

