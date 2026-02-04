import asyncio
import logging
import os
import sqlite3
import datetime
import aiohttp  # For ping requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery

# Debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Debug info
logger.info(f"Current directory: {os.getcwd()}")
logger.info(f"Config path exists: {os.path.exists('config.py')}")
logger.info(f"Files in current directory: {os.listdir('.')}")

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import BOT_TOKEN
import database as db
import ai_handler as ai
import professional_pdf as report
import tts_handler as tts
from admin_panel import admin_router
from teacher_panel import teacher_router, get_teacher_menu
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from config import REQUIRED_CHANNEL

# Debug config loading
logger.info(f"BOT_TOKEN loaded: {'Yes' if BOT_TOKEN else 'No'}")
logger.info(f"Bot token length: {len(BOT_TOKEN) if BOT_TOKEN else 0}")

# Logging
logging.basicConfig(level=logging.INFO)

from fastapi import FastAPI
import uvicorn

# Bot va Dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# FastAPI (Render health check uchun)
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok", "message": "Ravon AI Bot is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Render server auto-ping task
async def keep_alive_ping():
    """Har 10 daqiqada serverga ping yuborish (Render uchun)"""
    ping_url = os.getenv('PING_URL')
    if not ping_url:
        logging.warning("PING_URL .env faylida topilmadi! Auto-ping o'chirildi.")
        return
    
    logging.info(f"Auto-ping ishga tushdi: {ping_url}")
    
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(ping_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        logging.info(f"✅ Ping muvaffaqiyatli: {response.status}")
                    else:
                        logging.warning(f"⚠️ Ping javobi: {response.status}")
        except Exception as e:
            logging.error(f"❌ Ping xatosi: {e}")
        
        # 10 daqiqa kutish (600 soniya)
        await asyncio.sleep(600)

# Admin panelga bot instance ni o'rnatish
from admin_panel import set_bot_instance
set_bot_instance(bot)

dp.include_router(teacher_router)
dp.include_router(admin_router)

# Kanalga a'zolikni tekshirish funksiyasi
async def check_subscription(user_id):
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# Klaviatura
def get_main_menu(user_id=None):
    buttons = [
        [KeyboardButton(text="🎤 Talaffuzni test qilish")],
        [KeyboardButton(text="🔊 Matnni audioga aylantirish")],
        [KeyboardButton(text="👥 Do'stlarni taklif qilish")],
        [KeyboardButton(text="👤 Profil 👤"), KeyboardButton(text="📊 Statistika 📊")],
        [KeyboardButton(text="💎 Premium 💎"), KeyboardButton(text="ℹ️ Yordam ℹ️")]
    ]
    
    if user_id and db.is_admin(user_id):
        buttons.append([KeyboardButton(text="🛠 Admin Panel")])
    elif user_id and db.is_teacher(user_id):
        buttons.append([KeyboardButton(text="👨‍🏫 O'qituvchi Paneli")])
        
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    args = message.text.split()
    referrer_id = args[1] if len(args) > 1 else None
    
    is_new_referral = db.add_user(user_id, message.from_user.full_name, message.from_user.username, referrer_id)
    
    # Referalga xabar yuborish
    if is_new_referral and referrer_id:
        try:
            await bot.send_message(
                referrer_id, 
                f"🎉 Tabriklaymiz! Do'stingiz {message.from_user.full_name} sizning havolangiz orqali qo'shildi.\n\n"
                "Sizga +3 ta test limiti berildi! 🚀"
            )
        except:
            pass
    
    if not await check_subscription(user_id):
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Kanalga a'zo bo'lish", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}")],
            [InlineKeyboardButton(text="Tekshirish ✅", callback_data="check_sub")]
        ])
        await message.answer(f"Botdan foydalanish uchun {REQUIRED_CHANNEL} kanaliga a'zo bo'lishingiz shart!", reply_markup=markup)
        return

    welcome_text = (
        f"Salom, {message.from_user.full_name}! 👋\n\n"
        "Ravon AI botiga xush kelibsiz! AI yordamida talaffuzingizni tekshiring."
    )
    await message.answer(welcome_text, reply_markup=get_main_menu(user_id))

@dp.callback_query(F.data == "check_sub")
async def callback_check_sub(callback: types.CallbackQuery):
    if await check_subscription(callback.from_user.id):
        await callback.message.delete()
        await callback.message.answer("Rahmat! Endi botdan foydalanishingiz mumkin.", reply_markup=get_main_menu(callback.from_user.id))
    else:
        await callback.answer("Siz hali kanalga a'zo emassiz!", show_alert=True)

@dp.message(Command("teacher"))
async def cmd_teacher(message: Message):
    if db.is_teacher(message.from_user.id):
        await message.answer("O'qituvchi paneli:", reply_markup=get_teacher_menu())
    else:
        await message.answer("Siz o'qituvchi emassiz.")

@dp.message(F.text == "👥 Do'stlarni taklif qilish")
async def show_referral_system(message: Message):
    user_id = message.from_user.id
    ref_stats = db.get_referral_stats(user_id)
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    
    text = (
        "👥 **Do'stlarni taklif qilish tizimi**\n\n"
        "Har **3 ta** do'stingizni taklif qiling va **+3 ta bepul test limiti** oling! 🚀\n\n"
        f"📊 Sizning statistikangiz:\n"
        f"├ Jami taklif qilingan: {ref_stats['total_referrals']} ta\n"
        f"├ Bonuslar soni: {ref_stats['bonus_count']} ta\n"
        f"└ Keyingi bonusgacha: {ref_stats['referrals_needed']} ta\n\n"
        f"🔗 Sizning referal havolangiz:\n`{ref_link}`\n\n"
        "Havolani nusxalang va do'stlaringizga yuboring!"
    )
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Havolani ulashish", url=f"https://t.me/share/url?url={ref_link}&text=Ingliz tili talaffuzingizni AI yordamida tekshirib ko'ring!")]
    ])
    
    await message.answer(text, reply_markup=markup, parse_mode="Markdown")

@dp.message(F.text == "👤 Profil 👤")
async def show_profile(message: Message):
    # Premium statusni tekshirish
    db.check_premium_status(message.from_user.id)
    
    user = db.get_user(message.from_user.id)
    ref_stats = db.get_referral_stats(message.from_user.id)
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    
    # Premium obuna ma'lumotlarini olish
    subscription = db.get_user_subscription(message.from_user.id)
    
    if user:
        text = (
            f"👤 **Sizning profilingiz**\n\n"
            f"🆔 ID: `{user[0]}`\n"
            f"👤 Ism: {user[1]}\n"
            f"🌐 Username: @{user[2]}\n"
            f"🎯 Test limiti: {user[4]} ta\n"
            f"🌟 Status: {'Premium 💎' if user[5] else 'Oddiy'}\n"
        )
        
        if subscription:
            text += f"📅 Obuna: {subscription[5]} ({subscription[6]} ta test)\n"
            text += f"⏰ Tugash sanasi: {subscription[4][:10]}\n"
        
        text += (
            f"\n👥 Referal statistikasi:\n"
            f"├ Taklif qilingan: {ref_stats['total_referrals']} ta\n"
            f"├ Bonuslar: {ref_stats['bonus_count']} ta\n"
            f"└ Keyingi bonusgacha: {ref_stats['referrals_needed']} ta\n\n"
            f"🔗 Referal havola: `{ref_link}`\n"
            f"(Har 3 ta do'st uchun +3 test limiti beriladi!)"
        )
        # Markdown formatlash xatosini oldini olish uchun parse_mode=None
        await message.answer(text)

@dp.message(F.text == "🛠 Admin Panel")
async def admin_panel_button(message: Message):
    if db.is_admin(message.from_user.id):
        from admin_panel import cmd_admin
        await cmd_admin(message)
    else:
        await message.answer("Siz admin emassiz.")

@dp.message(F.text == "👨‍🏫 O'qituvchi Paneli")
async def teacher_panel_button(message: Message):
    if db.is_teacher(message.from_user.id):
        from teacher_panel import get_teacher_menu
        help_text = (
            "👨‍🏫 **O'qituvchi Paneli**\n\n"
            "O'quvchilaringizning progressini kuzatish va materiallar qo'shishingiz mumkin.\n\n"
            "📚 **Materiallar:** So'z va matn qo'shishingiz mumkin\n"
            "👥 **O'quvchilar:**  O'quvchilar ro'yxati va statistikasi\n"
            "🤖 **AI yordam:** AI orqali materiallar yaratish"
        )
        await message.answer(help_text, reply_markup=get_teacher_menu(), parse_mode="Markdown")
    else:
        await message.answer("Siz o'qituvchi emassiz.")

@dp.message(F.text == "⬅️ Asosiy menyu")
async def back_to_main(message: Message):
    user_id = message.from_user.id
    # Foydalanuvchi holatlarini tozalash
    if user_id in user_states:
        del user_states[user_id]
    if user_id in current_test_texts:
        del current_test_texts[user_id]
    
    await message.answer("Asosiy menyuga qaytdingiz.", reply_markup=get_main_menu(message.from_user.id))

@dp.message(F.text == "📊 Statistika 📊")
async def user_stats(message: Message):
    # Premium statusni tekshirish
    db.check_premium_status(message.from_user.id)
    
    user = db.get_user(message.from_user.id)
    if not user: return
    
    subscription = db.get_user_subscription(message.from_user.id)
    
    text = (
        f"📊 **Sizning natijalaringiz**\n\n"
        f"🎤 Jami testlar: {user[4]} ta qoldi\n"
        f"🌟 Status: {'Premium 💎' if user[5] else 'Oddiy'}\n"
    )
    
    if subscription:
        text += f"📅 Obuna: {subscription[5]}\n"
        text += f"⏰ Tugash sanasi: {subscription[4][:10]}\n"
    
    # Oxirgi tahlil natijasini olish
    last_res = last_analysis_results.get(message.from_user.id)
    
    if last_res:
        text += "\nOxirgi tahlil natijalaringiz PDF formatida tayyor:"
        pdf_path = report.create_pdf_report(message.from_user.full_name, last_res)
    else:
        text += "\nHozircha tahlil natijalari yo'q. Birinchi testni o'tkazing!"
        pdf_path = None

    if pdf_path and os.path.exists(pdf_path):
        await message.answer_document(
            FSInputFile(pdf_path), 
            caption=text
        )
        os.remove(pdf_path)
    else:
        await message.answer(text)

@dp.message(F.text == "👤 Profil 👤")
async def show_profile_alias(message: Message):
    await show_profile(message)

@dp.callback_query(F.data == "referral_info")
async def callback_referral_info(callback: types.CallbackQuery):
    await show_referral_system(callback.message)
    await callback.answer()

@dp.callback_query(F.data == "buy_premium")
async def callback_buy_premium(callback: types.CallbackQuery):
    await show_premium(callback.message)
    await callback.answer()

async def show_premium(message: Message):
    tariffs = db.get_tariffs()
    
    text = "💎 **Ravon AI Premium Tariflari**\n\n"
    
    for tariff in tariffs:
        text += f"{tariff[0]}. **{tariff[1]}** - {tariff[2]:,} so'm\n"
        text += f"   - Davomiyligi: {tariff[3]} kun\n"
        text += f"   - Test limiti: {tariff[4]} ta\n\n"
    
    text += (
        "💳 **To'lov qilish uchun admin kartasiga pul o'tkazing:**\n"
        "`5614 6868 3029 9486` (Sanatbek Hamidov)\n\n"
        "**Qabul qilinadigan formatlar:**\n"
        "• `5614686830299486` (bo'shliqsiz)\n"
        "• `5614 6868 3029 9486` (bo'shliqlar bilan)\n\n"
        "To'lovdan so'ng, chekni yoki karta raqamingizni yuboring."
    )
    
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "💎 Premium 💎")
async def show_tariffs_alias(message: Message):
    await show_premium(message)

@dp.message(F.text == "ℹ️ Yordam ℹ️")
async def show_help(message: Message):
    help_text = (
        "❓ **Botdan qanday foydalanish kerak?**\n\n"
        "1. '🎤 Talaffuzni test qilish' tugmasini bosing.\n"
        "2. Matnni tanlang yoki o'zingiz yozing.\n"
        "3. Bot yuborgan ovozni eshiting.\n"
        "4. O'zingiz ham ovozli xabar yuboring.\n"
        "5. AI tahlilini va PDF hisobotingizni oling!\n\n"
        "👥 **Referal tizimi:** Har bir taklif qilingan do'stingiz uchun +3 ta bepul test limiti beriladi."
    )
    await message.answer(help_text, parse_mode="Markdown")

@dp.message(F.photo)
async def handle_payment_photo(message: Message):
    """To'lov check rasmini qabul qilish"""
    user_id = message.from_user.id
    
    # Foydalanuvchi to'lov rasm yuborish holatida ekanligini tekshirish
    if user_id in payment_states and payment_states[user_id]['step'] == 'waiting_photo':
        # Rasimni saqlash
        file = await bot.get_file(message.photo[-1].file_id)
        
        # Faylni yuklab olish - to'g'ri usul
        file_path = f"payment_check_{user_id}_{message.photo[-1].file_id}.jpg"
        
        # File obyektini yuklab olish (BytesIO qaytaradi)
        file_content = await bot.download_file(file.file_path)
        
        # Faylni saqlash - BytesIO dan o'qish
        with open(file_path, 'wb') as f:
            f.write(file_content.read())
        
        # To'lov ma'lumotlarini olish
        card_number = payment_states[user_id]['card_number']
        amount = payment_states[user_id]['amount']
        tariff_id = payment_states[user_id]['tariff_id']
        
        # To'lov yaratish
        db.create_payment(user_id, amount, card_number, message.photo[-1].file_id)
        
        # Adminga xabar yuborish (rasm bilan)
        await notify_admins_about_payment_with_photo(user_id, amount, card_number, message.photo[-1].file_id)
        
        # Holatni tozalash
        del payment_states[user_id]
        
        await message.answer("📸 **To'lov cheki qabul qilindi!**\n\nAdmin tasdiqlashini kuting. ✅\n\n"
                             "Chek tasdiqlangach, sizga avtomatik tarzda Premium beriladi.", 
                             parse_mode="Markdown")
    else:
        # Agar foydalanuvchi rasm yuborsa, lekin to'lov holatida bo'lmasa
        await message.answer("❌ Iltimos, avval karta raqamini yuboring, keyin chek rasmini yuboring.")

@dp.message(F.text.regexp(r'^[\d\s]{16,19}$')) # 16 raqamli karta raqami (bo'shliqlar bilan) yuborilsa
async def process_payment_request(message: Message):
    user_id = message.from_user.id
    # Bo'shliqlarni olib tashlash
    card_number = message.text.replace(' ', '').replace('-', '')
    
    # Faqat raqamlar ekanligini tekshirish
    if not card_number.isdigit() or len(card_number) != 16:
        await message.answer("❌ Iltimos, to'g'ri 16 raqamli karta raqamini yuboring.")
        return
    
    # Tariflarni ko'rsatish va tanlashni so'rash
    tariffs = db.get_tariffs()
    if not tariffs:
        await message.answer("❌ Hozircha tariflar mavjud emas. Iltimos, keyinroq urinib ko'ring.")
        return
    
    # Karta raqamini vaqtincha saqlash
    payment_states[user_id] = {
        'card_number': card_number,
        'step': 'selecting_tariff'
    }
    
    # Tariflarni ko'rsatish
    text = "� **To'lov uchun tarifni tanlang:**\n\n"
    markup = InlineKeyboardMarkup(inline_keyboard=[])
    
    for i, tariff in enumerate(tariffs):
        text += f"{i+1}. **{tariff[1]}** - {tariff[2]:,} so'm\n"
        text += f"   - Davomiyligi: {tariff[3]} kun\n"
        text += f"   - Test limiti: {tariff[4]} ta kunlik\n\n"
        
        # Tugma qo'shish
        markup.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{tariff[1]} - {tariff[2]:,} so'm", 
                callback_data=f"select_tariff_{tariff[0]}"
            )
        ])
    
    # Bekor qilish tugmasi
    markup.inline_keyboard.append([
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_payment")
    ])
    
    await message.answer(text, parse_mode="Markdown", reply_markup=markup)

@dp.callback_query(F.data.startswith('select_tariff_'))
async def select_tariff_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    # Foydalanuvchi to'lov jarayonida ekanligini tekshirish
    if user_id not in payment_states or payment_states[user_id]['step'] != 'selecting_tariff':
        await callback.answer("❌ To'lov jarayoni topilmadi", show_alert=True)
        return
    
    # Tarif ID ni olish
    tariff_id = int(callback.data.split('_')[2])
    
    # Tarif ma'lumotlarini olish
    tariffs = db.get_tariffs()
    selected_tariff = None
    for tariff in tariffs:
        if tariff[0] == tariff_id:
            selected_tariff = tariff
            break
    
    if not selected_tariff:
        await callback.answer("❌ Tarif topilmadi", show_alert=True)
        return
    
    # To'lov holatini yangilash
    payment_states[user_id].update({
        'tariff_id': tariff_id,
        'amount': selected_tariff[2],
        'step': 'waiting_photo'
    })
    
    # Rasm yuborishni so'rash
    await callback.message.answer(
        f"💳 **{selected_tariff[1]}** tanlandi!\n\n"
        f"To'lov summasi: {selected_tariff[2]:,} so'm\n\n"
        "Endi to'lov chekining rasmini yuboring 📸\n\n"
        "Rasmni yuborish uchun quyidagi formatlardan foydalaning:\n"
        "• Bankdan olingan chek rasmi\n"
        "• To'lov kvitansiyasi\n"
        "• Mobil ilova orqali olingan skrinshot", 
        parse_mode="Markdown"
    )
    
    await callback.answer()

@dp.callback_query(F.data == 'cancel_payment')
async def cancel_payment_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    # To'lov holatini tozalash
    if user_id in payment_states:
        del payment_states[user_id]
    
    await callback.message.answer("❌ To'lov bekor qilindi.")
    await callback.answer()

async def notify_admins_about_payment_with_photo(user_id, amount, card_number, photo_file_id):
    """Adminlarni yangi to'lov haqida rasm bilan xabardor qilish"""
    from config import ADMIN_IDS
    
    user = db.get_user(user_id)
    if not user:
        return
    
    # Karta raqamini maskalash (faqat oxirgi 4 ta raqam)
    masked_card = f"**** **** **** {card_number[-4:]}"
    
    text = (
        f"🔔 **YANGI TO'LOV SO'ROVI!**\n\n"
        f"👤 **Foydalanuvchi:** {user[1]} (@{user[2] or 'N/A'})\n"
        f"🆔 **User ID:** `{user_id}`\n"
        f"💰 **Summa:** {amount:,} so'm\n"
        f"💳 **Karta:** {masked_card}\n"
        f"⏰ **Vaqt:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"📸 **Chek rasmi quyida:**\n\n"
        f"📋 **Boshqarish uchun admin panelga o'ting!**"
    )
    
    # Barcha adminlarga xabar yuborish
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, parse_mode="Markdown")
            # Rasimni yuborish - xatolikni oldini olish
            try:
                await bot.send_photo(admin_id, photo_file_id, caption="📸 To'lov cheki")
            except Exception as photo_error:
                print(f"Rasm yuborishda xatolik: {photo_error}")
                # Inline keyboard qo'shish
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📋 To'lovni tasdiqlash", callback_data=f"approve_payment_{user_id}")],
                    [InlineKeyboardButton(text="❌ To'lovni rad etish", callback_data=f"reject_payment_{user_id}")]
                ])
                await bot.send_message(admin_id, "📸 Rasimni yuborishda xatolik yuz berdi, lekin to'lov ma'lumotlari yuqorida.", reply_markup=markup)
        except Exception as e:
            print(f"Admin {admin_id} ga xabar yuborishda xatolik: {e}")

async def notify_admins_about_payment(user_id, amount, card_number):
    """Adminlarni yangi to'lov haqida xabardor qilish (eski versiya)"""
    from config import ADMIN_IDS
    
    user = db.get_user(user_id)
    if not user:
        return
    
    # Karta raqamini maskalash (faqat oxirgi 4 ta raqam)
    masked_card = f"**** **** **** {card_number[-4:]}"
    
    text = (
        f"🔔 **YANGI TO'LOV SO'ROVI!**\n\n"
        f"👤 **Foydalanuvchi:** {user[1]} (@{user[2] or 'N/A'})\n"
        f"🆔 **User ID:** `{user_id}`\n"
        f"💰 **Summa:** {amount:,} so'm\n"
        f"💳 **Karta:** {masked_card}\n"
        f"⏰ **Vaqt:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"📋 **Boshqarish uchun admin panelga o'ting!**"
    )
    
    # Barcha adminlarga xabar yuborish
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, parse_mode="Markdown")
        except Exception as e:
            print(f"Admin {admin_id} ga xabar yuborishda xatolik: {e}")

@dp.message(F.text == "🔊 Matnni audioga aylantirish")
async def text_to_audio_start(message: Message):
    user_id = message.from_user.id
    
    # Limitni tekshirish
    limit_check = await check_user_limit(user_id)
    if not limit_check["allowed"]:
        await send_limit_exceeded_message(message, limit_check)
        return
    
    await message.answer("Iltimos, audioga aylantirmoqchi bo'lgan inglizcha matningizni yuboring:")

@dp.message(F.text == "🎤 Talaffuzni test qilish")
async def start_test(message: Message):
    user_id = message.from_user.id
    
    # Limitni tekshirish
    limit_check = await check_user_limit(user_id)
    if not limit_check["allowed"]:
        await send_limit_exceeded_message(message, limit_check)
        return

    # Oldingi holatlarni tozalash
    if user_id in user_states:
        del user_states[user_id]
    if user_id in current_test_texts:
        del current_test_texts[user_id]

    markup = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📝 So'z yozish"), KeyboardButton(text="📄 Matn yozish")],
        [KeyboardButton(text="🎲 Tasodifiy so'z"), KeyboardButton(text="📖 Tasodifiy matn")],
        [KeyboardButton(text="⬅️ Asosiy menyu")]
    ], resize_keyboard=True)
    await message.answer("Test rejimini tanlang:", reply_markup=markup)

# Foydalanuvchi holatini saqlash uchun dictionary
user_states = {}
# Oxirgi test matnini saqlash uchun
last_test_texts = {}
# Joriy test matnini saqlash uchun
current_test_texts = {}
# Oxirgi tahlil natijalarini saqlash uchun
last_analysis_results = {}
# To'lov holatini saqlash uchun
payment_states = {}

# Universal limit tekshiruv funksiyasi
async def check_user_limit(user_id):
    """Foydalanuvchi limitini tekshiradi va natijani qaytaradi"""
    # Adminlar uchun limitni tekshirmaslik
    if db.is_admin(user_id):
        return {
            "allowed": True, 
            "reason": "admin",
            "daily_limit": 999999,
            "word_limit": 999999
        }
    
    db.check_premium_status(user_id)
    
    user = db.get_user(user_id)
    if not user:
        db.add_user(user_id, "Unknown", "unknown")
        user = db.get_user(user_id)
    
    subscription = db.get_user_subscription(user_id)
    daily_limit = 3  # Default free
    word_limit = 40   # Default free
    
    if subscription:
        tariffs = db.get_tariffs()
        for t in tariffs:
            if t[0] == subscription[2]:
                daily_limit = t[4]  # test_limit
                word_limit = t[5]   # word_limit
                break
    
    today_tests = db.get_today_test_count(user_id)
    user = db.get_user(user_id)
    
    # Barcha foydalanuvchilar uchun limit tekshirish (Premium ham kiradi)
    # Agar foydalanuvchining limiti 0 yoki kam bo'lsa, bloklash
    if user[4] <= 0:
        return {
            "allowed": False, 
            "reason": "limit_exceeded",
            "today_tests": today_tests,
            "daily_limit": daily_limit,
            "word_limit": word_limit
        }
    
    # Kunlik limitni tekshirish
    if today_tests >= daily_limit:
        return {
            "allowed": False, 
            "reason": "daily_limit_exceeded",
            "today_tests": today_tests,
            "daily_limit": daily_limit,
            "word_limit": word_limit
        }
    
    return {
        "allowed": True, 
        "reason": "normal",
        "daily_limit": daily_limit,
        "word_limit": word_limit
    }

# Limit tugagan xabarini yuboruvchi funksiya
async def send_limit_exceeded_message(message, limit_info):
    """Limit tugaganda xabar yuboradi"""
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Do'stlarni taklif qilish", callback_data="referral_info")],
        [InlineKeyboardButton(text="💎 Premium sotib olish", callback_data="buy_premium")]
    ])
    await message.answer(
        f"⚠️ **Limit tugagan.**\n\n"
        f"Bugun {limit_info['today_tests']}/{limit_info['daily_limit']} ta bepul so'rov qildingiz va bonuslaringiz qolmagan. "
        "Ertaga qayta urinib ko'ring yoki do'stlaringizni taklif qilib bepul limitlarga ega bo'ling! 🚀", 
        reply_markup=markup,
        parse_mode="Markdown"
    )

@dp.message(F.text == "📝 So'z yozish")
async def word_input_start(message: Message):
    user_states[message.from_user.id] = "waiting_for_word"
    await message.answer("Iltimos, talaffuz qilmoqchi bo'lgan so'zingizni yozing (faqat bitta so'z):")

@dp.message(F.text == "📄 Matn yozish")
async def text_input_start(message: Message):
    user_states[message.from_user.id] = "waiting_for_text"
    await message.answer("Iltimos, talaffuz qilmoqchi bo'lgan matningizni yozing (kamida 3 ta so'z):")

@dp.message(F.text == "🎲 Tasodifiy so'z")
async def random_word(message: Message):
    user_id = message.from_user.id
    
    # Limitni tekshirish
    limit_check = await check_user_limit(user_id)
    if not limit_check["allowed"]:
        await send_limit_exceeded_message(message, limit_check)
        return
    
    # Database dan tasodifiy so'z olish
    word = db.get_random_material("word")
    if word:
        current_test_texts[user_id] = word  # Matnni saqlash
        user_states[user_id] = "waiting_for_voice"  # Ovoz kutish holatiga o'tkazish
        await message.answer(f"Quyidagi so'zni talaffuz qiling:\n\n**{word}**", parse_mode="Markdown")
        await message.answer("Endi ushbu so'zni ovozli xabar orqali yuboring.")
    else:
        # Agar database da so'z bo'lmasa, standart ro'yxatdan foydalanish
        words = ["hello", "world", "computer", "programming", "language", "beautiful", "important", "development", "technology", "education"]
        import random
        word = random.choice(words)
        current_test_texts[user_id] = word  # Matnni saqlash
        user_states[user_id] = "waiting_for_voice"  # Ovoz kutish holatiga o'tkazish
        await message.answer(f"Quyidagi so'zni talaffuz qiling:\n\n**{word}**", parse_mode="Markdown")
        await message.answer("Endi ushbu so'zni ovozli xabar orqali yuboring.")

@dp.message(F.text == "📖 Tasodifiy matn")
async def random_text(message: Message):
    user_id = message.from_user.id
    
    # Limitni tekshirish
    limit_check = await check_user_limit(user_id)
    if not limit_check["allowed"]:
        await send_limit_exceeded_message(message, limit_check)
        return
    
    # Database dan tasodifiy matn olish
    text = db.get_random_material("sentence")
    if text:
        current_test_texts[user_id] = text  # Matnni saqlash
        user_states[user_id] = "waiting_for_voice"  # Ovoz kutish holatiga o'tkazish
        await message.answer(f"Quyidagi matnni talaffuz qiling:\n\n**{text}**", parse_mode="Markdown")
        await message.answer("Endi ushbu matnni ovozli xabar orqali yuboring.")
    else:
        # Agar database da matn bo'lmasa, standart ro'yxatdan foydalanish
        texts = [
            "The weather is very nice today",
            "I love learning new languages",
            "Technology is changing our world",
            "Education is very important for everyone",
            "Programming helps solve many problems"
        ]
        import random
        text = random.choice(texts)
        current_test_texts[user_id] = text  # Matnni saqlash
        user_states[user_id] = "waiting_for_voice"  # Ovoz kutish holatiga o'tkazish
        await message.answer(f"Quyidagi matnni talaffuz qiling:\n\n**{text}**", parse_mode="Markdown")
        await message.answer("Endi ushbu matnni ovozli xabar orqali yuboring.")

# Foydalanuvchi yozgan matnni qabul qilish (state ga qarab)
@dp.message(F.text & ~F.text.startswith("/") & ~F.text.in_([
    "👤 Profil 👤", "📊 Statistika 📊", "ℹ️ Yordam ℹ️", "💎 Premium 💎", 
    "🎤 Talaffuzni test qilish", "📝 So'z yozish", "📄 Matn yozish", 
    "🎲 Tasodifiy so'z", "📖 Tasodifiy matn", 
    "✍️ O'zim matn kiritaman", "⬅️ Asosiy menyu", "🔊 Matnni audioga aylantirish",
    "👥 Do'stlarni taklif qilish", "🛠 Admin Panel", "👨‍🏫 O'qituvchi Paneli",
    "📊 Umumiy statistika", "💳 To'lov so'rovlari", "💰 Tariflar boshqaruvi",
    "🧹 Tariflarni tozalash", "🗑️ Fayllarni tozalash", "👨‍🏫 O'qituvchi tayinlash", 
    "📢 Xabar yuborish (Ad)", "👤 Foydalanuvchilar",
    "👨‍🎓 Mening o'quvchilarim", "👥 O'quvchi biriktirish", "📝 Material qo'shish", "🤖 AI yordam",
    "📚 Materiallarim", "📊 O'quvchilar statistikasi", "📤 Material yuborish", "📝 So'z qo'shish",
    "📄 Matn qo'shish", "🤖 AI so'z yaratish", "🤖 AI matn yaratish", "📝 So'z yuborish",
    "📄 Matn yuborish", "🤖 AI so'z yuborish", "🤖 AI matn yuborish", "📝 So'z yaratish (AI)", 
    "📄 Matn yaratish (AI)", "⬅️ O'qituvchi menyu"
]))
async def handle_user_input(message: Message):
    user_id = message.from_user.id
    
    # Agar o'qituvchi bo'lsa, o'tkazib yuborish (teacher_router ishlasin)
    if db.is_teacher(user_id):
        return
    
    # Faqat broadcast uchun admin tekshirish
    if db.is_admin(user_id):
        if message.reply_to_message and "barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring" in message.reply_to_message.text:
            return  # Admin panel tomonidan qayta ishlashga ruxsat berish
    
    text = message.text.strip()
    words = text.split()
    
    # Limitni tekshirish
    limit_check = await check_user_limit(user_id)
    if not limit_check["allowed"]:
        await send_limit_exceeded_message(message, limit_check)
        return
    
    # So'z limitini tekshirish
    word_limit = limit_check["word_limit"]
    if len(words) > word_limit:
        await message.answer(
            f"❌ **Matn juda uzun!**\n\n"
            f"Sizning tarifingizda maksimal {word_limit} ta so'z ruxsat etilgan. "
            f"Siz {len(words)} ta so'z yubordingiz.\n\n"
            f"Limitni oshirish uchun yuqori tariflardan birini tanlang! 💎", 
            parse_mode="Markdown"
        )
        return

    # Agar foydalanuvchi so'z kiritish rejimida bo'lsa
    if user_states.get(user_id) == "waiting_for_word":
        if len(words) == 1:
            current_test_texts[user_id] = text  # Matnni saqlash
            user_states[user_id] = "waiting_for_voice"  # Ovoz kutish holatiga o'tkazish
            await message.answer(f"Yaxshi! Endi **{text}** so'zini ovozli xabar orqali yuboring:", parse_mode="Markdown")
        else:
            await message.answer("❌ Iltimos, faqat bitta so'z yozing:")
    
    # Agar foydalanuvchi matn kiritish rejimida bo'lsa
    elif user_states.get(user_id) == "waiting_for_text":
        if len(words) >= 3:
            current_test_texts[user_id] = text  # Matnni saqlash
            user_states[user_id] = "waiting_for_voice"  # Ovoz kutish holatiga o'tkazish
            await message.answer(f"Yaxshi! Endi quyidagi matnni ovozli xabar orqali yuboring:\n\n**{text}**", parse_mode="Markdown")
        elif len(words) == 2:
            await message.answer("❌ Matnda kamida 3 ta so'z bo'lishi kerak. Iltimos, qayta yozing:")
        else:
            await message.answer("❌ Matnda kamida 3 ta so'z bo'lishi kerak. Iltimos, qayta yozing:")
    
    # Agar foydalanuvchi test rejimida bo'lmasa, matnni audioga aylantirish
    else:
        # Bu yerda TTS funksiyasi chaqiriladi
        await handle_text_to_audio(message)
    
async def handle_text_to_audio(message: Message):
    user_id = message.from_user.id
    
    # Agar foydalanuvchi test rejimida bo'lsa, TTS ishlamaydi
    if user_id in user_states:
        return
    
    # Agar o'qituvchi material qo'shish rejimida bo'lsa, TTS ishlamaydi
    from teacher_panel import teacher_states
    if user_id in teacher_states:
        return
    
    # Limitni tekshirish
    limit_check = await check_user_limit(user_id)
    if not limit_check["allowed"]:
        await send_limit_exceeded_message(message, limit_check)
        return

    content = message.text
    logger.info(f"TTS: Received text: '{content}'")
    await message.answer("Ovozli xabar tayyorlanmoqda... ⏳")
    
    logger.info("TTS: Calling text_to_speech function...")
    audio_path = tts.text_to_speech(content)
    logger.info(f"TTS: Function returned: {audio_path}")
    
    if audio_path:
        try:
            logger.info(f"TTS: Sending voice file: {audio_path}")
            await message.answer_voice(FSInputFile(audio_path), caption=f"Matn: {content[:50]}...")
            if os.path.exists(audio_path): 
                os.remove(audio_path)
                logger.info("TTS: Temporary file removed")
        except Exception as e:
            logger.error(f"TTS: Voice sending error: {e}")
            await message.answer("❌ Ovozli xabar yuborishda xatolik yuz berdi.")
            if os.path.exists(audio_path): 
                os.remove(audio_path)
    else:
        logger.error("TTS: No audio path returned")
        await message.answer("❌ Matnni ovozga aylantirishda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
        
        # Limitni kamaytirish (barcha foydalanuvchilar uchun)
        user = db.get_user(user_id)
        if user:
            db.decrement_limit(user_id)
            updated_user = db.get_user(user_id)
            limit_check = await check_user_limit(user_id)
            await message.answer(
                f"Limit bittaga kamaydi. Qolgan limit: {updated_user[4]}\n"
                f"📊 Kunlik limit: {limit_check['daily_limit']} ta so'rov"
            )

@dp.message(F.voice)
async def handle_voice(message: Message):
    user_id = message.from_user.id
    
    # Agar foydalanuvchi ovoz kutish holatida bo'lsa, testni boshlash
    if user_states.get(user_id) == "waiting_for_voice":
        # Test matnini olish
        original_text = current_test_texts.get(user_id)
        if not original_text:
            await message.answer("❌ Test matni topilmadi. Iltimos, qaytadan testni boshlang.")
            del user_states[user_id]  # Holatni tozalash
            return
        
        # Limitni tekshirish
        limit_check = await check_user_limit(user_id)
        if not limit_check["allowed"]:
            await send_limit_exceeded_message(message, limit_check)
            del user_states[user_id]  # Holatni tozalash
            return
        
        # Pronunciation test logic ni davom ettirish
        await process_pronunciation_test(message, user_id, original_text)
        del user_states[user_id]  # Test tugagandan so'ng holatni tozalash
        return
    
    # Limitni tekshirish (oddiy voice message uchun)
    limit_check = await check_user_limit(user_id)
    if not limit_check["allowed"]:
        await send_limit_exceeded_message(message, limit_check)
        return

    try:
        await message.answer("Ovozli xabar qabul qilindi. Tahlil qilinmoqda... ⏳")
        
        # Ovozli xabarni yuklab olish
        file = await bot.get_file(message.voice.file_id)
        
        # Faylni Telegram serveridan yuklab olish
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        
        import requests
        response = requests.get(file_url)
        
        if response.status_code == 200:
            # Vaqtinchalik fayl nomi
            temp_audio_path = f"temp_audio_{user_id}.ogg"
            
            # Faylni saqlash
            with open(temp_audio_path, "wb") as f:
                f.write(response.content)
        else:
            await message.answer("❌ Audio faylni yuklashda xatolik yuz berdi.")
            return
        
        # Ovozni matnga aylantirish (Gemini orqali)
        original_text = current_test_texts.get(message.from_user.id, "The quick brown fox jumps over the lazy dog")
        
        await message.answer("Ovozni matnga aylantirilmoqda... 🎤")
        transcribed_text = ai.transcribe_audio_with_gemini(temp_audio_path)
        
        if not transcribed_text:
            transcribed_text = original_text  # Agar transkripsiya ishlamasa
            await message.answer("⚠️ Ovozni matnga aylantirishda xatolik, asl matn bilan tahlil qilinmoqda...")
        else:
            await message.answer(f"🎯 Transkripsiya: \"{transcribed_text}\"")
        
        # AI orqali tahlil - original text bilan
        analysis_result = ai.analyze_pronunciation(transcribed_text, original_text)
        
        if analysis_result:
            # Natijani bazaga saqlash
            db.save_test_result(
                message.from_user.id, 
                message.voice.file_id, 
                original_text, 
                analysis_result.get('transcription', transcribed_text), 
                analysis_result['pronunciation_score'],
                analysis_result['fluency_score'], 
                analysis_result['accuracy_score'], 
                analysis_result['feedback']
            )
            
            # Oxirgi test ma'lumotlarini saqlash
            last_test_texts[message.from_user.id] = transcribed_text
            analysis_result['date'] = datetime.datetime.now().strftime("%Y-%m-%d")
            last_analysis_results[message.from_user.id] = analysis_result
            
            # Foydalanuvchiga natijani yuborish
            res_text = (
                "✅ **Tahlil yakunlandi!**\n\n"
                f"🎯 Talaffuz: {analysis_result['pronunciation_score']}/100\n"
                f"🗣 Ravonlik: {analysis_result['fluency_score']}/100\n"
                f"📝 Aniqlik: {analysis_result['accuracy_score']}/100\n\n"
                f"💡 **AI Tavsiyasi:** {analysis_result['feedback']}\n\n"
            )
            
            # Limit ma'lumotini qo'shish
            limit_check = await check_user_limit(user_id)
            subscription = db.get_user_subscription(user_id)
            
            today_tests = db.get_today_test_count(user_id)
            
            if subscription:
                tariffs = db.get_tariffs()
                for t in tariffs:
                    if t[0] == subscription[2]:
                        tariff_name = t[1]
                        daily_limit = t[4]
                        break
                res_text += f"🎉 **{tariff_name}** tarif foydalanuvchisi!\n"
                res_text += f"📊 Bugungi faollik: {today_tests}/{daily_limit} ta so'rov"
            else:
                res_text += f"📊 Bugungi faollik: {today_tests}/3 ta so'rov"
            
            # PDF yaratish
            pdf_path = report.create_pdf_report(message.from_user.full_name, analysis_result)
            
            # Tugmalar: To'g'ri talaffuzni eshitish va PDF yuklash
            if pdf_path and os.path.exists(pdf_path):
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔊 To'g'ri talaffuzni eshitish", callback_data="hear_correct")],
                    [InlineKeyboardButton(text="📄 PDF Hisobotni yuklab olish", callback_data="download_pdf")]
                ])
                
                await message.answer(res_text, reply_markup=markup, parse_mode="Markdown")
                
                # PDF ni o'chirish (agar kerak bo'lmasa)
                # os.remove(pdf_path)
            else:
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔊 To'g'ri talaffuzni eshitish", callback_data="hear_correct")]
                ])
                await message.answer(res_text, reply_markup=markup, parse_mode="Markdown")
                await message.answer("⚠️ PDF hisobotini yaratishda xatolik yuz berdi, ammo tahlil natijalari yuqorida ko'rsatilgan.")
            
            # Limitni kamaytirish (barcha foydalanuvchilar uchun)
            user = db.get_user(user_id)
            if user:
                db.decrement_limit(user_id)
                updated_user = db.get_user(user_id)
                limit_check = await check_user_limit(user_id)
                await message.answer(
                    f"Limit bittaga kamaydi. Qolgan limit: {updated_user[4]}\n"
                    f"📊 Kunlik limit: {limit_check['daily_limit']} ta so'rov"
                )
        else:
            await message.answer("AI tahlilida xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
        
        # Vaqtinchalik audio faylni o'chirish
        try:
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
        except:
            pass
            
    except Exception as e:
        logging.error(f"Voice handling error: {e}")
        await message.answer("Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
        
        # Xatolik holatida ham faylni o'chirishga harakat qilish
        try:
            if 'temp_audio_path' in locals() and os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
        except:
            pass

@dp.callback_query(F.data == "hear_correct")
async def callback_hear_correct(callback: types.CallbackQuery):
    # Oxirgi test qilingan matnni olish
    user_id = callback.from_user.id
    sample_text = last_test_texts.get(user_id, current_test_texts.get(user_id, "The quick brown fox jumps over the lazy dog"))
    
    audio_path = tts.text_to_speech(sample_text)
    if audio_path:
        await callback.message.answer_voice(FSInputFile(audio_path), caption="To'g'ri talaffuz")
        if os.path.exists(audio_path): os.remove(audio_path)
    else:
        await callback.message.answer("Ovozli xabar yaratishda xatolik yuz berdi.")
    await callback.answer()

@dp.callback_query(F.data == "download_pdf")
async def callback_download_pdf(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    last_res = last_analysis_results.get(user_id)
    
    if not last_res:
        await callback.message.answer("⚠️ Oxirgi tahlil natijalari topilmadi. Iltimos, qaytadan test o'tkazing.")
        await callback.answer()
        return

    await callback.message.answer("PDF hisobotingiz tayyorlanmoqda...")
    
    pdf_path = report.create_pdf_report(callback.from_user.full_name, last_res)
    if pdf_path and os.path.exists(pdf_path):
        await callback.message.answer_document(FSInputFile(pdf_path), caption="Sizning talaffuz hisobotingiz (PDF)")
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
    else:
        await callback.message.answer("PDF hisobotini yaratishda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
    await callback.answer()

async def process_pronunciation_test(message: Message, user_id: int, original_text: str):
    """Pronunciation testni qayta ishlash funksiyasi"""
    try:
        await message.answer("Ovozli xabar qabul qilindi. Tahlil qilinmoqda... ⏳")
        
        # Ovozli xabarni yuklab olish
        file = await bot.get_file(message.voice.file_id)
        
        # Faylni Telegram serveridan yuklab olish
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        
        import requests
        response = requests.get(file_url)
        
        if response.status_code == 200:
            # Vaqtinchalik fayl nomi
            temp_audio_path = f"temp_audio_{user_id}.ogg"
            
            # Faylni saqlash
            with open(temp_audio_path, "wb") as f:
                f.write(response.content)
        else:
            await message.answer("❌ Audio faylni yuklashda xatolik yuz berdi.")
            return
        
        # Ovozni matnga aylantirish (Gemini orqali)
        await message.answer("Ovozni matnga aylantirilmoqda... 🎤")
        transcribed_text = ai.transcribe_audio_with_gemini(temp_audio_path)
        
        if not transcribed_text:
            transcribed_text = original_text  # Agar transkripsiya ishlamasa
            await message.answer("⚠️ Ovozni matnga aylantirishda xatolik, asl matn bilan tahlil qilinmoqda...")
        else:
            await message.answer(f"🎯 Transkripsiya: \"{transcribed_text}\"")
        
        # AI orqali tahlil - original text bilan
        analysis_result = ai.analyze_pronunciation(transcribed_text, original_text)
        
        if analysis_result:
            # Natijani bazaga saqlash
            db.save_test_result(
                user_id, 
                message.voice.file_id, 
                original_text, 
                analysis_result.get('transcription', transcribed_text), 
                analysis_result['pronunciation_score'],
                analysis_result['fluency_score'], 
                analysis_result['accuracy_score'], 
                analysis_result['feedback']
            )
            
            # Oxirgi test ma'lumotlarini saqlash
            last_test_texts[user_id] = transcribed_text
            analysis_result['date'] = datetime.datetime.now().strftime("%Y-%m-%d")
            last_analysis_results[user_id] = analysis_result
            
            # Foydalanuvchiga natijani yuborish
            res_text = (
                "✅ **Tahlil yakunlandi!**\n\n"
                f"🎯 Talaffuz: {analysis_result['pronunciation_score']}/100\n"
                f"🗣 Ravonlik: {analysis_result['fluency_score']}/100\n"
                f"📝 Aniqlik: {analysis_result['accuracy_score']}/100\n\n"
                f"💡 **AI Tavsiyasi:** {analysis_result['feedback']}\n\n"
            )
            
            # Limit ma'lumotini qo'shish
            limit_check = await check_user_limit(user_id)
            subscription = db.get_user_subscription(user_id)
            
            today_tests = db.get_today_test_count(user_id)
            
            if subscription:
                tariffs = db.get_tariffs()
                for t in tariffs:
                    if t[0] == subscription[2]:
                        tariff_name = t[1]
                        daily_limit = t[4]
                        break
                res_text += f"🎉 **{tariff_name}** tarif foydalanuvchisi!\n"
                res_text += f"📊 Bugungi faollik: {today_tests}/{daily_limit} ta so'rov"
            else:
                res_text += f"📊 Bugungi faollik: {today_tests}/3 ta so'rov"
            
            # PDF yaratish
            pdf_path = report.create_pdf_report(message.from_user.full_name, analysis_result)
            
            # Tugmalar: To'g'ri talaffuzni eshitish va PDF yuklash
            if pdf_path and os.path.exists(pdf_path):
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔊 To'g'ri talaffuzni eshitish", callback_data="hear_correct")],
                    [InlineKeyboardButton(text="📄 PDF Hisobotni yuklab olish", callback_data="download_pdf")]
                ])
                
                await message.answer(res_text, reply_markup=markup, parse_mode="Markdown")
                
                # PDF ni o'chirish (agar kerak bo'lmasa)
                # os.remove(pdf_path)
            else:
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔊 To'g'ri talaffuzni eshitish", callback_data="hear_correct")]
                ])
                await message.answer(res_text, reply_markup=markup, parse_mode="Markdown")
            
            # Limitni kamaytirish (barcha foydalanuvchilar uchun)
            user = db.get_user(user_id)
            if user:
                db.decrement_limit(user_id)
                updated_user = db.get_user(user_id)
                limit_check = await check_user_limit(user_id)
                await message.answer(
                    f"Limit bittaga kamaydi. Qolgan limit: {updated_user[4]}\n"
                    f"📊 Kunlik limit: {limit_check['daily_limit']} ta so'rov"
                )
        else:
            await message.answer("AI tahlilida xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
        
        # Vaqtinchalik audio faylni o'chirish
        try:
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
        except:
            pass
            
    except Exception as e:
        logging.error(f"Pronunciation test error: {e}")
        await message.answer("Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
        
        # Xatolik holatida ham faylni o'chirishga harakat qilish
        try:
            if 'temp_audio_path' in locals() and os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
        except:
            pass

async def main():
    db.init_db()
    print("Bot modulli tizimda ishga tushmoqda...")
    
    # Render server uchun auto-ping taskni ishga tushirish
    asyncio.create_task(keep_alive_ping())
    
    # FastAPI serverini backgroundda ishga tushirish
    port = int(os.getenv("PORT", 10000))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    
    # Ikkalasini ham birga ishga tushirish
    await asyncio.gather(
        server.serve(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi")
