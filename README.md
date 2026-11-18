# 🎓 Joylinks Target CRM — O'quv Markaz Lid Boshqaruv Tizimi

Facebook, Instagram va Meta Lead Ads target reklamalaridan keladigan lidlarni qabul qilish, **Telegram guruhga bir zumda xabar yuborish** va **Web CRM (Kanban doska)** orqali boshqarish uchun maxsus tayyorlangan tizim.

---

## 🌟 Asosiy Imkoniyatlar

1. **Telegram Guruhga Bir Zumda Bildirishnoma:**
   - Saytdan yoki Instagram reklamadan yangi o'quvchi ariza qoldirishi bilan o'quv markaz adminlari/menejerlari guruhiga batafsil chiroyli xabar keladi.
   - Xabar ostidagi tugmalar orqali Telegramning o'zida bir bosishda statusni o'zgartirish mumkin:
     - 📞 *Bog'lanildi*
     - 🔵 *Tasdiqlandi*
     - 🟣 *Sinov darsida*
     - ✅ *To'lov qildi*
     - ❌ *Rad etdi*
   - Xabar real vaqtda tahrirlanib, qaysi menejer qachon statusni o'zgartirgani ko'rinadi.

2. **Bot Token va Guruh ID sini to'g'ridan-to'g'ri CRM dan sozlash:**
   - Endi kod yoki `.env` faylini ochib yurish shart emas!
   - Web CRM boshqaruv panelidagi **"⚙️ Sozlamalar"** tugmasini bosib:
     - Telegram Bot Token
     - Telegram Guruh ID
     - Telegram Kanal Havolasi
     - Meta Pixel ID
   - **"Aloqani tekshirish"** tugmasini bosishingiz bilan bot guruhingizga test xabar yuborib, hammasi to'g'ri sozlanganini tekshiradi!
   - Saqlash tugmasini bosganda bot avtomatik tarzda qayta yuklanadi.

3. **Web CRM Dashboard (Kanban doska va Jadval):**
   - Brauzer orqali ochiladigan zamonaviy interfeys: `http://localhost:8000`
   - 6 bosqichli Kanban voronkasi (Yangi ➡️ Bog'lanildi ➡️ Tasdiqlandi ➡️ Sinov darsi ➡️ To'lov ➡️ Rad etdi).
   - Real-time Jonli yangilanish (SSE): yangi lid tushishi yoki status o'zgarishi bilan sahifa yangilanmasdan turib kartalar o'zgaradi.
   - Bir bosishda qo'ng'iroq qilish (`tel:`) va Telegram profilini ochish.
   - Ism, telefon va kurs bo'yicha tezkor qidiruv.
   - Barcha lidlarni **Excel (.xlsx)** formatida saralangan holda yuklab olish.
   - **"Test Lid"** tugmasi orqali tizimni 1 sekundda sinab ko'rish imkoniyati.

4. **Target Reklama Uchun Landing Forma (`/form`):**
   - Instagram / Facebook reklamalaridagi "Batafsil / Ro'yxatdan o'tish" tugmasiga qo'yiladigan tezyurar mobil sahifa.
   - Kurslar tanlovi (Ingliz tili, IT & Dasturlash, Rus tili, Matematika, Nemis tili, Koreys tili va h.k.).
   - Meta Pixel tracking integratsiyasi (`PageView` va `Lead` hodisalari).
   - Ariza to'ldirilgandan so'ng markazingiz Telegram kanaliga taklif qiluvchi bonus oyna.

5. **Meta / Instagram / Facebook Lead Ads Webhook:**
   - Facebook Forms orqali keluvchi so'rovlar uchun rasmiy webhook (`/webhook/meta`).

---

## 🚀 Ishga Tushirish (Juda Oson)

### 1-qadam. Tizimni ishga tushirish
Windows kompyuteringizda papkadagi **`run.bat`** fayliga 2 marta bosing.
U avtomatik tarzda serverni ishga tushiradi va brauzerda boshqaruv panelini ochadi:
- **Web CRM:** [http://localhost:8000](http://localhost:8000)
- **Target Formasi:** [http://localhost:8000/form](http://localhost:8000/form)
- **API Hujjatlari:** [http://localhost:8000/docs](http://localhost:8000/docs)

*(Yoki terminalda: `python run.py` buyrug'i orqali)*

---

### 2-qadam. Telegram Bot va Guruh ID sini kiritish
1. [http://localhost:8000](http://localhost:8000) ga kiring va tepadagi **"⚙️ Sozlamalar"** tugmasini bosing.
2. **Telegram Bot Token:** Telegramda [@BotFather](https://t.me/BotFather) orqali olgan bot tokeningizni kiriting.
3. **Telegram Guruh ID:**
   > **Guruh ID sini qanday bilish mumkin?**
   > 1. Yaratgan botingizni Telegram guruhingizga admin sifatida qo'shing.
   > 2. Guruhga `/id` deb yozing.
   > 3. Bot guruh ID sini chiqarib beradi (masalan: `-1001234567890`).
   > 4. O'sha ID ni CRM Sozlamalariga nusxalang.
4. **"Aloqani tekshirish"** tugmasini bosing: guruhingizga test xabari boradi.
5. **"Saqlash"** tugmasini bosing — Bo'ldi, bot tayyor!

---

### 3-qadam. Instagram Target Reklamasiga qo'yish (Ochiq Internet Havolasi)
Agar serveringiz kompyuteringizda ishlayotgan bo'lsa va uni Instagram target reklamaga qo'ymoqchi bo'lsangiz:
1. Papkadagi **`public_link.bat`** fayliga bosing.
2. U sizga bir zumda bepul **`https://...`** havola beradi.
3. Ushbu havolaning orqasiga `/form` qo'shib, Instagram reklamangizdagi havola (URL) qismiga joylashtirasiz!
*(Masalan: `https://xxxx.pinggy.link/form?course=Ingliz+tili&ref=Insta_Story`)*

---

## 📁 Loyiha Tuzilishi

```
D:\joylink\
├── config.py             # Loyiha konfiguratsiyasi
├── database.py           # SQLite baza, lidlar va sozlamalar boshqaruvi
├── models.py             # Pydantic ma'lumotlar modellari
├── bot.py                # Telegram bot (aiogram 3.x), guruh bildirishnomalari va tugmalar
├── meta_service.py       # Facebook Graph API Lead Ads xizmati
├── main.py               # FastAPI veb-serveri va API yo'nalishlari
├── run.py                # Ishga tushiruvchi skript
├── run.bat               # Windows uchun 1 bosishda ishga tushirish
├── public_link.bat       # Ochiq https internet havolasini ochish
├── run.sh                # Linux / VPS serverlar uchun
├── Dockerfile            # Docker konteyner fayli
├── docker-compose.yml    # Docker Compose sozlamasi
├── requirements.txt      # Kutubxonalar ro'yxati
├── static/               # SVG logo va statik fayllar
├── templates/            # HTML shablonlar (dashboard, lead_card, lead_form)
└── tests/                # Testlar va sinov skriptlari
```

---

## 🤖 Bot Buyruqlari (Guruhda va Shaxsiy Chatda)

- `/start` — Bot haqida ma'lumot va guruhga ulash yo'riqnomasi.
- `/id` — Joriy guruh yoki chat ID sini ko'rsatish (CRM ga kiritish uchun juda qulay).
- `/stats` — Bugungi va umumiy lidlar soni, to'lovlar va konversiya foizi.
