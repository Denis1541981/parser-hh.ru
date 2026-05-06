import asyncio
import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import (KeyboardButton, Message,
                           ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram import F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv, find_dotenv

from app import *
from settings.setting import USER_DB, DB_PATH

load_dotenv(find_dotenv('.env'))
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN not found in .env file")

db.create_db()
PROXY_URL = os.getenv("PROXY_URL")


session = AiohttpSession(proxy=PROXY_URL)
bot = Bot(token=TOKEN, session=session)

dp = Dispatcher()
db = SqliteDB()
# Инициализация SQLite
def init_db():
    with sqlite3.connect(USER_DB, check_same_thread=False) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS subscribers (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                subscribed_at TEXT
            )
        ''')
        conn.commit()

init_db()

def get_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/help"), KeyboardButton(text="/subscribe")],
            [KeyboardButton(text="/unsubscribe"), KeyboardButton(text="/filter")],
        ],
        resize_keyboard=True
    )


# Обработчики команд
@dp.message(CommandStart())
async def process_start_command(message: Message):
    logger.info(f"User {message.from_user.id} started the bot")
    await message.answer(
        'Привет! Я бот для отслеживания вакансий с HH.ru.\n'
        'Используй /subscribe чтобы подписаться на новые вакансии.\n'
        'Используй /latest чтобы получить последние вакансии.\n'
        'Полный список команд: /help',
        reply_markup=get_main_keyboard()
    )


@dp.message(Command(commands='help'))
async def process_help_command(message: Message):
    await message.answer(
        '📌 Доступные команды:\n'
        '/start - запустить бота\n'
        '/help - список команд\n'
        '/subscribe - подписаться на рассылку\n'
        '/unsubscribe - отписаться от рассылки\n'
        '/filter - некоторая статистика с сайта\n',
        reply_markup=get_main_keyboard()
    )


@dp.message(Command(commands='subscribe'))
async def subscribe_user(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)

    with sqlite3.connect(USER_DB) as conn:
        cursor = conn.cursor()
        # Проверяем, не подписан ли уже пользователь
        cursor.execute('SELECT 1 FROM subscribers WHERE user_id = ?', (user_id,))
        if cursor.fetchone():
            await message.answer("Вы уже подписаны на рассылку вакансий.")
            return

        # Добавляем нового подписчика
        cursor.execute(
            'INSERT INTO subscribers (user_id, username, subscribed_at) VALUES (?, ?, ?)',
            (user_id, username, datetime.now().isoformat())
        )
        conn.commit()

    await message.answer(
        "✅ Вы успешно подписались на рассылку новых вакансий!\n",
        reply_markup=get_main_keyboard()
    )
    logger.info(f"[+] User {user_id} subscribed to vacancies")


@dp.message(Command(commands='unsubscribe'))
async def unsubscribe_user(message: Message):
    user_id = message.from_user.id

    with sqlite3.connect(USER_DB) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM subscribers WHERE user_id = ?', (user_id,))
        conn.commit()

    if cursor.rowcount > 0:
        await message.answer(
            "Вы отписались от рассылки вакансий.",
            reply_markup=get_main_keyboard()
        )
        logger.info(f"[-] User {user_id} unsubscribed from vacancies")
    else:
        await message.answer("Вы не были подписаны на рассылку.")


@dp.message(Command("filter"))
async def filters(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 Топ по зарплате", callback_data="top_salary"),
                InlineKeyboardButton(text="🏢 Топ компании", callback_data="top_company"),
            ],
            [
                InlineKeyboardButton(text="📊 Топ вакансии", callback_data="top_vacancy"),
            ],
            [
                InlineKeyboardButton(text="🔎 Поиск по должности", callback_data="search_vacancy")
            ]
        ]
    )

    await message.answer("Выбери фильтр:", reply_markup=keyboard)


@dp.callback_query(F.data == "top_salary")
async def top_salary(callback: CallbackQuery):
    result = db.get_top_salary()

    if not result:
        await callback.message.answer("Нет данных по зарплатам")
        await callback.answer()
        return

    text = "💰 Топ 5 вакансий по зарплате:\n\n"

    for i, row in enumerate(result, start=1):
        title, employer, salary = row
        text += f"{i}. {title}\n🏢 {employer}\n💵 {salary}\n\n"

    await callback.message.answer(text)
    await callback.answer()



@dp.callback_query(F.data == "top_company")
async def top_company(callback: CallbackQuery):
    result = db.get_top_company()
    text = "🏢 Топ компаний по количеству вакансий:\n\n"
    for i, (employer, count) in enumerate(result, start=1):
        text += f"{i}. {employer} — {count} вакансий\n"
    await callback.message.answer(text)
    await callback.answer()


@dp.callback_query(F.data == "top_vacancy")
async def top_vacancy(callback: CallbackQuery):
    result = db.get_top_vacancy()

    text = "📊 Топ вакансий (спрос + зарплата):\n\n"

    for i, (title, count, avg_salary) in enumerate(result, start=1):
        text += f"{i}. {title}\n📈 {count} шт | 💰 {int(avg_salary)}\n\n"

    await callback.message.answer(text)
    await callback.answer()


@dp.callback_query(F.data == "search_vacancy")
async def search_vacancy(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название вакансии (например: водитель):")
    await state.set_state("waiting_for_vacancy")
    await callback.answer()


@dp.message(F.text, StateFilter("waiting_for_vacancy"))
async def process_search(message: Message, state: FSMContext):
    query = message.text

    result = db.search_vacancy(query)

    if not result:
        await message.answer("Ничего не найдено 😢")
        await state.clear()
        return

    text = f"🔎 Результаты по запросу: {query}\n\n"

    for i, (title, employer, salary) in enumerate(result, start=1):
        text += f"{i}. {title}\n🏢 {employer}\n💵 {salary}\n\n"

    await message.answer(text)
    await state.clear()


def get_new_vacancies():
    vacancies = get_parse(get_request(), max_page=0)
    logger.info(f"[+] Got {len(vacancies)} new vacancies")
    if len(vacancies) > 0:
        db.insert_many(vacancies)
        return get_update_message(vacancies)
    return None


async def get_sleep(tz='Asia/Novosibirsk'):
    time_hour = datetime.now(tz=ZoneInfo(tz)).hour
    if 8 >= time_hour > 22:
        return 10 * 60 * 60
    return 60 * 60


async def check_new_vacancies():
    """Периодически проверяет новые вакансии и рассылает подписчикам"""
    while True:
        try:
            logger.info("Checking for new vacancies...")
            new_vacancies = get_new_vacancies()

            if new_vacancies and new_vacancies != "Нет новых вакансий":
                with sqlite3.connect(USER_DB) as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT user_id FROM subscribers')
                    subscribers = cursor.fetchall()

                for (user_id,) in subscribers:
                    try:
                        await bot.send_message(
                            user_id,
                            "Новые вакансии:\n" + new_vacancies,
                        )
                        await asyncio.sleep(0.1)
                    except Exception as e:
                        logger.error(f"Error sending to user {user_id}: {str(e)}")

            else:
                logger.info("No new vacancies")

            logger.info(f"Sleeping {await get_sleep()//60} minutes...")
            await asyncio.sleep(await get_sleep())

        except Exception as e:
            logger.error(f"Error in check_new_vacancies: {str(e)}")
            await asyncio.sleep(await get_sleep())


async def main():
    
    task = asyncio.create_task(check_new_vacancies())
    try:
        logger.info("Starting bot...")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        task.cancel()
        await session.close()
        db.close()



if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")