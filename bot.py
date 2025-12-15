import telebot
from telebot import types
from telebot.types import BotCommand

from converter import handle_conversion
from weather import ask_city, handle_city_weather
from horoscope import show_zodiac_menu, handle_horoscope, ZODIAC_SIGNS
from wiki import handle_wiki
from states import user_states, STATE_NONE, STATE_WEATHER
from feedback import start_feedback

from database import (
    init_db, mark_order_paid, get_order_status,
    get_sneakers, add_sneaker, remove_sneaker, list_orders
)
from order import start_order, handle_callback


# =========================
# CONFIG
# =========================
TOKEN = "YOUR_TOKEN"
PROVIDER_TOKEN = "YOUR_TOKEN"

# ✅ сюди додай свій Telegram user_id
ADMINS = {}

bot = telebot.TeleBot(TOKEN)
bot.provider_token = PROVIDER_TOKEN

init_db()


def is_admin(user_id: int) -> bool:
    return user_id in ADMINS


# =========================
# COMMANDS
# =========================
bot.set_my_commands([
    BotCommand("start", "Запустити бота"),
    BotCommand("help", "Список команд"),
    BotCommand("feedback", "Залишити відгук"),

    BotCommand("admin", "Адмін-меню (тільки адмін)"),
    BotCommand("add_item", "Додати товар (адмін)"),
    BotCommand("remove_item", "Видалити товар (адмін)"),
    BotCommand("orders", "Список замовлень (адмін)"),
])


@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = (
        "📘 *Список команд бота:*\n\n"
        "/start – головне меню\n"
        "/help – список команд\n"
        "/feedback – залишити відгук\n\n"
        "📦 Замовлення взуття\n"
        "⛅ Прогноз погоди\n"
        "🔮 Гороскоп\n"
        "💱 Конвертер валют (формат: 100 USD UAH)\n"
        "📚 Вікіпедія\n\n"
        "🔐 Адмін:\n"
        "/admin, /add_item, /remove_item, /orders\n"
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")


@bot.message_handler(commands=['feedback'])
def feedback_command(message):
    start_feedback(bot, message)


@bot.message_handler(commands=['start'])
def start(message):
    user_states[message.chat.id] = STATE_NONE

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("📦 Замовити взуття"))
    markup.add(types.KeyboardButton("💱 Конвертер валют"), types.KeyboardButton("🔮 Гороскоп"))
    markup.add(types.KeyboardButton("⛅ Прогноз погоди"), types.KeyboardButton("📚 Вікіпедія"))

    bot.send_message(message.chat.id, "Вітаю! Оберіть дію:", reply_markup=markup)


# =========================
# ADMIN MENU + COMMANDS
# =========================
@bot.message_handler(commands=['admin'])
def admin_menu(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Доступ заборонено.")
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➕ Додати товар", callback_data="admin_add"))
    markup.add(types.InlineKeyboardButton("➖ Видалити товар", callback_data="admin_remove"))
    markup.add(types.InlineKeyboardButton("📦 Замовлення", callback_data="admin_orders"))

    bot.send_message(message.chat.id, "🔐 Адмін-меню:", reply_markup=markup)


@bot.message_handler(commands=['add_item'])
def cmd_add_item(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Доступ заборонено.")
        return

    bot.send_message(
        message.chat.id,
        "➕ Додавання товару.\nНадішли одним повідомленням:\n"
        "<code>Назва | Опис | Ціна_грн</code>\n"
        "Напр: <code>Nike X | Бігові кросівки | 2799</code>\n\n"
        "Після цього я попрошу фото.",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(message, admin_add_step1)


@bot.message_handler(commands=['remove_item'])
def cmd_remove_item(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Доступ заборонено.")
        return

    items = get_sneakers()
    text = "➖ Видалення товару.\nНадішли ID товару.\n\nСписок:\n"
    for (sid, name, desc, img_path, price, photo_id) in items:
        text += f"• ID {sid}: {name} ({price/100:.2f} UAH)\n"

    bot.send_message(message.chat.id, text)
    bot.register_next_step_handler(message, admin_remove_step)


@bot.message_handler(commands=['orders'])
def cmd_orders(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Доступ заборонено.")
        return
    send_orders(message.chat.id)


def send_orders(chat_id: int):
    rows = list_orders(30)
    if not rows:
        bot.send_message(chat_id, "Замовлень поки немає.")
        return

    msg = "📦 Останні замовлення:\n\n"
    for r in rows:
        (oid, user_id, username, sname, size, color, phone, status, paid, charge_id) = r
        uname = f"@{username}" if username else "—"
        msg += (
            f"#{oid} | {sname} | {size}/{color}\n"
            f"user: {user_id} {uname}\n"
            f"phone: {phone}\n"
            f"status: {status} | paid: {paid}\n"
            f"---\n"
        )
    bot.send_message(chat_id, msg)


def admin_add_step1(message):
    if not is_admin(message.from_user.id):
        return

    raw = (message.text or "").strip()
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) != 3:
        bot.send_message(message.chat.id, "❌ Формат невірний. Треба: Назва | Опис | Ціна_грн")
        bot.register_next_step_handler(message, admin_add_step1)
        return

    name, desc, price_str = parts
    try:
        price_uah = float(price_str.replace(",", "."))
        price_kop = int(price_uah * 100)
        if price_kop <= 0:
            raise ValueError
    except Exception:
        bot.send_message(message.chat.id, "❌ Ціна має бути числом, напр: 2799 або 2799.00")
        bot.register_next_step_handler(message, admin_add_step1)
        return

    bot.send_message(message.chat.id, "📸 Тепер надішли фото товару (саме фото, не файл).")
    bot.register_next_step_handler(message, lambda msg: admin_add_step2(msg, name, desc, price_kop))


def admin_add_step2(message, name, desc, price_kop):
    if not is_admin(message.from_user.id):
        return

    if not message.photo:
        bot.send_message(message.chat.id, "❌ Це не фото. Надішли саме фото.")
        bot.register_next_step_handler(message, lambda msg: admin_add_step2(msg, name, desc, price_kop))
        return

    photo_file_id = message.photo[-1].file_id
    new_id = add_sneaker(name, desc, price_kop, photo_file_id=photo_file_id)

    bot.send_message(message.chat.id, f"✅ Товар додано! ID: {new_id}\n{name} ({price_kop/100:.2f} UAH)")


def admin_remove_step(message):
    if not is_admin(message.from_user.id):
        return

    try:
        sneaker_id = int((message.text or "").strip())
    except Exception:
        bot.send_message(message.chat.id, "❌ Введи числовий ID.")
        bot.register_next_step_handler(message, admin_remove_step)
        return

    ok = remove_sneaker(sneaker_id)
    bot.send_message(
        message.chat.id,
        f"✅ Товар ID {sneaker_id} видалено." if ok else f"❌ Товар ID {sneaker_id} не знайдено."
    )


# =========================
# PAYMENTS
# =========================
@bot.pre_checkout_query_handler(func=lambda q: True)
def process_pre_checkout_query(pre_checkout_query):
    payload = pre_checkout_query.invoice_payload or ""

    if payload.startswith("order:"):
        try:
            order_id = int(payload.split(":", 1)[1])
        except Exception:
            bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False, error_message="Невірний payload.")
            return

        status = get_order_status(order_id)

        # ✅ дозволяємо оплату тільки коли pending
        # (якщо ти зробиш in_payment — заміниш тут логіку)
        if status != "pending":
            bot.answer_pre_checkout_query(
                pre_checkout_query.id,
                ok=False,
                error_message="Оплата скасована або замовлення вже закрите."
            )
            return

    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@bot.message_handler(content_types=['successful_payment'])
def process_successful_payment(message):
    sp = message.successful_payment
    payload = sp.invoice_payload or ""

    order_id = None
    if payload.startswith("order:"):
        try:
            order_id = int(payload.split(":", 1)[1])
        except Exception:
            order_id = None

    if order_id is not None:
        mark_order_paid(order_id, sp.telegram_payment_charge_id)

    bot.send_message(
        message.chat.id,
        "✅ Оплата успішна! Дякуємо.\n"
        f"Замовлення №: <code>{order_id if order_id else 'невідомо'}</code>\n"
        f"Сума: <b>{sp.total_amount/100:.2f} {sp.currency}</b>",
        parse_mode="HTML"
    )


# =========================
# MAIN TEXT HANDLER
# =========================
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text or ""

    if user_states.get(chat_id) == STATE_WEATHER:
        handle_city_weather(bot, message)
        return

    if text == "📦 Замовити взуття":
        start_order(bot, message)
        return

    if text == "⛅ Прогноз погоди":
        user_states[chat_id] = STATE_WEATHER
        ask_city(bot, chat_id)
        return

    if text == "🔮 Гороскоп":
        show_zodiac_menu(bot, chat_id)
        return

    if text in ZODIAC_SIGNS:
        handle_horoscope(bot, message)
        return

    if text == "💱 Конвертер валют":
        bot.send_message(chat_id, "Введіть у форматі: 100 USD UAH")
        return

    if text == "📚 Вікіпедія":
        bot.send_message(chat_id, "Введіть запит для пошуку:")
        bot.register_next_step_handler(message, lambda msg: handle_wiki(bot, msg))
        return

    if text.startswith("/"):
        bot.send_message(chat_id, "Невідома команда. Напиши /help")
        return

    handle_conversion(bot, message)


# =========================
# CALLBACK ROUTER
# =========================
@bot.callback_query_handler(func=lambda call: True)
def callback_router(call):
    # адмін-кнопки
    if call.data.startswith("admin_"):
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Нема доступу", show_alert=True)
            return

        if call.data == "admin_add":
            bot.answer_callback_query(call.id)
            bot.send_message(
                call.message.chat.id,
                "➕ Додавання товару.\nНадішли:\n<code>Назва | Опис | Ціна_грн</code>\n"
                "Після цього я попрошу фото.",
                parse_mode="HTML"
            )
            bot.register_next_step_handler(call.message, admin_add_step1)
            return

        if call.data == "admin_remove":
            bot.answer_callback_query(call.id)
            items = get_sneakers()
            text = "➖ Видалення товару.\nНадішли ID товару.\n\nСписок:\n"
            for (sid, name, desc, img_path, price, photo_id) in items:
                text += f"• ID {sid}: {name} ({price/100:.2f} UAH)\n"
            bot.send_message(call.message.chat.id, text)
            bot.register_next_step_handler(call.message, admin_remove_step)
            return

        if call.data == "admin_orders":
            bot.answer_callback_query(call.id)
            send_orders(call.message.chat.id)
            return

    # все інше — замовлення/оплата
    handle_callback(bot, call)


bot.polling(none_stop=True)
