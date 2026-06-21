import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
 
BOT_TOKEN = os.getenv("BOT_TOKEN", "8923862657:AAHdeOhKabUxww8Yn-x1L3-REJz5yyimdW4")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "1211960244")
 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
# ── STATES ──
MAIN_MENU, CHOOSE_SERVICE, ENTER_NAME, ENTER_PHONE, ENTER_CAR, ENTER_COMMENT, CHOOSE_DATE, CONFIRM, BROADCAST_WAIT = range(9)
 
# ── ПОДПИСЧИКИ (для рассылки) ──
SUBSCRIBERS_FILE = "subscribers.txt"
 
def load_subscribers():
    if not os.path.exists(SUBSCRIBERS_FILE):
        return set()
    with open(SUBSCRIBERS_FILE, "r") as f:
        return set(int(line.strip()) for line in f if line.strip())
 
def save_subscriber(chat_id):
    subs = load_subscribers()
    if chat_id not in subs:
        subs.add(chat_id)
        with open(SUBSCRIBERS_FILE, "a") as f:
            f.write(f"{chat_id}\n")
 
# ── ИСТОРИЯ ЗАПИСЕЙ (личный кабинет) ──
BOOKINGS_FILE = "bookings.txt"
SEP = "|||"
 
def save_booking(chat_id, service, name, phone, car, comment, visit_date):
    ts = __import__("datetime").datetime.now().strftime("%d.%m.%Y %H:%M")
    line = SEP.join([str(chat_id), ts, service, name, phone, car, comment, visit_date])
    with open(BOOKINGS_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
 
def get_bookings_for(chat_id):
    if not os.path.exists(BOOKINGS_FILE):
        return []
    result = []
    with open(BOOKINGS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(SEP)
            if len(parts) == 8 and parts[0] == str(chat_id):
                result.append(parts)
    return result
 
def get_all_bookings():
    if not os.path.exists(BOOKINGS_FILE):
        return []
    result = []
    with open(BOOKINGS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(SEP)
            if len(parts) == 8:
                result.append(parts)
    return result
 
# ── PHOTOS (file_id кешируется после первой отправки) ──
PHOTO_CACHE = {}
 
PHOTO_PATHS = {
    "WELCOME":  "welcome.jpg",
    "SERVICES": "services.jpg",
    "PRICES":   "prices.jpg",
    "ABOUT":    "about.jpg",
    "ADDRESS":  "address.jpg",
    "CONTACT":  "contact.jpg",
    "SUCCESS":  "success.jpg",
    "CONFIRM":  "confirm.jpg",
}
 
async def send_photo_text(update, ctx, photo_key, text, reply_markup=None):
    """Отправить фото + текст. Использует кеш file_id для скорости."""
    chat_id = update.effective_chat.id
    path = PHOTO_PATHS.get(photo_key)
 
    if photo_key in PHOTO_CACHE:
        msg = await ctx.bot.send_photo(
            chat_id=chat_id,
            photo=PHOTO_CACHE[photo_key],
            caption=text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    elif path and os.path.exists(path):
        with open(path, "rb") as f:
            msg = await ctx.bot.send_photo(
                chat_id=chat_id,
                photo=f,
                caption=text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        PHOTO_CACHE[photo_key] = msg.photo[-1].file_id
    else:
        # fallback без фото
        if update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
        else:
            await ctx.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown", reply_markup=reply_markup)
        return
 
    # Удалить предыдущее сообщение если это callback
    if update.callback_query:
        try:
            await update.callback_query.delete_message()
        except:
            pass
 
async def send_message_safe(update, ctx, text, reply_markup=None):
    """Отправить обычное текстовое сообщение, удалив предыдущее (для длинных списков без фото)."""
    chat_id = update.effective_chat.id
    if update.callback_query:
        try:
            await update.callback_query.delete_message()
        except:
            pass
    await ctx.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown", reply_markup=reply_markup)
 
# ── SERVICES ──
SERVICES = [
    "🔆 Полировка",
    "🔧 Ремонт вмятин без покраски",
    "🧹 Химчистка салона",
    "🛡️ Броня кузова (PPF)",
    "🎨 Покраска",
    "🔦 Реставрация фар / сколов / царапин",
    "⚫ Антихром",
    "🎭 Оклейка в винил / цветной полиуретан",
    "💡 Подсветка салона",
    "💎 Бронирование глянцевых элементов салона",
    "🪡 Перешив салона",
    "🌑 Притемнение оптики / бронирование",
    "🪟 Тонировка",
]
 
PRICES = """
💰 *ПРАЙС-ЛИСТ*
 
*Бронирование полиуретаном (PPF):*
├ Купе / Седан / Универсал / Кроссовер — *119 990 ₽*
├ Бизнес-класс / Джип — *159 990 ₽*
└ Минивэн — *179 990 ₽*
 
*Зоны риска:*
├ Купе / Седан / Универсал — *39 990 ₽*
├ Бизнес-класс / Кроссовер / Джип — *59 990 ₽*
└ Минивэн — *39 990 ₽*
 
*Дополнительные услуги:*
├ Полировка — *от 3 990 ₽*
├ Керамика — *от 7 990 ₽*
├ Химчистка салона — *от 5 990 ₽*
├ Тонировка — *от 5 490 ₽*
├ Ремонт вмятин — *от 1 500 ₽*
├ Реставрация фар — *от 990 ₽*
├ Антихром — *от 2 990 ₽*
├ Оклейка в винил — *от 25 990 ₽*
└ Подсветка салона — *от 3 990 ₽*
 
_Точная стоимость после осмотра_
"""
 
# ── KEYBOARDS ──
def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Записаться на услугу", callback_data="book")],
        [InlineKeyboardButton("💰 Цены", callback_data="prices"),
         InlineKeyboardButton("ℹ️ О нас", callback_data="about")],
        [InlineKeyboardButton("📍 Адрес и время работы", callback_data="address")],
        [InlineKeyboardButton("📞 Связаться с мастером", callback_data="contact")],
        [InlineKeyboardButton("🗂 Мои записи", callback_data="my_bookings")],
    ])
 
def services_kb():
    btns = [[InlineKeyboardButton(s, callback_data=f"svc_{i}")] for i, s in enumerate(SERVICES)]
    btns.append([InlineKeyboardButton("◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(btns)
 
def confirm_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_yes")],
        [InlineKeyboardButton("✏️ Изменить", callback_data="confirm_edit")],
        [InlineKeyboardButton("❌ Отмена", callback_data="confirm_cancel")],
    ])
 
def back_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Главное меню", callback_data="back_main")]])
 
def date_kb():
    import datetime
    days_ru = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
    months_ru = ["янв","фев","мар","апр","май","июн","июл","авг","сен","окт","ноя","дек"]
    today = datetime.date.today()
    buttons = []
    row = []
    for i in range(14):
        d = today + datetime.timedelta(days=i)
        label = f"{d.day} {months_ru[d.month-1]} ({days_ru[d.weekday()]})"
        row.append(InlineKeyboardButton(label, callback_data=f"date_{d.strftime('%d.%m.%Y')}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🤷 Уточню позже", callback_data="date_skip")])
    return InlineKeyboardMarkup(buttons)
 
# ── HANDLERS ──
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    save_subscriber(update.effective_chat.id)
    text = (
        "👋 Добро пожаловать в *ПОНТ ДЕТЕЙЛИНГ*!\n\n"
        "🚗 Профессиональный уход за вашим автомобилем\n"
        "📍 Красноярск, Ястынская 50\n\n"
        "Выберите, что вас интересует:"
    )
    await send_photo_text(update, ctx, "WELCOME", text, main_kb())
    return MAIN_MENU
 
async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
 
    if data == "back_main":
        return await start(update, ctx)
 
    elif data == "book":
        await send_photo_text(update, ctx, "SERVICES",
            "🔧 *Выберите услугу:*\n\n_Нажмите на нужную услугу_",
            services_kb())
        return CHOOSE_SERVICE
 
    elif data == "prices":
        await send_photo_text(update, ctx, "PRICES", PRICES, back_kb())
        return MAIN_MENU
 
    elif data == "about":
        text = (
            "🏆 *О ПОНТ ДЕТЕЙЛИНГ*\n\n"
            "✅ 5 лет на рынке Красноярска\n"
            "✅ 500+ довольных клиентов\n"
            "✅ 13 видов услуг\n"
            "✅ 100% гарантия качества\n\n"
            "💬 _Мы не просто делаем чисто — мы создаём совершенство_"
        )
        await send_photo_text(update, ctx, "ABOUT", text, back_kb())
        return MAIN_MENU
 
    elif data == "address":
        text = (
            "📍 *Наш адрес:*\n"
            "Красноярск, Ястынская 50\n\n"
            "🕐 *Режим работы:*\n"
            "Ежедневно с 9:00 до 20:00\n\n"
            "🚗 Удобная парковка рядом"
        )
        await send_photo_text(update, ctx, "ADDRESS", text, back_kb())
        return MAIN_MENU
 
    elif data == "contact":
        text = (
            "📞 *Связаться с мастером*\n\n"
            "Оставьте заявку — мастер перезвонит в течение часа!"
        )
        await send_photo_text(update, ctx, "CONTACT", text,
            InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Оставить заявку", callback_data="book")],
                [InlineKeyboardButton("◀️ Назад", callback_data="back_main")],
            ]))
        return MAIN_MENU
 
    elif data == "my_bookings":
        bookings = get_bookings_for(update.effective_chat.id)
        if not bookings:
            text = (
                "🗂 *Мои записи*\n\n"
                "У вас пока нет истории записей.\n"
                "Оформите первую заявку прямо сейчас!"
            )
        else:
            lines = ["🗂 *Мои записи*\n"]
            for b in reversed(bookings[-10:]):  # последние 10, новые сверху
                _, ts, service, name, phone, car, comment, visit_date = b
                lines.append(
                    f"📅 Визит: *{visit_date}*\n"
                    f"🔧 {service}\n"
                    f"🚘 {car}\n"
                    f"_оформлено {ts}_\n"
                    f"{'─'*20}"
                )
            text = "\n".join(lines)
        await send_message_safe(update, ctx, text,
            InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Новая запись", callback_data="book")],
                [InlineKeyboardButton("◀️ Главное меню", callback_data="back_main")],
            ]))
        return MAIN_MENU
 
    elif data.startswith("svc_"):
        idx = int(data.split("_")[1])
        ctx.user_data["service"] = SERVICES[idx]
        await q.delete_message()
        await ctx.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"✅ Выбрана: *{SERVICES[idx]}*\n\n👤 Введите ваше *имя:*",
            parse_mode="Markdown"
        )
        return ENTER_NAME
 
    elif data == "confirm_yes":
        await send_to_admin(ctx)
        d = ctx.user_data
        save_booking(
            update.effective_chat.id,
            d.get('service','—'), d.get('name','—'), d.get('phone','—'),
            d.get('car','—'), d.get('comment','—'), d.get('visit_date','—')
        )
        await send_photo_text(update, ctx, "SUCCESS",
            "✅ *Заявка успешно отправлена!*\n\n"
            "Наш мастер свяжется с вами в течение часа.\n\n"
            "📍 Красноярск, Ястынская 50\n"
            "🕐 Работаем ежедневно 9:00 – 20:00",
            InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Главное меню", callback_data="back_main")]]))
        ctx.user_data.clear()
        return MAIN_MENU
 
    elif data in ("confirm_edit", "confirm_cancel"):
        ctx.user_data.clear()
        return await start(update, ctx)
 
async def get_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["name"] = update.message.text
    await update.message.reply_text("📞 Введите ваш *номер телефона:*", parse_mode="Markdown")
    return ENTER_PHONE
 
async def get_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["phone"] = update.message.text
    await update.message.reply_text(
        "🚘 Введите *марку и модель автомобиля:*\n_Например: BMW X5_", parse_mode="Markdown")
    return ENTER_CAR
 
async def get_car(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["car"] = update.message.text
    await update.message.reply_text(
        "💬 *Комментарий* (необязательно):\n_Или отправьте — чтобы пропустить_", parse_mode="Markdown")
    return ENTER_COMMENT
 
async def get_comment(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    ctx.user_data["comment"] = "—" if t.strip() == "—" else t
    await update.message.reply_text(
        "📅 *Выберите удобную дату визита:*",
        parse_mode="Markdown",
        reply_markup=date_kb()
    )
    return CHOOSE_DATE
 
async def choose_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
 
    if data == "date_skip":
        ctx.user_data["visit_date"] = "Уточнить позже"
    elif data.startswith("date_"):
        ctx.user_data["visit_date"] = data.replace("date_", "")
 
    d = ctx.user_data
    summary = (
        "📋 *Проверьте вашу заявку:*\n\n"
        f"🔧 Услуга: *{d.get('service','—')}*\n"
        f"👤 Имя: *{d.get('name','—')}*\n"
        f"📞 Телефон: *{d.get('phone','—')}*\n"
        f"🚘 Авто: *{d.get('car','—')}*\n"
        f"📅 Дата визита: *{d.get('visit_date','—')}*\n"
        f"💬 Комментарий: *{d.get('comment','—')}*\n\n"
        "Всё верно?"
    )
    await send_photo_text(update, ctx, "CONFIRM", summary, confirm_kb())
    return CONFIRM
 
async def send_to_admin(ctx):
    d = ctx.user_data
    msg = (
        "🚗 *НОВАЯ ЗАЯВКА — ПОНТ ДЕТЕЙЛИНГ*\n\n"
        f"🔧 Услуга: *{d.get('service','—')}*\n"
        f"👤 Имя: *{d.get('name','—')}*\n"
        f"📞 Телефон: *{d.get('phone','—')}*\n"
        f"🚘 Авто: *{d.get('car','—')}*\n"
        f"📅 Дата визита: *{d.get('visit_date','—')}*\n"
        f"💬 Комментарий: *{d.get('comment','—')}*"
    )
    await ctx.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg, parse_mode="Markdown")
 
async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("Отменено. Напишите /start")
    return ConversationHandler.END
 
# ── РАССЫЛКА (только для админа) ──
async def broadcast_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != str(ADMIN_CHAT_ID):
        return  # игнорируем, если пишет не админ
    subs = load_subscribers()
    await update.message.reply_text(
        f"📢 *Режим рассылки*\n\n"
        f"Подписчиков в базе: *{len(subs)}*\n\n"
        f"Отправьте сообщение (текст, фото, любой формат) — оно уйдёт всем подписчикам.\n"
        f"Для отмены: /cancel",
        parse_mode="Markdown"
    )
    return BROADCAST_WAIT
 
async def broadcast_send(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != str(ADMIN_CHAT_ID):
        return ConversationHandler.END
 
    subs = load_subscribers()
    sent, failed = 0, 0
    status = await update.message.reply_text(f"⏳ Рассылка началась... 0/{len(subs)}")
 
    for chat_id in subs:
        try:
            await update.message.copy(chat_id=chat_id)
            sent += 1
        except Exception as e:
            failed += 1
            logger.warning(f"Broadcast failed for {chat_id}: {e}")
 
        if (sent + failed) % 20 == 0:
            try:
                await status.edit_text(f"⏳ Рассылка идёт... {sent+failed}/{len(subs)}")
            except:
                pass
 
    await status.edit_text(
        f"✅ *Рассылка завершена*\n\n"
        f"Доставлено: *{sent}*\n"
        f"Не удалось: *{failed}*",
        parse_mode="Markdown"
    )
    return ConversationHandler.END
 
async def broadcast_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Рассылка отменена.")
    return ConversationHandler.END
 
# ── НАПОМИНАНИЯ О ВИЗИТЕ (за день) ──
REMINDED_FILE = "reminded.txt"
 
def already_reminded(key):
    if not os.path.exists(REMINDED_FILE):
        return False
    with open(REMINDED_FILE, "r") as f:
        return key in f.read().splitlines()
 
def mark_reminded(key):
    with open(REMINDED_FILE, "a") as f:
        f.write(key + "\n")
 
async def send_reminders(ctx: ContextTypes.DEFAULT_TYPE):
    """Запускается раз в день. Шлёт напоминание тем, у кого визит завтра."""
    import datetime
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%d.%m.%Y")
 
    bookings = get_all_bookings()
    for b in bookings:
        chat_id, ts, service, name, phone, car, comment, visit_date = b
        if visit_date == tomorrow:
            key = f"{chat_id}_{visit_date}_{service}"
            if already_reminded(key):
                continue
            try:
                await ctx.bot.send_message(
                    chat_id=int(chat_id),
                    text=(
                        "⏰ *Напоминание о визите*\n\n"
                        f"Завтра, *{visit_date}*, вас ждём в ПОНТ ДЕТЕЙЛИНГ!\n\n"
                        f"🔧 Услуга: *{service}*\n"
                        f"🚘 Авто: *{car}*\n\n"
                        "📍 Красноярск, Ястынская 50\n"
                        "🕐 9:00 – 20:00\n\n"
                        "Если планы изменились — свяжитесь с нами заранее 🙏"
                    ),
                    parse_mode="Markdown"
                )
                mark_reminded(key)
                logger.info(f"Reminder sent to {chat_id} for {visit_date}")
            except Exception as e:
                logger.warning(f"Reminder failed for {chat_id}: {e}")
 
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU:      [CallbackQueryHandler(button)],
            CHOOSE_SERVICE: [CallbackQueryHandler(button)],
            ENTER_NAME:     [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            ENTER_PHONE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            ENTER_CAR:      [MessageHandler(filters.TEXT & ~filters.COMMAND, get_car)],
            ENTER_COMMENT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, get_comment)],
            CHOOSE_DATE:    [CallbackQueryHandler(choose_date)],
            CONFIRM:        [CallbackQueryHandler(button)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
    app.add_handler(conv)
 
    broadcast_conv = ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast_start)],
        states={
            BROADCAST_WAIT: [MessageHandler(filters.ALL & ~filters.COMMAND, broadcast_send)],
        },
        fallbacks=[CommandHandler("cancel", broadcast_cancel)],
        allow_reentry=True,
    )
    app.add_handler(broadcast_conv)
 
    # Ежедневная проверка напоминаний о визите (в 10:00 по серверу)
    import datetime
    app.job_queue.run_daily(send_reminders, time=datetime.time(hour=10, minute=0))
 
    print("✅ Бот ПОНТ ДЕТЕЙЛИНГ запущен!")
    app.run_polling(drop_pending_updates=True)
 
if __name__ == "__main__":
    main()
