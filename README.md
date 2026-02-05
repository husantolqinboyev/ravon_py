# 🤖 Ravon AI - English Pronunciation Bot

Ravon AI - bu ingliz tili talaffuzini AI yordamida tekshiruvchi Telegram boti.

## 🎯 Asosiy Funktsiyalar

- **🎤 Talaffuz Testi** - Ovozli xabar orqali talaffuzni tahlil qilish
- **🔊 Text-to-Speech** - Matnni ovozga aylantirish
- **💎 Premium** - Cheklangan testlar va qo'shimcha imkoniyatlar
- **👨‍🏫 O'qituvchi Paneli** - Materiallar qo'shish va o'quvchilarni kuzatish
- **🛠 Admin Paneli** - Foydalanuvchilar, to'lovlar va statistikani boshqarish

## 🚀 Installation
STT: Processing audio file with Vosk: temp_audio_xxx.ogg
VOSK: Transcribing temp_audio_xxx.ogg
VOSK: Transcribed: 'I love programming in Python'
STT: Vosk transcribed: 'I love programming in Python'
### Talablar:
- Python 3.8+
- Telegram Bot Token
- OpenRouter API Key

### O'rnatish:

1. **Repositoryni klonlash:**
   ```bash
   git clone https://github.com/husantolqinboyev/ravon_py.git
   cd ravon_py
   ```

2. **Kutubxonalarni o'rnatish:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Konfiguratsiya:**
   ```bash
   cp .env.example .env
   # .env faylini oching va o'zingizning ma'lumotlaringizni kiriting
   ```

4. **Botni ishga tushurish:**
   ```bash
   python main.py
   ```

## ⚙️ Konfiguratsiya

`.env` faylida quyidagilarni sozlang:

```env
BOT_TOKEN=your_telegram_bot_token
OPENROUTER_API_KEY=your_openrouter_api_key
REQUIRED_CHANNEL=@your_channel_username
ADMIN_IDS=123456789,987654321
TEACHER_IDS=123456789,987654321
```

## 📁 Struktura

```
ravon_bot/
├── main.py              # Asosiy bot fayli
├── admin_panel.py       # Admin paneli
├── teacher_panel.py     # O'qituvchi paneli  
├── database.py          # Ma'lumotlar bazasi
├── ai_handler.py        # AI integratsiyasi
├── tts_handler.py       # Text-to-Speech
├── professional_pdf.py  # PDF hisobotlar
├── config.py            # Konfiguratsiya
├── requirements.txt     # Kutubxonalar
├── .env.example         # Namuna konfiguratsiyasi
└── .gitignore          # Fayllarni ignore qilish
```

## 🎮 Foydalanish

### Oddiy Foydalanuvchilar:
1. `/start` - Botni boshlash
2. **🎤 Talaffuzni test qilish** - Talaffuzni tekshirish
3. **🔊 Matnni audioga aylantirish** - TTS
4. **💎 Premium** - Premium xizmatlar

### O'qituvchilar:
1. `/teacher` - O'qituvchi paneli
2. **📝 Material qo'shish** - So'z va matnlar
3. **🤖 AI yordam** - AI orqali material yaratish
4. **👨‍🎓 Mening o'quvchilarim** - O'quvchilar ro'yxati

### Adminlar:
1. `/admin` - Admin paneli
2. **📊 Umumiy statistika** - Bot statistikasi
3. **💳 To'lov so'rovlari** - To'lovlarni boshqarish
4. **🗑️ Fayllarni tozalash** - Vaqtinchalik fayllarni o'chirish

## 🤖 AI Xususiyatlari

- **🎯 Talaffuz tahlili** - 0-100 ball baholash
- **📊 Batafsil feedback** - O'zbek tilida tushuntirish
- **🔍 Aniqlik, ravonlik, talaffuz** - Uchta asosiy ko'rsatkich
- **📄 PDF hisobotlar** - Professional hisobotlar

## 📊 Ma'lumotlar Bazasi

- **SQLite** - Yengil va tez ma'lumotlar bazasi
- **Foydalanuvchilar** - Ro'yxatdan o'tish va statistika
- **Test natijalari** - Barcha testlar tarixi
- **Premium obunalar** - To'lovlar va obunalar
- **Materiallar** - O'qituvchi materiallari

## 🔧 Texnologiyalar

- **aiogram 3.4.1** - Telegram bot framework
- **OpenRouter API** - AI integratsiyasi
- **Google Gemini** - AI modeli
- **ReportLab** - PDF generatsiya
- **gTTS** - Text-to-Speech
- **SQLite** - Ma'lumotlar bazasi

## 📄 Litsenziya

Bu loyiha MIT litsenziyasi ostida tarqatiladi.

## 👥 Mualliflar

- [Husan Tolqinboyev](https://github.com/husantolqinboyev)

## 🤝 Hissa qo'shish

1. Repositoryni fork qiling
2. O'zgartirishlar uchun yangi branch yarating (`git checkout -b feature/AmazingFeature`)
3. O'zgartirishlarni commit qiling (`git commit -m 'Add some AmazingFeature'`)
4. Branchga push qiling (`git push origin feature/AmazingFeature`)
5. Pull Request yarating

## 📞 Aloqa

Agar savollaringiz bo'lsa, [Issues](https://github.com/husantolqinboyev/ravon_py/issues) bo'limida yozing.

---

⭐ Agar loyiha foydali bo'lsa, yulduzcha qo'ying!
