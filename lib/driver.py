import logging
from contextlib import contextmanager
from time import sleep, time

import docker
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
from urllib3.exceptions import ProtocolError

LOGGER = logging.getLogger(__name__)

SLEEPING_TIME = 1


def _get_options(lang, *args):

    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument(f'--lang={lang}')
    chrome_options.add_experimental_option('prefs', {'intl.accept_languages': lang})
    for arg in args:
        chrome_options.add_argument(arg)
    return chrome_options


def _get_driver(options, timeout=10):
    limit = time() + timeout
    while time() < limit:
        try:
            driver = webdriver.Remote('http://localhost:4444/wd/hub', DesiredCapabilities.CHROME,
                                      options=options)
        except ProtocolError:
            sleep(SLEEPING_TIME)
        else:
            return driver
    else:
        raise TimeoutError('Waiting for container to be ready for webdriver creation timed out')


@contextmanager
def run_driver(docker_image, driver_lang='en', **kwargs):

    LOGGER.info('Starting docker container')
    client = docker.from_env()
    container = client.containers.run(docker_image, detach=True, ports={'4444/tcp': 4444})

    try:
        LOGGER.info('Starting driver')
        options = _get_options(driver_lang, *kwargs.values())
        driver = _get_driver(options)
        yield driver

    finally:
        LOGGER.info('Stopping driver and docker container')
        container.stop()
        container.remove()
