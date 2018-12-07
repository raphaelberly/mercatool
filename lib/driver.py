from contextlib import contextmanager
from time import sleep

import docker
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.chrome.options import Options


@contextmanager
def run_driver():

    print('Starting docker container...')
    client = docker.from_env()
    client.images.pull('selenium/standalone-chrome:3.141.59-copernicium')
    container = client.containers.run('selenium/standalone-chrome:3.141.59-copernicium',
                                      detach=True, ports={'4444/tcp': 4444})

    try:
        print('Starting driver...')
        sleep(6)  # TRY AND WAIT HERE INSTEAD OF WAIT
        chrome_options = Options()
        chrome_options.add_argument('--window-size=300,800')
        chrome_options.add_argument('--lang=en')
        chrome_options.add_experimental_option('prefs', {'intl.accept_languages': 'en'})
        yield webdriver.Remote('http://127.0.0.1:4444/wd/hub', DesiredCapabilities.CHROME,
                               options=chrome_options)

    finally:
        print('Stopping driver and docker container...')
        container.stop()
        container.remove()
