import requests
import json
import time
import base64
from config import OPENROUTER_API_KEY, OPENROUTER_URL, MODEL_NAME

def transcribe_audio_with_gemini(audio_file_path):
    """
    OpenRouter Gemini modeli orqali ovozni matnga aylantirish
    """
    try:
        print(f"STT: Processing audio file: {audio_file_path}")
        
        # Audio faylni base64 formatiga o'tkazish
        with open(audio_file_path, "rb") as audio_file:
            audio_data = audio_file.read()
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        print(f"STT: Audio size: {len(audio_data)} bytes")
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        
        # Telegram voice uchun format
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Transcribe this English audio file. Return only the transcribed text without any additional comments."
                        },
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_base64,
                                "format": "oga"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 200
        }
        
        print("STT: Sending request to Gemini...")
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
        
        print(f"STT: Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"STT: Response keys: {result.keys()}")
            
            if 'choices' in result and len(result['choices']) > 0:
                transcribed_text = result['choices'][0]['message']['content'].strip()
                print(f"STT: Transcribed text: '{transcribed_text}'")
                
                # Agar javob transkripsiya bo'lmasa
                if len(transcribed_text) > 100 or "please provide" in transcribed_text.lower():
                    print("STT: Got generic response, returning None")
                    return None
                
                return transcribed_text
            else:
                print("STT: No choices in response")
                return None
        else:
            print(f"STT Error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"STT Exception: {str(e)}")
        return None

def analyze_pronunciation(transcribed_text, original_text=None):
    """
    OpenRouter orqali talaffuzni tahlil qilish.
    To'liq feedback, stress va xatolarni ko'rsatish bilan.
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    
    prompt = f"""
    Siz ingliz tili talaffuzi bo'yicha dunyo darajasidagi ekspert murabbiysiz. Quyidagi talaffuz qilingan matnni (transkripsiya) tahlil qiling va o'zbek tilida batafsil feedback bering.

    Foydalanuvchi aytdi (transkripsiya): "{transcribed_text}"
    {f'Asl kutilgan matn: "{original_text}"' if original_text else "Asl matn berilmagan"}
    
    Vazifangiz:
    1. Transkripsiyadagi xatolarni (masalan, ■ belgilari, noto'g'ri fonemalar) tushunib, foydalanuvchi nima demoqchi bo'lganini aniqlang.
    2. Talaffuz ballarini (0-100) realistik baholang.
    3. Xatolarni o'zbek tilida tushuntiring (masalan: "th" tovushini noto'g'ri aytish, so'z oxiridagi harflarni tushirib qoldirish).
    4. Foydalanuvchiga aynan qaysi so'zlarda xato qilganini va qanday to'g'irlashni ayting.

    Javobni FAQAT JSON formatida quyidagi tuzilmada qaytaring:
    {{
        "pronunciation_score": [ball],
        "fluency_score": [ball],
        "accuracy_score": [ball],
        "cefr_level": "[A1, A2, B1, B2, C1 yoki C2]",
        "transcription": "[transkripsiyani tozalangan va to'g'irlangan inglizcha varianti]",
        "strengths": ["kuchli tomon 1", "kuchli tomon 2", "kuchli tomon 3"],
        "improvement_plan": ["tavsiya 1", "tavsiya 2", "tavsiya 3"],
        "feedback": "📊 Talaffuz: [ball]%\\n🔍 Tahlil: [batafsil o'zbekcha tushuntirish]\\n💡 Tavsiya: [eng muhim maslahat]"
    }}
    """

    data = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "Siz ingliz tili talaffuzi bo'yicha ekspert murabbiysiz. O'zbek tilida batafsil va foydali feedback berasiz."},
            {"role": "user", "content": prompt}
        ]
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(OPENROUTER_URL, headers=headers, data=json.dumps(data))
            
            if response.status_code == 429:
                # Rate limit - kutish
                wait_time = 2 ** attempt  # 1, 2, 4 seconds
                print(f"AI Rate Limited. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                continue
                
            if response.status_code != 200:
                print(f"AI Pronunciation Error: Status {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
            result = response.json()
            
            # Response formatini tekshirish
            if 'choices' not in result or not result['choices']:
                print(f"AI Response Error: No choices in pronunciation response")
                print(f"Response: {result}")
                return None
                
            content = result['choices'][0]['message']['content']
            
            # JSONni tozalash (ba'zan AI markdown formatida qaytaradi)
            content = content.replace("■", "").strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            return json.loads(content)
        except Exception as e:
            print(f"AI Pronunciation Error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
            continue
    
    print("AI Pronunciation: Max retries reached")
    return None

def generate_content(prompt):
    """
    OpenRouter orqali ixtiyoriy kontent yaratish.
    O'qituvchilar uchun material yaratishda ishlatiladi.
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    
    data = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are a creative AI assistant for English teachers. Always generate unique and varied content."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 1.2,  # Randomlikni yanada oshirish uchun
        "max_tokens": 200,   # Uzunroq matnlar uchun
        "top_p": 0.9,       # Ko'proq xilma-xil javoblar uchun
        "presence_penalty": 0.3,  # Takrorlanishni oldini olish uchun
        "frequency_penalty": 0.3  # Takrorlanishni oldini olish uchun
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(OPENROUTER_URL, headers=headers, data=json.dumps(data))
            
            if response.status_code == 429:
                # Rate limit - kutish
                wait_time = 2 ** attempt  # 1, 2, 4 seconds
                print(f"AI Rate Limited. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                continue
                
            if response.status_code != 200:
                print(f"AI API Error: Status {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
            result = response.json()
            
            # Response formatini tekshirish
            if 'choices' not in result or not result['choices']:
                print(f"AI Response Error: No choices in response")
                print(f"Response: {result}")
                return None
                
            content = result['choices'][0]['message']['content']
            
            # Markdown formatni tozalash
            if "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            return content.strip()
        except Exception as e:
            print(f"AI Content Generation Error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
            continue
    
    print("AI Content Generation: Max retries reached")
    return None
