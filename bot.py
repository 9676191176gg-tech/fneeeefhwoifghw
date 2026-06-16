import logging
import os
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ── CONFIG ──
BOT_TOKEN = os.getenv("BOT_TOKEN", "8923862657:AAHdeOhKabUxww8Yn-x1L3-REJz5yyimdW4")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "1211960244")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── STATES ──
(
    MAIN_MENU,
    CHOOSE_SERVICE,
    ENTER_NAME,
    ENTER_PHONE,
    ENTER_CAR,
    ENTER_COMMENT,
    CONFIRM,
) = range(7)

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
├ Полировка кузова — *от 3 990 ₽*
├ Керамика — *от 7 990 ₽*
├ Притемнение оптики — *от 4 990 ₽*
├ Химчистка салона — *от 5 990 ₽*
├ Тонировка передней полусферы — *5 490 ₽*
├ Ремонт вмятин без покраски — *от 1 500 ₽*
├ Реставрация фар — *от 990 ₽*
├ Антихром — *от 2 990 ₽*
├ Оклейка в винил — *от 25 990 ₽*
└ Подсветка салона — *от 3 990 ₽*

_Точная стоимость рассчитывается после осмотра автомобиля_
"""

# ── KEYBOARDS ──
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Записаться на услугу", callback_data="book")],
        [InlineKeyboardButton("💰 Цены", callback_data="prices"),
         InlineKeyboardButton("ℹ️ О нас", callback_data="about")],
        [InlineKeyboardButton("📍 Адрес и время работы", callback_data="address")],
        [InlineKeyboardButton("📞 Связаться с мастером", callback_data="contact")],
    ])

def services_keyboard():
    buttons = []
    for i, s in enumerate(SERVICES):
        buttons.append([InlineKeyboardButton(s, callback_data=f"svc_{i}")])
    buttons.append([InlineKeyboardButton("◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)

def confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить заявку", callback_data="confirm_yes")],
        [InlineKeyboardButton("✏️ Изменить", callback_data="confirm_edit")],
        [InlineKeyboardButton("❌ Отмена", callback_data="confirm_cancel")],
    ])

def back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Главное меню", callback_data="back_main")]
    ])

# ── HANDLERS ──
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    text = (
        "👋 Добро пожаловать в *ПОНТ ДЕТЕЙЛИНГ*!\n\n"
        "🚗 Профессиональный уход за вашим автомобилем\n"
        "📍 Красноярск, Ястынская 50\n\n"
        "Выберите, что вас интересует:"
    )
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())
    else:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())
    return MAIN_MENU

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back_main":
        return await start(update, ctx)

    elif data == "book":
        await query.edit_message_text(
            "🔧 *Выберите услугу:*\n\n_Нажмите на нужную услугу из списка_",
            parse_mode="Markdown",
            reply_markup=services_keyboard()
        )
        return CHOOSE_SERVICE

    elif data == "prices":
        await query.edit_message_text(
            PRICES, parse_mode="Markdown", reply_markup=back_keyboard()
        )
        return MAIN_MENU

    elif data == "about":
        text = (
            "🏆 *О ПОНТ ДЕТЕЙЛИНГ*\n\n"
            "✅ 5 лет на рынке Красноярска\n"
            "✅ 500+ довольных клиентов\n"
            "✅ 13 видов услуг\n"
            "✅ 100% гарантия качества\n\n"
            "Мы не просто моем автомобили — мы их преображаем. "
            "Используем только сертифицированные материалы и даём гарантию на все виды работ."
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_keyboard())
        return MAIN_MENU

    elif data == "address":
        text = (
            "📍 *Наш адрес:*\n"
            "Красноярск, Ястынская 50\n\n"
            "🕐 *Режим работы:*\n"
            "Ежедневно с 9:00 до 20:00\n\n"
            "🚗 Удобная парковка рядом"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_keyboard())
        return MAIN_MENU

    elif data == "contact":
        text = (
            "📞 *Связаться с мастером:*\n\n"
            "Оставьте заявку через бота — мастер перезвонит в течение часа\n\n"
            "Или запишитесь через наш сайт"
        )
        await query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Оставить заявку", callback_data="book")],
                [InlineKeyboardButton("◀️ Назад", callback_data="back_main")],
            ])
        )
        return MAIN_MENU

    elif data.startswith("svc_"):
        idx = int(data.split("_")[1])
        ctx.user_data["service"] = SERVICES[idx]
        await query.edit_message_text(
            f"✅ Выбрана услуга: *{SERVICES[idx]}*\n\n"
            "👤 Введите ваше *имя:*",
            parse_mode="Markdown"
        )
        return ENTER_NAME

    elif data == "confirm_yes":
        await send_to_admin(ctx)
        await query.edit_message_text(
            "✅ *Заявка успешно отправлена!*\n\n"
            "Наш мастер свяжется с вами в течение часа.\n\n"
            "📍 Красноярск, Ястынская 50\n"
            "🕐 Работаем ежедневно 9:00 – 20:00",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Главное меню", callback_data="back_main")]
            ])
        )
        ctx.user_data.clear()
        return MAIN_MENU

    elif data == "confirm_edit":
        ctx.user_data.clear()
        await query.edit_message_text(
            "Заявка отменена. Начнём заново?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Записаться снова", callback_data="book")],
                [InlineKeyboardButton("◀️ Главное меню", callback_data="back_main")],
            ])
        )
        return MAIN_MENU

    elif data == "confirm_cancel":
        ctx.user_data.clear()
        return await start(update, ctx)

async def get_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["name"] = update.message.text
    await update.message.reply_text(
        "📞 Введите ваш *номер телефона:*",
        parse_mode="Markdown"
    )
    return ENTER_PHONE

async def get_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["phone"] = update.message.text
    await update.message.reply_text(
        "🚘 Введите *марку и модель автомобиля:*\n_Например: BMW X5, Mercedes S-класс_",
        parse_mode="Markdown"
    )
    return ENTER_CAR

async def get_car(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["car"] = update.message.text
    await update.message.reply_text(
        "💬 Добавьте *комментарий* (необязательно):\n_Или отправьте — чтобы пропустить_",
        parse_mode="Markdown"
    )
    return ENTER_COMMENT

async def get_comment(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    ctx.user_data["comment"] = "—" if text.strip() == "—" else text

    d = ctx.user_data
    summary = (
        "📋 *Проверьте вашу заявку:*\n\n"
        f"🔧 Услуга: *{d.get('service', '—')}*\n"
        f"👤 Имя: *{d.get('name', '—')}*\n"
        f"📞 Телефон: *{d.get('phone', '—')}*\n"
        f"🚘 Авто: *{d.get('car', '—')}*\n"
        f"💬 Комментарий: *{d.get('comment', '—')}*\n\n"
        "Всё верно?"
    )
    await update.message.reply_text(summary, parse_mode="Markdown", reply_markup=confirm_keyboard())
    return CONFIRM

async def send_to_admin(ctx: ContextTypes.DEFAULT_TYPE):
    d = ctx.user_data
    msg = (
        "🚗 *НОВАЯ ЗАЯВКА — ПОНТ ДЕТЕЙЛИНГ*\n\n"
        f"🔧 Услуга: *{d.get('service', '—')}*\n"
        f"👤 Имя: *{d.get('name', '—')}*\n"
        f"📞 Телефон: *{d.get('phone', '—')}*\n"
        f"🚘 Авто: *{d.get('car', '—')}*\n"
        f"💬 Комментарий: *{d.get('comment', '—')}*"
    )
    await ctx.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg, parse_mode="Markdown")

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("Отменено. Напишите /start чтобы начать заново.")
    return ConversationHandler.END

# ── MAIN ──
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [CallbackQueryHandler(button_handler)],
            CHOOSE_SERVICE: [CallbackQueryHandler(button_handler)],
            ENTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            ENTER_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            ENTER_CAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_car)],
            ENTER_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_comment)],
            CONFIRM: [CallbackQueryHandler(button_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("start", start))

    print("✅ Бот ПОНТ ДЕТЕЙЛИНГ запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
