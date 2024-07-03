import logging
import requests
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
from dotenv import load_dotenv
import os

# Загрузить переменные окружения из .env файла
load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Определяем состояния для нашего разговора
TITLE, SALARY, EXPERIENCE = range(3)

# Настраиваем журналирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        'Привет! Я бот по подбору вакансий на hh.ru.\n'
        'Я могу помочь вам найти работу по заданным критериям.\n'
        'Используйте команду /job_selection, чтобы начать подбор вакансий.'
    )

def job_selection(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Пожалуйста, отправь мне название вакансии, которую ты ищешь.')
    return TITLE

def title(update: Update, context: CallbackContext) -> int:
    context.user_data['title'] = update.message.text.strip()
    update.message.reply_text('Теперь укажи диапазон заработной платы (например, от 50000 до 100000)')
    return SALARY

def salary(update: Update, context: CallbackContext) -> int:
    salary_text = update.message.text.strip()
    if not salary_text.isdigit() or int(salary_text) <= 0:
        update.message.reply_text('Пожалуйста, введи положительное число для заработной платы.')
        return SALARY
    context.user_data['salary'] = salary_text
    reply_keyboard = [['Нет опыта', 'От 1 года до 3 лет'], ['От 3 до 5 лет', 'Более 5 лет']]
    update.message.reply_text(
        'Выбери диапазон опыта работы:',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return EXPERIENCE

def experience(update: Update, context: CallbackContext) -> int:
    experience_text = update.message.text.strip()
    valid_experiences = ["Нет опыта", "От 1 года до 3 лет", "От 3 до 5 лет", "Более 5 лет"]

    if experience_text in valid_experiences:
        context.user_data['experience'] = experience_text
        title = context.user_data['title']
        salary = context.user_data['salary']
        experience = context.user_data['experience']
        
        # Выполняем поиск вакансий с использованием переданных параметров
        vacancies = fetch_vacancies(title, salary, experience)
        if vacancies:
            response_text = "Вот несколько найденных вакансий:\n\n" + "\n\n".join(vacancies)
        else:
            response_text = "К сожалению, вакансий по заданным критериям не найдено."
        
        update.message.reply_text(response_text, reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END
    else:
        update.message.reply_text(
            "Пожалуйста, выбери один из предложенных вариантов для опыта работы."
        )
        return EXPERIENCE

def fetch_vacancies(title, salary, experience):
    url = 'https://api.hh.ru/vacancies'
    headers = {'User-Agent': 'YourAppName/1.0'}
    experience_mapping = {
        "Нет опыта": "noExperience",
        "От 1 года до 3 лет": "between1And3",
        "От 3 до 5 лет": "between3And6",
        "Более 5 лет": "moreThan6"
    }
    experience_id = experience_mapping.get(experience, "noExperience")

    params = {
        'text': title,
        'salary': salary,
        'experience': experience_id,
        'per_page': 5
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        vacancies = response.json().get('items', [])
        vacancy_list = []
        for i, vacancy in enumerate(vacancies, start=1):
            name = vacancy.get('name')
            employer = vacancy.get('employer', {}).get('name')
            salary = vacancy.get('salary')
            if salary:
                salary_from = salary.get('from')
                salary_to = salary.get('to')
                currency = salary.get('currency')
                salary_info = f"{salary_from} - {salary_to} {currency}" if salary_from and salary_to else "Не указана"
            else:
                salary_info = "Не указана"
            url = vacancy.get('alternate_url')
            vacancy_list.append(f"{i}. *{name}* в *{employer}*\n   Зарплата: {salary_info}\n   [Ссылка на вакансию]({url})")
        return vacancy_list
    else:
        logger.error(f"Failed to fetch data from API. Status code: {response.status_code}")
        return []

def main():
    updater = Updater(TOKEN, use_context=True)

    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('job_selection', job_selection)],
        states={
            TITLE: [MessageHandler(Filters.text & ~Filters.command, title)],
            SALARY: [MessageHandler(Filters.text & ~Filters.command, salary)],
            EXPERIENCE: [MessageHandler(Filters.text & ~Filters.command, experience)],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler('start', start))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
