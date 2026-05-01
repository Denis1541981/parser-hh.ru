import sqlite3
from settings.setting import DB_PATH


class SqliteDB:
    def __init__(self, db_name=DB_PATH):

        self.db = sqlite3.connect(db_name)
        self.db.row_factory = sqlite3.Row

    def create_db(self):
        with self.db as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vacancies (
                    id_vacancies TEXT PRIMARY KEY,
                    title TEXT,
                    salary INTEGER,
                    employer TEXT,
                    employer_address TEXT,
                    description TEXT,
                    rating REAL,
                    link TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_salary ON vacancies(salary)")

    def insert_vacancy(self, data):
        with self.db as conn:
            conn.execute("""
                INSERT OR IGNORE INTO vacancies (
                    id_vacancies, title, salary, employer,
                    employer_address, description, rating, link
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, data)

    def insert_many(self, data_list):
        with self.db as conn:
            conn.executemany("""
                INSERT OR IGNORE INTO vacancies (
                    id_vacancies, title, salary, employer,
                    employer_address, description, rating, link
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, data_list)

    def exists(self, vacancy_id):
        with self.db as conn:
            cursor = conn.execute(
                "SELECT 1 FROM vacancies WHERE id_vacancies=?",
                (vacancy_id,)
            )
            return cursor.fetchone() is not None

    def all_execute(self):
        with self.db as conn:
            return conn.execute("SELECT * FROM vacancies").fetchall()

    def get_all_ids(self):
        with self.db as conn:
            rows = conn.execute("SELECT id_vacancies FROM vacancies").fetchall()
            return {row[0] for row in rows}


    def close(self):
        self.db.close()