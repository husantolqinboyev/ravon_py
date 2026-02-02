from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.colors import Color, HexColor, black, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Flowable, Image as RLImage
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import os
import datetime
import qrcode
from PIL import Image as PILImage
import io

class CircularScore(Flowable):
    def __init__(self, score, size=1.5*inch):
        Flowable.__init__(self)
        self.score = score
        self.size = size
        self.width = size
        self.height = size

    def draw(self):
        canvas = self.canv
        canvas.saveState()
        
        # Draw Circle
        canvas.setLineWidth(5)
        canvas.setStrokeColor(HexColor('#2E7D32')) # Green color from image
        canvas.circle(self.size/2, self.size/2, self.size/2 - 5, stroke=1, fill=0)
        
        # Draw Score Text
        canvas.setFont("Helvetica-Bold", 32)
        canvas.setFillColor(HexColor('#2C3E50'))
        canvas.drawCentredString(self.size/2, self.size/2 - 10, f"{self.score}%")
        
        canvas.restoreState()

class StarRating(Flowable):
    def __init__(self, score, size=1.2*inch):
        Flowable.__init__(self)
        self.score = score
        self.size = size
        self.width = size
        self.height = 20

    def draw(self):
        canvas = self.canv
        canvas.saveState()
        
        # Draw 5 stars
        num_stars = 5
        star_size = 15
        gap = 5
        start_x = (self.width - (num_stars * star_size + (num_stars-1) * gap)) / 2
        
        canvas.setFillColor(HexColor('#F1C40F')) # Gold color
        for i in range(num_stars):
            # Simple star using text character if possible, or drawing
            canvas.setFont("Helvetica-Bold", star_size)
            canvas.drawCentredString(start_x + i * (star_size + gap), 0, "&") # Using & as a placeholder or drawing a star
            
        canvas.restoreState()

def generate_qr_code():
    """QR kod generatsiya qilish"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data("https://t.me/englishwithSanatbek")
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img.save("qrcode.png")
        return True
    except:
        return False

def draw_page_background(canvas, doc):
    """Sahifa atrofiga yanada nafis ramka va naqshlar chizish"""
    canvas.saveState()
    
    # Sahifa o'lchamlari
    width, height = A4
    
    # 1. Tashqi asosiy yashil ramka
    canvas.setStrokeColor(HexColor('#1B5E20'))
    canvas.setLineWidth(1.5)
    canvas.rect(15, 15, width-30, height-30)
    
    # 2. O'rta ingichka oltinrang ramka
    canvas.setStrokeColor(HexColor('#D4AF37')) # Metallic Gold
    canvas.setLineWidth(0.5)
    canvas.rect(20, 20, width-40, height-40)
    
    # 3. Ichki dekorativ yashil ramka
    canvas.setStrokeColor(HexColor('#2E7D32'))
    canvas.setLineWidth(0.8)
    canvas.rect(23, 23, width-46, height-46)
    
    # 4. Burchaklardagi murakkab naqshlar
    def draw_complex_ornament(x, y, rotate):
        canvas.saveState()
        canvas.translate(x, y)
        canvas.rotate(rotate)
        
        # Asosiy elementlar
        canvas.setStrokeColor(HexColor('#1B5E20'))
        canvas.setLineWidth(1.5)
        canvas.line(0, 0, 50, 0)
        canvas.line(0, 0, 0, 50)
        
        # Oltinrang bezaklar
        canvas.setStrokeColor(HexColor('#D4AF37'))
        canvas.setLineWidth(0.7)
        canvas.line(5, 5, 40, 5)
        canvas.line(5, 5, 5, 40)
        
        # Geometrik elementlar
        canvas.setLineWidth(0.5)
        canvas.circle(12, 12, 4, fill=0)
        canvas.setFillColor(HexColor('#D4AF37'))
        canvas.circle(22, 22, 2, fill=1)
        canvas.circle(32, 32, 1, fill=1)
        
        # Dekorativ yoy
        canvas.setStrokeColor(HexColor('#2E7D32'))
        canvas.arc(0, 0, 60, 60, 0, 90)
        
        canvas.restoreState()

    # To'rt burchakka murakkab naqsh qo'shish
    draw_complex_ornament(15, 15, 0)               # Pastki chap
    draw_complex_ornament(width-15, 15, 90)         # Pastki o'ng
    draw_complex_ornament(width-15, height-15, 180) # Yuqori o'ng
    draw_complex_ornament(15, height-15, 270)       # Yuqori chap
    
    # 5. Sahifa chetidagi dekorativ nuqtalar (Pattern)
    canvas.setStrokeColor(HexColor('#E0E0E0'))
    canvas.setLineWidth(0.3)
    # Faqat yuqori va pastga nuqtali chiziqlar
    for i in range(100, int(width)-100, 20):
        canvas.circle(i, 20, 0.5, fill=1)
        canvas.circle(i, height-20, 0.5, fill=1)

    # 6. Footer matni
    canvas.setFont("Helvetica-Oblique", 8)
    canvas.setFillColor(HexColor('#7F8C8D'))
    canvas.drawCentredString(width/2, 10, "Ravon AI - Professional English Pronunciation Analysis © 2026")
    
    canvas.restoreState()

def create_pdf_report(user_full_name, test_data):
    """
    ReportLab bilan professional PDF hisobot generatsiya qilish
    Foydalanuvchi taqdim etgan rasmga moslashtirilgan.
    """
    try:
        # QR kod yaratish
        generate_qr_code()
        
        # Fayl nomi va yo'li
        safe_name = ''.join(c for c in user_full_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        file_name = f"RavonAI_Report_{safe_name.replace(' ', '_')}.pdf"
        file_path = os.path.join(os.getcwd(), file_name)
        
        # PDF hujjat yaratish
        doc = SimpleDocTemplate(
            file_path,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=30
        )
        
        # Story (kontent) ro'yxati
        story = []
        
        # Ranglar
        primary_color = HexColor('#2E7D32') # Green
        accent_color = HexColor('#E67E22') # Orange
        text_color = HexColor('#2C3E50')
        
        # Custom stylelar
        styles = getSampleStyleSheet()
        
        # Header style
        header_style = ParagraphStyle(
            'Header',
            fontSize=22,
            alignment=TA_CENTER,
            textColor=primary_color,
            spaceAfter=5,
            fontName="Helvetica-Bold"
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            fontSize=12,
            alignment=TA_CENTER,
            textColor=text_color,
            spaceAfter=20
        )
        
        section_title_style = ParagraphStyle(
            'SectionTitle',
            fontSize=14,
            alignment=TA_CENTER,
            textColor=text_color,
            spaceAfter=15,
            fontName="Helvetica-Bold",
            textTransform='uppercase'
        )
        
        strength_title_style = ParagraphStyle(
            'StrengthTitle',
            fontSize=12,
            textColor=HexColor('#2E7D32'),
            fontName="Helvetica-Bold",
            spaceAfter=10,
            textTransform='uppercase'
        )
        
        plan_title_style = ParagraphStyle(
            'PlanTitle',
            fontSize=12,
            textColor=HexColor('#E67E22'),
            fontName="Helvetica-Bold",
            spaceAfter=10,
            textTransform='uppercase'
        )
        
        list_style = ParagraphStyle(
            'ListStyle',
            fontSize=10,
            textColor=text_color,
            leftIndent=10,
            firstLineIndent=-10,
            spaceAfter=5
        )
        
        # 1. Circular Score
        p_score = test_data.get('pronunciation_score', 0)
        
        # Sarlavha bezagi
        story.append(Spacer(1, 10))
        story.append(Paragraph("RAVON AI TALAF FUZ HISOBOTI", header_style))
        story.append(Paragraph("<hr color='#2E7D32' width='80%'/>", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Doira va Yulduzchalarni markazga olish uchun jadval
        visuals_table_data = [
            [CircularScore(p_score)],
            [Spacer(1, 10)],
            [StarRating(p_score)]
        ]
        visuals_table = Table(visuals_table_data, colWidths=[A4[0]-100])
        visuals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(visuals_table)
        story.append(Spacer(1, 15))
        
        # 3. Overall Grade
        cefr = test_data.get('cefr_level', 'A2')
        story.append(Paragraph(f"Umumiy Ball: {cefr}", header_style))
        story.append(Paragraph("Nutqingiz tahlili natijalari quyidagicha:", subtitle_style))
        
        story.append(Spacer(1, 10))
        story.append(Paragraph("<hr color='#ECF0F1' width='100%'/>", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # 4. TRANSKRIPT VA XATOLAR
        story.append(Paragraph("SIZNING NUTQINGIZ VA TAHLIL", section_title_style))
        transcription = test_data.get('transcription', '...')
        feedback_main = test_data.get('feedback', '')
        
        # Agar feedback ichida tahlil bo'lsa, uni alohida ko'rsatish
        story.append(Paragraph(f"<b>Nutqingiz:</b> {transcription}", subtitle_style))
        story.append(Spacer(1, 10))
        story.append(Paragraph(feedback_main, list_style))
        story.append(Spacer(1, 20))
        
        # 5. Two Columns: Strengths and Plan
        strengths = test_data.get('strengths', ["Har bir so'z aniq va tushunarli talaffuz qilingan."])
        plans = test_data.get('improvement_plan', ["So'zlarni bir-biriga bog'lab aytishni mashq qiling."])
        
        strength_points = [Paragraph(f"- {s}", list_style) for s in strengths]
        plan_points = [Paragraph(f"- {p}", list_style) for p in plans]
        
        col_data = [
            [
                [Paragraph("KUCHLI TOMONLAR", strength_title_style)] + strength_points,
                [Paragraph("RIVOJLANISH REJASI", plan_title_style)] + plan_points
            ]
        ]
        
        col_table = Table(col_data, colWidths=[2.8*inch, 2.8*inch])
        col_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        story.append(col_table)
        
        # 6. Footer / QR
        story.append(Spacer(1, 40))
        if os.path.exists("qrcode.png"):
            qr_table_data = [[RLImage("qrcode.png", width=1*inch, height=1*inch)]]
            qr_table = Table(qr_table_data, colWidths=[6*inch])
            qr_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(qr_table)
            story.append(Paragraph("To'liq ma'lumot uchun kanalimizga a'zo bo'ling", subtitle_style))
        
        # Build PDF
        doc.build(story, onFirstPage=draw_page_background, onLaterPages=draw_page_background)
        
        if os.path.exists("qrcode.png"):
            os.remove("qrcode.png")
            
        return file_path

    except Exception as e:
        print(f"PDF Error: {e}")
        return None
