import sqlite3

from db import SqliteDB

db = sqlite3.connect('data/vacancies.db')
cursor = db.cursor()

vacancy = cursor.execute("""
    SELECT id_vacancies FROM vacancies LIMIT 10
""").fetchall()
print(vacancy[0][0])

bd_db = SqliteDB()

# bd_db.exists('115482755')
print(len(bd_db.get_all_ids()))



db.close()





