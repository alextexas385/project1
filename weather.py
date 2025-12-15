import requests
from telebot import types

API_KEY = "6d0ad0bdcaac43f765829c196e64323b"

# --- Показ меню для введення міста ---
def ask_city(bot, chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_cancel = types.KeyboardButton("❌ Скасувати")
    markup.add(btn_cancel)

    bot.send_message(
        chat_id,
        "Введіть назву міста для отримання прогнозу погоди:",
        reply_markup=markup
    )


# --- Отримання погоди по місту ---
def get_weather(city):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric&lang=ua"

    response = requests.get(url)
    data = response.json()

    if data.get("cod") != 200:
        return None

    weather = data["weather"][0]["description"]
    temp = data["main"]["temp"]
    feels = data["main"]["feels_like"]
    humidity = data["main"]["humidity"]
    wind = data["wind"]["speed"]

    text = (
        f"☁ Погода у місті *{city.title()}*:\n"
        f"🌡 Температура: {temp}°C\n"
        f"🤗 Відчувається як: {feels}°C\n"
        f"💧 Вологість: {humidity}%\n"
        f"🌬 Вітер: {wind} м/с\n"
        f"📌 Опис: {weather.capitalize()}"
    )

    return text


# --- Обробка введеного міста ---
def handle_city_weather(bot, message):
    city = message.text.strip()

    if city == "❌ Скасувати":
        bot.send_message(message.chat.id, "Операцію скасовано.", reply_markup=types.ReplyKeyboardRemove())
        return

    weather_text = get_weather(city)

    if weather_text is None:
        bot.send_message(message.chat.id, "Не вдалося знайти місто. Спробуйте інше.")
        # ПОВТОРНО просимо місто, а не переносимо в конвертер!
        bot.register_next_step_handler(message, lambda msg: handle_city_weather(bot, msg))
        return

    bot.send_message(message.chat.id, weather_text, parse_mode="Markdown")

