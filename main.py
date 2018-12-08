import argparse

import yaml

from lib.driver import run_driver
from lib.spider_daily import SpiderDaily


if __name__ == '__main__':

    # Create argument parser
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('day', type=int, help='Day to scrape and load')

    credentials = yaml.load(open('config/credentials.yaml'))
    conf_driver = yaml.load(open('config/driver.yaml'))
    conf_spider = yaml.load(open('config/spider.yaml'))

    # Parse arguments
    args = parser.parse_args()

    # Instantiate the spider
    with run_driver(**conf_driver) as driver:
        spider = SpiderDaily(args.day, driver, credentials, **conf_spider)
        spider.login()
        spider.scrape()
        spider.export()
