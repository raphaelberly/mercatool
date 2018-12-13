# -*- coding: utf-8 -*-
import os
from warnings import warn
from random import randint
from sys import stdout
from time import sleep

import psycopg2
from selenium.common.exceptions import NoSuchElementException

import pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.action_chains import ActionChains
from sqlalchemy import create_engine

from .tools import fraction_to_float


class Scraper(object):

    def __init__(self, day, season, driver, credentials, urls, classes, features, maps):

        self.day = day
        self.season = season
        self.driver = driver
        self.credentials = credentials
        self.urls = urls
        self.classes = classes
        self.features = features
        self.maps = maps
        self.details = []

    def get_player_df(self):
        print('Getting players dataframe...')
        path_to_player_csv = 'data/players_{:02d}.csv'.format(self.day)
        if os.path.exists(path_to_player_csv):
            print(f'> using cached players list: {path_to_player_csv}')
            return pd.read_csv(path_to_player_csv)
        else:
            df = self.parse_player_list()
            df.to_csv(path_to_player_csv, index=False)
            return df

    # GET A WEBPAGE
    def get_page(self, url):
        self.driver.get(url)
        sleep(randint(2, 3))

    # GET PARAMS OF THE BEAUTIFUL SOUP FIND(ALL) FUNCTIONS
    def get_find_args(self, class_name):
        return {
            'name': self.classes[class_name]['tag'],
            'attrs': {'class': self.classes[class_name]['key']}
        }

    # LOG IN TO THE WEBSITE
    def login(self):
        print('Logging in...')
        # Get the login page
        self.driver.get(self.urls['login'])
        # Submit the credentials
        username = self.driver.find_element_by_name("email")
        password = self.driver.find_element_by_name("password")
        password.send_keys(self.credentials['mpg']['password'])
        username.send_keys(self.credentials['mpg']['username'])
        password.submit()
        # Sleep
        sleep(randint(3, 5))

    # GET LIST OF GAMES URL
    def get_url_list(self):
        print('Getting list of URLs to scrape...')
        # Get the day page
        self.get_page(self.urls['calendar'].format(self.day))
        # Parse the day page's code
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        games = soup.findAll(**self.get_find_args('games'))
        # Fill the urls_to_scrape list
        urls = []
        for game in games:
            game_score = game.find(**self.get_find_args('game_score'))
            game_url = game_score['href'] if game_score else None
            # Check that it could find a URL
            if game_url:
                # Check that it has the right format (sometimes, ads pop up)
                if game_url.startswith('/championships'):
                    # Add it to the URLs to scrape
                    urls.append(game_url)
                else: warn("Could not retrieve 1 game's URL for day {}".format(self.day))
            else: warn("Could not retrieve 1 game's URL for day {}".format(self.day))
        return urls

    # PARSE GAME DETAILS
    def parse_game_details(self, url):
        print('Getting details from game {}'.format(url))
        url_root = self.urls['root']
        self.get_page(url_root + url)
        # Parse overall code
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        # Repeat process for home and away team
        for loc in ['home', 'away']:
            # Get team name
            team_name = soup.find(**self.get_find_args(f'{loc}_team_name')).text
            # Get the team players
            stadium = self.driver.find_element_by_class_name(self.classes['stadium']['key'])
            players = stadium \
                .find_element_by_class_name(self.classes[f'{loc}_team_players']['key']) \
                .find_elements_by_class_name(self.classes['player']['key'])
            # Get the team opponents
            opponent_loc = 'home' if loc == 'away' else 'away'
            opponent_name = soup.find(**self.get_find_args(f'{opponent_loc}_team_name')).text

            # Iterate over all players of the team
            i, n = 0, len(players)
            for player in players:
                i += 1
                stdout.write(f'\rParsing {loc}: {i}/{n} players parsed')
                player_grade = None
                try:
                    player_grade = player \
                        .find_element_by_class_name(self.classes['player_grade']['key']) \
                        .get_attribute('innerHTML')
                except NoSuchElementException:
                    pass
                if player_grade:
                    # Move to element and click on it
                    actions = ActionChains(self.driver)
                    self.driver.execute_script("arguments[0].scrollIntoView();", player)
                    actions.move_to_element(player).click().perform()
                    sleep(randint(1, 2))
                    # Perform function
                    data = self.parse_player_table()
                    data.update({'team': team_name, 'grade': player_grade, 'opponent': opponent_name})
                    self.details.append(data)
            print("")

    # PARSE ONE PLAYER'S DATA
    def parse_player_table(self):
        # Parse the day page's code
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        table = soup.find(**self.get_find_args('stats_table'))
        lines = table.findAll('tr')
        data = {'player': lines[2].text.split(" - ")[0], 'day': self.day, 'played': 1}
        for line in lines[2:]:
            feature = [col.text for col in line.findAll('td')]
            if feature[0] in self.features.keys():
                # Handle the raw score separately
                if feature[1] != "":
                    data.update({self.features[feature[0]]: feature[1]})
                else:
                    data.update({self.features[feature[0]]: feature[2]})
        return data

    # PARSE GAME DETAILS
    def parse_player_list(self):
        print('Getting players list...')
        self.get_page(self.urls['mercato'])
        # Parse overall code
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        # Get all lines (one per player)
        lines = soup.findAll(**self.get_find_args('player_line'))
        # Parse all lines
        to_extract = ['player_name', 'player_position', 'player_team', 'player_rating']
        players = []
        for line in lines:
            # Remove player first name
            _ = line.find(**self.get_find_args('player_first_name')).extract()
            # Parse line
            player = {'day': self.day, 'season': self.season}
            for item in to_extract:
                name = item[len('player_'):]
                player[name] = line.find(**self.get_find_args(item)).text.replace('\xa0', '')
            players.append(player)
        return pd.DataFrame(players)

    # APPLY EXCEPTIONS
    def _apply_maps(self, df):
        return df.replace(self.maps)

    # EXPORT THE GATHERED DATA
    def export(self):
        print('Exporting data...')
        # Create data frames out of collected lists
        df_details = pd.DataFrame(self.details).applymap(lambda x: 0 if x == '-' else x).fillna(0)
        for col in ['grade', 'raw_grade']:
            df_details[col] = df_details[col].str.replace(',', '.').astype(float)
        df_details.perc_successful_passes = df_details.perc_successful_passes.str.rstrip('%').astype(float) / 100
        df_details.clean_sheet = df_details.clean_sheet.astype(str).apply(fraction_to_float).astype(float)
        # Load players list
        df_players = self.get_player_df()
        df_players = self._apply_maps(df_players)
        df_details = self._apply_maps(df_details)
        # Merge scores and goals data together
        df_output = pd.merge(df_players, df_details, on=['day', 'team', 'player'], how='left')
        # Export data as a CSV
        df_output.to_csv('data/day_{:02d}.csv'.format(self.day), index=False)
        # Upload to the database
        self.to_db(df_output)

    # LOAD A DATAFRAME INTO A DATABASE
    def to_db(self, df):
        self._delete_day_if_exists(**self.credentials['db'])
        return self._df_to_db(df, **self.credentials['db'])

    def _delete_day_if_exists(self, host, port, db, user, password, schema, table):
        print('Deleting existing data for this day and season...')
        conn_str = f"host='{host}' dbname='{db}' port={port} user='{user}' password='{password}'"
        with psycopg2.connect(conn_str) as conn:
            cur = conn.cursor()
            day, season = self.day, self.season
            cur.execute(f"DELETE FROM {schema}.{table} WHERE day = {day} AND season = '{season}'")

    @staticmethod
    def _df_to_db(df, host, port, db, user, password, schema, table):
        engine_string = f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}'
        engine = create_engine(engine_string)
        df.to_sql(table, con=engine, schema=schema, if_exists='append', index=False)

    # SCRAPE THE CHOSEN DAY
    def scrape(self):
        # Get the list of URLs
        urls = self.get_url_list()
        # Get the games details
        for game_url in urls:
            self.parse_game_details(game_url)
