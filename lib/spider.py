# -*- coding: utf-8 -*-

import configparser
from time import sleep
from random import randint
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class Spider:

    def __init__(self, config_directory):
        # Set the config attributes
        self.config = configparser.ConfigParser()
        self.config.read(config_directory + '/credentials.ini')
        # Set chrome options
        self.chrome_options = Options()
        self.chrome_options.add_argument("--window-size=300,800")

    # START DRIVER
    def start_driver(self):
        print('Starting driver...')
        self.driver = webdriver.Chrome(chrome_options=self.chrome_options)
        sleep(4)

    # CLOSE DRIVER
    def close_driver(self):
        print('Closing driver...')
        self.driver.close()

    # GET A WEBPAGE
    def get_page(self, url):
        self.driver.get(url)
        sleep(randint(2, 3))
