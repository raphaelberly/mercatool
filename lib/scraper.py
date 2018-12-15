# -*- coding: utf-8 -*-
from contextlib import contextmanager
from time import sleep

import psycopg2
from selenium.common.exceptions import NoSuchElementException

from bs4 import BeautifulSoup
from selenium.webdriver.common.action_chains import ActionChains

from .tools import resolve, ensure_folder_exists


BATCH_SIZE = 10


class BasicScraper(object):

    def __init__(self, driver):
        self.driver = driver

    # GET A WEBPAGE
    def get_page(self, url):
        self.driver.get(url)
        sleep(1)

    # GET SOUP FROM CURRENT WEBPAGE
    def get_soup(self):
        return BeautifulSoup(self.driver.page_source, 'html.parser')


class Scraper(BasicScraper):

    def __init__(self, day, season, driver, table_name, credentials, urls, classes,
                 mappings=None, transformations=None):

        super().__init__(driver)

        self.day = day
        self.season = season
        self.table_name = table_name

        self.credentials = credentials
        self.urls = urls
        self.classes = classes
        self.mappings = mappings
        self.transformations = transformations

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
        sleep(2)

    def _apply_maps(self, dict_item):
        if not self.mappings:
            return dict_item
        for key, map in self.mappings.items():
            if key in dict_item:
                old_value = dict_item[key]
                dict_item[key] = map.get(old_value, old_value)
        return dict_item

    def _apply_transformations(self, dict_item):
        if not self.transformations:
            return dict_item
        for key, func in self.transformations.items():
            if key in dict_item:
                dict_item[key] = resolve(func)(dict_item[key])
        return dict_item

    # EMPTY A DAY IF
    @staticmethod
    def _get_connection_string(host, port, db, user, password):
        return f"host='{host}' dbname='{db}' port={port} user='{user}' password='{password}'"

    def _erase_day_from_table(self, conn):
        print('Deleting existing data for this day and season...')
        cur = conn.cursor()
        query = f"DELETE FROM {self.table_name} WHERE day={self.day} AND season='{self.season}'"
        cur.execute(query)
        cur.close()

    @staticmethod
    def _get_insert_query(table_name, player_dict):
        key_str = ','.join(player_dict.keys())
        val_str = "'{}'".format("','".join([str(val) for val in player_dict.values()]))
        return f'INSERT INTO {table_name} ({key_str}) VALUES ({val_str});'

    # EMPTY A DAY IF
    def insert_values_into_table(self, values_generator, batch_size=BATCH_SIZE):
        print('Inserting new data for this day and season...')
        with psycopg2.connect(self._get_connection_string(**self.credentials['db'])) as conn:
            # Erase day if already existing in the database
            self._erase_day_from_table(conn)
            # Insert values by batch
            i, queries = 0, []
            for value in values_generator:
                i += 1
                queries.append(self._get_insert_query(self.table_name, value))
                if i == batch_size:
                    cur = conn.cursor()
                    cur.execute('\n'.join(queries))
                    cur.close()
                    print(len(queries))
                    i, queries = 0, []


class RatingScraper(Scraper):

    # PARSE GAME DETAILS
    def get_rating_values(self):
        print('Getting players ratings...')
        self.get_page(self.urls['mercato'])
        # Parse overall code
        soup = self.get_soup()
        # Get all lines (one per player)
        lines = soup.findAll(**self.get_find_args('line'))
        # Parse all lines
        to_extract = ['player', 'position', 'team', 'rating']
        for line in lines:
            # Remove player first name
            _ = line.find(**self.get_find_args('first_name')).extract()
            # Parse line
            player = {'day': self.day, 'season': self.season}
            for item in to_extract:
                player[item] = line.find(**self.get_find_args(item)).text.replace('\xa0', '')
            player = self._apply_maps(player)
            player = self._apply_transformations(player)
            yield player


class DetailScraper(Scraper):

    def __init__(self, day, season, driver, credentials, table_name, urls, classes, features,
                 mappings=None, transformations=None):
        super().__init__(day, season, driver, table_name, credentials, urls, classes, mappings,
                         transformations)
        self.features = features

    # GET LIST OF GAMES URL
    def get_urls(self):
        print('Getting list of URLs to scrape...')
        # Get the day page
        self.get_page(self.urls['calendar'].format(self.day))
        # Parse the day page's code
        soup = self.get_soup()
        games = soup.findAll(**self.get_find_args('games'))
        # Fill the urls_to_scrape list
        for game in games:
            game_score = game.find(**self.get_find_args('game_score'))
            game_url = game_score['href'] if game_score else None
            # Check that it could find a URL and it has the right format
            if game_url:
                # Check that it  (sometimes, ads pop up)
                if game_url.startswith('/championships'):
                    yield game_url

    # PARSE GAME DETAILS
    def get_player_values(self, url_generator):
        for url in url_generator:
            print('Getting details from game {}'.format(url))
            self.get_page(self.urls['root'] + url)
            soup = self.get_soup()
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
                for player in players:
                    try:
                        grade = player \
                            .find_element_by_class_name(self.classes['player_grade']['key']) \
                            .get_attribute('innerHTML')
                    except NoSuchElementException:
                        continue
                    player_dict = self._create_player_dict(player)
                    player_dict.update({'team': team_name, 'grade': grade, 'opponent': opponent_name})
                    player_dict = self._apply_maps(player_dict)
                    player_dict = self._apply_transformations(player_dict)
                    yield player_dict

    # PARSE ONE PLAYER'S DATA
    def _create_player_dict(self, player):
        # Move to element and click on it
        actions = ActionChains(self.driver)
        self.driver.execute_script("arguments[0].scrollIntoView();", player)
        actions.move_to_element(player).click().perform()
        # Parse the day page's code
        soup = self.get_soup()
        table = soup.find(**self.get_find_args('stats_table'))
        lines = table.findAll('tr')
        # Parse first lines
        player, position = tuple(lines[2].text.split(' - '))
        data = {'player': player, 'position': position, 'day': self.day, 'season': self.season}
        # Iterate through all lines except first ones
        for line in lines[2:]:
            feature = [col.text for col in line.findAll('td')]
            if feature[0] in self.features:
                # Handle the raw score
                if feature[1] == '':
                    data.update({self.features[feature[0]]: feature[2]})
                # Handle the non-zero cases (where value == '-')
                elif feature[1] != '-':
                    data.update({self.features[feature[0]]: feature[1]})
        return data
