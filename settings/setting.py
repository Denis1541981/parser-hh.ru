from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
LOG_PATH = BASE_DIR / 'TEMP' / 'hh_ru.log'
DB_PATH = BASE_DIR / 'data' / 'vacancies.db'
USER_DB = BASE_DIR / 'data' / 'user.db'
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
USER_DB.parent.mkdir(parents=True, exist_ok=True)

