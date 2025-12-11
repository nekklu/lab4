import telebot
from telebot import types
import requests
import random
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
API_URL = os.getenv('API_URL')
COVERS_URL = os.getenv('COVERS_URL')

bot = telebot.TeleBot(BOT_TOKEN)

user_wishlist = {}
users_cache = {}



def show_wishlist(chat_id):
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

def show_genres(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Фантастика", callback_data="genre:science_fiction"),
        types.InlineKeyboardButton("Детектив", callback_data="genre:detective_and_mystery"),
        types.InlineKeyboardButton("Ужасы", callback_data="genre:horror"),
        types.InlineKeyboardButton("Романтика", callback_data="genre:romance")
    )
    bot.send_message(chat_id, "Выберите категорию:", reply_markup=markup)

def start_search(chat_id):
    msg = bot.send_message(chat_id, "Введите название книги или автора:")
    bot.register_next_step_handler(msg, perform_search)

def perform_search(message):
    if not message.text: return
    params = {'q': message.text, 'limit': 3}
    get_books_data(message.chat.id, params)


@bot.message_handler(commands=['start'])
def start_cmd(message):
    markup1 = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Найти книгу")
    btn2 = types.KeyboardButton("Выбрать жанр")
    btn3 = types.KeyboardButton("Список желаний")

    markup2 = types.InlineKeyboardMarkup()
    btn4 = types.InlineKeyboardButton("Найти книгу", callback_data="menu_search")
    btn5 = types.InlineKeyboardButton("Выбрать жанр", callback_data="menu_genre")
    btn6 = types.InlineKeyboardButton("Список желаний", callback_data="menu_wishlist")

    markup2.add(btn4, btn5)
    markup2.add(btn6)

    markup1.add(btn1, btn2)
    markup1.add(btn3)
    
    bot.send_message(message.chat.id, "Привет! Я помогу найти и сохранить книги.", reply_markup=markup1)

    bot.send_message(message.chat.id, "Или используй эти кнопки:", reply_markup=markup2)


@bot.message_handler(func=lambda message: message.text.lower() == "список желаний")
def handle_text_wishlist(message):
    show_wishlist(message.chat.id)

@bot.message_handler(func=lambda message: message.text.lower() == "выбрать жанр")
def handle_text_genres(message):
    show_genres(message.chat.id)

@bot.message_handler(func=lambda message: message.text.lower() == "найти книгу")
def handle_text_search(message):
    start_search(message.chat.id)



@bot.callback_query_handler(func=lambda call: call.data.startswith("menu_"))
def handle_menu_callbacks(call):
    bot.answer_callback_query(call.id)
    
    if call.data == "menu_search":
        start_search(call.message.chat.id)
        
    elif call.data == "menu_genre":
        show_genres(call.message.chat.id)
        
    elif call.data == "menu_wishlist":
        show_wishlist(call.message.chat.id)



@bot.callback_query_handler(func=lambda call: call.data == "clear_wishlist")
def clear_list(call):
    user_wishlist[call.message.chat.id] = []
    bot.answer_callback_query(call.id, "Список очищен")
    bot.edit_message_text("Список желаний пуст.", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("genre:"))
def callback_genre(call):
    genre = call.data.split(":")[1]
    bot.answer_callback_query(call.id, "Ищу что-нибудь интересное...")
    
    random_offset = random.randint(0, 50)
    params = {'subject': genre, 'limit': 3, 'offset': random_offset}
    
    get_books_data(call.message.chat.id, params)



@bot.callback_query_handler(func=lambda call: call.data.startswith("save:"))
def save_book_handler(call):
    chat_id = call.message.chat.id
    try:
        index = int(call.data.split(":")[1])
        cached_books = users_cache.get(chat_id, [])
        
        if index < len(cached_books):
            book_info = cached_books[index]
            book_str = f"{book_info['title']} - {book_info['author']}"
            
            if chat_id not in user_wishlist:
                user_wishlist[chat_id] = []
                
            if book_str not in user_wishlist[chat_id]:
                user_wishlist[chat_id].append(book_str)
                bot.answer_callback_query(call.id, "✅ Добавлено!")
            else:
                bot.answer_callback_query(call.id, "⚠️ Уже есть в списке")
        else:
            bot.answer_callback_query(call.id, "Ошибка: поиск устарел")
    except ValueError:
        pass


def get_books_data(chat_id, params):
    try:
        response = requests.get(API_URL, params=params, timeout=10)
        data = response.json()
        
        if not data.get('docs'):
            bot.send_message(chat_id, "Ничего не найдено.")
            return

        users_cache[chat_id] = []

        for i, doc in enumerate(data['docs']):
            title = doc.get('title', 'Без названия')
            authors = ", ".join(doc.get('author_name', ['Неизвестно']))
            year = doc.get('first_publish_year', '-')
            pages = doc.get('number_of_pages') or doc.get('number_of_pages_median') or '-'
            publisher = doc.get('publisher', '-')
            editions = doc.get('edition_count', '-')
            book_url = f"https://openlibrary.org{doc.get('key', '')}"                
            
            users_cache[chat_id].append({'title': title, 'author': authors})
            
            text = (f"📖 *{title}*\n"
                    f"👤 Автор: {authors}\n"
                    f"📅 Год: {year}\n"
                    f"Изданий: {editions}\n"
                    f"Кол-во страниц: {pages}\n"
                    f"Издатель: {publisher}\n"
                    f"Подробнее:{book_url}")

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


@bot.message_handler(func=lambda message: True)
def gag(message):
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("Найти книгу", callback_data="menu_search")
    btn2 = types.InlineKeyboardButton("Выбрать жанр", callback_data="menu_genre")
    btn3 = types.InlineKeyboardButton("Список желаний", callback_data="menu_wishlist")
    
    markup.add(btn1, btn2)
    markup.add(btn3)

    bot.send_message(message.chat.id, "Неизвестная команда. Выберите действие:", reply_markup=markup)


if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()