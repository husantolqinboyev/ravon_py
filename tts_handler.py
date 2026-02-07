# -*- coding: utf-8 -*-
from gtts import gTTS
import os
import tempfile
import uuid
import database as db

def text_to_speech(text, lang='en'):
    """
    Matnni ovozga aylantiradi va fayl yo'lini qaytaradi.
    Render serverda ishlashi uchun temp papkadan foydalanadi.
    """
    try:
        if not text or not text.strip():
            print("TTS Error: Empty text")
            return None
            
        print(f"TTS: Processing text: '{text[:50]}...'")
        
        # Avval gTTS ni urinib ko'rish
        try:
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
                # TTS statistikasini oshirish
                db.increment_api_stats("tts")
                return file_path
            else:
                print("TTS: gTTS file not created or empty")
                
        except Exception as gtts_error:
            print(f"TTS: gTTS failed: {gtts_error}")
            
        # gTTS ishlamasa, fallback sifatida text response
        print("TTS: Using text fallback")
        return None
            
    except Exception as e:
        print(f"TTS Error: {e}")
        return None

def test_tts():
    """TTS funksiyasini test qilish uchun"""
    try:
        result = text_to_speech("hello world")
        if result:
            print(f"TTS Test: Success - {result}")
            return result
        else:
            print("TTS Test: Failed")
            return None
    except Exception as e:
        print(f"TTS Test Error: {e}")
        return None
