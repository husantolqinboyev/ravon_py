from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
import database as db
import ai_handler as ai
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
        [KeyboardButton(text="📝 Material qo'shish"), KeyboardButton(text="🤖 AI yordam")],
        [KeyboardButton(text="📚 Materiallarim"), KeyboardButton(text="📊 O'quvchilar statistikasi")],
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
            for i, word in enumerate(words[:10], 1):
                text += f"{i}. {word}\n"
            if len(words) > 10:
                text += f"... va yana {len(words) - 10} ta so'z\n"
        
        if sentences:
            text += "\n📄 **Matnlar:**\n"
            for i, sent in enumerate(sentences[:5], 1):
                text += f"{i}. {sent[:50]}...\n"
            if len(sentences) > 5:
                text += f"... va yana {len(sentences) - 5} ta matn\n"
        
        await message.answer(text)

@teacher_router.message(F.text == "📝 So'z qo'shish")
async def start_add_word(message: Message):
    if db.is_teacher(message.from_user.id):
        teacher_states[message.from_user.id] = "adding_word"
        await message.answer("Iltimos, qo'shmoqchi bo'lgan so'zingizni yozing:")

@teacher_router.message(F.text == "📄 Matn qo'shish")
async def start_add_sentence(message: Message):
    if db.is_teacher(message.from_user.id):
        teacher_states[message.from_user.id] = "adding_sentence"
        await message.answer("Iltimos, qo'shmoqchi bo'lgan matningizni yozing:")

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
        await message.answer("🤖 AI so'z yordami:\n\nMavzuni kiriting (masalan: 'technology', 'nature', 'daily life'):")
        # Bu yerda state mexanizmi qo'shilishi kerak

@teacher_router.message(F.text == "📄 Matn yaratish (AI)")
async def ai_sentence_help(message: Message):
    if db.is_teacher(message.from_user.id):
        await message.answer("🤖 AI matn yordami:\n\nMavzu va darajani kiriting (masalan: 'business, intermediate'):")
        # Bu yerda state mexanizmi qo'shilishi kerak

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
@teacher_router.message(F.text & ~F.text.startswith("/") & ~F.text.in_([
    "👨‍🎓 Mening o'quvchilarim", "📝 Material qo'shish", "🤖 AI yordam",
    "📚 Materiallarim", "📊 O'quvchilar statistikasi", "📝 So'z qo'shish",
    "📄 Matn qo'shish", "🤖 AI so'z yaratish", "🤖 AI matn yaratish",
    "📝 So'z yaratish (AI)", "📄 Matn yaratish (AI)", "⬅️ O'qituvchi menyu",
    "⬅️ Asosiy menyu"
]))
async def handle_teacher_input(message: Message):
    user_id = message.from_user.id
    
    # Faqat o'qituvchi bo'lganlar uchun
    if not db.is_teacher(user_id):
        return
    
    # State ni tekshirish
    state = teacher_states.get(user_id)
    
    if state == "adding_word":
        word = message.text.strip()
        if len(word.split()) == 1:  # Faqat bitta so'z
            db.add_material(user_id, word, "word")
            await message.answer(f"✅ So'z muvaffaqiyatli qo'shildi: **{word}**", parse_mode="Markdown")
            del teacher_states[user_id]  # State ni tozalash
        else:
            await message.answer("❌ Iltimos, faqat bitta so'z yozing:")
    
    elif state == "adding_sentence":
        sentence = message.text.strip()
        if len(sentence.split()) >= 3:  # Kamida 3 ta so'z
            db.add_material(user_id, sentence, "sentence")
            await message.answer(f"✅ Matn muvaffaqiyatli qo'shildi: **{sentence}**", parse_mode="Markdown")
            del teacher_states[user_id]  # State ni tozalash
        else:
            await message.answer("❌ Matnda kamida 3 ta so'z bo'lishi kerak. Iltimos, qayta yozing:")

@teacher_router.message(F.text == "⬅️ O'qituvchi menyu")
async def back_to_teacher_menu(message: Message):
    if db.is_teacher(message.from_user.id):
        # State ni tozalash
        if message.from_user.id in teacher_states:
            del teacher_states[message.from_user.id]
        await message.answer("O'qituvchi menyuga qaytdingiz.", reply_markup=get_teacher_menu())

@teacher_router.message(F.text == "📊 O'quvchilar statistikasi")
async def student_stats(message: Message):
    if db.is_teacher(message.from_user.id):
        await message.answer("O'quvchilarning oxirgi test natijalari yuklanmoqda...")
