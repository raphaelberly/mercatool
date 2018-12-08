# -*- coding: utf-8 -*-
from warnings import warn
from random import randint
from sys import stdout
from time import sleep

from selenium.common.exceptions import NoSuchElementException

import pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.action_chains import ActionChains
from sqlalchemy import create_engine

from .tools import fraction_to_float


class Scraper(object):

    def __init__(self, day, season, driver, credentials, urls, classes, features, scrape_players_list=True):
        self.day = day
        self.season = season
        self.credentials = credentials
        self.urls = urls
        self.classes = classes
        self.features = features
        # Instantiate urls_to_scrape_list
        self.urls_to_scrape = []
        self.players = []
        self.players_list = [] if scrape_players_list else None
        self.driver = driver

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
    def parse_games_url(self):
        print('Getting list of URLs to scrape...')
        # Get the day page
        self.get_page(self.urls['calendar'].format(self.day))
        # Parse the day page's code
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        games = soup.findAll(**self.get_find_args('games'))
        # Fill the urls_to_scrape list
        for game in games:
            game_score = game.find(**self.get_find_args('game_score'))
            game_url = game_score['href'] if game_score else None
            # Check that it could find a URL
            if game_url:
                # Check that it has the right format (sometimes, ads pop up)
                if game_url.startswith('/championships'):
                    # Add it to the URLs to scrape
                    self.urls_to_scrape.append(game_url)
                else: warn("Could not retrieve 1 game's URL for day {}".format(self.day))
            else: warn("Could not retrieve 1 game's URL for day {}".format(self.day))

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
                player_grade = None
                try:
                    player_grade = player \
                        .find_element_by_class_name(self.classes['player_grade']['key']) \
                        .get_attribute('innerHTML')
                except NoSuchElementException:
                    pass

                if player_grade:
                    stdout.write(f'\rParsing {loc}: {i}/{n} players parsed')
                    # Move to element and click on it
                    actions = ActionChains(self.driver)
                    self.driver.execute_script("arguments[0].scrollIntoView();", player)
                    actions.move_to_element(player).click().perform()
                    sleep(randint(1, 2))
                    # Perform function
                    data = self.parse_player_table()
                    data.update({'team': team_name, 'grade': player_grade, 'opponent': opponent_name})
                    self.players.append(data)

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
    def parse_players_list(self):
        print('Getting players list...')
        self.get_page(self.urls['mercato'])
        # Parse overall code
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        # Get all lines (one per player)
        lines = soup.findAll(**self.get_find_args('player_line'))
        # Parse all lines
        to_extract = ['player_name', 'player_position', 'player_team', 'player_rating']
        for line in lines:
            # Remove player first name
            _ = line.find(**self.get_find_args('player_first_name')).extract()
            # Collect features to extract
            self.players_list.append(tuple([self.day, self.season] + [line.find(**self.get_find_args(x)).text.replace('\xa0', '') for x in to_extract]))

    # APPLY EXCEPTIONS
    @staticmethod
    def _apply_exceptions(df):
        if 'player' in df.columns:
            df.player = df.player.apply(lambda x: 'Lopes' if x == 'Anthony Lopes' else x)
            df.player = df.player.apply(lambda x: 'Pléa' if x == 'Plea' else x)

    # EXPORT THE GATHERED DATA
    def export(self):
        print('Exporting data...')
        # Create data frames out of collected lists
        df_players = pd.DataFrame(self.players).applymap(lambda x: 0 if x == '-' else x).fillna(0)
        for col in ['grade', 'raw_grade']:
            df_players[col] = df_players[col].str.replace(',', '.').astype(float)
        df_players.perc_successful_passes = df_players.perc_successful_passes.str.rstrip('%').astype(float) / 100
        df_players.clean_sheet = df_players.clean_sheet.astype(str).apply(fraction_to_float).astype(float)
        self._apply_exceptions(df_players)
        if self.players_list is None:
            df_players_list = pd.read_csv('data/players_{:02d}.csv'.format(self.day))
            self._apply_exceptions(df_players_list)
        else:
            df_players_list = pd.DataFrame(self.players_list, columns=['day', 'season', 'player', 'position', 'team', 'rating'])
            self._apply_exceptions(df_players_list)
            df_players_list.to_csv('data/players_{:02d}.csv'.format(self.day), index=False)
        # Merge scores and goals data together
        df_output = pd.merge(df_players_list, df_players, on=['day', 'team', 'player'], how='left')
        # Export data as a CSV
        df_output.to_csv('data/day_{:02d}.csv'.format(self.day), index=False)
        # Upload to the database
        self.to_db(df_output)

    # LOAD A DATAFRAME INTO A DATABASE
    def to_db(self, df):
        return self._df_to_db(df, **self.credentials['db'])

    @staticmethod
    def _df_to_db(df, host, port, db, user, password, schema, table):
        engine_string = f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}'
        engine = create_engine(engine_string)
        df.to_sql(table, con=engine, schema=schema, if_exists='append', index=False)

    # SCRAPE THE CHOSEN DAY
    def scrape(self):
        # Get the list of URLs
        self.parse_games_url()
        # Get the games details
        for game_url in self.urls_to_scrape:
            self.parse_game_details(game_url)
        # Get players list
        if self.players_list is not None:
            self.parse_players_list()
        else:
            print('Players list not scraped, local data will be used...')
