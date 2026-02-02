from fpdf import FPDF
import os
import qrcode
from config import REQUIRED_CHANNEL

class PronunciationReport(FPDF):
    def header(self):
        try:
            self.set_fill_color(0, 102, 204)
            self.rect(0, 0, 210, 40, 'F')
            self.set_text_color(255, 255, 255)
            self.set_font('Arial', 'B', 24)
            self.cell(0, 20, 'RAVON AI', 0, 1, 'C')
            self.set_font('Arial', 'B', 14)
            self.cell(0, 10, 'Talaffuz Tahlili Hisoboti', 0, 1, 'C')
            self.ln(15)
        except Exception as e:
            print(f"Header Error: {e}")

    def footer(self):
        try:
            self.set_y(-30)
            # QR kod joyi - Windows uchun moslangan
            qr_path = os.path.join(os.getcwd(), "channel_qr.png")
            if os.path.exists(qr_path):
                self.image(qr_path, x=170, y=265, w=25)
            
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, f'Sahifa {self.page_no()} | Ravon AI Bot | Kanal: {REQUIRED_CHANNEL}', 0, 0, 'L')
        except Exception as e:
            print(f"Footer Error: {e}")

def generate_qr():
    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(f"https://t.me/{REQUIRED_CHANNEL[1:]}")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        # Windows uchun moslangan yo'l
        qr_path = os.path.join(os.getcwd(), "channel_qr.png")
        img.save(qr_path)
    except Exception as e:
        print(f"QR Error: {e}")

def generate_pdf_report(user_full_name, test_data):
    try:
        # QR kodni generatsiya qilish (xatolikni oldini olish)
        try:
            generate_qr()
        except:
            pass
        
        pdf = PronunciationReport()
        pdf.add_page()
        
        # Header qismi - chiroyli gradient fon
        pdf.set_fill_color(52, 152, 219)
        pdf.rect(0, 0, 210, 60, 'F')
        
        # Font xatoliklariga qarshi himoya
        try:
            pdf.set_font("Arial", 'B', 24)
        except:
            pdf.set_font("Helvetica", 'B', 24)
        
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 20, "Ravon AI", 0, 1, 'C')
        
        try:
            pdf.set_font("Arial", 'B', 16)
        except:
            pdf.set_font("Helvetica", 'B', 16)
        
        pdf.cell(0, 10, "Pronunciation Analysis Report", 0, 1, 'C')
        pdf.cell(0, 10, f"Generated: {test_data.get('date', 'Unknown')}", 0, 1, 'C')
        
        # Foydalanuvchi ma'lumotlari
        pdf.set_text_color(40, 40, 40)
        try:
            pdf.set_font("Arial", 'B', 14)
        except:
            pdf.set_font("Helvetica", 'B', 14)
        
        # Foydalanuvchi ismini xavfsiz qilish
        safe_name = ''.join(char for char in user_full_name if ord(char) < 128)
        pdf.cell(0, 15, f"Student: {safe_name}", 0, 1)
        pdf.ln(10)

        # Natijalar jadvali - chiroyi dizayn
        try:
            pdf.set_font("Arial", 'B', 16)
        except:
            pdf.set_font("Helvetica", 'B', 16)
            
        pdf.set_text_color(52, 152, 219)
        pdf.cell(0, 12, "Performance Scores", 0, 1)
        pdf.ln(5)

        # Jadval header
        pdf.set_fill_color(52, 152, 219)
        pdf.set_text_color(255, 255, 255)
        
        try:
            pdf.set_font("Arial", 'B', 12)
        except:
            pdf.set_font("Helvetica", 'B', 12)
            
        pdf.cell(60, 12, "Category", 1, 0, 'C', True)
        pdf.cell(40, 12, "Score", 1, 0, 'C', True)
        pdf.cell(90, 12, "Performance", 1, 1, 'C', True)

        scores = [
            ("Pronunciation", test_data.get('pronunciation_score', 0) or 0),
            ("Fluency", test_data.get('fluency_score', 0) or 0),
            ("Accuracy", test_data.get('accuracy_score', 0) or 0)
        ]

        # Jadval qatorlari
        for i, (cat, score) in enumerate(scores):
            # Alternating row colors
            if i % 2 == 0:
                pdf.set_fill_color(240, 248, 255)
            else:
                pdf.set_fill_color(255, 255, 255)
            
            pdf.set_text_color(40, 40, 40)
            try:
                pdf.set_font("Arial", 'B', 11)
            except:
                pdf.set_font("Helvetica", 'B', 11)
                
            pdf.cell(60, 12, f"  {cat}", 1, 0, 'L', True)
            
            # Score va performance
            try:
                pdf.set_font("Arial", 'B', 11)
            except:
                pdf.set_font("Helvetica", 'B', 11)
            
            if score >= 90:
                pdf.set_text_color(0, 128, 0)
                performance = "Excellent"
                color = (0, 200, 0)
            elif score >= 80:
                pdf.set_text_color(0, 128, 0)
                performance = "Very Good"
                color = (50, 205, 50)
            elif score >= 70:
                pdf.set_text_color(255, 140, 0)
                performance = "Good"
                color = (255, 165, 0)
            elif score >= 60:
                pdf.set_text_color(255, 140, 0)
                performance = "Fair"
                color = (255, 140, 0)
            else:
                pdf.set_text_color(220, 20, 60)
                performance = "Needs Work"
                color = (220, 20, 60)
                
            pdf.cell(40, 12, str(score), 1, 0, 'C', True)
            
            # Performance bar
            pdf.set_fill_color(*color)
            bar_width = int(score * 0.8)  # 80px max width
            pdf.cell(90, 12, f" {performance}", 1, 1, 'L', True)
            
            # Performance indicator - ASCII belgilar bilan
            pdf.set_text_color(255, 255, 255)
            pdf.set_font_size(8)
            progress_bar = "=" * int(score/10) + "-" * (10 - int(score/10))
            pdf.cell(-90, 6, f"[{progress_bar}]", 0, 0, 'L', True)
            pdf.ln(6)

        # Overall Score - chiroyli ko'rsatkich
        pdf.ln(15)
        p_score = test_data.get('pronunciation_score', 0) or 0
        f_score = test_data.get('fluency_score', 0) or 0
        a_score = test_data.get('accuracy_score', 0) or 0
        
        overall_score = int((p_score + f_score + a_score) // 3)
        
        pdf.set_fill_color(52, 152, 219)
        pdf.set_text_color(255, 255, 255)
        try:
            pdf.set_font("Arial", 'B', 14)
        except:
            pdf.set_font("Helvetica", 'B', 14)
            
        pdf.cell(0, 12, f"Overall Score: {overall_score}/100", 0, 1, 'C', True)
        
        # Progress bar
        pdf.set_fill_color(200, 200, 200)
        pdf.rect(55, None, 100, 10, 'F')
        pdf.set_fill_color(0, 200, 0)
        pdf.rect(55, None, overall_score, 10, 'F')
        
        pdf.ln(20)

        # AI Recommendations - chiroyli quti
        pdf.set_draw_color(52, 152, 219)
        pdf.set_fill_color(240, 248, 255)
        pdf.rect(10, None, 190, 60, 'DF')
        
        try:
            pdf.set_font("Arial", 'B', 14)
        except:
            pdf.set_font("Helvetica", 'B', 14)
            
        pdf.set_text_color(52, 152, 219)
        pdf.cell(0, 12, "AI Recommendations", 0, 1, 'C')
        pdf.ln(5)
        
        try:
            pdf.set_font("Arial", size=11)
        except:
            pdf.set_font("Helvetica", size=11)
            
        pdf.set_text_color(40, 40, 40)
        
        # Faqat inglizcha feedback - barcha o'zbekcha harflarni almashtirish
        feedback = test_data.get('feedback', 'No feedback available.')
        
        # Barcha o'zbekcha kirill harflarini lotin harflariga almashtirish
        cyrillic_to_latin = {
            'А': 'A', 'а': 'a', 'Б': 'B', 'б': 'b', 'В': 'V', 'в': 'v',
            'Г': 'G', 'г': 'g', 'Д': 'D', 'д': 'd', 'Е': 'E', 'е': 'e',
            'Ё': 'Yo', 'ё': 'yo', 'Ж': 'J', 'ж': 'j', 'З': 'Z', 'з': 'z',
            'И': 'I', 'и': 'i', 'Й': 'Y', 'й': 'y', 'К': 'K', 'к': 'k',
            'Л': 'L', 'л': 'l', 'М': 'M', 'м': 'm', 'Н': 'N', 'н': 'n',
            'О': 'O', 'о': 'o', 'П': 'P', 'п': 'p', 'Р': 'R', 'р': 'r',
            'С': 'S', 'с': 's', 'Т': 'T', 'т': 't', 'У': 'U', 'у': 'u',
            'Ф': 'F', 'ф': 'f', 'Х': 'X', 'х': 'x', 'Ц': 'Ts', 'ц': 'ts',
            'Ч': 'Ch', 'ч': 'ch', 'Ш': 'Sh', 'ш': 'sh', 'Щ': 'Shch', 'щ': 'shch',
            'Ъ': '', 'ъ': '', 'Ы': 'Y', 'ы': 'y', 'Ь': '', 'ь': '',
            'Э': 'E', 'э': 'e', 'Ю': 'Yu', 'ю': 'yu', 'Я': 'Ya', 'я': 'ya',
            'Ғ': 'Gh', 'ғ': 'gh', 'Қ': 'Q', 'қ': 'q', 'Ҳ': 'H', 'ҳ': 'h',
            'Ў': 'O', 'ў': 'o', 'Ҳ': 'H', 'ҳ': 'h'
        }
        
        # Har bir harfni almashtirish
        for cyrillic, latin in cyrillic_to_latin.items():
            feedback = feedback.replace(cyrillic, latin)
        
        # Qolgan no'obek harflarni olib tashlash
        feedback = ''.join(char for char in feedback if ord(char) < 128 or char in '.,!?-:; ')
        
        # Feedback ni xavfsiz tarzda qo'shish
        try:
            pdf.multi_cell(170, 8, feedback, border=0, align='L')
        except Exception as e:
            print(f"Feedback rendering error: {e}")
            pdf.multi_cell(170, 8, "Excellent pronunciation analysis completed.", border=0, align='L')

        # Footer
        pdf.ln(20)
        pdf.set_text_color(150, 150, 150)
        try:
            pdf.set_font("Arial", size=8)
        except:
            pdf.set_font("Helvetica", size=8)
            
        pdf.cell(0, 5, "Generated by Ravon AI - English Pronunciation Assistant", 0, 1, 'C')
        pdf.cell(0, 5, "www.ravonai.uz", 0, 1, 'C')

        file_name = f"RavonAI_Report_{safe_name.replace(' ', '_')}.pdf"
        file_path = os.path.join(os.getcwd(), file_name)
        
        try:
            pdf.output(file_path)
            return file_path
        except:
            return None
            
    except Exception as e:
        print(f"PDF Generation Error: {e}")
        return None
