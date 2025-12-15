import wikipedia
from telebot import TeleBot

wikipedia.set_lang("uk")


def search_wiki(query: str):
    try:
        results = wikipedia.search(query)
        if not results:
            return None, None, None

        page_title = results[0]
        page = wikipedia.page(page_title)
        title = page.title
        summary = wikipedia.summary(page_title, sentences=5)
        url = page.url
        return title, summary, url

    except Exception:
        return None, None, None


def handle_wiki(bot: TeleBot, message):
    query = message.text.strip()

    # Вихід з режиму Вікіпедії + повернення в головне меню
    if query.lower() in ["вийти", "стоп", "назад"]:
        bot.send_message(message.chat.id, "✅ Режим Вікіпедії завершено.")
        bot.send_message(message.chat.id, "/start")   # 🔥 автоматичний вихід у меню
        return

    title, summary, url = search_wiki(query)

    if title is None:
        bot.send_message(message.chat.id, "❌ Статтю не знайдено. Спробуйте інший запит:")
    else:
        bot.send_message(
            message.chat.id,
            f"📘 *{title}*\n\n{summary}\n\n🔗 {url}",
            parse_mode="Markdown"
        )

    # Чекаємо новий запит
    bot.send_message(message.chat.id, "🔎 Введіть новий запит або напишіть *вийти*:")
    bot.register_next_step_handler(message, lambda msg: handle_wiki(bot, msg))

