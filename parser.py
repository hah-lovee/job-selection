import os
import psycopg2
import requests
import sys
import re
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')
POSTGRES_URL = "postgresql://user:password@db:5432/postgres"

def create_database():
    try:
        conn = psycopg2.connect(POSTGRES_URL)
        conn.autocommit = True
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = 'vacancies_db'")
        exists = cursor.fetchone()
        if not exists:
            cursor.execute('CREATE DATABASE vacancies_db')

        cursor.close()
        conn.close()
    except psycopg2.Error as e:
        print(f"Error creating database: {e}")

def create_table():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS vacancies (
            id SERIAL PRIMARY KEY,
            vacancy_id TEXT,
            name TEXT,
            employer_name TEXT,
            experience TEXT,
            salary_from INTEGER,
            salary_to INTEGER,
            currency TEXT,
            city TEXT,
            schedule TEXT,
            published_at TIMESTAMP
        )
        ''')

        cursor.close()
        conn.close()
    except psycopg2.Error as e:
        print(f"Error creating table: {e}")

def fetch_vacancies(title, salary, experience, city, schedule):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cursor = conn.cursor()

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

        salary_from, salary_to = re.findall(r'\d+', salary)
        params = {
            'text': title,
            'salary': (int(salary_from) + int(salary_to)) // 2,
            'experience': experience_id,
            'area': city,
            'schedule': schedule_id,
            'per_page': 5
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            vacancies = response.json().get('items', [])

            for vacancy in vacancies:
                vacancy_id = vacancy.get('id')
                name = vacancy.get('name')
                employer_name = vacancy.get('employer', {}).get('name')
                experience = vacancy.get('experience', {}).get('name')
                salary_from = vacancy.get('salary', {}).get('from')
                salary_to = vacancy.get('salary', {}).get('to')
                currency = vacancy.get('salary', {}).get('currency')
                city = vacancy.get('area', {}).get('name')
                schedule = vacancy.get('schedule', {}).get('name')
                published_at = vacancy.get('published_at')

                cursor.execute('''
                    INSERT INTO vacancies (vacancy_id, name, employer_name, experience, salary_from, salary_to, currency, city, schedule, published_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (vacancy_id, name, employer_name, experience, salary_from, salary_to, currency, city, schedule, published_at))

            print("Data successfully inserted into PostgreSQL")
        else:
            print(f"Failed to fetch data from API. Status code: {response.status_code}")

    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL: {e}")

    finally:
        if 'conn' in locals():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("Usage: python parser.py <title> <salary> <experience> <city> <schedule>")
        sys.exit(1)

    title = sys.argv[1]
    salary = sys.argv[2]
    experience = sys.argv[3]
    city = sys.argv[4]
    schedule = sys.argv[5]

    create_database()
    create_table()
    fetch_vacancies(title, salary, experience, city, schedule)
