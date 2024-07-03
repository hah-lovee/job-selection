import logging
import requests
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# Определяем состояния для нашего разговора
TITLE, SALARY, EXPERIENCE, CITY, SCHEDULE = range(5)

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
        update.message.reply_text('Укажи город, в котором ты ищешь работу.')
        return CITY
    else:
        update.message.reply_text(
            "Пожалуйста, выбери один из предложенных вариантов для опыта работы."
        )
        return EXPERIENCE

def city(update: Update, context: CallbackContext) -> int:
    context.user_data['city'] = update.message.text.strip()
    reply_keyboard = [['Полный рабочий день', 'Сменный график'], ['Гибкий график', 'Удаленная работа']]
    update.message.reply_text(
        'Выбери график работы:',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return SCHEDULE

def schedule(update: Update, context: CallbackContext) -> int:
    schedule_text = update.message.text.strip()
    valid_schedules = ["Полный рабочий день", "Сменный график", "Гибкий график", "Удаленная работа"]

    if schedule_text in valid_schedules:
        context.user_data['schedule'] = schedule_text
        title = context.user_data['title']
        salary = context.user_data['salary']
        experience = context.user_data['experience']
        city = context.user_data['city']
        schedule = context.user_data['schedule']
        
        # Выполняем поиск вакансий с использованием переданных параметров
        vacancies = fetch_vacancies(title, salary, experience, city, schedule)
        if vacancies:
            response_text = "Вот несколько найденных вакансий:\n\n" + "\n".join(vacancies)
        else:
            response_text = "К сожалению, вакансий по заданным критериям не найдено."
        
        update.message.reply_text(response_text, reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    else:
        update.message.reply_text(
            "Пожалуйста, выбери один из предложенных вариантов для графика работы."
        )
        return SCHEDULE

def get_city_id(city_name):
    url = 'https://api.hh.ru/suggests/areas'
    params = {'text': city_name}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        areas = response.json().get('items', [])
        if areas:
            return areas[0].get('id')
    return None

def fetch_vacancies(title, salary, experience, city, schedule):
    url = 'https://api.hh.ru/vacancies'
    headers = {'User-Agent': 'YourAppName/1.0'}
    experience_mapping = {
        "Нет опыта": "noExperience",
        "От 1 года до 3 лет": "between1And3",
        "От 3 до 5 лет": "between3And6",
        "Более 5 лет": "moreThan6"
    }
    schedule_mapping = {
        "Полный рабочий день": "fullDay",
        "Сменный график": "shift",
        "Гибкий график": "flexible",
        "Удаленная работа": "remote"
    }
    experience_id = experience_mapping.get(experience, "noExperience")
    schedule_id = schedule_mapping.get(schedule, "fullDay")
    city_id = get_city_id(city)

    if not city_id:
        logger.error(f"City '{city}' not found")
        return []

    params = {
        'text': title,
        'salary': salary,
        'experience': experience_id,
        'area': city_id,
        'schedule': schedule_id,
        'per_page': 5
    }

    logger.info(f"Fetching vacancies with params: {params}")
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        vacancies = response.json().get('items', [])
        logger.info(f"API response: {response.json()}")
        
        vacancy_list = []
        for idx, vacancy in enumerate(vacancies, start=1):
            name = vacancy.get('name')
            employer = vacancy.get('employer', {}).get('name')
            salary = vacancy.get('salary')
            if salary:
                salary_from = salary.get('from')
                salary_to = salary.get('to')
                currency = salary.get('currency')
                salary_info = f"{salary_from} - {salary_to} {currency}"
            else:
                salary_info = "Не указана"
            city = vacancy.get('area', {}).get('name')
            schedule = vacancy.get('schedule', {}).get('name')
            url = vacancy.get('alternate_url')
            vacancy_list.append(f"{idx}. [{name} в {employer} с зарплатой {salary_info} в {city} ({schedule})]({url})")
        return vacancy_list
    else:
        logger.error(f"Failed to fetch data from API. Status code: {response.status_code}, Response: {response.text}")
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
            CITY: [MessageHandler(Filters.text & ~Filters.command, city)],
            SCHEDULE: [MessageHandler(Filters.text & ~Filters.command, schedule)],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler('start', start))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
