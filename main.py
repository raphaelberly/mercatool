import argparse

import yaml

from lib.driver import run_driver
from lib.scraper import Scraper


DEFAULT_CREDENTIALS_LOC = 'conf/credentials.yaml'
DEFAULT_DRIVER_CONF_LOC = 'conf/driver.yaml'
DEFAULT_SCRAPER_CONF_LOC = 'conf/scraper.yaml'


if __name__ == '__main__':

    # Create argument parser
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--day', required=True, type=int)
    parser.add_argument('--credentials', type=str)
    parser.add_argument('--conf-driver', type=str)
    parser.add_argument('--conf-scraper', type=str)

    # Parse arguments
    args = parser.parse_args()

    credentials = yaml.load(open(args.credentials or DEFAULT_CREDENTIALS_LOC))
    conf_driver = yaml.load(open(args.conf_driver or DEFAULT_DRIVER_CONF_LOC))
    conf_scraper = yaml.load(open(args.conf_scraper or DEFAULT_SCRAPER_CONF_LOC))

    # Instantiate the scraper
    with run_driver(**conf_driver) as driver:
        scraper = Scraper(day=args.day, driver=driver, credentials=credentials, **conf_scraper)
        scraper.login()
        scraper.scrape()
        scraper.export()
