import argparse

from lib.driver import run_driver
from lib.spider_daily import SpiderDaily


if __name__ == '__main__':

    # Create argument parser
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('day', type=int, help='Day to scrape and load')

    # Parse arguments
    args = parser.parse_args()

    # Instantiate the spider
    with run_driver() as driver:
        spider = SpiderDaily(args.day, driver, 'config')
        spider.login()
        spider.scrape()
        spider.export()
