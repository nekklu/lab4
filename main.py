import telebot
from telebot import types
import requests

BOT_TOKEN = '8244664004:AAFV8MlCk32KOsWQzMqIc-MXDVeSXtLBKFg'

API_URL = 'http://openlibrary.org/search.json'
COVERS_URL = 'https://covers.openlibrary.org/b/id'

bot = telebot.TeleBot(BOT_TOKEN)


user_wishlist = {}


users_cache = {}


@bot.message_handler(commands=['start'])
def start_cmd(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("🔍 Найти книгу")
    btn2 = types.KeyboardButton("🏷 Выбрать жанр")
    btn3 = types.KeyboardButton("❤️ Список желаний")
    
    markup.add(btn1, btn2)
    markup.add(btn3)
    
    bot.send_message(message.chat.id, "Привет! Я помогу найти и сохранить книги.", reply_markup=markup)



@bot.message_handler(func=lambda message: message.text == "❤️ Список желаний")
def show_wishlist(message):
    chat_id = message.chat.id
    saved_books = user_wishlist.get(chat_id, [])
    
    if not saved_books:
        bot.send_message(chat_id, "Ваш список желаний пуст.")
        return


    text = "📚 **Хочу прочитать:**\n\n"
    for i, book in enumerate(saved_books, 1):
        text += f"{i}. {book}\n"
        
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🗑 Очистить список", callback_data="clear_wishlist"))
    
    bot.send_message(chat_id, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "clear_wishlist")
def clear_list(call):
    user_wishlist[call.message.chat.id] = []
    bot.answer_callback_query(call.id, "Список очищен")
    bot.edit_message_text("Список желаний пуст.", call.message.chat.id, call.message.message_id)


@bot.message_handler(func=lambda message: message.text == "🏷 Выбрать жанр")
def genres_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Фантастика", callback_data="genre:science_fiction"),
        types.InlineKeyboardButton("Детектив", callback_data="genre:detective_and_mystery"),
        types.InlineKeyboardButton("Ужасы", callback_data="genre:horror"),
        types.InlineKeyboardButton("Романтика", callback_data="genre:romance")
    )
    bot.send_message(message.chat.id, "Выберите категорию:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("genre:"))
def callback_genre(call):
    genre = call.data.split(":")[1]
    bot.answer_callback_query(call.id, "Ищу книги...")
    
    params = {'subject': genre, 'limit': 3}
    get_books_data(call.message.chat.id, params)



@bot.message_handler(func=lambda message: message.text == "🔍 Найти книгу")
def search_start(message):
    msg = bot.send_message(message.chat.id, "Введите название или автора:")
    bot.register_next_step_handler(msg, perform_search)

def perform_search(message):
    if not message.text: return
    params = {'q': message.text, 'limit': 3}
    get_books_data(message.chat.id, params)


@bot.callback_query_handler(func=lambda call: call.data.startswith("save:"))
def save_book_handler(call):
    chat_id = call.message.chat.id
    # Получаем индекс книги из кнопки (save:0, save:1...)
    index = int(call.data.split(":")[1])
    
    # Достаем книгу из временного кэша
    cached_books = users_cache.get(chat_id, [])
    
    if index < len(cached_books):
        book_info = cached_books[index]
        book_str = f"{book_info['title']} - {book_info['author']}"
        
        # Создаем список, если его нет
        if chat_id not in user_wishlist:
            user_wishlist[chat_id] = []
            
        if book_str not in user_wishlist[chat_id]:
            user_wishlist[chat_id].append(book_str)
            bot.answer_callback_query(call.id, "✅ Добавлено!")
        else:
            bot.answer_callback_query(call.id, "⚠️ Уже есть в списке")
    else:
        bot.answer_callback_query(call.id, "Ошибка: поиск устарел")


def get_books_data(chat_id, params):
    try:
        response = requests.get(API_URL, params=params, timeout=10)
        data = response.json()
        
        if not data.get('docs'):
            bot.send_message(chat_id, "Ничего не найдено.")
            return

        # Очищаем кэш пользователя перед новым поиском
        users_cache[chat_id] = []

        # Перебираем результаты
        for i, doc in enumerate(data['docs']):
            title = doc.get('title', 'Без названия')
            authors = ", ".join(doc.get('author_name', ['Неизвестно']))
            year = doc.get('first_publish_year', '---')
            
            # Сохраняем во временный список (чтобы потом добавить в вишлист)
            users_cache[chat_id].append({'title': title, 'author': authors})
            
            text = (f"📖 *{title}*\n"
                    f"👤 Автор: {authors}\n"
                    f"📅 Год: {year}")

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("❤️ В список желаний", callback_data=f"save:{i}"))

            cover_id = doc.get('cover_i')
            if cover_id:
                img_url = f"{COVERS_URL}/{cover_id}-M.jpg"
                bot.send_photo(chat_id, img_url, caption=text, parse_mode='Markdown', reply_markup=markup)
            else:
                bot.send_message(chat_id, text, parse_mode='Markdown', reply_markup=markup)

    except Exception as e:
        bot.send_message(chat_id, "Ошибка поиска.")
        print(f"Error: {e}")

if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()