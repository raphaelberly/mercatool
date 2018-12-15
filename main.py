import argparse

import yaml

from lib.driver import run_driver
from lib.tools import resolve

DEFAULT_DRIVER = 'conf/driver.yaml'
DEFAULT_CREDENTIALS = 'conf/credentials.yaml'


if __name__ == '__main__':

    # Create argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument('--day', required=True, type=int, help='Day to scrape')
    parser.add_argument('--scraper', required=True, type=str, help='Path to scraper config')
    parser.add_argument('--credentials', default=DEFAULT_CREDENTIALS, help='Path to credentials')
    parser.add_argument('--driver', default=DEFAULT_DRIVER, help='Path to driver config')

    # Parse arguments
    args = parser.parse_args()
    conf_scraper = yaml.load(open(args.scraper))
    credentials = yaml.load(open(args.credentials))
    conf_driver = yaml.load(open(args.driver))

    # Instantiate the scraper
    with run_driver(**conf_driver) as driver:

        Scraper = resolve(conf_scraper.pop('scraper'))
        scraper = Scraper(day=args.day, driver=driver, credentials=credentials, **conf_scraper)
        scraper.login()
        scraper.run()
