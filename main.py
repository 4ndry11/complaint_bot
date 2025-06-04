from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
import requests
from datetime import datetime, timedelta
import os
from telegram import Bot

# Налаштування
BITRIX_URL = os.environ.get("BITRIX_WEBHOOK_URL")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
RESPONSIBLE_ID = 596

# Етапи діалогу
(SELECTING_DEPARTMENT, ENTER_EMPLOYEE_NAME, ENTER_CLIENT_NAME,
 ENTER_CONTACT_METHOD, ENTER_COMPLAINT) = range(5)

# Відділи
departments = [
    "Юридичний відділ",
    "Відділ піклування (Підтримка)",
    "Служба антиколекторської пдтримки",
    "Відділ досудового врегулювання боргів",
    "Консультаційний відділ (Помічник Юриста)"
]

# Тимчасове сховище
user_data_temp = {}

# Показати кнопку «Залишити нову скаргу»
def show_main_button(update: Update):
    keyboard = [["📝 Залишити скаргу"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text(
        "Оберіть дію:",
        reply_markup=reply_markup
    )

# Команда /start
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Це офіційний бот компанії «Звільнимо». Тут ви можете залишити скаргу."
    )
    show_main_button(update)

# Початок скарги
def new_complaint(update: Update, context: CallbackContext):
    keyboard = [[d] for d in departments]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text("Будь ласка, оберіть відділ, на який ви хочете залишити скаргу:", reply_markup=reply_markup)
    return SELECTING_DEPARTMENT

def handle_department(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    username = update.effective_user.username or "Невідомо"
    user_data_temp[chat_id] = {
        "department": update.message.text,
        "telegram_username": f"@{username}" if username != "Невідомо" else "Немає username"
    }
    update.message.reply_text("👤Введіть ПІБ співробітника, на якого ви хочете залишити скаргу:")
    return ENTER_EMPLOYEE_NAME

def handle_employee_name(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_data_temp[chat_id]["employee_name"] = update.message.text
    update.message.reply_text("🙂Введіть ваше ПІБ:")
    return ENTER_CLIENT_NAME

def handle_client_name(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_data_temp[chat_id]["client_name"] = update.message.text
    update.message.reply_text("☎️Як вам зручно отримати зворотній зв’язок? (Телефон, Telegram, Email):")
    return ENTER_CONTACT_METHOD

def handle_contact_method(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_data_temp[chat_id]["contact_method"] = update.message.text
    update.message.reply_text("🎤Опишіть, будь ласка, вашу скаргу:")
    return ENTER_COMPLAINT

def handle_complaint(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_data_temp[chat_id]["complaint_text"] = update.message.text
    data = user_data_temp[chat_id]

    task_title = f"Скарга на {data['department']}"
    task_description = (
        f"📌 Суть скарги:\n{data['complaint_text']}\n\n"
        f"👤 Співробітник: {data['employee_name']}\n"
        f"🙍‍♂️ Клієнт: {data['client_name']}\n"
        f"📬 Зв’язок: {data['contact_method']}\n"
        f"🔗 Telegram Username: {data['telegram_username']}"
    )

    now = datetime.now()
    deadline = now + timedelta(days=1)
    deadline_str = deadline.strftime("%Y-%m-%dT%H:%M:%S+03:00")

    payload = {
        "fields": {
            "TITLE": task_title,
            "DESCRIPTION": task_description,
            "RESPONSIBLE_ID": RESPONSIBLE_ID,
            "DEADLINE": deadline_str
        },
        "notify": True
    }

    response = requests.post(BITRIX_URL, json=payload)
    if response.status_code == 200 and "result" in response.json():
        update.message.reply_text('Ваша скарга прийнята та вже передана на опрацювання нашій команді.✅\nМи зробимо все можливе, щоб знайти рішення якнайшвидше.🔍\nДякуємо за вашу довіру, очікуйте зворотного зв\'язку.❤️⏳ ')
    else:
        update.message.reply_text("❌ Помилка при створенні задачі.")

    user_data_temp.pop(chat_id, None)
    show_main_button(update)
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("Операцію скасовано.")
    show_main_button(update)
    return ConversationHandler.END

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex("^(📝 Залишити скаргу)$"), new_complaint)],
        states={
            SELECTING_DEPARTMENT: [MessageHandler(Filters.text & ~Filters.command, handle_department)],
            ENTER_EMPLOYEE_NAME: [MessageHandler(Filters.text & ~Filters.command, handle_employee_name)],
            ENTER_CLIENT_NAME: [MessageHandler(Filters.text & ~Filters.command, handle_client_name)],
            ENTER_CONTACT_METHOD: [MessageHandler(Filters.text & ~Filters.command, handle_contact_method)],
            ENTER_COMPLAINT: [MessageHandler(Filters.text & ~Filters.command, handle_complaint)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
