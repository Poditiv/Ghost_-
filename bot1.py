import telebot
from telebot import types
from datetime import datetime, timedelta

TOKEN = "8284319046:AAFv18kRPZw-Yw_E-IK95mSzPQgRddMtLoc"
bot = telebot.TeleBot(TOKEN)


RESTAURANTS = [
    {"name": "Dodo Pizza", "address": "Алматы, проспект Достык 123", "lat": 43.2386, "lon": 76.9451, "hours": "10:00-23:00"},
    {"name": "Starbucks", "address": "Алматы, ул. Абылай хана 45", "lat": 43.2567, "lon": 76.9281, "hours": "08:00-22:00"},
    {"name": "McDonald's", "address": "Алматы, ул. Толе би 78", "lat": 43.2471, "lon": 76.9123, "hours": "09:00-00:00"},
    {"name": "Burger King", "address": "Алматы, ул. Райымбека 99", "lat": 43.2623, "lon": 76.9384, "hours": "10:00-23:00"},
]

bookings = {}
user_state = {}
ratings = {}

ADMIN_ID = 1351333844  

def generate_slots(hours):
    start, end = hours.split("-")
    start_hour = int(start.split(":")[0])
    end_hour = int(end.split(":")[0])
    slots = []
    for h in range(start_hour, end_hour, 2):
        slots.append(f"{h:02d}:00")
    return slots

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Рестораны Алматы", "Мои бронирования", "О боте")
    bot.send_message(message.chat.id, "Привет! Я помогу забронировать столик.", reply_markup=markup)


@bot.message_handler(commands=['stats'])
def stats(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Доступ запрещен ❌")
        return
    text = "📊 Статистика бронирований:\n\n"
    for r in RESTAURANTS:
        count = sum(1 for user in bookings.values() for b in user if b["restaurant"] == r["name"])
        text += f"{r['name']}: {count} бронирований\n"
    bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda message: True)
def menu(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if text == "Рестораны Алматы":
        markup = types.InlineKeyboardMarkup()
        for r in RESTAURANTS:
            markup.add(types.InlineKeyboardButton(r["name"], callback_data=f"restaurant:{r['name']}"))
        bot.send_message(chat_id, "Выберите ресторан:", reply_markup=markup)
        return

    elif text == "О боте":
        bot.send_message(chat_id, "Бот позволяет:\n"
                                  "- Бронировать столики в популярных заведениях Алматы\n"
                                  "- Оценивать рестораны ⭐\n"
                                  "- Отправляет адрес и геолокацию\n"
                                  "- Админ-статистика бронирований\n"
                                  "- Пользователь может отменить бронирование")

    elif text == "Мои бронирования":
        user_bookings = bookings.get(chat_id, [])
        if not user_bookings:
            bot.send_message(chat_id, "У вас нет бронирований.")
        else:
            txt = "Ваши бронирования:\n"
            markup = types.InlineKeyboardMarkup()
            for i, b in enumerate(user_bookings):
                txt += f"{i+1}. {b['restaurant']} — {b['date']} в {b['time']}\nАдрес: {b['address']}\n\n"
                markup.add(types.InlineKeyboardButton(f"❌ Отменить #{i+1}", callback_data=f"cancel:{i}"))
            bot.send_message(chat_id, txt, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    chat_id = call.message.chat.id
    data = call.data

    if data.startswith("restaurant:"):
        restaurant_name = data.split(":", 1)[1]
        restaurant = next(r for r in RESTAURANTS if r["name"] == restaurant_name)
        user_state[chat_id] = {"restaurant": restaurant, "step": "date"}

        markup = types.InlineKeyboardMarkup()
        for i in range(3):
            date = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
            markup.add(types.InlineKeyboardButton(date, callback_data=f"date:{date}"))

        bot.edit_message_text(chat_id=chat_id,
         message_id=call.message.message_id,
        text=f"Вы выбрали ресторан:\n\n{restaurant['name']}\n📍 {restaurant['address']}\n🕒 Часы работы: {restaurant['hours']}\n\nТеперь выберите дату:",
        reply_markup=markup)

    elif data.startswith("date:"):
        date = data.split(":", 1)[1]
        user_state[chat_id]["date"] = date
        user_state[chat_id]["step"] = "time"

        restaurant = user_state[chat_id]["restaurant"]
        slots = generate_slots(restaurant["hours"])

        markup = types.InlineKeyboardMarkup()
        for t in slots:
            markup.add(types.InlineKeyboardButton(t, callback_data=f"time:{t}"))

        bot.edit_message_text(chat_id=chat_id,
        message_id=call.message.message_id,
        text=f"Дата выбрана: {date}\nВыберите время:",
        reply_markup=markup)

    elif data.startswith("time:"):
        time = data.split(":", 1)[1]
        restaurant = user_state[chat_id]["restaurant"]
        date = user_state[chat_id]["date"]

        bookings.setdefault(chat_id, []).append({
            "restaurant": restaurant["name"],
            "date": date,
            "time": time,
            "address": restaurant["address"],
            "lat": restaurant["lat"],
            "lon": restaurant["lon"]
        })

        bot.edit_message_text(chat_id=chat_id,
        message_id=call.message.message_id,
        text=f"Столик в ресторане {restaurant['name']} забронирован на {date} в {time}! 🎉\nАдрес: {restaurant['address']}")

        bot.send_location(chat_id, latitude=restaurant["lat"], longitude=restaurant["lon"])

        markup = types.InlineKeyboardMarkup()
        for i in range(1, 6):
            markup.add(types.InlineKeyboardButton(f"⭐ {i}", callback_data=f"rate:{restaurant['name']}:{i}"))
        bot.send_message(chat_id, "Оцените ресторан:", reply_markup=markup)

        user_state.pop(chat_id, None)

    elif data.startswith("rate:"):
        _, name, score = data.split(":")
        ratings.setdefault(name, []).append(int(score))
        avg = sum(ratings[name]) / len(ratings[name])
        bot.answer_callback_query(call.id, f"Спасибо! Средний рейтинг {name}: {avg:.1f} ⭐")

    elif data.startswith("cancel:"):
        idx = int(data.split(":")[1])
        if chat_id in bookings and idx < len(bookings[chat_id]):
            removed = bookings[chat_id].pop(idx)
            bot.answer_callback_query(call.id, f"Бронирование {removed['restaurant']} отменено ✅")

bot.polling(non_stop=True)