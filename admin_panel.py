from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import database as db
import os

admin_router = Router()

# Global bot o'zgaruvchisi
bot = None

def set_bot_instance(bot_instance):
    """Bot instance ni o'rnatish"""
    global bot
    bot = bot_instance

def get_admin_menu():
    buttons = [
        [KeyboardButton(text="📊 Umumiy statistika")],
        [KeyboardButton(text="💳 To'lov so'rovlari")],
        [KeyboardButton(text="💰 Tariflar boshqaruvi"), KeyboardButton(text="🔢 Limitlarni boshqarish")],
        [KeyboardButton(text="🧹 Tariflarni tozalash"), KeyboardButton(text="👨‍🏫 O'qituvchi tayinlash")],
        [KeyboardButton(text="�️ Fayllarni tozalash"), KeyboardButton(text="� Xabar yuborish (Ad)")],
        [KeyboardButton(text="👤 Foydalanuvchilar"), KeyboardButton(text="⬅️ Asosiy menyu")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

@admin_router.message(Command("admin"))
async def cmd_admin(message: Message):
    # Agar bazada birorta ham admin bo'lmasa, birinchi bo'lib /admin yozgan odam admin bo'ladi
    conn = db.sqlite3.connect(db.DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM admins')
    admin_count = cursor.fetchone()[0]
    conn.close()
    
    if admin_count == 0:
        db.add_admin(message.from_user.id)
        await message.answer("Siz birinchi admin qilib tayinlandingiz! 👑")
    
    if db.is_admin(message.from_user.id):
        help_text = (
            "🛠 **Admin Boshqaruv Paneli**\n\n"
            "Botni boshqarish uchun quyidagi tugmalardan foydalaning. "
            "Endi o'qituvchi tayinlash va limitlarni boshqarish juda oson!\n\n"
            "📊 **Statistika:** Botdagi foydalanuvchilar va testlar.\n"
            "💳 **To'lovlar:** Yangi kelgan to'lovlarni tasdiqlash.\n"
            "💰 **Tariflar:** Narx va limitlarni o'zgartirish.\n"
            "🔢 **Limitlar:** Barcha foydalanuvchilar limitini boshqarish.\n"
            "👨‍🏫 **O'qituvchi tayinlash:** Foydalanuvchilarni o'qituvchi qilish.\n"
            "📢 **Reklama:** Barchaga xabar yuborish."
        )
        await message.answer(help_text, reply_markup=get_admin_menu(), parse_mode="Markdown")
    else:
        await message.answer("Kechirasiz, siz admin emassiz.")

@admin_router.message(F.text == "📊 Umumiy statistika")
async def show_admin_stats(message: Message):
    if db.is_admin(message.from_user.id):
        stats = db.get_stats()
        text = (
            "📊 **Bot kengaytirilgan statistikasi**\n\n"
            f"👥 **Foydalanuvchilar:**\n"
            f"├ Jami: {stats['total_users']}\n"
            f"└ Premium: {stats['premium_users']}\n\n"
            f"🚀 **API Ishlatilishi (Testlar):**\n"
            f"└ Jami o'tkazilgan testlar: {stats['total_tests']}\n\n"
            f"🔥 **Faollik:**\n"
            f"├ Oxirgi 24 soatda: {stats['active_users_24h']} ta user\n"
            f"└ Oxirgi 7 kunda: {stats['active_users_7d']} ta user"
        )
        await message.answer(text, parse_mode="Markdown")

@admin_router.message(F.text == "💳 To'lov so'rovlari")
async def view_payments(message: Message):
    if db.is_admin(message.from_user.id):
        payments = db.get_pending_payments()
        if not payments:
            await message.answer("📥 **Hozircha yangi to'lov so'rovlari yo'q.**\n\nBarcha to'lovlar tasdiqlangan!", parse_mode="Markdown")
            return
        
        await message.answer(f"🔔 **Jami {len(payments)} ta to'lov so'rovi bor:**\n\n", parse_mode="Markdown")
        
        for p in payments:
            # Foydalanuvchi ma'lumotlarini olish
            user = db.get_user(p[1])
            user_name = user[1] if user else f"User {p[1]}"
            user_username = f"@{user[2]}" if user and user[2] else "N/A"
            
            # Karta raqamini maskalash
            masked_card = f"**** **** **** {p[3][-4:]}" if len(p[3]) >= 4 else p[3]
            
            # To'lov vaqtini formatlash
            payment_time = p[6][:19] if len(p) > 6 else "Noma'lum"
            
            # Rasm borligini tekshirish
            has_photo = "📸 Rasmi bor" if len(p) > 4 and p[4] else "📷 Rasmi yo'q"
            
            text = (
                f"💳 **To'lov so'rovi #{p[0]}**\n\n"
                f"👤 **Foydalanuvchi:** {user_name}\n"
                f"🆔 **User ID:** `{p[1]}`\n"
                f"📱 **Username:** {user_username}\n"
                f"💰 **Summa:** {p[2]:,} so'm\n"
                f"💳 **Karta:** {masked_card}\n"
                f"📸 **Holat:** {has_photo}\n"
                f"⏰ **Vaqt:** {payment_time}\n"
                f"📋 **Status:** {p[5]}\n\n"
            )
            
            # Agar rasm bo'lsa, rasmni yuborish
            if len(p) > 4 and p[4]:
                try:
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"pay_approve_{p[0]}"),
                            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"pay_reject_{p[0]}")
                        ]
                    ])
                    await message.answer_photo(p[4], caption=text, reply_markup=kb, parse_mode="Markdown")
                except Exception as e:
                    print(f"Rasm yuborishda xatolik: {e}")
                    # Agar rasm yuborib bo'lmasa, text bilan yuborish
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"pay_approve_{p[0]}"),
                            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"pay_reject_{p[0]}")
                        ]
                    ])
                    await message.answer(text, reply_markup=kb, parse_mode="Markdown")
            else:
                # Rasmsiz to'lov
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"pay_approve_{p[0]}"),
                        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"pay_reject_{p[0]}")
                    ]
                ])
                await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@admin_router.callback_query(F.data.startswith("pay_"))
async def process_payment_callback(callback: CallbackQuery):
    if not db.is_admin(callback.from_user.id):
        await callback.answer("Siz admin emassiz!", show_alert=True)
        return

    action = callback.data.split("_")[1] # approve yoki reject
    payment_id = int(callback.data.split("_")[2])
    
    if action == "approve":
        user_id = db.update_payment_status(payment_id, 'approved')
        if user_id:
            try:
                # Rasm bilan xabar bo'lsa, caption ni o'zgartirish
                if callback.message.photo:
                    await callback.message.edit_caption(
                        f"✅ To'lov #{payment_id} tasdiqlandi va foydalanuvchiga premium berildi!",
                        reply_markup=None
                    )
                else:
                    # Oddiy text xabar bo'lsa, edit_text
                    await callback.message.edit_text(f"✅ To'lov #{payment_id} tasdiqlandi va foydalanuvchiga premium berildi!")
            except Exception as edit_error:
                # Agar edit qilib bo'lmasa, yangi xabar yuborish
                await callback.message.answer(f"✅ To'lov #{payment_id} tasdiqlandi va foydalanuvchiga premium berildi!")
                
            try:
                await bot.send_message(
                    user_id, 
                    "🎉 **Tabriklaymiz! To'lovingiz tasdiqlandi.**\n\n"
                    "💎 Sizga **Premium** maqomi berildi va kunlik test limitingiz ko'paytirildi!\n"
                    "Endi kuniga ko'proq testlardan foydalanishingiz mumkin.\n"
                    "Tarif ma'lumotlarini 👤 Profil 👤 bo'limida ko'rishingiz mumkin.",
                    parse_mode="Markdown"
                )
            except Exception as e:
                print(f"Xabar yuborishda xatolik: {e}")
        else:
            await callback.answer("Xatolik: To'lov topilmadi yoki allaqachon yakunlangan.", show_alert=True)
            
    elif action == "reject":
        user_id = db.update_payment_status(payment_id, 'rejected')
        if user_id:
            try:
                # Rasm bilan xabar bo'lsa, caption ni o'zgartirish
                if callback.message.photo:
                    await callback.message.edit_caption(
                        f"❌ To'lov #{payment_id} rad etildi.",
                        reply_markup=None
                    )
                else:
                    # Oddiy text xabar bo'lsa, edit_text
                    await callback.message.edit_text(f"❌ To'lov #{payment_id} rad etildi.")
            except Exception as edit_error:
                # Agar edit qilib bo'lmasa, yangi xabar yuborish
                await callback.message.answer(f"❌ To'lov #{payment_id} rad etildi.")
                
            try:
                await bot.send_message(
                    user_id, 
                    "❌ **Kechirasiz, siz yuborgan to'lov so'rovi rad etildi.**\n\n"
                    "Iltimos, ma'lumotlarni tekshirib qaytadan yuboring yoki admin bilan bog'laning.",
                    parse_mode="Markdown"
                )
            except Exception as e:
                print(f"Xabar yuborishda xatolik: {e}")
        else:
            await callback.answer("Xatolik: To'lov topilmadi.", show_alert=True)
    
    await callback.answer()

@admin_router.message(F.text == "👨‍🏫 O'qituvchi tayinlash")
async def start_assign_teacher(message: Message):
    if db.is_admin(message.from_user.id):
        users = db.get_all_users()
        
        if not users:
            await message.answer("❌ Hech qanday foydalanuvchi topilmadi!")
            return
        
        text = "👨‍🏫 **O'qituvchi tayinlash**\n\nQuyidagi foydalanuvchilardan birini tanlang:"
        
        # 3 ta foydalanuvchi har bir qatorda
        buttons = []
        current_row = []
        
        for i, user in enumerate(users[:15]):  # Birinchi 15 ta foydalanuvchi
            user_id, full_name, username = user[0], user[1] or "Ism yo'q", user[2] or "username yo'q"
            button_text = f"{full_name} (@{username})"
            
            current_row.append(InlineKeyboardButton(
                text=button_text, 
                callback_data=f"assign_teacher_{user_id}"
            ))
            
            if len(current_row) == 1:  # Har bir qatorda 1 ta foydalanuvchi
                buttons.append(current_row)
                current_row = []
        
        if current_row:
            buttons.append(current_row)
        
        # Agar foydalanuvchilar ko'p bo'lsa, qidirish tugmasi
        if len(users) > 15:
            buttons.append([InlineKeyboardButton(
                text="🔍 Boshqa foydalanuvchilarni qidirish",
                callback_data="search_users_teacher"
            )])
        
        buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_admin")])
        
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer(text, reply_markup=markup, parse_mode="Markdown")

@admin_router.callback_query(F.data.startswith("assign_teacher_"))
async def assign_teacher_callback(callback: CallbackQuery):
    if db.is_admin(callback.from_user.id):
        user_id = int(callback.data.split("_")[2])
        
        try:
            # Tekshirish - allaqachon o'qituvchi emasligini
            if db.is_teacher(user_id):
                await callback.answer("Bu foydalanuvchi allaqachon o'qituvchi!", show_alert=True)
                return
            
            db.add_teacher(user_id, callback.from_user.id)
            
            # Foydalanuvchi ma'lumotlarini olish
            user = db.get_user(user_id)
            if user:
                user_name = user[1] or "Ism yo'q"
                await callback.message.answer(
                    f"✅ **{user_name}** muvaffaqiyatli o'qituvchi qilib tayinlandi!\n"
                    f"🆔 ID: {user_id}",
                    parse_mode="Markdown"
                )
            else:
                await callback.message.answer(f"✅ Foydalanuvchi {user_id} muvaffaqiyatli o'qituvchi qilib tayinlandi!")
            
            await callback.answer("O'qituvchi tayinlandi!")
            
        except Exception as e:
            await callback.answer(f"Xatolik: {str(e)}", show_alert=True)

@admin_router.callback_query(F.data == "back_to_admin")
async def back_to_admin_callback(callback: CallbackQuery):
    if db.is_admin(callback.from_user.id):
        await callback.message.answer(
            "🛠 **Admin Paneliga qaytdingiz**",
            reply_markup=get_admin_menu(),
            parse_mode="Markdown"
        )
        await callback.answer()

@admin_router.message(F.text == "� Limitlarni boshqarish")
async def manage_limits(message: Message):
    if db.is_admin(message.from_user.id):
        text = (
            "🔢 **Limitlarni Boshqarish**\n\n"
            "Quyidagi amallardan birini tanlang:\n\n"
            "👥 **Barcha foydalanuvchilar limiti** - Barcha uchun umumiy limit o'rnatish\n"
            "🎯 **Bitta foydalanuvchi** - Ma'lum bir foydalanuvchi limitini o'zgartirish\n"
            "🔄 **Kunlik limitni tiklash** - Barcha foydalanuvchilar limitini tiklash"
        )
        
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="👥 Barcha uchun limit o'rnatish", callback_data="set_all_limits"),
                InlineKeyboardButton(text="🎯 Bitta foydalanuvchi limiti", callback_data="set_user_limit")
            ],
            [
                InlineKeyboardButton(text="🔄 Barcha limitlarni tiklash", callback_data="reset_all_limits"),
                InlineKeyboardButton(text="📊 Limit statistikasi", callback_data="limit_stats")
            ],
            [
                InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_admin")
            ]
        ])
        
        await message.answer(text, reply_markup=markup, parse_mode="Markdown")

@admin_router.callback_query(F.data == "set_all_limits")
async def set_all_limits_callback(callback: CallbackQuery):
    if db.is_admin(callback.from_user.id):
        await callback.message.answer(
            "👥 **Barcha foydalanuvchilar uchun limit**\n\n"
            "Yangi limitni kiriting (raqamda):\n"
            "Masalan: `5` (kuniga 5 ta test)\n\n"
            "⚠️ Eslatma: Bu barcha foydalanuvchilar limitini o'zgartiradi!",
            parse_mode="Markdown"
        )
        
        # State o'rnatish - keyingi xabarni kutish uchun
        # Bu yerda state management qo'shish kerak
        await callback.answer()

@admin_router.message(F.text.regexp(r'^\d+$'))
async def set_all_limits_handler(message: Message):
    """Barcha foydalanuvchilar limitini o'rnatish"""
    if db.is_admin(message.from_user.id):
        try:
            new_limit = int(message.text)
            
            if new_limit < 0 or new_limit > 100:
                await message.answer("❌ Limit 0 dan 100 gacha bo'lishi kerak!")
                return
            
            # Barcha foydalanuvchilar limitini yangilash
            conn = db.sqlite3.connect(db.DB_NAME)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET daily_limit = ? WHERE subscription_id IS NULL", (new_limit,))
            
            # Premium foydalanuvchilar limitini ham yangilash (agar kerak bo'lsa)
            cursor.execute("UPDATE users SET daily_limit = ? WHERE subscription_id IS NOT NULL", (new_limit,))
            
            conn.commit()
            conn.close()
            
            await message.answer(
                f"✅ Barcha foydalanuvchilar limiti {new_limit} taga o'zgartirildi!\n\n"
                f"👥 Oddiy foydalanuvchilar: {new_limit} ta\n"
                f"💎 Premium foydalanuvchilar: {new_limit} ta"
            )
            
        except ValueError:
            await message.answer("❌ Iltimos, faqat raam kiriting!")
        except Exception as e:
            await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")

@admin_router.message(F.text.regexp(r'^\d+$'))
async def set_user_limit_handler(message: Message):
    """Bitta foydalanuvchi limitini o'rnatish"""
    if db.is_admin(message.from_user.id):
        try:
            new_limit = int(message.text)
            
            if new_limit < 0 or new_limit > 100:
                await message.answer("❌ Limit 0 dan 100 gacha bo'lishi kerak!")
                return
            
            # Bu yerda state management kerak - qaysi foydalanuvchi tanlanganini bilish uchun
            # Hozircha xabar yuborish
            await message.answer(
                f"✅ Limit {new_limit} taga o'rnatildi!\n\n"
                f"⚠️ Eslatma: Bu barcha foydalanuvchilar limitini o'zgartiradi.\n"
                f"Agar faqat bitta foydalanuvchini o'zgartirmoqchi bo'lsangiz, "
                f"ildan foydalanuvchini tanlang."
            )
            
        except ValueError:
            await message.answer("❌ Iltimos, faqat raam kiriting!")
        except Exception as e:
            await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")

@admin_router.callback_query(F.data == "set_user_limit")
async def set_user_limit_callback(callback: CallbackQuery):
    if db.is_admin(callback.from_user.id):
        users = db.get_all_users()
        
        if not users:
            await callback.answer("❌ Hech qanday foydalanuvchi topilmadi!", show_alert=True)
            return
        
        text = "🎯 **Bitta foydalanuvchi limitini o'zgartirish**\n\nQuyidagi foydalanuvchilardan birini tanlang:"
        
        # 3 ta foydalanuvchi har bir qatorda
        buttons = []
        current_row = []
        
        for i, user in enumerate(users[:15]):  # Birinchi 15 ta foydalanuvchi
            user_id, full_name, username = user[0], user[1] or "Ism yo'q", user[2] or "username yo'q"
            button_text = f"{full_name} (@{username})"
            
            current_row.append(InlineKeyboardButton(
                text=button_text, 
                callback_data=f"edit_user_limit_{user_id}"
            ))
            
            if len(current_row) == 1:  # Har bir qatorda 1 ta foydalanuvchi
                buttons.append(current_row)
                current_row = []
        
        if current_row:
            buttons.append(current_row)
        
        # Agar foydalanuvchilar ko'p bo'lsa, qidirish tugmasi
        if len(users) > 15:
            buttons.append([InlineKeyboardButton(
                text="🔍 Boshqa foydalanuvchilarni qidirish",
                callback_data="search_users_limit"
            )])
        
        buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_limits")])
        
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.answer(text, reply_markup=markup, parse_mode="Markdown")
        await callback.answer()

@admin_router.callback_query(F.data.startswith("edit_user_limit_"))
async def edit_user_limit_callback(callback: CallbackQuery):
    if db.is_admin(callback.from_user.id):
        user_id = int(callback.data.split("_")[3])
        
        # Foydalanuvchi ma'lumotlarini olish
        user = db.get_user(user_id)
        if not user:
            await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
            return
        
        user_name = user[1] or "Ism yo'q"
        current_limit = user[4] or 0
        
        await callback.message.answer(
            f"🎯 **{user_name}** limitini o'zgartirish\n\n"
            f"🆔 ID: {user_id}\n"
            f"📊 Hozirgi limit: {current_limit} ta\n\n"
            f"Yangi limitni kiriting (raqamda):\n"
            f"Masalan: `10` (kuniga 10 ta test)",
            parse_mode="Markdown"
        )
        
        # State o'rnatish - keyingi xabarni ushlab qolish uchun
        # Bu yerda state management kerak
        await callback.answer()

@admin_router.callback_query(F.data == "back_to_limits")
async def back_to_limits_callback(callback: CallbackQuery):
    if db.is_admin(callback.from_user.id):
        from admin_panel import manage_limits
        await manage_limits(callback.message)
        await callback.answer()

@admin_router.callback_query(F.data == "reset_all_limits")
async def reset_all_limits_callback(callback: CallbackQuery):
    if db.is_admin(callback.from_user.id):
        try:
            # Barcha foydalanuvchilar limitini tiklash
            conn = db.sqlite3.connect(db.DB_NAME)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET daily_limit = 3 WHERE subscription_id IS NULL")
            cursor.execute("UPDATE users SET daily_limit = (SELECT daily_limit FROM tariffs WHERE users.subscription_id = tariffs.id) WHERE subscription_id IS NOT NULL")
            conn.commit()
            conn.close()
            
            await callback.message.answer("✅ Barcha foydalanuvchilar limiti muvaffaqiyatli tiklandi!")
            await callback.answer("Limitlar tiklandi!")
            
        except Exception as e:
            await callback.answer(f"Xatolik: {str(e)}", show_alert=True)

@admin_router.callback_query(F.data == "limit_stats")
async def limit_stats_callback(callback: CallbackQuery):
    if db.is_admin(callback.from_user.id):
        try:
            conn = db.sqlite3.connect(db.DB_NAME)
            cursor = conn.cursor()
            
            # Limit statistikasi
            cursor.execute("SELECT COUNT(*) FROM users WHERE daily_limit > 0")
            active_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(daily_limit) FROM users WHERE daily_limit > 0")
            avg_limit = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE daily_limit = 0")
            zero_limit_users = cursor.fetchone()[0]
            
            conn.close()
            
            text = (
                f"📊 **Limit Statistikasi**\n\n"
                f"👥 Faol foydalanuvchilar: {active_users} ta\n"
                f"📈 O'rtacha limit: {avg_limit:.1f} ta\n"
                f"⚠️ Limiti tugagan: {zero_limit_users} ta\n\n"
                f"🔄 Kunlik limitlar har soat 00:00 da tiklanadi."
            )
            
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_admin")]
            ])
            
            await callback.message.answer(text, reply_markup=markup, parse_mode="Markdown")
            await callback.answer()
            
        except Exception as e:
            await callback.answer(f"Xatolik: {str(e)}", show_alert=True)

@admin_router.message(F.text == "💰 Tariflar boshqaruvi")
async def manage_tariffs(message: Message):
    if db.is_admin(message.from_user.id):
        tariffs = db.get_tariffs()
        text = "💰 **Mavjud tariflar boshqaruvi**\n\n"
        
        for t in tariffs:
            text = (
                f"📌 **Tarif:** {t[1]}\n"
                f"💰 **Narxi:** {t[2]:,} so'm\n"
                f"⏳ **Muddati:** {t[3]} kun\n"
                f"📊 **Limit:** {t[4]} ta test\n\n"
                f"Tahrirlash uchun quyidagi formatda yuboring:\n"
                f"`/edit_tariff_{t[0]}_narx_kun_limit`"
            )
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"tariff_edit_{t[0]}")]
            ])
            
            await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@admin_router.callback_query(F.data.startswith("tariff_edit_"))
async def process_tariff_edit_callback(callback: CallbackQuery):
    tariff_id = callback.data.split("_")[2]
    await callback.message.answer(
        f"🛠 **Tarif #{tariff_id} ni tahrirlash**\n\n"
        f"Yangi ma'lumotlarni quyidagi formatda yuboring:\n"
        f"`/edit_tariff_{tariff_id}_narx_kun_limit`\n\n"
        f"Masalan: `/edit_tariff_{tariff_id}_25000_30_50`",
        parse_mode="Markdown"
    )
    await callback.answer()

@admin_router.message(F.text.startswith("/edit_tariff_"))
async def edit_tariff_handler(message: Message):
    if db.is_admin(message.from_user.id):
        try:
            parts = message.text.split("_")
            tariff_id = int(parts[2])
            price = int(parts[3])
            days = int(parts[4])
            limit = int(parts[5])
            
            # database.py dagi update_tariff funksiyasini chaqiramiz
            db.update_tariff(tariff_id, f"Tarif {tariff_id}", price, days, limit)
            
            await message.answer(f"✅ **Tarif #{tariff_id} muvaffaqiyatli yangilandi!**\n\n"
                               f"Yangi narx: {price:,} so'm\n"
                               f"Yangi muddat: {days} kun\n"
                               f"Yangi limit: {limit} ta test", 
                               parse_mode="Markdown")
        except Exception as e:
            await message.answer(f"❌ **Xatolik yuz berdi!**\n\nFormatni tekshiring: `/edit_tariff_ID_narx_kun_limit`", parse_mode="Markdown")

@admin_router.message(F.text == "📢 Xabar yuborish (Ad)")
async def start_broadcast(message: Message):
    if db.is_admin(message.from_user.id):
        text = (
            "📢 **E'lon yuborish**\n\n"
            "Quyidagilardan birini tanlang:\n\n"
            "📝 **Faqat matn** - Oddiy xabar yuboring\n"
            "🖼️ **Rasm + Izoh** - Rasm yuboring (caption bilan)\n"
            "🎥 **Video + Izoh** - Video yuboring (caption bilan)\n\n"
            "📋 **Cheklovlar:**\n"
            "• Rasm/Video maksimal: 20MB\n"
            "• Izoh maksimal: 1000 ta belgi\n"
            "• Izohsiz media qabul qilinmaydi!"
        )
        
        await message.answer(text, parse_mode="Markdown")

@admin_router.message(F.photo)
async def handle_broadcast_photo(message: Message):
    """Admin tomonidan yuborilgan rasmni barcha foydalanuvchilarga yuborish"""
    if not db.is_admin(message.from_user.id):
        return
    
    # Adminning oldingi xabarini tekshirish
    if message.reply_to_message and "📢 **E'lon yuborish**" in message.reply_to_message.text:
        # Rasm va izoh birga yuborilgan
        caption = message.caption or ""
        
        if len(caption) > 1000:
            await message.answer("❌ Izoh 1000 ta belgidan oshmasligi kerak!")
            return
        
        # Rasmni saqlash
        file = await bot.get_file(message.photo[-1].file_id)
        file_path = f"broadcast_photo_{message.from_user.id}_{message.photo[-1].file_id}.jpg"
        
        # Faylni yuklab olish
        file_content = await bot.download_file(file.file_path)
        with open(file_path, 'wb') as f:
            f.write(file_content.read())
        
        # To'g'ridan yuborish
        state = {
            'type': 'photo',
            'file_path': file_path,
            'file_id': message.photo[-1].file_id
        }
        
        await send_media_broadcast(state, caption, message.from_user.id)
        
        # Tozalash
        if os.path.exists(file_path):
            os.remove(file_path)
        
        await message.answer(
            f"📸 **Rasm e'loni yuborildi!**\n\n"
            f"📝 Izoh: {caption[:100]}{'...' if len(caption) > 100 else ''}\n\n"
            f"✅ Barcha foydalanuvchilarga yuborildi!",
            parse_mode="Markdown"
        )
    else:
        # Agar bu broadcast bo'lmasa, normal admin xabi sifatida qayta ishlash
        pass

@admin_router.message(F.video)
async def handle_broadcast_video(message: Message):
    """Admin tomonidan yuborilgan videoni barcha foydalanuvchilarga yuborish"""
    if not db.is_admin(message.from_user.id):
        return
    
    # Adminning oldingi xabarini tekshirish
    if message.reply_to_message and "📢 **E'lon yuborish**" in message.reply_to_message.text:
        # Video va izoh birga yuborilgan
        caption = message.caption or ""
        
        if len(caption) > 1000:
            await message.answer("❌ Izoh 1000 ta belgidan oshmasligi kerak!")
            return
        
        # Videoni saqlash
        file = await bot.get_file(message.video.file_id)
        file_path = f"broadcast_video_{message.from_user.id}_{message.video.file_id}.mp4"
        
        # Faylni yuklab olish
        file_content = await bot.download_file(file.file_path)
        with open(file_path, 'wb') as f:
            f.write(file_content.read())
        
        # To'g'ridan yuborish
        state = {
            'type': 'video',
            'file_path': file_path,
            'file_id': message.video.file_id,
            'duration': message.video.duration
        }
        
        await send_media_broadcast(state, caption, message.from_user.id)
        
        # Tozalash
        if os.path.exists(file_path):
            os.remove(file_path)
        
        await message.answer(
            f"🎥 **Video e'loni yuborildi!**\n\n"
            f"📊 Davomiyligi: {message.video.duration} soniya\n"
            f"📝 Izoh: {caption[:100]}{'...' if len(caption) > 100 else ''}\n\n"
            f"✅ Barcha foydalanuvchilarga yuborildi!",
            parse_mode="Markdown"
        )
    else:
        # Agar bu broadcast bo'lmasa, normal admin xabi sifatida qayta ishlash
        pass

# Global state for broadcast
broadcast_states = {}

async def send_media_broadcast(state, caption, admin_id):
    """Media bilan e'lon yuborish"""
    import database as db
    
    # Barcha faol foydalanuvchilarni olish
    users = db.get_all_users()
    
    success_count = 0
    error_count = 0
    
    for user in users:
        try:
            if state['type'] == 'photo':
                await bot.send_photo(
                    user[0], 
                    state['file_id'],
                    caption=caption,
                    parse_mode="Markdown"
                )
            elif state['type'] == 'video':
                await bot.send_video(
                    user[0],
                    state['file_id'],
                    caption=caption,
                    parse_mode="Markdown",
                    duration=state.get('duration', None)
                )
            success_count += 1
        except Exception as e:
            error_count += 1
            print(f"User {user[0]} ga media yuborishda xatolik: {e}")
    
    return {"success": success_count, "errors": error_count}

async def send_broadcast_to_all_users(text):
    """Xabarni barcha foydalanuvchilarga yuborish"""
    import database as db
    
    # Barcha faol foydalanuvchilarni olish
    users = db.get_all_users()
    
    success_count = 0
    error_count = 0
    
    for user in users:
        try:
            await bot.send_message(user[0], text)
            success_count += 1
        except Exception as e:
            error_count += 1
            print(f"User {user[0]} ga xabar yuborishda xatolik: {e}")
    
    return {"success": success_count, "errors": error_count}

@admin_router.message(F.text == "👤 Foydalanuvchilar")
async def show_users_list(message: Message):
    if db.is_admin(message.from_user.id):
        users = db.get_all_users()
        total_users = len(users)
        
        if total_users == 0:
            await message.answer("📥 Hozircha hech qanday foydalanuvchi yo'q.")
            return
        
        text = f"👥 Barcha foydalanuvchilar\n\n"
        text += f"📊 Jami foydalanuvchilar: {total_users} ta\n\n"
        
        # Birinchi 10 ta foydalanuvchini ko'rsatish
        text += "Oxirgi qo'shilgan foydalanuvchilar:\n"
        count = 0
        for user_id in users[-10:]:  # Oxirgi 10 ta foydalanuvchi
            user = db.get_user(user_id)
            if user:
                count += 1
                status = "💎 Premium" if user[5] else "👤 Oddiy"
                # Foydalanuvchi ismidagi maxsus belgilarni tozalash
                safe_name = str(user[1]).replace('*', '').replace('_', '').replace('`', '').replace('[', '').replace(']', '')
                safe_username = str(user[2] or 'N/A').replace('*', '').replace('_', '').replace('`', '').replace('[', '').replace(']', '')
                text += f"{count}. {safe_name} (@{safe_username}) - {status}\n"
        
        if total_users > 10:
            text += f"\n... va yana {total_users - 10} ta foydalanuvchi"
        
        # Statistika qo'shish
        stats = db.get_stats()
        text += f"\n\n📈 Qisqacha statistika:\n"
        text += f"├ Premium foydalanuvchilar: {stats['premium_users']} ta\n"
        text += f"├ Oxirgi 24 soatda faol: {stats['active_users_24h']} ta\n"
        text += f"└ Oxirgi 7 kunda faol: {stats['active_users_7d']} ta"
        
        await message.answer(text)  # parse_mode ni olib tashladik

@admin_router.message(F.text == "🗑️ Fayllarni tozalash")
async def clean_files(message: Message):
    if db.is_admin(message.from_user.id):
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑️ Barcha fayllarni o'chirish", callback_data="clean_all_files")],
            [InlineKeyboardButton(text="📊 Fayl statistikasi", callback_data="file_stats")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_clean_files")]
        ])
        await message.answer(
            "🗑️ **Fayllarni tozalash**\n\n"
            "Qaysi amalni bajarmoqchisiz?\n\n"
            "• **Barcha fayllarni o'chirish** - vaqtinchalik fayllarni (PDF, audio, rasm) o'chiradi\n"
            "• **Fayl statistikasi** - serverdagi fayllar haqida ma'lumot beradi", 
            reply_markup=markup,
            parse_mode="Markdown"
        )

@admin_router.message(F.text == "🧹 Tariflarni tozalash")
async def clean_tariffs(message: Message):
    print(f"DEBUG: clean_tariffs message received from user {message.from_user.id}")
    print(f"DEBUG: User is admin: {db.is_admin(message.from_user.id)}")
    
    if db.is_admin(message.from_user.id):
        print("DEBUG: Sending tariff cleaning options...")
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧹 Takrorlarni o'chirish", callback_data="clean_duplicates")],
            [InlineKeyboardButton(text="🔄 Standart tariflarni qayta yaratish", callback_data="reset_tariffs")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_clean")]
        ])
        await message.answer(
            "🧹 **Tariflarni tozalash**\n\n"
            "Qaysi amalni bajarmoqchisiz?\n\n"
            "• **Takrorlarni o'chirish** - bir xil tariflarning takrorlarini o'chiradi\n"
            "• **Standart tariflarni qayta yaratish** - barcha eski tariflarni o'chirib, 7 ta standart tarif yaratadi", 
            reply_markup=markup,
            parse_mode="Markdown"
        )
        print("DEBUG: Message sent successfully")
    else:
        print("DEBUG: User is not admin")
        await message.answer("Siz admin emassiz!")

@admin_router.callback_query(F.data.in_(["clean_duplicates", "reset_tariffs", "cancel_clean", "clean_all_files", "file_stats", "cancel_clean_files", "back_to_file_menu"]))
async def handle_tariff_callbacks(callback: types.CallbackQuery):
    print(f"DEBUG: Callback received: {callback.data} from user {callback.from_user.id}")
    
    if not db.is_admin(callback.from_user.id):
        print(f"DEBUG: User {callback.from_user.id} is not admin")
        await callback.answer("Siz admin emassiz!", show_alert=True)
        return
    
    try:
        if callback.data == "clean_duplicates":
            print("DEBUG: Cleaning duplicates...")
            removed_count = db.clean_duplicate_tariffs()
            print(f"DEBUG: Cleaned {removed_count} duplicate groups")
            await callback.message.edit_text(
                f"✅ **Takrorlanuvchi tariffar o'chirildi!**\n\n"
                f"Jami {removed_count} ta takrorlanuvchi tarif guruhi tozalandi.", 
                parse_mode="Markdown"
            )
            
        elif callback.data == "reset_tariffs":
            print("DEBUG: Resetting tariffs...")
            db.reset_tariffs_to_default()
            print("DEBUG: Tariffs reset successfully")
            await callback.message.edit_text(
                "✅ **Tariflar muvaffaqiyatli qayta yaratildi!**\n\n"
                "Endi 7 ta standart tarif mavjud:\n"
                "1. Free (0 so'm)\n"
                "2. Basic (19,000 so'm)\n"
                "3. Standart (32,000 so'm)\n"
                "4. Premium (49,000 so'm)\n"
                "5. Haftalik (15,000 so'm)\n"
                "6. Oylik (45,000 so'm)\n"
                "7. Yillik (300,000 so'm)", 
                parse_mode="Markdown"
            )
            
        elif callback.data == "cancel_clean":
            await callback.message.delete()
            await callback.answer("Bekor qilindi.")
            return
            
        elif callback.data == "clean_all_files":
            import os
            import glob
            
            # Vaqtinchalik fayllarni tozalash
            deleted_count = 0
            total_size = 0
            
            # Audio fayllarini o'chirish
            audio_files = glob.glob("temp_audio_*.ogg")
            for file in audio_files:
                try:
                    size = os.path.getsize(file)
                    os.remove(file)
                    deleted_count += 1
                    total_size += size
                except Exception as e:
                    print(f"Audio faylni o'chirishda xatolik {file}: {e}")
            
            # PDF fayllarini o'chirish
            pdf_files = glob.glob("RavonAI_Report_*.pdf")
            for file in pdf_files:
                try:
                    size = os.path.getsize(file)
                    os.remove(file)
                    deleted_count += 1
                    total_size += size
                except Exception as e:
                    print(f"PDF faylni o'chirishda xatolik {file}: {e}")
            
            # To'lov chek rasmlarini o'chirish
            payment_files = glob.glob("payment_check_*.jpg")
            for file in payment_files:
                try:
                    size = os.path.getsize(file)
                    os.remove(file)
                    deleted_count += 1
                    total_size += size
                except Exception as e:
                    print(f"Payment faylni o'chirishda xatolik {file}: {e}")
            
            # Hajmni MB ga o'tkazish
            size_mb = total_size / (1024 * 1024)
            
            await callback.message.edit_text(
                f"✅ **Fayllar muvaffaqiyatli tozalandi!**\n\n"
                f"🗑️ O'chirilgan fayllar: {deleted_count} ta\n"
                f"💾 Bo'shatilgan joy: {size_mb:.2f} MB\n\n"
                f"🧹 Tozalandi:\n"
                f"• Audio fayllar (*.ogg)\n"
                f"• PDF hisobotlar (*.pdf)\n"
                f"• To'lov cheklari (*.jpg)", 
                parse_mode="Markdown"
            )
            
        elif callback.data == "file_stats":
            import os
            import glob
            
            # Fayl statistikasini yig'ish
            stats = {
                'audio': {'count': 0, 'size': 0},
                'pdf': {'count': 0, 'size': 0},
                'payment': {'count': 0, 'size': 0}
            }
            
            # Audio fayllar
            audio_files = glob.glob("temp_audio_*.ogg")
            for file in audio_files:
                try:
                    size = os.path.getsize(file)
                    stats['audio']['count'] += 1
                    stats['audio']['size'] += size
                except:
                    pass
            
            # PDF fayllar
            pdf_files = glob.glob("RavonAI_Report_*.pdf")
            for file in pdf_files:
                try:
                    size = os.path.getsize(file)
                    stats['pdf']['count'] += 1
                    stats['pdf']['size'] += size
                except:
                    pass
            
            # Payment fayllar
            payment_files = glob.glob("payment_check_*.jpg")
            for file in payment_files:
                try:
                    size = os.path.getsize(file)
                    stats['payment']['count'] += 1
                    stats['payment']['size'] += size
                except:
                    pass
            
            total_count = stats['audio']['count'] + stats['pdf']['count'] + stats['payment']['count']
            total_size = stats['audio']['size'] + stats['pdf']['size'] + stats['payment']['size']
            total_size_mb = total_size / (1024 * 1024)
            
            text = (
                f"📊 **Fayl statistikasi**\n\n"
                f"🎵 **Audio fayllar:**\n"
                f"└ {stats['audio']['count']} ta, {stats['audio']['size']/(1024*1024):.2f} MB\n\n"
                f"📄 **PDF hisobotlar:**\n"
                f"└ {stats['pdf']['count']} ta, {stats['pdf']['size']/(1024*1024):.2f} MB\n\n"
                f"📸 **To'lov cheklari:**\n"
                f"└ {stats['payment']['count']} ta, {stats['payment']['size']/(1024*1024):.2f} MB\n\n"
                f"📈 **Jami:**\n"
                f"└ {total_count} ta fayl, {total_size_mb:.2f} MB"
            )
            
            # Orqaga tugmasi
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_file_menu")]
            ])
            
            await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
            
        elif callback.data == "cancel_clean_files":
            await callback.message.delete()
            await callback.answer("Bekor qilindi.")
            return
            
        elif callback.data == "back_to_file_menu":
            # Asosiy fayl menyusiga qaytish
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🗑️ Barcha fayllarni o'chirish", callback_data="clean_all_files")],
                [InlineKeyboardButton(text="📊 Fayl statistikasi", callback_data="file_stats")],
                [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_clean_files")]
            ])
            await callback.message.edit_text(
                "🗑️ **Fayllarni tozalash**\n\n"
                "Qaysi amalni bajarmoqchisiz?\n\n"
                "• **Barcha fayllarni o'chirish** - vaqtinchalik fayllarni (PDF, audio, rasm) o'chiradi\n"
                "• **Fayl statistikasi** - serverdagi fayllar haqida ma'lumot beradi", 
                reply_markup=markup,
                parse_mode="Markdown"
            )
            
        await callback.answer()
        
    except Exception as e:
        print(f"DEBUG: Error in {callback.data}: {str(e)}")
        await callback.message.edit_text(f"❌ **Xatolik:** {str(e)}")
        await callback.answer()

@admin_router.message(F.text == "⬅️ Asosiy menyu")
async def back_to_main(message: Message):
    from main import get_main_menu
    await message.answer("Asosiy menyuga qaytdingiz.", reply_markup=get_main_menu(message.from_user.id))
