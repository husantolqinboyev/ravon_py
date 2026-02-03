from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import database as db
import ai_handler as ai
import sqlite3
import random

teacher_router = Router()

# O'qituvchi holatini saqlash uchun dictionary
teacher_states = {}

@teacher_router.message(Command("teacher"))
async def cmd_teacher(message: Message):
    if db.is_teacher(message.from_user.id):
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

def get_teacher_menu():
    buttons = [
        [KeyboardButton(text="👨‍🎓 Mening o'quvchilarim")],
        [KeyboardButton(text="👥 O'quvchi biriktirish"), KeyboardButton(text="📝 Material qo'shish")],
        [KeyboardButton(text="🤖 AI yordam"), KeyboardButton(text="📚 Materiallarim")],
        [KeyboardButton(text="📊 O'quvchilar statistikasi"), KeyboardButton(text="📤 Material yuborish")],
        [KeyboardButton(text="⬅️ Asosiy menyu")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

@teacher_router.message(F.text == "👨‍🎓 Mening o'quvchilarim")
async def view_students(message: Message):
    if db.is_teacher(message.from_user.id):
        students = db.get_teacher_students(message.from_user.id)
        if not students:
            await message.answer("Sizga hali o'quvchilar biriktirilmagan.")
            return
        
        text = "👨‍🎓 **Sizning o'quvchilaringiz:**\n\n"
        for s in students:
            text += f"👤 {s[1]} (@{s[2]})\n"
        await message.answer(text, parse_mode="Markdown")

@teacher_router.message(F.text == "👥 O'quvchi biriktirish")
async def assign_student_menu(message: Message):
    if not db.is_teacher(message.from_user.id):
        await message.answer("❌ Siz o'qituvchi emassiz!")
        return
    
    # Soddalashtirilgan variant - faqat ro'yxatdan tanlash
    await show_users_list(message)

@teacher_router.message((F.text.contains("Ro'yxat")) | (F.text == "1") | (F.text.contains("ro'yxat")))
async def show_users_list(message: Message):
    print(f"📋 show_users_list called by {message.from_user.id} with text: '{message.text}'")
    
    if not db.is_teacher(message.from_user.id):
        await message.answer("❌ Siz o'qituvchi emassiz!")
        return
    
    try:
        # Database dan foydalanuvchilarni olish
        users = db.get_all_users_for_teacher()
        print(f"📊 Database dan {len(users)} ta foydalanuvchi olindi")
        
        if not users:
            await message.answer("❌ Hech qanday foydalanuvchi topilmadi.")
            return
        
        # Inline keyboard yaratish
        keyboard = []
        for user in users[:15]:  # Birinchi 15 ta
            user_id, full_name, username = user
            user_text = f"{full_name}"
            if username and username != 'None':
                user_text += f" (@{username})"
            
            keyboard.append([
                InlineKeyboardButton(
                    text=user_text, 
                    callback_data=f"assign_{user_id}"
                )
            ])
        
        # Orqaga tugmasi
        keyboard.append([
            InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_teacher")
        ])
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await message.answer(
            f"📋 **Foydalanuvchilar ro'yxati**\n\n"
            f"Jami: {len(users)} ta foydalanuvchi\n"
            f"Biriktirmoqchi bo'lgan o'quvchingizni tanlang:",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        print(f"❌ show_users_list xatosi: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")

@teacher_router.message(F.text.in_(["2", "🔍 Username bilan qidirish"]))
async def search_by_username(message: Message):
    if db.is_teacher(message.from_user.id):
        teacher_states[message.from_user.id] = "searching_username"
        await message.answer("🔍 Qidirish uchun username ni kiriting (masalan: @username):")

@teacher_router.message(F.text.in_(["3", "🆔 User ID bilan biriktirish"]))
async def assign_by_user_id(message: Message):
    if db.is_teacher(message.from_user.id):
        teacher_states[message.from_user.id] = "assigning_by_id"
        await message.answer("🆔 Biriktirish uchun User ID ni kiriting:")

# Callback query handlers
@teacher_router.callback_query(F.data.startswith("assign_"))
async def assign_student_callback(callback: types.CallbackQuery):
    print(f"🎯 assign_student_callback called with data: {callback.data}")
    
    teacher_id = callback.from_user.id
    
    if not db.is_teacher(teacher_id):
        await callback.answer("❌ Siz o'qituvchi emassiz!", show_alert=True)
        return
    
    try:
        # O'quvchi ID sini olish
        student_id = int(callback.data.replace("assign_", ""))
        print(f"🎯 Trying to assign student {student_id} to teacher {teacher_id}")
        
        # O'quvchi ma'lumotlarini olish
        student = db.get_user(student_id)
        if not student:
            await callback.answer("❌ Foydalanuvchi topilmadi!", show_alert=True)
            return
        
        # Biriktirish
        success = db.assign_student_to_teacher(teacher_id, student_id)
        
        if success:
            await callback.answer(
                f"✅ {student[1]} o'quvchi sifatida biriktirildi!", 
                show_alert=True
            )
            
            # Xabarni yangilash
            await callback.message.edit_text(
                f"✅ **Muvaffaqiyatli biriktirildi!**\n\n"
                f"👤 **O'quvchi:** {student[1]}\n"
                f"📱 **Username:** @{student[2] or 'yo\'q'}\n"
                f"🆔 **ID:** `{student_id}`\n\n"
                f"Endi sizning o'quvchingiz!",
                parse_mode="Markdown"
            )
        else:
            await callback.answer(
                f"❌ {student[1]} allaqachon biriktirilgan!", 
                show_alert=True
            )
            
    except ValueError:
        await callback.answer("❌ Noto'g'ri ID formati!", show_alert=True)
    except Exception as e:
        print(f"❌ assign_student_callback xatosi: {e}")
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)

@teacher_router.callback_query(F.data == "back_teacher")
async def back_teacher_callback(callback: types.CallbackQuery):
    if not db.is_teacher(callback.from_user.id):
        await callback.answer("❌ Siz o'qituvchi emassiz!", show_alert=True)
        return
    
    help_text = (
        "👨‍🏫 **O'qituvchi Paneli**\n\n"
        "O'quvchilaringizning progressini kuzatish va materiallar qo'shishingiz mumkin.\n\n"
        "📚 **Materiallar:** So'z va matn qo'shishingiz mumkin\n"
        "👥 **O'quvchilar:**  O'quvchilar ro'yxati va statistikasi\n"
        "🤖 **AI yordam:** AI orqali materiallar yaratish"
    )
    
    # State ni tozalash
    if callback.from_user.id in teacher_states:
        del teacher_states[callback.from_user.id]
        
    await callback.message.edit_text(help_text, reply_markup=get_teacher_menu_inline(), parse_mode="Markdown")
    await callback.answer()

def get_teacher_menu_inline():
    buttons = [
        [InlineKeyboardButton(text="👨‍🎓 O'quvchilarim", callback_data="view_students_list")],
        [InlineKeyboardButton(text="👥 Biriktirish", callback_data="assign_menu"), 
         InlineKeyboardButton(text="📝 Material qo'shish", callback_data="add_material_menu")],
        [InlineKeyboardButton(text="🤖 AI yordam", callback_data="ai_help_menu"),
         InlineKeyboardButton(text="📊 Statistika", callback_data="view_stats")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@teacher_router.callback_query(F.data == "assign_menu")
async def assign_menu_callback(callback: types.CallbackQuery):
    await show_users_list(callback.message)
    await callback.answer()

@teacher_router.message(F.text == "⬅️ Asosiy menyu")
async def back_to_main(message: Message):
    from main import get_main_menu
    await message.answer("Asosiy menyuga qaytdingiz.", reply_markup=get_main_menu(message.from_user.id))

@teacher_router.message(F.text == "📤 Material yuborish")
async def send_material_to_students(message: Message):
    if db.is_teacher(message.from_user.id):
        # O'qituvchining o'quvchilarini tekshirish
        students = db.get_teacher_students(message.from_user.id)
        if not students:
            await message.answer("❌ Sizga hali o'quvchilar biriktirilmagan. Avval o'quvchi biriktiring!")
            return
        
        markup = ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="📝 So'z yuborish"), KeyboardButton(text="📄 Matn yuborish")],
            [KeyboardButton(text="🤖 AI so'z yuborish"), KeyboardButton(text="🤖 AI matn yuborish")],
            [KeyboardButton(text="⬅️ O'qituvchi menyu")]
        ], resize_keyboard=True)
        
        await message.answer(
            f"📤 **Material yuborish**\n\n"
            f"👥 O'quvchilar soni: {len(students)} ta\n"
            f"Qanday material yubormoqchisiz?",
            reply_markup=markup,
            parse_mode="Markdown"
        )

@teacher_router.message(F.text == "📝 Material qo'shish")
async def start_add_material(message: Message):
    if db.is_teacher(message.from_user.id):
        markup = ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="📝 So'z qo'shish"), KeyboardButton(text="📄 Matn qo'shish")],
            [KeyboardButton(text="🤖 AI so'z yaratish"), KeyboardButton(text="🤖 AI matn yaratish")],
            [KeyboardButton(text="⬅️ O'qituvchi menyu")]
        ], resize_keyboard=True)
        await message.answer("Material qo'shish turini tanlang:", reply_markup=markup)

@teacher_router.message(F.text == "🤖 AI yordam")
async def ai_help_menu(message: Message):
    if db.is_teacher(message.from_user.id):
        markup = ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="📝 So'z yaratish (AI)"), KeyboardButton(text="📄 Matn yaratish (AI)")],
            [KeyboardButton(text="💡 Dars reja yaratish"), KeyboardButton(text="🔍 Talaffuz maslahati")],
            [KeyboardButton(text="⬅️ O'qituvchi menyu")]
        ], resize_keyboard=True)
        await message.answer("AI yordam turini tanlang:", reply_markup=markup)

@teacher_router.message(F.text == "📚 Materiallarim")
async def view_materials(message: Message):
    if db.is_teacher(message.from_user.id):
        materials = db.get_teacher_materials(message.from_user.id)
        if not materials:
            await message.answer("Siz hali material qo'shmadingiz.")
            return
        
        text = "📚 **Sizning materiallaringiz:**\n\n"
        words = []
        sentences = []
        
        for mat in materials:
            if mat[3] == 'word':
                words.append(mat[2])
            else:
                sentences.append(mat[2])
        
        if words:
            text += "📝 **So'zlar:**\n"
            for i, word in enumerate(words, 1):
                text += f"{i}. {word[1]}\n"
            if len(words) >= 50:
                text += "*(Faqat oxirgi 50 ta so'z ko'rsatilmoqda)*\n"
        
        if sentences:
            text += "\n📄 **Matnlar:**\n"
            for i, sent in enumerate(sentences, 1):
                content = sent[1][:50] + "..." if len(sent[1]) > 50 else sent[1]
                text += f"{i}. {content}\n"
            if len(sentences) >= 20:
                text += "*(Faqat oxirgi 20 ta matn ko'rsatilmoqda)*\n"
        
        await message.answer(text)

@teacher_router.message(F.text == "📝 So'z yuborish")
async def send_word_to_students(message: Message):
    if db.is_teacher(message.from_user.id):
        teacher_states[message.from_user.id] = "sending_word"
        await message.answer("📝 O'quvchilarga yubormoqchi bo'lgan so'zingizni kiriting:")

@teacher_router.message(F.text == "📄 Matn yuborish")
async def send_sentence_to_students(message: Message):
    if db.is_teacher(message.from_user.id):
        teacher_states[message.from_user.id] = "sending_sentence"
        await message.answer("📄 O'quvchilarga yubormoqchi bo'lgan matningizni kiriting:")

@teacher_router.message(F.text == "🤖 AI so'z yuborish")
async def send_ai_word_to_students(message: Message):
    if db.is_teacher(message.from_user.id):
        await message.answer("🤖 AI orqali so'z yaratilmoqda... ⏳")
        
        import random
        categories = ["animals", "food and cooking", "technology and computers", "nature and environment", "daily life activities", "education and learning", "sports and games", "music and arts", "emotions and feelings", "transportation"]
        category = random.choice(categories)
        prompt = f"Generate an interesting English word related to {category} that is excellent for pronunciation practice. Choose a word that is not too common but still useful. Return only the word, no explanation."
        
        ai_result = ai.generate_content(prompt)
        if ai_result:
            word = ai_result.strip().lower()
            await send_material_to_all_students(message.from_user.id, word, "word", message.bot)
            await message.answer(f"✅ AI yaratgan so'z **{word}** barcha o'quvchilarga yuborildi!", parse_mode="Markdown")
        else:
            await message.answer("❌ AI bilan xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")

@teacher_router.message(F.text == "🤖 AI matn yuborish")
async def send_ai_sentence_to_students(message: Message):
    if db.is_teacher(message.from_user.id):
        await message.answer("🤖 AI orqali matn yaratilmoqda... ⏳")
        
        import random
        topics = ["daily routine and habits", "weekend activities and hobbies", "work and career goals", "travel experiences and dreams", "cooking and favorite foods", "technology and gadgets", "weather and seasons", "friendship and relationships", "sports and exercise", "music and entertainment"]
        topic = random.choice(topics)
        prompt = f"Create 3-4 unique, interesting English sentences (total 25-35 words) about {topic} that are perfect for pronunciation practice. Make them natural and conversational. Connect them into one coherent text. Return only the sentences, no explanation."
        
        ai_result = ai.generate_content(prompt)
        if ai_result:
            sentence = ai_result.strip()
            await send_material_to_all_students(message.from_user.id, sentence, "sentence", message.bot)
            await message.answer(f"✅ AI yaratgan matn barcha o'quvchilarga yuborildi!\n\n📝 {sentence}", parse_mode="Markdown")
        else:
            await message.answer("❌ AI bilan xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")

async def send_material_to_all_students(teacher_id, content, material_type, bot_instance):
    """O'qituvchining barcha o'quvchilariga material yuborish"""
    students = db.get_teacher_students(teacher_id)
    if not students:
        return False
    
    success_count = 0
    error_count = 0
    
    for student in students:
        try:
            if material_type == "word":
                await bot_instance.send_message(
                    student[0],  # user_id
                    f"📚 **Yangi so'z!**\n\n"
                    f"👨‍🏫 Sizning o'qituvchingiz yubordi:\n"
                    f"🔤 **{content}**\n\n"
                    f"🎤 Ushbu so'zni talaffuz qiling va testni topshiring!",
                    parse_mode="Markdown"
                )
            else:  # sentence
                await bot_instance.send_message(
                    student[0],  # user_id
                    f"📖 **Yangi matn!**\n\n"
                    f"👨‍🏫 Sizning o'qituvchingiz yubordi:\n"
                    f"📝 **{content}**\n\n"
                    f"🎤 Ushbu matnni talaffuz qiling va testni topshiring!",
                    parse_mode="Markdown"
                )
            success_count += 1
        except Exception as e:
            print(f"O'quvchiga xabar yuborishda xatolik {student[0]}: {e}")
            error_count += 1
    
    return success_count, error_count

@teacher_router.message(F.text == "📝 So'z qo'shish")
async def start_add_word(message: Message):
    """So'z qo'shishni boshlash"""
    print(f"DEBUG: start_add_word called by {message.from_user.id}")
    
    if not db.is_teacher(message.from_user.id):
        await message.answer("❌ Siz o'qituvchi emassiz!")
        return
    
    teacher_states[message.from_user.id] = "adding_word"
    await message.answer(
        "📝 **So'z qo'shish**\n\n"
        "Qo'shmoqchi bo'lgan inglizcha so'zingizni yozing:\n\n"
        "⚠️ **Eslatma:** Faqat bitta so'z yozing (masalan: 'hello', 'computer', 'beautiful')",
        parse_mode="Markdown"
    )

@teacher_router.message(F.text == "📄 Matn qo'shish")
async def start_add_sentence(message: Message):
    """Matn qo'shishni boshlash"""
    print(f"DEBUG: start_add_sentence called by {message.from_user.id}")
    
    if not db.is_teacher(message.from_user.id):
        await message.answer("❌ Siz o'qituvchi emassiz!")
        return
    
    teacher_states[message.from_user.id] = "adding_sentence"
    await message.answer(
        "📄 **Matn qo'shish**\n\n"
        "Qo'shmoqchi bo'lgan inglizcha matningizni yozing:\n\n"
        "⚠️ **Eslatma:** Kamida 3 ta so'z bo'lishi kerak (masalan: 'The weather is nice today')",
        parse_mode="Markdown"
    )

@teacher_router.message(F.text == "🤖 AI so'z yaratish")
async def ai_generate_word(message: Message):
    if db.is_teacher(message.from_user.id):
        await message.answer("AI so'z yaratilmoqda... ⏳")
        
        # AI orqali so'z yaratish
        import random
        categories = ["animals", "food and cooking", "technology and computers", "nature and environment", "daily life activities", "education and learning", "sports and games", "music and arts", "emotions and feelings", "transportation"]
        category = random.choice(categories)
        prompt = f"Generate an interesting English word related to {category} that is excellent for pronunciation practice. Choose a word that is not too common but still useful. Return only the word, no explanation."
        
        # Bu yerda AI chaqiriladi
        ai_result = ai.generate_content(prompt)
        if ai_result:
            word = ai_result.strip().lower()
            db.add_material(message.from_user.id, word, "word")
            await message.answer(f"🤖 AI yaratdi: **{word}** ✅\n\nSo'z materiallarga qo'shildi!")
        else:
            await message.answer("AI bilan xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")

@teacher_router.message(F.text == "🤖 AI matn yaratish")
async def ai_generate_sentence(message: Message):
    if db.is_teacher(message.from_user.id):
        await message.answer("AI matn yaratilmoqda... ⏳")
        
        # AI orqali matn yaratish
        import random
        topics = ["daily routine and habits", "weekend activities and hobbies", "work and career goals", "travel experiences and dreams", "cooking and favorite foods", "technology and gadgets", "weather and seasons", "friendship and relationships", "sports and exercise", "music and entertainment"]
        topic = random.choice(topics)
        prompt = f"Create 3-4 unique, interesting English sentences (total 25-35 words) about {topic} that are perfect for pronunciation practice. Make them natural and conversational. Connect them into one coherent text. Return only the sentences, no explanation."
        
        ai_result = ai.generate_content(prompt)
        if ai_result:
            sentence = ai_result.strip()
            db.add_material(message.from_user.id, sentence, "sentence")
            await message.answer(f"🤖 AI yaratdi: **{sentence}** ✅\n\nMatn materiallarga qo'shildi!")
        else:
            await message.answer("AI bilan xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")

@teacher_router.message(F.text == "📝 So'z yaratish (AI)")
async def ai_word_help(message: Message):
    if db.is_teacher(message.from_user.id):
        teacher_states[message.from_user.id] = "ai_word_topic"
        await message.answer(
            "🤖 **AI so'z yordami**\n\n"
            "Mavzuni kiriting (masalan: 'technology', 'nature', 'daily life'):\n\n"
            "AI ushbu mavzuga oid qiziqarli so'z topib beradi.",
            parse_mode="Markdown"
        )

@teacher_router.message(F.text == "📄 Matn yaratish (AI)")
async def ai_sentence_help(message: Message):
    if db.is_teacher(message.from_user.id):
        teacher_states[message.from_user.id] = "ai_sentence_topic"
        await message.answer(
            "🤖 **AI matn yordami**\n\n"
            "Mavzu va darajani kiriting (masalan: 'business, intermediate' yoki 'travel, beginner'):\n\n"
            "AI ushbu mavzuga oid talaffuz uchun matn yaratib beradi.",
            parse_mode="Markdown"
        )

@teacher_router.message(F.text.startswith("/add_word "))
async def add_word(message: Message):
    if db.is_teacher(message.from_user.id):
        content = message.text.replace("/add_word ", "").strip()
        db.add_material(message.from_user.id, content, "word")
        await message.answer(f"Yangi so'z qo'shildi: {content} ✅")

@teacher_router.message(F.text.startswith("/add_sentence "))
async def add_sentence(message: Message):
    if db.is_teacher(message.from_user.id):
        content = message.text.replace("/add_sentence ", "").strip()
        db.add_material(message.from_user.id, content, "sentence")
        await message.answer(f"Yangi gap qo'shildi: {content} ✅")

# O'qituvchi matn kiritishini qayta ishlovchi handler
@teacher_router.message(F.text & ~F.text.startswith("/"))
async def handle_teacher_input(message: Message):
    """O'qituvchi xabarlarini qayta ishlash"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    print(f"DEBUG: handle_teacher_input called by {user_id}, text: '{text}', state: {teacher_states.get(user_id)}")
    
    # Faqat o'qituvchi bo'lganlar uchun
    if not db.is_teacher(user_id):
        return
    
    # State ni tekshirish
    state = teacher_states.get(user_id)
    
    # Orqaga qaytishni tekshirish
    if text in ["⬅️ O'qituvchi menyu", "⬅️ Orqaga", "bekor qilish", "cancel"]:
        if user_id in teacher_states:
            del teacher_states[user_id]
        await message.answer("Amal bekor qilindi.", reply_markup=get_teacher_menu())
        return
    
    # ===== MATERIAL QO'SHISH =====
    if state == "adding_word":
        print(f"DEBUG: Processing adding_word for {user_id}")
        
        word = text.lower().strip()
        words = word.split()
        
        if len(words) == 1:  # Faqat bitta so'z
            # So'zni bazaga qo'shish
            db.add_material(user_id, word, "word")
            
            await message.answer(
                f"✅ **So'z muvaffaqiyatli qo'shildi!**\n\n"
                f"🔤 **So'z:** {word}\n"
                f"📁 **Tip:** So'z\n"
                f"📊 Endi sizda {len(db.get_teacher_materials(user_id))} ta material bor",
                parse_mode="Markdown"
            )
            
            # State ni tozalash
            del teacher_states[user_id]
            
            # Materiallar menyusiga qaytish
            markup = ReplyKeyboardMarkup(keyboard=[
                [KeyboardButton(text="📝 So'z qo'shish"), KeyboardButton(text="📄 Matn qo'shish")],
                [KeyboardButton(text="🤖 AI so'z yaratish"), KeyboardButton(text="🤖 AI matn yaratish")],
                [KeyboardButton(text="⬅️ O'qituvchi menyu")]
            ], resize_keyboard=True)
            
            await message.answer(
                "📚 **Material qo'shish**\n\n"
                "Yana material qo'shmoqchimisiz?",
                reply_markup=markup,
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                "❌ **Xatolik!**\n\n"
                "Faqat bitta so'z yozing. Qaytadan urinib ko'ring yoki 'cancel' deb yozing:",
                parse_mode="Markdown"
            )
    
    elif state == "adding_sentence":
        print(f"DEBUG: Processing adding_sentence for {user_id}")
        
        sentence = text.strip()
        words = sentence.split()
        
        if len(words) >= 3:  # Kamida 3 ta so'z
            # Matnni bazaga qo'shish
            db.add_material(user_id, sentence, "sentence")
            
            await message.answer(
                f"✅ **Matn muvaffaqiyatli qo'shildi!**\n\n"
                f"📝 **Matn:** {sentence}\n"
                f"📁 **Tip:** Matn\n"
                f"📊 Endi sizda {len(db.get_teacher_materials(user_id))} ta material bor",
                parse_mode="Markdown"
            )
            
            # State ni tozalash
            del teacher_states[user_id]
            
            # Materiallar menyusiga qaytish
            markup = ReplyKeyboardMarkup(keyboard=[
                [KeyboardButton(text="📝 So'z qo'shish"), KeyboardButton(text="📄 Matn qo'shish")],
                [KeyboardButton(text="🤖 AI so'z yaratish"), KeyboardButton(text="🤖 AI matn yaratish")],
                [KeyboardButton(text="⬅️ O'qituvchi menyu")]
            ], resize_keyboard=True)
            
            await message.answer(
                "📚 **Material qo'shish**\n\n"
                "Yana material qo'shmoqchimisiz?",
                reply_markup=markup,
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                "❌ **Xatolik!**\n\n"
                "Matnda kamida 3 ta so'z bo'lishi kerak. Qaytadan urinib ko'ring yoki 'cancel' deb yozing:",
                parse_mode="Markdown"
            )
            # ===== MATERIAL YUBORISH =====
    elif state == "sending_word":
        print(f"DEBUG: Processing sending_word for {user_id}")
        
        word = text.lower().strip()
        words = word.split()
        
        if len(words) == 1:  # Faqat bitta so'z
            # O'quvchilarga yuborish
            success_count, error_count = await send_material_to_all_students(
                user_id, word, "word", message.bot
            )
            
            if success_count > 0:
                await message.answer(
                    f"✅ **So'z muvaffaqiyatli yuborildi!**\n\n"
                    f"🔤 **So'z:** {word}\n"
                    f"👥 **O'quvchilar:** {success_count} ta o'quvchiga yuborildi\n"
                    f"❌ **Xatolar:** {error_count} ta xatolik",
                    parse_mode="Markdown"
                )
            else:
                await message.answer(
                    f"❌ **Hech qanday o'quvchiga yuborilmadi!**\n\n"
                    f"Sizda hali o'quvchilar yo'q yoki ularga xabar yuborishda xatolik yuz berdi.",
                    parse_mode="Markdown"
                )
            
            # State ni tozalash
            del teacher_states[user_id]
            
            # Material yuborish menyusiga qaytish
            markup = ReplyKeyboardMarkup(keyboard=[
                [KeyboardButton(text="📝 So'z yuborish"), KeyboardButton(text="📄 Matn yuborish")],
                [KeyboardButton(text="🤖 AI so'z yuborish"), KeyboardButton(text="🤖 AI matn yuborish")],
                [KeyboardButton(text="⬅️ O'qituvchi menyu")]
            ], resize_keyboard=True)
            
            await message.answer(
                f"📤 **Material yuborish**\n\n"
                f"Yana material yubormoqchimisiz?",
                reply_markup=markup,
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                "❌ **Xatolik!**\n\n"
                "Faqat bitta so'z yozing. Qaytadan urinib ko'ring:",
                parse_mode="Markdown"
            )
    
    elif state == "sending_sentence":
        print(f"DEBUG: Processing sending_sentence for {user_id}")
        
        sentence = text.strip()
        words = sentence.split()
        
        if len(words) >= 3:  # Kamida 3 ta so'z
            # O'quvchilarga yuborish
            success_count, error_count = await send_material_to_all_students(
                user_id, sentence, "sentence", message.bot
            )
            
            if success_count > 0:
                await message.answer(
                    f"✅ **Matn muvaffaqiyatli yuborildi!**\n\n"
                    f"📝 **Matn:** {sentence[:50]}...\n"
                    f"👥 **O'quvchilar:** {success_count} ta o'quvchiga yuborildi\n"
                    f"❌ **Xatolar:** {error_count} ta xatolik",
                    parse_mode="Markdown"
                )
            else:
                await message.answer(
                    f"❌ **Hech qanday o'quvchiga yuborilmadi!**\n\n"
                    f"Sizda hali o'quvchilar yo'q yoki ularga xabar yuborishda xatolik yuz berdi.",
                    parse_mode="Markdown"
                )
            
            # State ni tozalash
            del teacher_states[user_id]
            
            # Material yuborish menyusiga qaytish
            markup = ReplyKeyboardMarkup(keyboard=[
                [KeyboardButton(text="📝 So'z yuborish"), KeyboardButton(text="📄 Matn yuborish")],
                [KeyboardButton(text="🤖 AI so'z yuborish"), KeyboardButton(text="🤖 AI matn yuborish")],
                [KeyboardButton(text="⬅️ O'qituvchi menyu")]
            ], resize_keyboard=True)
            
            await message.answer(
                f"📤 **Material yuborish**\n\n"
                f"Yana material yubormoqchimisiz?",
                reply_markup=markup,
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                "❌ **Xatolik!**\n\n"
                "Matnda kamida 3 ta so'z bo'lishi kerak. Qaytadan urinib ko'ring:",
                parse_mode="Markdown"
            )
    
    # ===== BOSHQA STATELAR =====
    elif state == "searching_username":
        print(f"DEBUG: Processing searching_username for {user_id}")
        
        username = text.strip().replace("@", "")
        users = db.search_user_by_username(username)
        
        if users:
            keyboard = []
            for user in users[:5]:  # Birinchi 5 ta natija
                user_text = f"{user[1]} (@{user[2] or 'username yo\'q'})"
                keyboard.append([InlineKeyboardButton(text=user_text, callback_data=f"assign_{user[0]}")])
            
            keyboard.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_teacher")])
            
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await message.answer(
                f"🔍 **Qidiruv natijalari**\n\n"
                f"\"@{username}\" bo'yicha {len(users)} ta foydalanuvchi topildi.\n"
                f"Biriktirmoqchi bo'lgan o'quvchini tanlang:",
                reply_markup=markup,
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                f"❌ **Qidiruv natijasi**\n\n"
                f"\"@{username}\" bo'yicha hech kim topilmadi.\n"
                f"Qaytadan urinib ko'ring:",
                parse_mode="Markdown"
            )
        
        del teacher_states[user_id]
    
    elif state == "assigning_by_id":
        print(f"DEBUG: Processing assigning_by_id for {user_id}")
        
        try:
            student_id = int(text.strip())
            
            # O'quvchi ma'lumotlarini olish
            student = db.get_user(student_id)
            if not student:
                await message.answer("❌ Bu ID ga ega foydalanuvchi topilmadi. Qaytadan urinib ko'ring:")
                return
            
            # Biriktirish
            success = db.assign_student_to_teacher(user_id, student_id)
            
            if success:
                await message.answer(
                    f"✅ **Muvaffaqiyatli biriktirildi!**\n\n"
                    f"👤 **O'quvchi:** {student[1]}\n"
                    f"📱 **Username:** @{student[2] or 'yo\'q'}\n"
                    f"🆔 **ID:** `{student_id}`\n\n"
                    f"Endi sizning o'quvchingiz!",
                    parse_mode="Markdown"
                )
            else:
                await message.answer(
                    f"❌ {student[1]} allaqachon sizga biriktirilgan yoki boshqa xatolik yuz berdi.",
                    parse_mode="Markdown"
                )
            
            del teacher_states[user_id]
            
        except ValueError:
            await message.answer("❌ Iltimos, to'g'ri User ID (faqat raqam) kiriting:")
    
    # ===== AI YORDAM STATELARI =====
    elif state == "ai_word_topic":
        print(f"DEBUG: Processing ai_word_topic for {user_id}")
        
        topic = text.strip()
        await message.answer(f"🤖 **'{topic}'** mavzusida so'z qidirilmoqda... ⏳", parse_mode="Markdown")
        
        prompt = f"Generate an interesting English word related to '{topic}' that is excellent for pronunciation practice. Choose a word that is not too common but still useful. Return only the word, no explanation."
        
        ai_result = ai.generate_content(prompt)
        if ai_result:
            word = ai_result.strip().lower()
            
            # Bazaga qo'shish
            db.add_material(user_id, word, "word")
            
            await message.answer(
                f"🤖 AI topdi: **{word}** ✅\n\n"
                f"So'z materiallaringizga qo'shildi!",
                parse_mode="Markdown"
            )
        else:
            await message.answer("❌ AI bilan xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
            
        del teacher_states[user_id]
        
    elif state == "ai_sentence_topic":
        print(f"DEBUG: Processing ai_sentence_topic for {user_id}")
        
        topic = text.strip()
        await message.answer(f"🤖 **'{topic}'** bo'yicha matn yaratilmoqda... ⏳", parse_mode="Markdown")
        
        prompt = f"Create 3-4 unique, interesting English sentences (total 25-35 words) about '{topic}' that are perfect for pronunciation practice. Make them natural and conversational. Connect them into one coherent text. Return only the sentences, no explanation."
        
        ai_result = ai.generate_content(prompt)
        if ai_result:
            sentence = ai_result.strip()
            
            # Bazaga qo'shish
            db.add_material(user_id, sentence, "sentence")
            
            await message.answer(
                f"🤖 AI yaratdi:\n\n**{sentence}** ✅\n\n"
                f"Matn materiallaringizga qo'shildi!",
                parse_mode="Markdown"
            )
        else:
            await message.answer("❌ AI bilan xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
            
        del teacher_states[user_id]
    
    # ===== AGAR STATE BO'LMASA =====
    else:
        print(f"DEBUG: No state for user {user_id}, ignoring input")

@teacher_router.message(Command("debug_assign"))
async def debug_assign(message: Message):
    """O'quvchi biriktirishni debug qilish"""
    if not db.is_teacher(message.from_user.id):
        await message.answer("❌ Siz o'qituvchi emassiz!")
        return
    
    teacher_id = message.from_user.id
    
    # 1. Database statistikasi
    conn = sqlite3.connect(db.DB_NAME)
    cursor = conn.cursor()
    
    # Jami foydalanuvchilar
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    # O'qituvchining o'quvchilari
    cursor.execute('SELECT COUNT(*) FROM student_teacher WHERE teacher_id = ?', (teacher_id,))
    my_students = cursor.fetchone()[0]
    
    # O'qituvchilar jadvalida borligi
    cursor.execute('SELECT 1 FROM teachers WHERE teacher_id = ?', (teacher_id,))
    in_teachers_table = bool(cursor.fetchone())
    
    conn.close()
    
    # 2. Test biriktirish
    test_result = "Test qilinmadi"
    try:
        # O'zingizga o'zingizni biriktirish testi
        if db.assign_student_to_teacher(teacher_id, teacher_id):
            test_result = "❌ O'ziga o'zini biriktira oldi (XATO)"
        else:
            test_result = "✅ O'ziga o'zini biriktira olmaydi (TO'G'RI)"
    except Exception as e:
        test_result = f"❌ Test xatosi: {e}"
    
    debug_text = f"""
🔧 **DEBUG MA'LUMOTLARI**

👨‍🏫 **O'qituvchi ID:** `{teacher_id}` 

📊 **Database statistikasi:**
├ Jami foydalanuvchilar: {total_users} ta
├ Mening o'quvchilarim: {my_students} ta
└ Teachers jadvalida: {'✅ Bor' if in_teachers_table else '❌ Yo\'q'}

🧪 **Test natijasi:**
{test_result}

🛠 **Qadamlar:**
1. '👥 O'quvchi biriktirish' tugmasini bosing
2. '📋 Ro'yxatdan tanlash' ni tanlang
3. Ro'yxatdan bir foydalanuvchini tanlang
"""
    
    await message.answer(debug_text, parse_mode="Markdown")

@teacher_router.message(F.text == "📊 O'quvchilar statistikasi")
async def student_stats(message: Message):
    if not db.is_teacher(message.from_user.id):
        await message.answer("❌ Siz o'qituvchi emassiz!")
        return
        
    await message.answer("📊 **O'quvchilar statistikasi yuklanmoqda...** ⏳", parse_mode="Markdown")
    
    try:
        stats = db.get_student_stats(message.from_user.id)
        
        if not stats:
            await message.answer("❌ Sizda hali o'quvchilar yo'q.")
            return
            
        text = "📊 **O'quvchilar statistikasi:**\n\n"
        for s in stats:
            user_id, full_name, total_tests, avg_score, last_test = s
            name = full_name or f"User {user_id}"
            avg = round(avg_score, 1) if avg_score else 0
            
            text += f"👤 **{name}**\n"
            text += f"├ Testlar: {total_tests} ta\n"
            text += f"├ O'rtacha ball: {avg}%\n"
            text += f"└ Oxirgi test: {last_test or 'yo\'q'}\n\n"
            
        await message.answer(text, parse_mode="Markdown")
        
    except Exception as e:
        print(f"❌ student_stats xatosi: {e}")
        await message.answer("❌ Statistikani yuklashda xatolik yuz berdi.")
