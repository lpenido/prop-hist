import logging

# Create a custom logger
logger = logging.getLogger("scraper_log")
logger.setLevel(logging.DEBUG)

# Stream
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
chformatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
ch.setFormatter(chformatter)
logger.addHandler(ch)

# File
fh = logging.FileHandler(filename='./logs/scraper.log')
fh.setLevel(logging.DEBUG)
fhformatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(fhformatter)
logger.addHandler(fh)