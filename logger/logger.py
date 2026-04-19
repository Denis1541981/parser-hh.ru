import logging

from settings.setting import LOG_PATH

logger = logging.getLogger()
logger.setLevel(logging.INFO)
strfmt = '[%(asctime)s] [%(name)s] [%(levelname)s] > %(message)s'
datefmt = '%Y-%m-%d %H:%M:%S'
Format = '%(threadName)s %(name)s %(levelname)s: %(message)s'

formatter = logging.Formatter(fmt=strfmt, datefmt=datefmt)

ch = logging.FileHandler(LOG_PATH, 'a', 'utf-8')
ch.setLevel(logging.INFO)

ch.setFormatter(formatter)
logger.addHandler(ch)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

if __name__=="__main__":
    logger.info("Start programm")
    logger.info("Finish")

