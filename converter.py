import requests
from telebot import TeleBot

API_URL = "https://open.er-api.com/v6/latest/"
ALLOWED = ["USD", "EUR", "UAH"]

def get_rates(base: str):
    """Отримати курси для базової валюти"""
    base = base.upper()
    if base not in ALLOWED:
        raise ValueError("Доступні тільки USD, EUR, UAH")

    response = requests.get(API_URL + base)
    if response.status_code != 200:
        raise ValueError(f"API помилка: {response.status_code}")
    
    data = response.json()
    if data.get("result") != "success":
        raise ValueError(f"API не повернуло успіх: {data}")
    
    return data["rates"]


def convert_currency(amount: float, from_cur: str, to_cur: str) -> float:
    """Конвертація з однієї валюти в іншу"""
    from_cur = from_cur.upper()
    to_cur = to_cur.upper()

    if from_cur not in ALLOWED or to_cur not in ALLOWED:
        raise ValueError("Доступні тільки USD, EUR, UAH")

    rates = get_rates(from_cur)
    if to_cur not in rates:
        raise ValueError(f"Немає курсу для {to_cur}")

    return amount * rates[to_cur]


def handle_conversion(bot: TeleBot, message):
    """Обробка повідомлення з конвертацією"""
    try:
        parts = message.text.split()
        if len(parts) == 3:
            amount = float(parts[0])
            from_cur = parts[1]
            to_cur = parts[2]
            result = convert_currency(amount, from_cur, to_cur)
            bot.send_message(
                message.chat.id, 
                f"{amount} {from_cur.upper()} = {result:.2f} {to_cur.upper()}"
            )
        else:
            bot.send_message(message.chat.id, "Введіть у форматі: 100 USD UAH")
    except Exception as e:
        bot.send_message(message.chat.id, f"Помилка: {e}")
