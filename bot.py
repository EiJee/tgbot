import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from db import init_db, add_product, remove_product, list_fridge, list_shopping, mark_as_bought
import os
from dotenv import load_dotenv

init_db()
load_dotenv()


bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))

user_state = {}

ALLOWED_USERS = {
    934625858,  # MatveevDmitry
    613878272,  # MatveevaOlga
}


def is_allowed(message):
    return message.chat.id in ALLOWED_USERS


@bot.message_handler(commands=['myid'])
def get_my_id(message):
    bot.send_message(message.chat.id, f"Ваш chat_id: {message.chat.id}")


def get_menu_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        KeyboardButton("➕ В холодильник"),
        KeyboardButton("🛒 В список покупок")
    )
    markup.row(
        KeyboardButton("📋 Показать холодильник"),
        KeyboardButton("🛍 Показать покупки")
    )
    markup.row(
        KeyboardButton("✅ Куплено"),
        KeyboardButton("❌ Удалить")
    )
    return markup


@bot.message_handler(commands=['start'])
def handle_start(message):
    if not is_allowed(message):
        bot.send_message(message.chat.id, "⛔️ У вас нет доступа к боту.")
        return

    bot.send_message(
        message.chat.id,
        f"👋 Привет, {message.from_user.first_name}! Это семейный холодильник 🧊\n"
        "Выбери действие:",
        reply_markup=get_menu_keyboard()
    )


@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip()
    state = user_state.get(chat_id)

    if text == "➕ В холодильник":
        user_state[chat_id] = "add_fridge"
        bot.send_message(chat_id, "🍎 Введи продукты через запятую:")
    elif text == "🛒 В список покупок":
        user_state[chat_id] = "add_buy"
        bot.send_message(chat_id, "🛍 Введи, что купить (через запятую):")
    elif text == "📋 Показать холодильник":
        items = list_fridge()
        msg = "🧊 В холодильнике:\n" + \
            "\n".join(
                f"• {i}" for i in items) if items else "🫙 Холодильник пуст."
        bot.send_message(chat_id, msg)
    elif text == "🛍 Показать покупки":
        items = list_shopping()
        if not items:
            bot.send_message(chat_id, "🧺 Список покупок пуст.")
            return
        for item in items:
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("✅ Куплено", callback_data=f"buy:{item}"),
                InlineKeyboardButton(
                    "🗑 Удалить", callback_data=f"delete:{item}")
            )
            bot.send_message(chat_id, f"🛒 {item}", reply_markup=markup)
    elif text == "✅ Куплено":
        user_state[chat_id] = "mark_bought"
        bot.send_message(chat_id, "✅ Напиши, что куплено:")
    elif text == "❌ Удалить":
        items = list_fridge()
        if not items:
            bot.send_message(chat_id, "🫙 Холодильник пуст, нечего удалять.")
            return
        markup = InlineKeyboardMarkup(row_width=1)
        for item in items:
            markup.add(InlineKeyboardButton(
                f"🗑 Удалить {item}", callback_data=f"delete_fridge:{item}"))
        bot.send_message(
            chat_id, "Выбери продукт для удаления из холодильника:", reply_markup=markup)
    else:
        # Обработка состояния
        if state in ("add_fridge", "add_buy"):
            products = [p.strip() for p in text.split(",") if p.strip()]
            added, existed = [], []

            for product in products:
                success = add_product(
                    product, in_fridge=(state == "add_fridge"))
                (added if success else existed).append(product)

            reply = ""
            if added:
                reply += f"✅ Добавлено: {', '.join(added)}\n"
            if existed:
                reply += f"⚠️ Уже есть: {', '.join(existed)}"
            bot.send_message(chat_id, reply.strip())
            user_state[chat_id] = None

        elif state == "mark_bought":
            if mark_as_bought(text):
                bot.send_message(
                    chat_id, f"✅ {text} куплен и добавлен в холодильник.")
            else:
                bot.send_message(chat_id, f"❌ {text} не найден в покупках.")
            user_state[chat_id] = None

        elif state == "remove":
            if remove_product(text):
                bot.send_message(chat_id, f"🗑 {text} удалён.")
            else:
                bot.send_message(chat_id, f"❌ {text} не найден.")
            user_state[chat_id] = None

        else:
            bot.send_message(chat_id, "❓ Пожалуйста, выбери действие из меню.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("buy:") or call.data.startswith("delete:"))
def handle_buy_or_delete(call):
    chat_id = call.message.chat.id
    if chat_id not in ALLOWED_USERS:
        bot.answer_callback_query(call.id, "⛔️ Доступ запрещён.")
        return

    action, product = call.data.split(":", 1)

    if action == "buy":
        if mark_as_bought(product):
            bot.answer_callback_query(
                call.id, f"{product} добавлен в холодильник.")
            bot.edit_message_text(
                f"✅ {product} куплен и в холодильнике.", chat_id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, f"{product} не найден.")
    elif action == "delete":
        if remove_product(product):
            bot.answer_callback_query(call.id, f"{product} удалён.")
            bot.edit_message_text(
                f"🗑 {product} удалён из списка.", chat_id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, f"{product} не найден.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_fridge:"))
def handle_delete_fridge(call):
    chat_id = call.message.chat.id
    product = call.data.split("delete_fridge:", 1)[1]

    if remove_product(product):
        bot.answer_callback_query(
            call.id, f"🗑 {product} удалён из холодильника.")
        # Обновляем список кнопок после удаления
        items = list_fridge()
        if not items:
            bot.edit_message_text("🫙 Холодильник пуст.",
                                  chat_id, call.message.message_id)
            return
        markup = InlineKeyboardMarkup(row_width=1)
        for item in items:
            markup.add(InlineKeyboardButton(
                f"🗑 Удалить {item}", callback_data=f"delete_fridge:{item}"))
        bot.edit_message_text("Выбери продукт для удаления из холодильника:",
                              chat_id, call.message.message_id, reply_markup=markup)
    else:
        bot.answer_callback_query(
            call.id, f"❌ {product} не найден в холодильнике.")


bot.polling(none_stop=True)
