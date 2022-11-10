#!/usr/bin/python3

import logging
import sqlite3
from urllib.request import urlopen
import xml.dom.minidom  # Maybe replace this one...

from database import NewsDatabase

logger = logging.getLogger(__name__)

# Hardcoded list of AppIDs that return news related to Steam as a whole (not games)
# Mileage may vary. Use app_id_discovery.py to maybe find more of these...
STEAM_APPIDS = {753: 'Steam',
        221410: 'Steam for Linux',
        223300: 'Steam Hardware',
        250820: 'SteamVR',
        353370: 'Steam Controller',
        353380: 'Steam Link',
        358720: 'SteamVR Developer Hardware',
        596420: 'Steam Audio',
        613220: 'Steam 360 Video Player'}


def seed_database(idOrVanity, db: NewsDatabase):
    try:
        sid = int(idOrVanity)
        url = 'https://steamcommunity.com/profiles/{}/games?xml=1'.format(sid)
    except ValueError:  # it's probably a vanity str
        url = 'https://steamcommunity.com/id/{}/games?xml=1'.format(idOrVanity)

    newsids = getAppIDsFromURL(url)
    #Also add the hardcoded ones...
    newsids.update(STEAM_APPIDS)
    db.add_games(newsids)


def getAppIDsFromURL(url):
    """Given a steam profile url, produce a dict of
    appids to names of games owned (appids are strings)
    i.e. parses unofficial XML API of a Steam user's game list.
    Note that the profile in question needs to be public for this to work!"""
    logger.info('Parsing XML from %s...', url)
    xmlstr = urlopen(url).read().decode('utf-8')
    dom = xml.dom.minidom.parseString(xmlstr)
    gameEls = dom.getElementsByTagName('game')

    games = {}
    for ge in gameEls:
        appid = int(ge.getElementsByTagName('appID')[0].firstChild.data)
        name = ge.getElementsByTagName('name')[0].firstChild.data
        games[appid] = name

    logger.info('Found %d games.', len(games))
    return games

if __name__ == '__main__':
    import os.path
    import sys
    logging.basicConfig(stream=sys.stdout,
            format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            level=logging.DEBUG)
    with NewsDatabase() as db:
        if not os.path.isfile(db.path):
            db.first_run()

        if len(sys.argv) >= 2:
            seed_database(sys.argv[1], db)
            logger.info('Database seeded with games from ' + sys.argv[1])
        else:
            logger.info('Run this script with a Steam ID or vanity URL as an argument to add its games to the list to fetch')
