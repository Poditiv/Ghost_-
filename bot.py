import telebot
from telebot import types
from datetime import datetime, timedelta

TOKEN = "8129857175:AAHNOmBD_rv76-8kQfZL9v9JvhCM_ode7_o"
bot = telebot.TeleBot(TOKEN)

restaurants = {
    "Итальянский ресторан": ["18:00", "19:00", "20:00"],
    "Японский ресторан": ["17:30", "19:00", "20:30"],
    "Кафе на углу": ["12:00", "13:00", "14:00"]
}
bookings = {}
user_state = {}

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Забронировать столик", "Мои бронирования", "О боте")
    bot.send_message(message.chat.id, "Привет! Я помогу забронировать столик 🍽️", reply_markup=markup)
                     
@bot.message_handler(func=lambda message: True)
def menu(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if text == "О боте":
        bot.send_message(chat_id, "Этот бот демонстрирует бронирование столиков с выбором ресторана, даты и времени.")
    
    elif text == "Мои бронирования":
        user_bookings = bookings.get(chat_id, [])
        if not user_bookings:
            bot.send_message(chat_id, "У вас нет бронирований.")
        else:
            text = "Ваши бронирования:\n"
            for b in user_bookings:
                text += f"- {b['restaurant']} на {b['date']} в {b['time']}\n"
            bot.send_message(chat_id, text)
    
    elif text == "Забронировать столик":
        markup = types.InlineKeyboardMarkup()
        for r in restaurants.keys():
            markup.add(types.InlineKeyboardButton(r, callback_data=f"restaurant:{r}"))
        bot.send_message(chat_id, "Выберите ресторан:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    chat_id = call.message.chat.id
    data = call.data

    if data.startswith("restaurant:"):
        restaurant = data.split(":")[1]
        user_state[chat_id] = {"step": "date", "restaurant": restaurant}
        
        markup = types.InlineKeyboardMarkup()
        for i in range(3):
            date = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
            markup.add(types.InlineKeyboardButton(date, callback_data=f"date:{date}"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                              text=f"Вы выбрали {restaurant}. Теперь выберите дату:", reply_markup=markup)

    
    elif data.startswith("date:") and chat_id in user_state and user_state[chat_id]["step"] == "date":
        date = data.split(":")[1]
        user_state[chat_id]["date"] = date
        user_state[chat_id]["step"] = "time"

        restaurant = user_state[chat_id]["restaurant"]
        markup = types.InlineKeyboardMarkup()
        for t in restaurants[restaurant]:
            markup.add(types.InlineKeyboardButton(t, callback_data=f"time:{t}"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                              text=f"Выбрана дата {date}. Выберите время:", reply_markup=markup)

    
    elif data.startswith("time:") and chat_id in user_state and user_state[chat_id]["step"] == "time":
        time = data.split(":")[1]
        restaurant = user_state[chat_id]["restaurant"]
        date = user_state[chat_id]["date"]

        bookings.setdefault(chat_id, []).append({
            "restaurant": restaurant,
            "date": date,
            "time": time
        })

        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                              text=f"✅ Ваш столик в {restaurant} забронирован на {date} в {time}!")

        
        user_state.pop(chat_id, None)

bot.polling(non_stop=True)

