#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import time

import requests
from bs4 import BeautifulSoup
from logger.logger import logger
from db import SqliteDB


db = SqliteDB()
db.create_db()

def get_request(url="https://berdsk.hh.ru/search/vacancy?resume=86dd64cbff0f11cc130039ed1f625967623934&from=resumelist&area=1204&search_field=name&search_field=company_name&search_field=description&enable_snippets=true&forceFiltersSaving=true&L_save_area=true"):
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(f"[+] Status code: {response.status_code}")
        with open("html.html", "wb") as f:
            f.write(response.content)
        return response.text
    except requests.exceptions.HTTPError as e:
        logger.error(f"Ошибка запроса: {e}")


def convert_solary(s):
    if not s or "Нет" in s:
        return 0
    nums = re.findall(r'\d+', s)
    return int(nums[0]) if nums else 0


def get_id(s):
    if not s or 'Нет id' in s:
        return 0
    pattern = re.compile(r"\d+")
    nums = pattern.search(s).group()
    return nums if nums else 0

def get_page(s):
    pattern = re.compile(r'page=(\d+)')
    page = re.findall(pattern, s)
    return int(page[0]) if page else 0


def get_parse(html, all_vacancies=None, max_page=2):
    if all_vacancies is None:
        all_vacancies = []
    existing_ids = db.get_all_ids()
    soup = BeautifulSoup(html, "lxml")
    for el in soup.find_all("div", class_="magritte-redesign"):
        title = el.find("span", attrs={"data-qa": "serp-item__title-text"}).text.strip()
        salary = convert_solary(el.find("span", class_="magritte-text___pbpft_5-0-1 magritte-text_style-primary___AQ7MW_5-0-1 magritte-text_typography-label-1-regular___pi3R-_5-0-1").text.replace("\u202f", "").replace("\xa0", " ").replace('₽', '').strip() if el.find("span", class_="magritte-text___pbpft_5-0-1 magritte-text_style-primary___AQ7MW_5-0-1 magritte-text_typography-label-1-regular___pi3R-_5-0-1") else "Нет оклада")
        employer = el.find("span", attrs={"data-qa": "vacancy-serp__vacancy-employer-text"}).text.replace("\xa0", " ").strip()
        employer_address = el.find("span", attrs={"data-qa": "vacancy-serp__vacancy-address"}).text.strip()
        description = el.find("div", attrs={"data-qa": "vacancy-serp__vacancy_snippet_responsibility"}).text.strip() if el.find("div", attrs={"data-qa": "vacancy-serp__vacancy_snippet_responsibility"}) else "Нет описания"
        rating = float(el.find("span", attrs={"data-qa": "company-review-rating-value"}).text.strip()) if el.find("span", attrs={"data-qa": "company-review-rating-value"}) else 0
        link = el.find("a", attrs={"data-qa": "serp-item__title"}).get("href")
        id_vacancies = get_id(el.find("a", attrs={"data-qa": "serp-item__title"}).get("href") if el.find("a", attrs={"data-qa": "serp-item__title"}).get("href") else 0)
        if id_vacancies not in existing_ids:
            item = (
                id_vacancies,
                title,
                salary,
                employer,
                employer_address,
                description,
                rating,
                link
            )
            all_vacancies.append(item)

    next_page = soup.find("a", attrs={"data-qa": "pager-next"})
    if next_page and get_page(next_page.get("href")) <= max_page:
        next_url = "https://berdsk.hh.ru" + next_page.get("href")
        logger.info(f"Парсим страницу №{get_page(next_url)}")
        time.sleep(2)
        return get_parse(get_request(next_url), all_vacancies)
    count = len(all_vacancies)
    logger.info(f"+ {count} {plural(count, 'вакансия', 'вакансии', 'вакансий')}")
    return all_vacancies

def plural(n, one, few, many):
    """Функция склонения"""
    n = abs(n) % 100
    n1 = n % 10
    if 10 < n < 20:
        return many
    if 1 < n1 < 5:
        return few
    if n1 == 1:
        return one
    return many


def get_update_message(lst: list):
    if not lst:
        return "Нет новых вакансий"

    messages = []

    for el in lst:
        id_vac, title, salary, company, address, description, rating, link = el

        salary = salary or "Не указана"
        rating = rating or "Нет оценки"
        description = (description[:150] + "...") if description else "Нет описания"

        message = (
            f"📌 {title}\n"
            f"💰 Зарплата: {salary}\n"
            f"🏢 Компания: {company}\n"
            f"📍 Адрес: {address}\n"
            f"⭐ Рейтинг: {rating}\n"
            f"📝 {description}\n"
            f"🔗 {link}\n"
        )
        messages.append(message)
    return "\n\n".join(messages)



if __name__ == "__main__":
    vacancies = get_parse(get_request(), max_page=1)
    if len(vacancies) > 0:
        db.insert_many(vacancies)
        db.close()
        message = get_update_message(vacancies)
        print(message)




