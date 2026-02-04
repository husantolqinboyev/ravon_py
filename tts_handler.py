from gtts import gTTS
import os
import tempfile
import uuid

def text_to_speech(text, lang='en'):
    """
    Matnni ovozga aylantiradi va fayl yo'lini qaytaradi.
    Render serverda ishlashi uchun temp papkadan foydalanadi.
    """
    try:
        if not text or not text.strip():
            print("TTS Error: Empty text")
            return None
            
        tts = gTTS(text=text.strip(), lang=lang)
        
        # Render uchun temp papkadan foydalanish
        temp_dir = tempfile.gettempdir()
        unique_id = str(uuid.uuid4())[:8]
        file_path = os.path.join(temp_dir, f"tts_{unique_id}.mp3")
        
        print(f"TTS: Saving to {file_path}")
        tts.save(file_path)
        
        # Fayl mavjudligini tekshirish
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            print(f"TTS: Success - file size: {os.path.getsize(file_path)} bytes")
            return file_path
        else:
            print("TTS Error: File not created or empty")
            return None
            
    except Exception as e:
        print(f"TTS Error: {e}")
        return None
