import os
import asyncio
import io
import json
import logging
from contextlib import asynccontextmanager
from typing import Optional, Set
from datetime import datetime

from fastapi import FastAPI, Request, Response, Query, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from config import settings
import database
import models
import bot
import meta_service

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("joylink.crm")

# SSE Subscribers
subscribers: Set[asyncio.Queue] = set()

def enrich_lead(lead: dict) -> dict:
    item = dict(lead)
    notes_str = item.get("notes") or ""

    daraja = ""
    if "Daraja:" in notes_str:
        try:
            daraja = notes_str.split("Daraja:")[1].split("|")[0].strip()
        except Exception:
            pass

    vaqt = ""
    if "Qulay vaqt:" in notes_str:
        try:
            vaqt = notes_str.split("Qulay vaqt:")[1].split("|")[0].split("\n")[0].strip()
        except Exception:
            pass

    filial = ""
    if "Filial:" in notes_str:
        try:
            filial = notes_str.split("Filial:")[1].split("|")[0].split("\n")[0].strip()
        except Exception:
            pass

    clean_notes = notes_str
    for fragment in ["Format: Markazda (Offline)", "Format: Markazda", "Format: Online"]:
        clean_notes = clean_notes.replace(fragment, "")
    clean_notes = clean_notes.replace("||", "|").strip(" |").strip()

    item["parsed_daraja"] = daraja
    item["parsed_vaqt"] = vaqt
    item["parsed_filial"] = filial
    item["clean_notes"] = clean_notes
    return item

async def broadcast_event(event_type: str, data: dict):
    msg = json.dumps({"type": event_type, "data": data})
    for queue in list(subscribers):
        try:
            queue.put_nowait(msg)
        except Exception:
            subscribers.discard(queue)

# Background polling task for Telegram bot
polling_task: Optional[asyncio.Task] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global polling_task
    # 1. Initialize SQLite Database
    database.init_db()
    logger.info("Database muvaffaqiyatli ishga tushdi.")

    # 2. Hook bot status change to SSE broadcast
    bot.on_status_change_hook = broadcast_event

    # 3. Load persistent settings from SQLite (takes precedence over .env file)
    db_token = database.get_setting("BOT_TOKEN")
    if db_token:
        settings.BOT_TOKEN = db_token
    elif settings.BOT_TOKEN:
        database.set_setting("BOT_TOKEN", settings.BOT_TOKEN)

    db_group = database.get_setting("TELEGRAM_GROUP_ID")
    if db_group:
        settings.TELEGRAM_GROUP_ID = db_group
    elif settings.TELEGRAM_GROUP_ID:
        database.set_setting("TELEGRAM_GROUP_ID", settings.TELEGRAM_GROUP_ID)

    db_channel = database.get_setting("TELEGRAM_CHANNEL_URL")
    if db_channel:
        settings.TELEGRAM_CHANNEL_URL = db_channel
    elif settings.TELEGRAM_CHANNEL_URL:
        database.set_setting("TELEGRAM_CHANNEL_URL", settings.TELEGRAM_CHANNEL_URL)

    db_pixel = database.get_setting("META_PIXEL_ID")
    if db_pixel:
        settings.META_PIXEL_ID = db_pixel

    db_center = database.get_setting("CENTER_NAME")
    if db_center:
        settings.CENTER_NAME = db_center

    # 4. Initialize bot if token is present
    if settings.BOT_TOKEN:
        bot.init_bot(token=settings.BOT_TOKEN)
        if bot.bot and bot.dp:
            logger.info("Telegram Bot polling ishga tushirilmoqda...")
            try:
                await bot.bot.delete_webhook(drop_pending_updates=True)
                polling_task = asyncio.create_task(bot.dp.start_polling(bot.bot))
                logger.info("Telegram Bot polling faol holatda!")
            except Exception as e:
                logger.error(f"Telegram Bot pollingni boshlashda xatolik: {e}")
    else:
        logger.warning("BOT_TOKEN ko'rsatilmagan. Bot offline rejimda. CRM Sozlamalaridan kiriting.")

    yield

    # Teardown
    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
    if bot.bot:
        await bot.bot.session.close()
    logger.info("Tizim to'xtatildi.")

app = FastAPI(
    title="Joylinks Target CRM",
    description="Facebook va Instagram reklamalaridan keluvchi lidlarni qabul qilish va Telegram guruhga yuborish tizimi",
    version="2.0.0",
    lifespan=lifespan
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# ==========================================
# WEB CRM DASHBOARD & PUBLIC FORM
# ==========================================

@app.get("/form", response_class=HTMLResponse)
async def public_lead_form(
    request: Request,
    course: Optional[str] = None,
    ref: Optional[str] = "Instagram Target",
    ad: Optional[str] = None
):
    """
    Instagram / Facebook Target reklamalariga qo'yiladigan landing forma.
    Misol: /form?course=Ingliz+tili&ref=Instagram_Story
    """
    campaign_ref = ad or ref or "Instagram Target"
    pixel_id = database.get_setting("META_PIXEL_ID", settings.META_PIXEL_ID or "")
    channel_url = database.get_setting("TELEGRAM_CHANNEL_URL", settings.TELEGRAM_CHANNEL_URL or "https://t.me")
    center_name = database.get_setting("CENTER_NAME", settings.CENTER_NAME or "Joylinks")
    
    return templates.TemplateResponse(
        request=request,
        name="lead_form.html",
        context={
            "course": course,
            "ref": campaign_ref,
            "pixel_id": pixel_id,
            "channel_url": channel_url,
            "center_name": center_name
        }
    )

@app.get("/", response_class=HTMLResponse)
async def web_dashboard(request: Request, search: Optional[str] = None):
    stats = database.get_lead_stats()
    raw_leads = database.get_all_leads(search=search, limit=500)
    enriched_leads = [enrich_lead(lead) for lead in raw_leads]

    leads_by_status = {
        "NEW": [],
        "CONTACTED": [],
        "CONFIRMED": [],
        "TRIAL_SCHEDULED": [],
        "PAID": [],
        "CANCELLED": []
    }
    for lead in enriched_leads:
        st = lead["status"]
        if st in leads_by_status:
            leads_by_status[st].append(lead)
        else:
            leads_by_status["NEW"].append(lead)

    configured_token = database.get_setting("BOT_TOKEN", settings.BOT_TOKEN or "")
    configured_group = database.get_setting("TELEGRAM_GROUP_ID", settings.TELEGRAM_GROUP_ID or "")
    bot_configured = bool(configured_token and configured_group)

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "stats": stats,
            "leads_by_status": leads_by_status,
            "all_leads": enriched_leads,
            "search": search,
            "bot_configured": bot_configured,
            "center_name": database.get_setting("CENTER_NAME", settings.CENTER_NAME or "Joylinks")
        }
    )

# ==========================================
# REST API ENDPOINTS
# ==========================================

@app.post("/api/leads")
async def create_lead_api(payload: models.LeadCreate, background_tasks: BackgroundTasks):
    combined_notes = payload.notes or ""
    extra_details = []
    if payload.level:
        extra_details.append(f"Daraja: {payload.level}")
    if payload.time_pref:
        extra_details.append(f"Qulay vaqt: {payload.time_pref}")
    if payload.branch:
        extra_details.append(f"Filial: {payload.branch}")
    
    if extra_details:
        prefix = " | ".join(extra_details)
        combined_notes = f"{prefix}\n{combined_notes}".strip()

    lead = database.create_lead(
        full_name=payload.full_name,
        phone=payload.phone,
        course=payload.course,
        source=payload.source,
        ad_name=payload.ad_name,
        notes=combined_notes
    )

    enriched = enrich_lead(lead)

    # 1. Send Telegram Notification to the configured Group
    async def send_tg_task():
        try:
            await bot.send_lead_notification(lead)
        except Exception as e:
            logger.error(f"Telegram notification error: {e}")

    background_tasks.add_task(send_tg_task)

    # 2. Push real-time event to CRM dashboard
    await broadcast_event("lead_created", enriched)

    return {"status": "ok", "lead": enriched}

@app.get("/api/leads")
async def get_leads_api(status: Optional[str] = None, search: Optional[str] = None):
    leads = database.get_all_leads(status=status, search=search)
    return [enrich_lead(lead) for lead in leads]

@app.get("/api/leads/{lead_id}")
async def get_lead_detail_api(lead_id: int):
    lead = database.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lid topilmadi")
    timeline = database.get_lead_timeline(lead_id)
    enriched = enrich_lead(lead)
    enriched["timeline"] = timeline
    return enriched

@app.patch("/api/leads/{lead_id}/status")
async def update_status_api(lead_id: int, payload: models.StatusUpdate, background_tasks: BackgroundTasks):
    updated = database.update_lead_status(
        lead_id=lead_id,
        new_status=payload.status,
        changed_by=payload.assigned_to or "Web CRM",
        note=payload.note,
        trial_date=payload.trial_date,
        cancel_reason=payload.cancel_reason
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Lid topilmadi")

    enriched = enrich_lead(updated)

    # Notify Telegram group if status changed
    async def notify_tg_task():
        try:
            await bot.notify_status_update(updated, payload.status, payload.assigned_to or "Web CRM")
        except Exception as e:
            logger.error(f"Telegram status notify error: {e}")

    background_tasks.add_task(notify_tg_task)
    await broadcast_event("lead_updated", enriched)

    return {"status": "ok", "lead": enriched}

@app.post("/api/leads/{lead_id}/notes")
async def add_note_api(lead_id: int, payload: models.NoteCreate):
    updated = database.add_lead_note(
        lead_id=lead_id,
        note=payload.note,
        author=payload.author or "Admin"
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Lid topilmadi")

    enriched = enrich_lead(updated)
    await broadcast_event("lead_updated", enriched)
    return {"status": "ok", "lead": enriched}

@app.delete("/api/leads/{lead_id}")
async def delete_lead_api(lead_id: int):
    success = database.delete_lead(lead_id)
    if not success:
        raise HTTPException(status_code=404, detail="Lid topilmadi")
    await broadcast_event("lead_deleted", {"id": lead_id})
    return {"status": "ok", "message": "Lid o'chirildi"}

@app.get("/api/stats")
async def get_stats_api():
    return database.get_lead_stats()

# ==========================================
# SETTINGS MANAGEMENT (BOT TOKEN & GROUP ID)
# ==========================================

@app.get("/api/settings")
async def get_settings_api():
    return {
        "bot_token": database.get_setting("BOT_TOKEN", settings.BOT_TOKEN or ""),
        "telegram_group_id": database.get_setting("TELEGRAM_GROUP_ID", settings.TELEGRAM_GROUP_ID or ""),
        "telegram_channel_url": database.get_setting("TELEGRAM_CHANNEL_URL", settings.TELEGRAM_CHANNEL_URL or ""),
        "meta_pixel_id": database.get_setting("META_PIXEL_ID", settings.META_PIXEL_ID or ""),
        "center_name": database.get_setting("CENTER_NAME", settings.CENTER_NAME or "Joylinks")
    }

@app.post("/api/settings")
async def save_settings_api(payload: models.SettingsPayload):
    global polling_task
    new_token = (payload.bot_token or "").strip()
    new_group = (payload.telegram_group_id or "").strip()
    new_channel = (payload.telegram_channel_url or "").strip()
    new_pixel = (payload.meta_pixel_id or "").strip()
    new_center = (payload.center_name or "").strip() or "Joylinks"

    # 1. Persist directly to SQLite database
    database.set_setting("BOT_TOKEN", new_token)
    database.set_setting("TELEGRAM_GROUP_ID", new_group)
    database.set_setting("TELEGRAM_CHANNEL_URL", new_channel)
    database.set_setting("META_PIXEL_ID", new_pixel)
    database.set_setting("CENTER_NAME", new_center)

    # 2. Update runtime memory settings
    settings.BOT_TOKEN = new_token
    settings.TELEGRAM_GROUP_ID = new_group
    settings.TELEGRAM_CHANNEL_URL = new_channel
    settings.META_PIXEL_ID = new_pixel
    settings.CENTER_NAME = new_center

    # 3. Update .env file
    try:
        env_dict = {}
        if os.path.exists(".env"):
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    line_s = line.strip()
                    if line_s and not line_s.startswith("#") and "=" in line_s:
                        k, v = line_s.split("=", 1)
                        env_dict[k.strip()] = v.strip()

        env_dict["BOT_TOKEN"] = new_token
        env_dict["TELEGRAM_GROUP_ID"] = new_group
        if new_channel:
            env_dict["TELEGRAM_CHANNEL_URL"] = new_channel
        if new_pixel:
            env_dict["META_PIXEL_ID"] = new_pixel
        if new_center:
            env_dict["CENTER_NAME"] = new_center

        with open(".env", "w", encoding="utf-8") as f:
            f.write("# Joylinks Target CRM Configuration\n")
            for k, v in env_dict.items():
                f.write(f"{k}={v}\n")
        logger.info(".env fayli muvaffaqiyatli yangilandi.")
    except Exception as e:
        logger.warning(f".env faylini yozishda ogohlantirish: {e}")

    # 4. Gracefully restart Telegram Bot instance with new token
    try:
        if polling_task and not polling_task.done():
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass
            polling_task = None

        if bot.bot:
            try:
                await bot.bot.session.close()
            except Exception:
                pass

        if new_token:
            bot.init_bot(token=new_token)
            if bot.bot and bot.dp:
                await bot.bot.delete_webhook(drop_pending_updates=True)
                polling_task = asyncio.create_task(bot.dp.start_polling(bot.bot))
                logger.info("Telegram Bot yangi token bilan muvaffaqiyatli ishga tushdi.")
    except Exception as be:
        logger.error(f"Telegram Botni qayta ishga tushirishda xatolik: {be}")

    return {"status": "ok", "message": "Sozlamalar saqlandi va Telegram Bot yangilandi!"}

@app.post("/api/settings/test")
async def test_telegram_connection_api():
    token = database.get_setting("BOT_TOKEN", settings.BOT_TOKEN or "").strip()
    group_id = database.get_setting("TELEGRAM_GROUP_ID", settings.TELEGRAM_GROUP_ID or "").strip()
    center_name = database.get_setting("CENTER_NAME", settings.CENTER_NAME or "Joylinks")

    if not token:
        raise HTTPException(status_code=400, detail="Telegram Bot Token kiritilmagan! Avval bot tokenini kiriting.")
    if not group_id:
        raise HTTPException(status_code=400, detail="Telegram Guruh ID kiritilmagan! Avval guruh ID sini kiriting.")

    if not bot.bot or bot.bot.token != token:
        bot.init_bot(token=token)

    if not bot.bot:
        raise HTTPException(status_code=400, detail="Telegram Bot obyektini ishga tushirib bo'lmadi. Token to'g'riligini tekshiring.")

    try:
        me = await bot.bot.get_me()
        text = (
            f"✅ <b>Telegram aloqasi muvaffaqiyatli tekshirildi!</b>\n\n"
            f"🤖 <b>Bot:</b> @{me.username} ({me.first_name})\n"
            f"🏫 <b>Markaz:</b> {center_name}\n"
            f"📊 <b>Tizim:</b> Target CRM tayyor! Yangi kelgan har bir lid ushbu guruhga tushadi."
        )
        try:
            msg = await bot.bot.send_message(
                chat_id=group_id,
                text=text,
                parse_mode="HTML"
            )
            return {"status": "ok", "bot_username": me.username, "message_id": msg.message_id}
        except Exception as se:
            new_id = bot.check_and_update_migration(se)
            if new_id:
                msg = await bot.bot.send_message(
                    chat_id=new_id,
                    text=(
                        f"{text}\n\n"
                        f"🔄 <i>Guruh superguruhga aylanganligi aniqlandi va Chat ID avtomatik yangilandi: {new_id}</i>"
                    ),
                    parse_mode="HTML"
                )
                return {
                    "status": "ok",
                    "bot_username": me.username,
                    "message_id": msg.message_id,
                    "migrated_to": new_id
                }
            raise se
    except Exception as e:
        logger.error(f"Telegram aloqani tekshirishda xatolik: {e}")
        raise HTTPException(status_code=400, detail=f"Telegram xatoligi: {str(e)}")

# ==========================================
# EXPORT TO EXCEL
# ==========================================

@app.get("/export/excel")
async def export_leads_excel(status: Optional[str] = None):
    leads = database.get_all_leads(status=status, limit=5000)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Joylinks Lidlar"

    # Header styling
    header_fill = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )

    headers = [
        "ID", "F.I.SH", "Telefon", "Kurs", "Target Reklama", 
        "Status", "Sinov Darsi", "Mas'ul", "Izohlar / Ma'lumot", "Kelgan Vaqti"
    ]
    ws.append(headers)

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    status_labels = {
        "NEW": "Yangi",
        "CONTACTED": "Bog'lanildi",
        "CONFIRMED": "Tasdiqlandi",
        "TRIAL_SCHEDULED": "Sinov darsida",
        "PAID": "To'lov qildi",
        "CANCELLED": "Rad etdi"
    }

    for row_idx, lead in enumerate(leads, start=2):
        st_clean = status_labels.get(lead["status"], lead["status"])
        row_data = [
            lead["id"],
            lead["full_name"],
            lead["phone"],
            lead.get("course") or "",
            lead.get("ad_name") or "",
            st_clean,
            lead.get("trial_date") or "",
            lead.get("assigned_to") or "",
            lead.get("notes") or "",
            lead.get("created_at") or ""
        ]
        ws.append(row_data)
        for col_idx in range(1, len(row_data) + 1):
            c = ws.cell(row=row_idx, column=col_idx)
            c.border = thin_border
            if col_idx in [1, 3, 6, 7, 8, 10]:
                c.alignment = Alignment(horizontal="center", vertical="center")
            else:
                c.alignment = Alignment(horizontal="left", vertical="center")

    # Auto column widths
    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)

    filename = f"Joylinks_Lidlar_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ==========================================
# SSE REALTIME EVENTS
# ==========================================

@app.get("/api/events")
async def sse_events(request: Request):
    async def event_generator():
        queue: asyncio.Queue = asyncio.Queue()
        subscribers.add(queue)
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            subscribers.discard(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ==========================================
# FACEBOOK & INSTAGRAM WEBHOOKS
# ==========================================

@app.get("/webhook/meta")
async def meta_webhook_verification(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == settings.META_VERIFY_TOKEN:
            logger.info("Meta Webhook muvaffaqiyatli tasdiqlandi!")
            return Response(content=challenge, media_type="text/plain")
        else:
            raise HTTPException(status_code=403, detail="Verification token mismatch")
    raise HTTPException(status_code=400, detail="Missing parameters")

@app.post("/webhook/meta")
async def meta_webhook_receive(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()
        logger.info(f"Meta webhook keldi: {body}")

        if body.get("object") in ["page", "instagram"]:
            for entry in body.get("entry", []):
                for change in entry.get("changes", []):
                    if change.get("field") == "leadgen":
                        value = change.get("value", {})
                        leadgen_id = str(value.get("leadgen_id", ""))
                        ad_id = str(value.get("ad_id", ""))
                        form_id = str(value.get("form_id", ""))

                        async def process_leadgen(lid: str, ad: str, fid: str):
                            details = await meta_service.fetch_leadgen_details(lid)
                            if details and details.get("phone"):
                                full_name = details.get("full_name") or "Meta O'quvchi"
                                phone = details.get("phone")
                                course = details.get("course") or "Joylinks Target"
                                ad_name = details.get("ad_name") or f"Meta Ad #{ad}"
                                notes = f"Form ID: {fid} | Leadgen ID: {lid}"

                                new_lead = database.create_lead(
                                    full_name=full_name,
                                    phone=phone,
                                    course=course,
                                    source="Meta Lead Ads",
                                    ad_name=ad_name,
                                    notes=notes
                                )
                                await bot.send_lead_notification(new_lead)
                                await broadcast_event("lead_created", enrich_lead(new_lead))

                        background_tasks.add_task(process_leadgen, leadgen_id, ad_id, form_id)

            return {"status": "EVENT_RECEIVED"}
        return {"status": "IGNORED"}
    except Exception as e:
        logger.error(f"Webhook qabul qilishda xatolik: {e}")
        return {"status": "error", "message": str(e)}
