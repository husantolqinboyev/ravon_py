import sqlite3
import datetime
from config import DB_NAME, ADMIN_IDS, TEACHER_IDS

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        full_name TEXT,
        username TEXT,
        language TEXT DEFAULT 'uz',
        test_limit INTEGER DEFAULT 5,
        is_premium BOOLEAN DEFAULT 0,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tests (
        test_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        audio_file_id TEXT,
        original_text TEXT,
        transcribed_text TEXT,
        pronunciation_score REAL,
        fluency_score REAL,
        accuracy_score REAL,
        feedback TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    cursor.execute('CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)')
    
    # O'qituvchilar jadvali
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS teachers (
        teacher_id INTEGER PRIMARY KEY,
        assigned_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # O'qituvchi-O'quvchi bog'liqligi
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS student_teacher (
        student_id INTEGER,
        teacher_id INTEGER,
        PRIMARY KEY (student_id, teacher_id),
        FOREIGN KEY (student_id) REFERENCES users (user_id),
        FOREIGN KEY (teacher_id) REFERENCES teachers (teacher_id)
    )
    ''')
    
    # Referallar jadvali
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS referrals (
        referrer_id INTEGER,
        referred_id INTEGER PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (referrer_id) REFERENCES users (user_id),
        FOREIGN KEY (referred_id) REFERENCES users (user_id)
    )
    ''')
    
    # Referal bonuslar jadvali (har 3 ta referal uchun bonus)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS referral_bonus (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        referral_count INTEGER,
        bonus_given INTEGER DEFAULT 3,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    # Anti-cheat loglar jadvali
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS anti_cheat_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        referrer_id INTEGER,
        reason TEXT,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id),
        FOREIGN KEY (referrer_id) REFERENCES users (user_id)
    )
    ''')

    # O'quv materiallari jadvali
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS materials (
        material_id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_id INTEGER,
        content TEXT,
        type TEXT, -- 'word' yoki 'sentence'
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # To'lovlar jadvali
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        card_number TEXT,
        photo_file_id TEXT,
        status TEXT DEFAULT 'pending', -- pending, approved, rejected
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    # Tariflar jadvali
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tariffs (
        tariff_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        price INTEGER,
        duration_days INTEGER,
        test_limit INTEGER, -- Kunlik so'rovlar soni
        word_limit INTEGER DEFAULT 40, -- Maksimal so'zlar soni
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Premium obunalar jadvali
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS premium_subscriptions (
        subscription_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        tariff_id INTEGER,
        starts_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ends_at TIMESTAMP,
        is_active BOOLEAN DEFAULT 1,
        FOREIGN KEY (user_id) REFERENCES users (user_id),
        FOREIGN KEY (tariff_id) REFERENCES tariffs (tariff_id)
    )
    ''')
    
    # Standart tariflarni qo'shish
    cursor.execute('INSERT OR IGNORE INTO tariffs (name, price, duration_days, test_limit) VALUES (?, ?, ?, ?)', 
                   ('Haftalik', 15000, 7, 50))
    cursor.execute('INSERT OR IGNORE INTO tariffs (name, price, duration_days, test_limit) VALUES (?, ?, ?, ?)', 
                   ('Oylik', 45000, 30, 200))
    cursor.execute('INSERT OR IGNORE INTO tariffs (name, price, duration_days, test_limit) VALUES (?, ?, ?, ?)', 
                   ('Yillik', 300000, 365, 1000))
    
    # Takrorlangan tariflarni tozalash
    clean_duplicate_tariffs()
    
    conn.commit()
    conn.close()

def add_user(user_id, full_name, username, referrer_id=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Anti-cheat protection 1: O'z-o'zini taklif qilishni taqiqlash
    if referrer_id and str(user_id) == str(referrer_id):
        log_anti_cheat(user_id, referrer_id, "SELF_REFERRAL", f"User {user_id} tried to refer themselves")
        conn.commit()
        conn.close()
        return False
    
    # Anti-cheat protection 2: Foydalanuvchi allaqachon mavjudligini tekshirish
    cursor.execute('SELECT user_id, full_name, username FROM users WHERE user_id = ?', (user_id,))
    existing_user = cursor.fetchone()
    
    if existing_user:
        # Agar foydalanuvchi allaqachon mavjud bo'lsa va referrer_id berilgan bo'lsa,
        # faqat birinchi marta referal qabul qilamiz
        if referrer_id:
            # Anti-cheat protection 3: Allaqachon referal bo'lganligini tekshirish
            cursor.execute('SELECT 1 FROM referrals WHERE referred_id = ?', (user_id,))
            if cursor.fetchone():
                log_anti_cheat(user_id, referrer_id, "DUPLICATE_REFERRAL", f"User {user_id} already referred")
                conn.commit()
                conn.close()
                return False
            
            # Anti-cheat protection 4: Username va full_name tekshirish (xavfsizlik choralari)
            cursor.execute('SELECT COUNT(*) FROM users WHERE full_name = ? OR username = ?', 
                         (full_name, username))
            similar_users = cursor.fetchone()[0]
            
            # Anti-cheat protection 5: Bir xil ma'lumotli foydalanuvchilar soni cheklovi
            if similar_users > 3:  # Bir xil ism/username bilan 3 tadan ortiq foydalanuvchi bo'lsa
                log_anti_cheat(user_id, referrer_id, "TOO_MANY_SIMILAR_USERS", 
                              f"Found {similar_users} similar users for {full_name}/{username}")
                conn.commit()
                conn.close()
                return False
            
            # Anti-cheat protection 6: Referrer limiti (kuniga maksimal 10 ta referal)
            cursor.execute('''
                SELECT COUNT(*) FROM referrals 
                WHERE referrer_id = ? AND DATE(created_at) = DATE('now')
            ''', (referrer_id,))
            daily_referrals = cursor.fetchone()[0]
            
            if daily_referrals >= 10:
                log_anti_cheat(user_id, referrer_id, "DAILY_LIMIT_EXCEEDED", 
                              f"User {referrer_id} exceeded daily limit: {daily_referrals}")
                conn.commit()
                conn.close()
                return False
            
            # Anti-cheat protection 7: Referrerning umumiy referal limiti
            cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (referrer_id,))
            total_referrals = cursor.fetchone()[0]
            
            if total_referrals >= 50:  # Jami 50 tadan ortiq referal bo'lsa
                log_anti_cheat(user_id, referrer_id, "TOTAL_LIMIT_EXCEEDED", 
                              f"User {referrer_id} exceeded total limit: {total_referrals}")
                conn.commit()
                conn.close()
                return False
            
            # Referalni qo'shish
            cursor.execute('INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)', 
                           (referrer_id, user_id))
            
            if cursor.rowcount > 0:
                # Referal sonini hisoblash
                cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (referrer_id,))
                referral_count = cursor.fetchone()[0]
                
                # Har 3 ta referal uchun bonus berish
                if referral_count % 3 == 0:
                    # Bonus allaqachon berilganligini tekshirish
                    cursor.execute('SELECT 1 FROM referral_bonus WHERE user_id = ? AND referral_count = ?', 
                                 (referrer_id, referral_count))
                    if not cursor.fetchone():
                        # Bonus berish
                        cursor.execute('UPDATE users SET test_limit = test_limit + 3 WHERE user_id = ?', (referrer_id,))
                        # Bonusni yozib qo'yish
                        cursor.execute('INSERT INTO referral_bonus (user_id, referral_count, bonus_given) VALUES (?, ?, ?)', 
                                       (referrer_id, referral_count, 3))
        
        conn.commit()
        conn.close()
        return False  # Yangi foydalanuvchi emas
    
    # Yangi foydalanuvchi qo'shish
    cursor.execute('INSERT INTO users (user_id, full_name, username) VALUES (?, ?, ?)', 
                   (user_id, full_name, username))
    
    new_referral = False
    if referrer_id:
        # Anti-cheat protection 8: Yangi foydalanuvchi uchun ham tekshirishlar
        cursor.execute('SELECT 1 FROM referrals WHERE referred_id = ?', (user_id,))
        if not cursor.fetchone():
            # Anti-cheat protection 9: Username va full_name tekshirish
            cursor.execute('SELECT COUNT(*) FROM users WHERE full_name = ? OR username = ?', 
                         (full_name, username))
            similar_users = cursor.fetchone()[0]
            
            if similar_users <= 3:  # Xavfsizlik chegarasi ichida
                # Anti-cheat protection 10: Kunlik referal limiti
                cursor.execute('''
                    SELECT COUNT(*) FROM referrals 
                    WHERE referrer_id = ? AND DATE(created_at) = DATE('now')
                ''', (referrer_id,))
                daily_referrals = cursor.fetchone()[0]
                
                if daily_referrals < 10:
                    # Anti-cheat protection 11: Umumiy referal limiti
                    cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (referrer_id,))
                    total_referrals = cursor.fetchone()[0]
                    
                    if total_referrals < 50:
                        # Referalni qo'shish
                        cursor.execute('INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)', 
                                       (referrer_id, user_id))
                        
                        if cursor.rowcount > 0:
                            new_referral = True
                            
                            # Referal sonini hisoblash
                            cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (referrer_id,))
                            referral_count = cursor.fetchone()[0]
                            
                            # Har 3 ta referal uchun bonus berish
                            if referral_count % 3 == 0:
                                # Bonus allaqachon berilganligini tekshirish
                                cursor.execute('SELECT 1 FROM referral_bonus WHERE user_id = ? AND referral_count = ?', 
                                             (referrer_id, referral_count))
                                if not cursor.fetchone():
                                    # Bonus berish
                                    cursor.execute('UPDATE users SET test_limit = test_limit + 3 WHERE user_id = ?', (referrer_id,))
                                    # Bonusni yozib qo'yish
                                    cursor.execute('INSERT INTO referral_bonus (user_id, referral_count, bonus_given) VALUES (?, ?, ?)', 
                                                   (referrer_id, referral_count, 3))
    
    conn.commit()
    conn.close()
    return new_referral

def get_referral_count(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_referral_stats(user_id):
    """Foydalanuvchining referal statistikasini qaytaradi"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Jami referallar soni
    cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (user_id,))
    total_referrals = cursor.fetchone()[0]
    
    # Bonuslar soni
    cursor.execute('SELECT COUNT(*) FROM referral_bonus WHERE user_id = ?', (user_id,))
    bonus_count = cursor.fetchone()[0]
    
    # Oxirgi bonus qachon berilgan
    cursor.execute('SELECT referral_count FROM referral_bonus WHERE user_id = ? ORDER BY referral_count DESC LIMIT 1', 
                   (user_id,))
    last_bonus_referral_count = cursor.fetchone()
    
    conn.close()
    
    # Keyingi bonus uchun qancha referal kerakligini hisoblash
    if last_bonus_referral_count:
        next_bonus_at = last_bonus_referral_count[0] + 3
        referrals_needed = max(0, next_bonus_at - total_referrals)
    else:
        next_bonus_at = 3
        referrals_needed = max(0, 3 - total_referrals)
    
    return {
        'total_referrals': total_referrals,
        'bonus_count': bonus_count,
        'referrals_needed': referrals_needed,
        'next_bonus_at': next_bonus_at
    }

def log_anti_cheat(user_id, referrer_id, reason, details):
    """Anti-cheat logini yozish"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO anti_cheat_logs (user_id, referrer_id, reason, details)
    VALUES (?, ?, ?, ?)
    ''', (user_id, referrer_id, reason, details))
    conn.commit()
    conn.close()

def get_anti_cheat_stats():
    """Anti-cheat statistikasini olish"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Oxirgi 24 soatdagi loglar
    cursor.execute('''
        SELECT COUNT(*) FROM anti_cheat_logs 
        WHERE created_at > datetime('now', '-1 day')
    ''')
    last_24h = cursor.fetchone()[0]
    
    # Oxirgi 7 kunlik loglar
    cursor.execute('''
        SELECT COUNT(*) FROM anti_cheat_logs 
        WHERE created_at > datetime('now', '-7 days')
    ''')
    last_7d = cursor.fetchone()[0]
    
    # Jami loglar
    cursor.execute('SELECT COUNT(*) FROM anti_cheat_logs')
    total = cursor.fetchone()[0]
    
    # Eng ko'p uchraydigan sabablar
    cursor.execute('''
        SELECT reason, COUNT(*) as count 
        FROM anti_cheat_logs 
        GROUP BY reason 
        ORDER BY count DESC 
        LIMIT 5
    ''')
    top_reasons = cursor.fetchall()
    
    conn.close()
    
    return {
        'last_24h': last_24h,
        'last_7d': last_7d,
        'total': total,
        'top_reasons': top_reasons
    }

def add_material(teacher_id, content, m_type):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO materials (teacher_id, content, type) VALUES (?, ?, ?)', 
                   (teacher_id, content, m_type))
    conn.commit()
    conn.close()

def get_random_material():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT content FROM materials ORDER BY RANDOM() LIMIT 1')
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else "The quick brown fox jumps over the lazy dog."

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def is_admin(user_id):
    if user_id in ADMIN_IDS:
        return True
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM admins WHERE user_id = ?', (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res is not None

def add_admin(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def get_today_test_count(user_id):
    """Foydalanuvchining bugun qilgan testlar sonini olish"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) FROM tests 
        WHERE user_id = ? AND date(created_at) = date('now')
    ''', (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_stats():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Jami foydalanuvchilar
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    # Jami testlar (API ishlatilgani)
    cursor.execute('SELECT COUNT(*) FROM tests')
    total_tests = cursor.fetchone()[0]
    
    # Faol foydalanuvchilar (oxirgi 24 soatda test topshirganlar)
    cursor.execute('''
        SELECT COUNT(DISTINCT user_id) 
        FROM tests 
        WHERE created_at >= datetime('now', '-1 day')
    ''')
    active_users_24h = cursor.fetchone()[0]
    
    # Faol foydalanuvchilar (oxirgi 7 kunda test topshirganlar)
    cursor.execute('''
        SELECT COUNT(DISTINCT user_id) 
        FROM tests 
        WHERE created_at >= datetime('now', '-7 days')
    ''')
    active_users_7d = cursor.fetchone()[0]
    
    # Premium foydalanuvchilar
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_premium = 1')
    premium_users = cursor.fetchone()[0]
    
    conn.close()
    return {
        "total_users": total_users,
        "total_tests": total_tests,
        "active_users_24h": active_users_24h,
        "active_users_7d": active_users_7d,
        "premium_users": premium_users
    }

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    conn.close()
    return [u[0] for u in users]

def add_admin(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def is_teacher(user_id):
    if user_id in TEACHER_IDS:
        return True
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM teachers WHERE teacher_id = ?', (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res is not None

def add_teacher(user_id, admin_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO teachers (teacher_id, assigned_by) VALUES (?, ?)', (user_id, admin_id))
    conn.commit()
    conn.close()

def assign_student(student_id, teacher_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO student_teacher (student_id, teacher_id) VALUES (?, ?)', (student_id, teacher_id))
    conn.commit()
    conn.close()

def get_teacher_students(teacher_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.user_id, u.full_name, u.username 
        FROM users u 
        JOIN student_teacher st ON u.user_id = st.student_id 
        WHERE st.teacher_id = ?
    ''', (teacher_id,))
    students = cursor.fetchall()
    conn.close()
    return students

def add_material(teacher_id, content, material_type):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO materials (teacher_id, content, type) VALUES (?, ?, ?)
    ''', (teacher_id, content, material_type))
    conn.commit()
    conn.close()

def get_teacher_materials(teacher_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT material_id, teacher_id, content, type, created_at 
        FROM materials 
        WHERE teacher_id = ? 
        ORDER BY created_at DESC
    ''', (teacher_id,))
    materials = cursor.fetchall()
    conn.close()
    return materials

def get_random_material(material_type=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if material_type:
        cursor.execute('''
            SELECT content FROM materials WHERE type = ? ORDER BY RANDOM() LIMIT 1
        ''', (material_type,))
    else:
        cursor.execute('SELECT content FROM materials ORDER BY RANDOM() LIMIT 1')
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def decrement_limit(user_id):
    """Foydalanuvchi limitini bittaga kamaytirish"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT is_premium, test_limit FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    if user and not user[0] and user[1] > 0:
        cursor.execute('UPDATE users SET test_limit = test_limit - 1 WHERE user_id = ?', (user_id,))
        conn.commit()
    conn.close()

def save_test_result(user_id, audio_id, original, transcribed, p_score, f_score, a_score, feedback):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO tests (user_id, audio_file_id, original_text, transcribed_text, 
                       pronunciation_score, fluency_score, accuracy_score, feedback)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, audio_id, original, transcribed, p_score, f_score, a_score, feedback))
    
    # Limitni kamaytirish (faqat kunlik limitdan oshganda bonusdan chegirish)
    cursor.execute('SELECT is_premium, test_limit FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    if user and not user[0]:
        # Bugungi testlar sonini tekshiramiz (bu test ham allaqachon qo'shilgan)
        cursor.execute('''
            SELECT COUNT(*) FROM tests 
            WHERE user_id = ? AND date(created_at) = date('now')
        ''', (user_id,))
        today_count = cursor.fetchone()[0]
        
        # Foydalanuvchi tarifini aniqlash
        cursor.execute('''
            SELECT t.test_limit FROM premium_subscriptions ps
            JOIN tariffs t ON ps.tariff_id = t.tariff_id
            WHERE ps.user_id = ? AND ps.is_active = 1 AND ps.ends_at > CURRENT_TIMESTAMP
        ''', (user_id,))
        tariff_res = cursor.fetchone()
        daily_limit = tariff_res[0] if tariff_res else 3 # Free limit 3
        
        # Agar bugungi testlar soni kunlik limitdan oshgan bo'lsa, bonusdan kamaytiramiz
        if today_count > daily_limit and user[1] > 0:
            cursor.execute('UPDATE users SET test_limit = test_limit - 1 WHERE user_id = ?', (user_id,))
    
    conn.commit()
    conn.close()

def create_payment(user_id, amount, card_number, photo_file_id=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO payments (user_id, amount, card_number, photo_file_id) VALUES (?, ?, ?, ?)', 
                   (user_id, amount, card_number, photo_file_id))
    conn.commit()
    conn.close()

def get_pending_payments():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM payments WHERE status = "pending"')
    payments = cursor.fetchall()
    conn.close()
    return payments

def update_payment_status(payment_id, status):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE payments SET status = ? WHERE payment_id = ?', (status, payment_id))
    
    user_id = None
    if status == 'approved':
        cursor.execute('SELECT user_id, amount FROM payments WHERE payment_id = ?', (payment_id,))
        payment = cursor.fetchone()
        if payment:
            user_id = payment[0]
            amount = payment[1]
            
            # To'lov summasiga mos tarifni topish
            cursor.execute('SELECT tariff_id, duration_days, test_limit, word_limit FROM tariffs WHERE price = ? LIMIT 1', (amount,))
            tariff = cursor.fetchone()
            
            if tariff:
                tariff_id, duration_days, test_limit, word_limit = tariff
                
                # Premium subscription yaratish
                end_date = datetime.datetime.now() + datetime.timedelta(days=duration_days)
                cursor.execute('''
                    INSERT OR REPLACE INTO premium_subscriptions 
                    (user_id, tariff_id, starts_at, ends_at, is_active)
                    VALUES (?, ?, date('now'), ?, 1)
                ''', (user_id, tariff_id, end_date.strftime('%Y-%m-%d')))
                
                # Foydalanuvchiga premium statusini va limitini berish
                cursor.execute('UPDATE users SET is_premium = 1, test_limit = test_limit + ? WHERE user_id = ?', (test_limit, user_id))
            else:
                # Agar tarif topilmasa, default Basic berish
                cursor.execute('UPDATE users SET is_premium = 1, test_limit = test_limit + 7 WHERE user_id = ?', (7, user_id))
                
    elif status == 'rejected':
        cursor.execute('SELECT user_id FROM payments WHERE payment_id = ?', (payment_id,))
        payment = cursor.fetchone()
        if payment:
            user_id = payment[0]
    
    conn.commit()
    conn.close()
    return user_id

def get_tariffs():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tariffs WHERE is_active = 1 ORDER BY price')
    tariffs = cursor.fetchall()
    conn.close()
    return tariffs

def get_user_subscription(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    SELECT ps.*, t.name, t.test_limit 
    FROM premium_subscriptions ps
    JOIN tariffs t ON ps.tariff_id = t.tariff_id
    WHERE ps.user_id = ? AND ps.is_active = 1 AND ps.ends_at > date('now')
    ORDER BY ps.ends_at DESC LIMIT 1
    ''', (user_id,))
    subscription = cursor.fetchone()
    conn.close()
    return subscription

def check_premium_status(user_id):
    """Premium statusini tekshirish va agar muddati tugagan bo'lsa, bekor qilish"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Faol obunani tekshirish
    cursor.execute('''
    SELECT subscription_id FROM premium_subscriptions 
    WHERE user_id = ? AND is_active = 1 AND ends_at <= date('now')
    ''', (user_id,))
    
    expired_subscriptions = cursor.fetchall()
    
    # Muddati tugagan obunalarni bekor qilish
    for sub in expired_subscriptions:
        cursor.execute('UPDATE premium_subscriptions SET is_active = 0 WHERE subscription_id = ?', (sub[0],))
    
    # Premium statusini yangilash
    cursor.execute('''
    UPDATE users SET is_premium = 0 
    WHERE user_id = ? AND NOT EXISTS (
        SELECT 1 FROM premium_subscriptions 
        WHERE user_id = ? AND is_active = 1 AND ends_at > date('now')
    )
    ''', (user_id, user_id))
    
    conn.commit()
    conn.close()

def update_tariff(tariff_id, name, price, duration_days, test_limit, word_limit=40):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE tariffs SET name = ?, price = ?, duration_days = ?, test_limit = ?, word_limit = ?
    WHERE tariff_id = ?
    ''', (name, price, duration_days, test_limit, word_limit, tariff_id))
    conn.commit()
    conn.close()

def delete_tariff(tariff_id):
    """Tarifni o'chirish (soft delete - is_active = 0)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE tariffs SET is_active = 0 WHERE tariff_id = ?', (tariff_id,))
    conn.commit()
    conn.close()

def clean_duplicate_tariffs():
    """Takrorlanuvchi tariflarni tozalash"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Barcha takrorlanuvchi tariflarni topish
    cursor.execute('''
    SELECT name, price, duration_days, test_limit, COUNT(*) as count
    FROM tariffs 
    WHERE is_active = 1
    GROUP BY name, price, duration_days, test_limit
    HAVING count > 1
    ''')
    
    duplicates = cursor.fetchall()
    
    for dup in duplicates:
        name, price, duration, test_limit, count = dup
        # Birinchidan tashqari barchasini o'chirish
        cursor.execute('''
        SELECT tariff_id FROM tariffs 
        WHERE name = ? AND price = ? AND duration_days = ? AND test_limit = ? AND is_active = 1
        ORDER BY tariff_id
        ''', (name, price, duration, test_limit))
        
        tariff_ids = cursor.fetchall()
        # Birinchisini qoldirib, qolganlarini o'chirish
        for tariff_id in tariff_ids[1:]:
            cursor.execute('UPDATE tariffs SET is_active = 0 WHERE tariff_id = ?', (tariff_id[0],))
    
    conn.commit()
    conn.close()
    return len(duplicates)

def reset_tariffs_to_default():
    """Standart tariflarni qayta yaratish"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Barcha eski tariflarni o'chirish
    cursor.execute('UPDATE tariffs SET is_active = 0')
    
    # Standart tariflarni qo'shish
    default_tariffs = [
        ("Free", 0, 0, 3, 40),           # ID: 1
        ("Basic", 19000, 30, 7, 40),      # ID: 2  
        ("Standart", 32000, 30, 14, 60),  # ID: 3
        ("Premium", 49000, 30, 30, 100),  # ID: 4
        ("Haftalik", 15000, 7, 50, 80),   # ID: 5
        ("Oylik", 45000, 30, 200, 150),   # ID: 6
        ("Yillik", 300000, 365, 1000, 500) # ID: 7
    ]
    
    for name, price, days, tests, words in default_tariffs:
        cursor.execute('''
        INSERT INTO tariffs (name, price, duration_days, test_limit, word_limit, is_active)
        VALUES (?, ?, ?, ?, ?, 1)
        ''', (name, price, days, tests, words))
    
    conn.commit()
    conn.close()

def assign_student_to_teacher(teacher_id, student_id):
    """O'quvchini o'qituvchiga biriktirish - TO'G'RI VERSIYA"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # 1. O'ziga o'zini biriktirishni oldini olish
        if teacher_id == student_id:
            print(f"❌ O'qituvchi {teacher_id} o'ziga o'zini biriktira olmaydi")
            return False
        
        # 2. Avval biriktirilganligini tekshirish
        cursor.execute('SELECT 1 FROM student_teacher WHERE teacher_id = ? AND student_id = ?', 
                      (teacher_id, student_id))
        if cursor.fetchone():
            print(f"❌ O'quvchi {student_id} allaqachon {teacher_id} ga biriktirilgan")
            return False
        
        # 3. O'qituvchi jadvalida mavjudligini tekshirish
        cursor.execute('SELECT 1 FROM teachers WHERE teacher_id = ?', (teacher_id,))
        if not cursor.fetchone():
            # Agar teachers jadvalida yo'q bo'lsa, qo'shamiz
            cursor.execute('INSERT OR IGNORE INTO teachers (teacher_id) VALUES (?)', (teacher_id,))
            print(f"✅ O'qituvchi {teacher_id} teachers jadvaliga qo'shildi")
        
        # 4. TO'G'RI TARTIBDA INSERT QILISH: (student_id, teacher_id)
        cursor.execute('INSERT INTO student_teacher (student_id, teacher_id) VALUES (?, ?)', 
                      (student_id, teacher_id))
        
        conn.commit()
        print(f"✅ O'quvchi {student_id} o'qituvchi {teacher_id} ga muvaffaqiyatli biriktirildi")
        return True
        
    except Exception as e:
        print(f"❌ assign_student_to_teacher xatosi: {e}")
        return False
    finally:
        conn.close()

def remove_student_from_teacher(teacher_id, student_id):
    """O'quvchini o'qituvchidan olib tashlash"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM student_teacher WHERE teacher_id = ? AND student_id = ?', (teacher_id, student_id))
    conn.commit()
    conn.close()

def get_all_users_for_teacher():
    """O'qituvchilar uchun barcha foydalanuvchilar ro'yxati"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id, full_name, username FROM users ORDER BY full_name')
    users = cursor.fetchall()
    conn.close()
    return users

def search_user_by_username(username):
    """Username bo'yicha foydalanuvchi qidirish"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id, full_name, username FROM users WHERE username LIKE ? ORDER BY full_name', (f'%{username}%',))
    users = cursor.fetchall()
    conn.close()
    return users
