from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import database as db

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
        [KeyboardButton(text="💰 Tariflar boshqaruvi"), KeyboardButton(text="🧹 Tariflarni tozalash")],
        [KeyboardButton(text="�️ Fayllarni tozalash"), KeyboardButton(text="�👨‍🏫 O'qituvchi tayinlash")],
        [KeyboardButton(text="📢 Xabar yuborish (Ad)"), KeyboardButton(text="👤 Foydalanuvchilar")],
        [KeyboardButton(text="⬅️ Asosiy menyu")]
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
            "To'lovlarni tasdiqlash va tariflarni tahrirlash endi qulay inline tugmalar orqali amalga oshiriladi.\n\n"
            "📊 **Statistika:** Botdagi foydalanuvchilar va testlar.\n"
            "💳 **To'lovlar:** Yangi kelgan to'lovlarni tasdiqlash.\n"
            "� **Tariflar:** Narx va limitlarni o'zgartirish.\n"
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
        await message.answer("O'qituvchi qilmoqchi bo'lgan foydalanuvchining ID raqamini yuboring:\nMasalan: `/set_teacher_12345678`")

@admin_router.message(F.text.startswith("/set_teacher_"))
async def set_teacher(message: Message):
    if db.is_admin(message.from_user.id):
        try:
            user_id = int(message.text.split("_")[2])
            db.add_teacher(user_id, message.from_user.id)
            await message.answer(f"Foydalanuvchi {user_id} muvaffaqiyatli o'qituvchi qilib tayinlandi! ✅")
        except:
            await message.answer("Xatolik! ID raqamini to'g'ri kiriting.")

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
        await message.answer("Iltimos, barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring.")

@admin_router.message(F.text & ~F.text.startswith("/") & ~F.text.in_([
    "📊 Umumiy statistika", "💳 To'lov so'rovlari", "💰 Tariflar boshqaruvi",
    "👨‍🏫 O'qituvchi tayinlash", "📢 Xabar yuborish (Ad)", "👤 Foydalanuvchilar", "⬅️ Asosiy menyu"
]))
async def handle_broadcast_message(message: Message):
    """Admin tomonidan yuborilgan xabarni barcha foydalanuvchilarga yuborish"""
    if not db.is_admin(message.from_user.id):
        return
    
    # Adminning oldingi xabarini tekshirish (broadcast boshlanganmi)
    if message.reply_to_message and message.reply_to_message.text == "Iltimos, barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring.":
        broadcast_text = message.text
        await send_broadcast_to_all_users(broadcast_text)
        await message.answer("✅ Xabar barcha foydalanuvchilarga muvaffaqiyatli yuborildi!")
    else:
        # Agar bu broadcast bo'lmasa, normal admin xabi sifatida qayta ishlash
        pass

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
