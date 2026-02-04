#!/usr/bin/env python3
import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import tts_handler

def test_tts():
    print("TTS Test boshlanmoqda...")
    
    # Test 1: Oddiy matn
    result = tts_handler.text_to_speech("hello world")
    print(f"Test 1 - 'hello world': {result}")
    
    if result and os.path.exists(result):
        print(f"✅ Fayl yaratildi: {result}")
        print(f"📁 Fayl hajmi: {os.path.getsize(result)} bytes")
        
        # Faylni o'chirish
        os.remove(result)
        print("🗑️ Test fayl o'chirildi")
    else:
        print("❌ Fayl yaratilmadi")
    
    # Test 2: Uzunroq matn
    result2 = tts_handler.text_to_speech("The weather is very nice today")
    print(f"Test 2 - uzun matn: {result2}")
    
    if result2 and os.path.exists(result2):
        os.remove(result2)
        print("✅ Test 2 muvaffaqiyatli")
    else:
        print("❌ Test 2 muvaffaqiyatsiz")

if __name__ == "__main__":
    test_tts()
