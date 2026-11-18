import requests
import random
import time

BASE_URL = "http://localhost:8000"

NAMES = [
    "Sardor Rahimov", "Madina Karimova", "Jasur Boboyev", 
    "Nilufar Azimova", "Ulug'bek Yusupov", "Zilola Umarova"
]

COURSES = [
    "Kompyuter savodxonligi", "IT Foundation", "Frontend dasturlash", 
    "Backend dasturlash", "English for IT", "Kiberxavfsizlik", 
    "Robototexnika", "Prompt Engineering (AI bilan ishlash)"
]

def send_test_lead():
    name = random.choice(NAMES)
    phone = f"+998 90 {random.randint(100, 999)} {random.randint(10, 99)} {random.randint(10, 99)}"
    course = random.choice(COURSES)

    payload = {
        "full_name": name,
        "phone": phone,
        "course": course,
        "source": "Instagram Story Target",
        "ad_name": "Target Noyabr 2026",
        "notes": "Target landing sahifasidan yuborildi",
        "level": "Boshlang'ich",
        "time_pref": "Kechki (18:30 - 21:00)"
    }

    try:
        resp = requests.post(f"{BASE_URL}/api/leads", json=payload, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Muvaffaqiyatli: #{data['lead']['id']} - {name} ({course}) - {phone}")
        else:
            print(f"❌ Xatolik ({resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"⚠️ Serverga ulanib bo'lmadi: {e}. 'run.bat' orqali serverni ishga tushiring!")

if __name__ == "__main__":
    print("🚀 Joylinks CRM ga test lid yuborilmoqda...")
    send_test_lead()
