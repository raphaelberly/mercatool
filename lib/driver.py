from contextlib import contextmanager
from time import sleep

import docker
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.chrome.options import Options


@contextmanager
def run_driver(docker_image, driver_lang='en', driver_size=None):

    print('Starting docker container...')
    client = docker.from_env()
    container = client.containers.run(docker_image, detach=True, ports={'4444/tcp': 4444})

    try:
        print('Starting driver...')
        sleep(12)  # TODO: REPLACE THIS WITH: WHILE... TRY...
        chrome_options = Options()
        chrome_options.add_argument(f'--lang={driver_lang}')
        chrome_options.add_experimental_option('prefs', {'intl.accept_languages': driver_lang})
        if driver_size:
            chrome_options.add_argument('--window-size={0},{1}'.format(*driver_size))
        yield webdriver.Remote('http://localhost:4444/wd/hub', DesiredCapabilities.CHROME,
                               options=chrome_options)

    finally:
        print('Stopping driver and docker container...')
        container.stop()
        container.remove()
