# feedback.py
from telebot import TeleBot

#  Встав сюди ID адмінів 
ADMIN_IDS = {404724889}  # <-- заміни на свій ID

def send_to_admins(bot: TeleBot, text: str):
    """Надсилає повідомлення всім адмінам у приват."""
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, text)
        except Exception:
            pass

def start_feedback(bot: TeleBot, message):
    """Старт /feedback: просимо текст і чекаємо наступне повідомлення."""
    bot.send_message(message.chat.id, "✍️ Напиши свій відгук одним повідомленням.")
    bot.register_next_step_handler(message, lambda msg: handle_feedback(bot, msg))

def handle_feedback(bot: TeleBot, message):
    """Отримали відгук → відправляємо адмінам."""
    fb = (message.text or "").strip()
    if not fb:
        bot.send_message(message.chat.id, "Відгук порожній. Спробуй ще раз: /feedback")
        return

    u = message.from_user
    admin_text = (
        "📝 <b>Новий відгук</b>\n"
        f"Від: <b>{u.first_name}</b> "
        f"(@{u.username if u.username else 'нема'})\n"
        f"ID: <code>{u.id}</code>\n\n"
        f"<b>Текст:</b>\n{fb}"
    )

    send_to_admins(bot, admin_text)
    bot.send_message(message.chat.id, "✅ Дякую! Відгук надіслано адміністраторам.")
