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
MAIN_MENU, CHOOSE_SERVICE, ENTER_NAME, ENTER_PHONE, ENTER_CAR, ENTER_COMMENT, CONFIRM = range(7)

# ── PHOTOS (file_id кешируется после первой отправки) ──
PHOTO_CACHE = {}

PHOTO_PATHS = {
    "WELCOME":  "images/welcome.jpg",
    "SERVICES": "images/services.jpg",
    "PRICES":   "images/prices.jpg",
    "ABOUT":    "images/about.jpg",
    "ADDRESS":  "images/address.jpg",
    "CONTACT":  "images/contact.jpg",
    "SUCCESS":  "images/success.jpg",
    "CONFIRM":  "images/confirm.jpg",
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

# ── HANDLERS ──
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
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
    d = ctx.user_data
    summary = (
        "📋 *Проверьте вашу заявку:*\n\n"
        f"🔧 Услуга: *{d.get('service','—')}*\n"
        f"👤 Имя: *{d.get('name','—')}*\n"
        f"📞 Телефон: *{d.get('phone','—')}*\n"
        f"🚘 Авто: *{d.get('car','—')}*\n"
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
        f"💬 Комментарий: *{d.get('comment','—')}*"
    )
    await ctx.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg, parse_mode="Markdown")

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("Отменено. Напишите /start")
    return ConversationHandler.END

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
            CONFIRM:        [CallbackQueryHandler(button)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
    app.add_handler(conv)
    print("✅ Бот ПОНТ ДЕТЕЙЛИНГ запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
