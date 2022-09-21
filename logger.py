import logging
import time

class IterLog:
    def __init__(self):
        self.logger = logging.getLogger(time.strftime('%Y%m%d', time.gmtime()))
        self.logger.setLevel(logging.DEBUG)
        hdlr = logging.FileHandler('Summary.log')
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        self.logger.addHandler(hdlr)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
    
    def info(self, msg):
        self.logger.info(msg)
