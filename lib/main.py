# -*- coding: utf-8 -*-

import argparse
import configparser

import pandas as pd
import psycopg2

from spider_daily import SpiderDaily


def main_load(credentials_file, csv_file):

    # Read credentials
    config = configparser.ConfigParser()
    config.read(credentials_file)

    # Create connector
    conn = psycopg2.connect(host=config.get('PIDB', 'host'),
                            port=config.get('PIDB', 'port'),
                            database=config.get('PIDB', 'database'),
                            user=config.get('PIDB', 'user'),
                            password=config.get('PIDB', 'password'))
    # Create cursor
    cur = conn.cursor()

    # Get the list of
    cur.execute("SELECT * FROM wingman.details LIMIT 0")
    colnames = [desc[0] for desc in cur.description]

    # Load raw data from CSV file
    print('Reading collected data...')
    table = pd.read_csv(csv_file, header=0)
    table.titular = table.titular.map({True: 'TRUE', False: 'FALSE'}).fillna('FALSE')
    table.player = table.player.apply(lambda name: "''".join(name.split("'")))
    table = table.fillna('NULL')

    # Prepare the query
    query_root = "INSERT INTO wingman.details VALUES ({0}, '{1}', '{2}', '{3}', {4}, {5}, {6}, {7})"

    # Add every line row per row
    print('Uploading data to the database...')
    for index, row in table.iterrows():
        # print('iteration ', index)
        query = query_root.format(*[str(row[col]) for col in colnames])
        cur.execute(query)

    # Commit and close connector
    conn.commit()
    conn.close()


def main_scrape(day, config_folder):
    # Instantiate the spider
    spider = SpiderDaily(day, config_folder)
    # Scrape the web
    spider.scrape()
    # Export to CSV
    spider.export()


# WHEN RUN AS A SCRIPT

if __name__ == '__main__':

    # Create argument parser
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('day', type=int, help='Day to scrape and load')

    # Parse arguments
    args = vars(parser.parse_args())

    # Scrape the website
    main_scrape(args.get('day'), '../config')

    # Load data to the database
    # main_load('../config/credentials.ini', '../data/day_{:02d}.csv'.format(args.get('day')))

