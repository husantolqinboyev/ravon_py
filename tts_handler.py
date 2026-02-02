from gtts import gTTS
import os

def text_to_speech(text, lang='en'):
    """
    Matnni ovozga aylantiradi va fayl yo'lini qaytaradi.
    """
    try:
        tts = gTTS(text=text, lang=lang)
        # Windows uchun moslangan fayl yo'li
        file_path = os.path.join(os.getcwd(), f"tts_{hash(text)}.mp3")
        tts.save(file_path)
        return file_path
    except Exception as e:
        print(f"TTS Error: {e}")
        return None
