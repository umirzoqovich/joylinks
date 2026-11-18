import logging
from typing import Dict, Any, Optional
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.session.aiohttp import AiohttpSession
from config import settings
import database

logger = logging.getLogger("joylink.bot")

STATUS_NAMES = {
    "NEW": "🟢 Yangi lid",
    "CONTACTED": "🟡 Bog'lanildi",
    "CONFIRMED": "🔵 Tasdiqlandi",
    "TRIAL_SCHEDULED": "🟣 Sinov darsida",
    "PAID": "✅ To'lov qildi",
    "CANCELLED": "❌ Rad etdi"
}

STATUS_ICONS = {
    "NEW": "🟢",
    "CONTACTED": "🟡",
    "CONFIRMED": "🔵",
    "TRIAL_SCHEDULED": "🟣",
    "PAID": "✅",
    "CANCELLED": "❌"
}

# Bot instance
bot: Optional[Bot] = None
dp: Optional[Dispatcher] = None
# Callback hook to notify FastAPI SSE when status changed from Telegram
on_status_change_hook = None

def init_bot(token: Optional[str] = None, proxy: Optional[str] = None):
    global bot, dp
    t = (token or settings.BOT_TOKEN or "").strip()
    p = proxy or settings.TELEGRAM_PROXY
    if t:
        try:
            session = AiohttpSession(proxy=p) if p else None
            bot = Bot(token=t, session=session)
            dp = Dispatcher()
            register_handlers(dp)
            logger.info("Telegram Bot muvaffaqiyatli ishga tushirildi.")
        except Exception as e:
            logger.error(f"Bot init xatosi: {e}")
            bot = None
            dp = None
    else:
        bot = None
        dp = None

def get_status_label(status: str) -> str:
    return STATUS_NAMES.get(status, status)

def format_lead_message(lead: Dict[str, Any]) -> str:
    reapply_badge = "\n🚨 <b>DIQQAT! QAYTA MUROJAAT (HOT LEAD)!</b>\n" if lead.get("is_reapplied") else ""

    text = (
        f"🚀 <b>YANGI TARGET LIDI! (#{lead['id']})</b>\n"
        f"🏫 <b>Markaz:</b> {settings.CENTER_NAME}\n"
        f"{reapply_badge}"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>F.I.SH:</b> {lead['full_name']}\n"
        f"📞 <b>Tel:</b> <code>{lead['phone']}</code>\n"
        f"🎯 <b>Kurs:</b> {lead.get('course') or 'Umumiy'}\n"
    )
    if lead.get("notes"):
        text += f"📋 <b>Ma'lumot:</b> {lead['notes']}\n"
    if lead.get("ad_name"):
        text += f"📣 <b>Target:</b> {lead['ad_name']}\n"
        
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    text += f"📊 <b>Status:</b> {get_status_label(lead['status'])}\n"
    if lead.get("assigned_to"):
        text += f"👨‍💼 <b>Mas'ul:</b> {lead['assigned_to']}\n"
    if lead.get("trial_date"):
        text += f"📅 <b>Sinov darsi:</b> {lead['trial_date']}\n"
    if lead.get("cancel_reason"):
        text += f"❌ <b>Rad sababi:</b> {lead['cancel_reason']}\n"
    text += f"⏰ <b>Kelgan vaqti:</b> {lead.get('created_at', '')}\n"
    return text

def build_lead_keyboard(lead_id: int, current_status: str) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="📞 Bog'lanildi", callback_data=f"st:CONTACTED:{lead_id}"),
            InlineKeyboardButton(text="🔵 Tasdiqlandi", callback_data=f"st:CONFIRMED:{lead_id}")
        ],
        [
            InlineKeyboardButton(text="🟣 Sinov darsi", callback_data=f"st:TRIAL_SCHEDULED:{lead_id}"),
            InlineKeyboardButton(text="✅ To'lov qildi", callback_data=f"st:PAID:{lead_id}")
        ],
        [
            InlineKeyboardButton(text="❌ Rad etdi", callback_data=f"st:CANCELLED:{lead_id}")
        ]
    ]
    if current_status != "NEW":
        buttons.append([InlineKeyboardButton(text="🔄 Yangi holatga qaytarish", callback_data=f"st:NEW:{lead_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def check_and_update_migration(e: Exception) -> Optional[str]:
    """If Telegram group was upgraded to supergroup, automatically updates settings and SQLite DB."""
    import re
    msg = str(e)
    match = re.search(r"migrated to a (?:supergroup|chat) with id\s+(-?\d+)", msg)
    if match:
        new_id = match.group(1).strip()
        logger.info(f"Telegram guruhi yangi superguruhga o'tdi: {new_id}. Sozlamalar avtomatik yangilanmoqda...")
        settings.TELEGRAM_GROUP_ID = new_id
        try:
            database.set_setting("TELEGRAM_GROUP_ID", new_id)
        except Exception:
            pass
        return new_id
    return None

async def send_lead_notification(lead: Dict[str, Any]) -> Optional[int]:
    """Sends new lead notification to the configured Telegram Group."""
    group_id = (database.get_setting("TELEGRAM_GROUP_ID") or settings.TELEGRAM_GROUP_ID or "").strip()
    if not bot or not group_id:
        logger.warning("Telegram Bot yoki TELEGRAM_GROUP_ID sozlanmagan. Xabar yuborilmadi.")
        return None

    text = format_lead_message(lead)
    keyboard = build_lead_keyboard(lead["id"], lead["status"])

    try:
        msg = await bot.send_message(
            chat_id=group_id,
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        database.update_lead_telegram_msg_id(lead["id"], msg.message_id)
        return msg.message_id
    except Exception as e:
        new_id = check_and_update_migration(e)
        if new_id:
            try:
                msg = await bot.send_message(
                    chat_id=new_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
                database.update_lead_telegram_msg_id(lead["id"], msg.message_id)
                logger.info(f"Xabar yangi superguruhga ({new_id}) muvaffaqiyatli yetkazildi!")
                return msg.message_id
            except Exception as e2:
                logger.error(f"Yangi superguruhga yuborishda xatolik: {e2}")
        logger.error(f"Telegramga xabar yuborishda xatolik: {e}")
        return None

async def notify_status_update(lead: Dict[str, Any], new_status: str, admin_name: str) -> None:
    """Sends status change notification to the Telegram group."""
    group_id = (database.get_setting("TELEGRAM_GROUP_ID") or settings.TELEGRAM_GROUP_ID or "").strip()
    if not bot or not group_id:
        return
    status_label = get_status_label(new_status)
    text = (
        f"🔔 <b>STATUS YANGILANDI! (#{lead['id']})</b>\n"
        f"👤 <b>O'quvchi:</b> {lead['full_name']}\n"
        f"📞 <b>Tel:</b> <code>{lead['phone']}</code>\n"
        f"📊 <b>Yangi status:</b> {status_label}\n"
        f"👨‍💼 <b>O'zgartirdi:</b> {admin_name}"
    )
    if lead.get("trial_date") and new_status == "TRIAL_SCHEDULED":
        text += f"\n📅 <b>Sinov darsi:</b> {lead['trial_date']}"
    if lead.get("cancel_reason") and new_status == "CANCELLED":
        text += f"\n❌ <b>Sabab:</b> {lead['cancel_reason']}"

    try:
        await bot.send_message(chat_id=group_id, text=text, parse_mode="HTML")
    except Exception as e:
        new_id = check_and_update_migration(e)
        if new_id:
            try:
                await bot.send_message(chat_id=new_id, text=text, parse_mode="HTML")
            except Exception:
                pass
        else:
            logger.warning(f"Telegramga status bildirishnomasi yuborishda xatolik: {e}")

def register_handlers(target_dp: Dispatcher):
    @target_dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        user_name = message.from_user.first_name if message.from_user else "Foydalanuvchi"
        await message.answer(
            f"👋 <b>Assalomu alaykum, {user_name}!</b>\n\n"
            f"Bu <b>{settings.CENTER_NAME} Target CRM</b> bildirishnoma boti.\n\n"
            f"🔹 <b>Guruhga ulash uchun:</b>\n"
            f"1. Botni Telegram guruhingizga qo'shing va unga admin huquqini bering.\n"
            f"2. O'sha guruhga <code>/id</code> deb yozing.\n"
            f"3. Bot guruh ID sini chiqarib beradi (masalan: <code>-1001234567890</code>).\n"
            f"4. Chiqqan Guruh ID sini CRM panelidagi <b>'Sozlamalar'</b> bo'limiga kiriting.\n\n"
            f"📊 <b>Buyruqlar:</b>\n"
            f"/id — Chat yoki guruh ID sini bilish\n"
            f"/stats — Bugungi va umumiy lidlar statistikasi",
            parse_mode="HTML"
        )

    @target_dp.message(Command("id"))
    async def cmd_id(message: types.Message):
        chat = message.chat
        chat_type = "Guruh" if chat.type in ["group", "supergroup"] else "Shaxsiy chat"
        await message.answer(
            f"🆔 <b>{chat_type} ID si:</b>\n"
            f"<code>{chat.id}</code>\n\n"
            f"<i>Ushbu ID raqamni nusxalab oling va Joylinks CRM ning 'Sozlamalar' bo'limidagi <b>Telegram Guruh ID</b> maydoniga qo'ying.</i>",
            parse_mode="HTML"
        )

    @target_dp.message(Command("stats"))
    async def cmd_stats(message: types.Message):
        stats = database.get_lead_stats()
        text = (
            f"📊 <b>{settings.CENTER_NAME} CRM — Bugungi Statistika:</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🌟 <b>Bugungi yangi lidlar:</b> {stats['today']} ta\n"
            f"📁 <b>Jami lidlar soni:</b> {stats['total']} ta\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🟢 <b>Yangi:</b> {stats['new']}\n"
            f"🟡 <b>Bog'lanildi:</b> {stats['contacted']}\n"
            f"🔵 <b>Tasdiqlandi:</b> {stats['confirmed']}\n"
            f"🟣 <b>Sinov darsida:</b> {stats['trial']}\n"
            f"✅ <b>To'lov qildi:</b> {stats['paid']}\n"
            f"❌ <b>Rad etdi:</b> {stats['cancelled']}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 <b>Konversiya:</b> {stats['conversion']}%\n"
        )
        await message.answer(text, parse_mode="HTML")

    @target_dp.callback_query(F.data.startswith("st:"))
    async def process_status_callback(call: types.CallbackQuery):
        parts = call.data.split(":")
        if len(parts) != 3:
            await call.answer("Noto'g'ri so'rov!", show_alert=True)
            return

        _, new_status, lead_id_str = parts
        try:
            lead_id = int(lead_id_str)
        except ValueError:
            await call.answer("Lid ID noto'g'ri!", show_alert=True)
            return

        operator_name = call.from_user.full_name or f"@{call.from_user.username}" if call.from_user else "Telegram Operator"
        updated = database.update_lead_status(
            lead_id=lead_id,
            new_status=new_status,
            changed_by=f"Telegram ({operator_name})"
        )

        if not updated:
            await call.answer("Lid topilmadi!", show_alert=True)
            return

        new_text = format_lead_message(updated)
        new_keyboard = build_lead_keyboard(lead_id, new_status)

        try:
            await call.message.edit_text(
                text=new_text,
                reply_markup=new_keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Telegram xabarini tahrirlashda: {e}")

        status_lbl = get_status_label(new_status)
        await call.answer(f"Status yangilandi: {status_lbl}")

        # Broadcast SSE to web CRM
        if on_status_change_hook:
            try:
                import asyncio
                if asyncio.iscoroutinefunction(on_status_change_hook):
                    asyncio.create_task(on_status_change_hook("lead_updated", updated))
                else:
                    on_status_change_hook("lead_updated", updated)
            except Exception as e:
                logger.error(f"SSE hook error: {e}")
