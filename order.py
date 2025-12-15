from telebot import types
from database import (
    add_user, get_sneakers, get_sneaker_by_id,
    add_order_pending, cancel_order, get_order_for_payment, get_order_status
)
import re


def start_order(bot, message):
    add_user(message.from_user)
    sneakers = get_sneakers()

    for s in sneakers:
        sneaker_id, name, desc, img_path, price, photo_file_id = s

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Обрати", callback_data=f"choose_{sneaker_id}"))

        caption = f"**{name}**\n\n{desc}\n\n💳 Ціна: **{price/100:.2f} UAH**"

        if photo_file_id:
            bot.send_photo(
                message.chat.id,
                photo_file_id,
                caption=caption,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        else:
            # fallback на локальний шлях (якщо є)
            with open(img_path, "rb") as photo:
                bot.send_photo(
                    message.chat.id,
                    photo,
                    caption=caption,
                    reply_markup=markup,
                    parse_mode="Markdown"
                )


def handle_callback(bot, call):
    # ✅ Скасувати оплату
    if call.data.startswith("cancelpay_"):
        order_id = int(call.data.split("_")[1])

        status = get_order_status(order_id)
        if status != "pending":
            bot.answer_callback_query(call.id, "ℹ️ Замовлення вже закрите.", show_alert=True)
            try:
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            except Exception:
                pass
            return

        cancel_order(order_id)

        # прибираємо кнопки
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except Exception:
            pass

        bot.answer_callback_query(call.id, "❌ Скасовано")
        bot.send_message(call.message.chat.id, f"❌ Оплату скасовано. Замовлення №{order_id} має статус CANCELED.")
        return

    # ✅ Оплатити
    if call.data.startswith("pay_"):
        order_id = int(call.data.split("_")[1])

        status = get_order_status(order_id)
        if status != "pending":
            bot.answer_callback_query(call.id, "❌ Це замовлення вже закрите", show_alert=True)
            try:
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            except Exception:
                pass
            return

        row = get_order_for_payment(order_id)
        if not row:
            bot.answer_callback_query(call.id, "❌ Замовлення не знайдено", show_alert=True)
            return

        (oid, user_id, sneaker_id, size, color, phone, row_status,
         name, desc, price) = row

        if row_status != "pending":
            bot.answer_callback_query(call.id, "❌ Це замовлення вже закрите", show_alert=True)
            return

        payload = f"order:{oid}"
        prices = [types.LabeledPrice(label=name, amount=int(price))]

        bot.answer_callback_query(call.id, "✅ Відкриваю оплату…")

        bot.send_invoice(
            chat_id=call.message.chat.id,
            title=f"Оплата: {name}",
            description=f"{desc}\nРозмір: {size}, Колір: {color}\nЗамовлення #{oid}",
            invoice_payload=payload,
            provider_token=bot.provider_token,
            currency="UAH",
            prices=prices,
            start_parameter="pay_sneakers"
        )
        return

    # --- Вибір моделі ---
    if call.data.startswith("choose_"):
        sneaker_id = int(call.data.split("_")[1])

        markup = types.InlineKeyboardMarkup(row_width=3)
        sizes = ["38", "39", "40", "41", "42", "43"]
        buttons = [types.InlineKeyboardButton(sz, callback_data=f"size_{sneaker_id}_{sz}") for sz in sizes]
        markup.add(*buttons)

        bot.send_message(call.message.chat.id, "📏 Оберіть розмір:", reply_markup=markup)
        return

    # --- Вибір розміру ---
    if call.data.startswith("size_"):
        _, sneaker_id, size = call.data.split("_")

        markup = types.InlineKeyboardMarkup(row_width=3)
        colors = ["Чорний", "Білий", "Синій", "Сірий"]
        buttons = [types.InlineKeyboardButton(c, callback_data=f"color_{sneaker_id}_{size}_{c}") for c in colors]
        markup.add(*buttons)

        bot.send_message(call.message.chat.id, "🎨 Оберіть колір:", reply_markup=markup)
        return

    # --- Вибір кольору → телефон ---
    if call.data.startswith("color_"):
        _, sneaker_id, size, color = call.data.split("_")
        bot.send_message(call.message.chat.id, "📞 Введіть ваш номер телефону (+380XXXXXXXXX):")

        bot.register_next_step_handler(
            call.message,
            lambda msg: validate_phone(bot, msg, sneaker_id, size, color)
        )
        return


def validate_phone(bot, message, sneaker_id, size, color):
    phone = (message.text or "").strip()
    phone_clean = phone.replace(" ", "").replace("-", "")

    pattern = r"^(\+380\d{9}|380\d{9}|0\d{9})$"

    if not re.match(pattern, phone_clean):
        bot.send_message(
            message.chat.id,
            "❌ *Невірний формат номера телефону!*\n\n"
            "Приклади:\n"
            "`+380931234567`\n"
            "`380931234567`\n"
            "`0931234567`\n\n"
            "Спробуйте ще раз:",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(
            message,
            lambda msg: validate_phone(bot, msg, sneaker_id, size, color)
        )
        return

    # нормалізація у +380XXXXXXXXX
    if phone_clean.startswith("0"):
        phone_clean = "+38" + phone_clean
    elif phone_clean.startswith("380"):
        phone_clean = "+" + phone_clean

    confirm_order(bot, message, sneaker_id, size, color, phone_clean)


def confirm_order(bot, message, sneaker_id, size, color, phone):
    user_id = message.from_user.id
    sneaker_id = int(sneaker_id)

    order_id = add_order_pending(user_id, sneaker_id, size, color, phone)

    sneaker = get_sneaker_by_id(sneaker_id)
    if not sneaker:
        bot.send_message(message.chat.id, "❌ Помилка: модель не знайдена.")
        return

    _id, name, desc, img_path, price, photo_file_id = sneaker
    if not price or price <= 0:
        bot.send_message(message.chat.id, "❌ Помилка: для цього товару не задано ціну.")
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("💳 Оплатити", callback_data=f"pay_{order_id}"),
        types.InlineKeyboardButton("❌ Скасувати", callback_data=f"cancelpay_{order_id}")
    )

    bot.send_message(
        message.chat.id,
        f"🧾 Замовлення №<code>{order_id}</code> сформовано.\n"
        f"👟 <b>{name}</b>\n"
        f"📏 Розмір: <b>{size}</b>\n"
        f"🎨 Колір: <b>{color}</b>\n"
        f"📞 Телефон: <b>{phone}</b>\n"
        f"💳 Сума: <b>{price/100:.2f} UAH</b>\n\n"
        f"Натисни <b>💳 Оплатити</b> або <b>❌ Скасувати</b>.",
        parse_mode="HTML",
        reply_markup=markup
    )
