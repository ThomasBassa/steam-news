#!/usr/bin/env python3

# Inspired by the likes of
# https://bendodson.com/weblog/2016/05/17/fetching-rss-feeds-for-steam-game-updates/
# http://www.getoffmalawn.com/blog/rss-feeds-for-steam-games

import argparse
from datetime import datetime, timezone, timedelta
import json
import logging
import subprocess
import sys
import time
from urllib.request import urlopen
from urllib.error import HTTPError
import xml.dom.minidom  # Maybe replace this one...

from database import NewsDatabase
from NewsPublisher import publish

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
        #593110 is the source for the megaphone icon in the client, not in appid list...
        593110: 'Steam News',
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

# Date/time manipulation

def getExpiresDTFromResponse(response):
    exp = response.getheader('Expires')
    if exp is None:
        return datetime.now(timezone.utc)
    else:
        return parseExpiresAsDT(exp)


def parseExpiresAsDT(exp):
    # e.g. 'Sun, 15 Apr 2018 17:20:14 GMT'
    t = datetime.strptime(exp, '%a, %d %b %Y %H:%M:%S %Z')
    # The %Z parsing doesn't work right since it seems to expect a +##:## code on top of the GMT
    # So we're going to assume it's always GMT/UTC
    return t.replace(tzinfo=timezone.utc)

# Why are there so many variables named ned?
# I shorthanded "news element dict" to distinguish it as a single item
# vs. 'news' which is typically used for the entire JSON payload Steam gives us

def getNewsForAppID(appid):
    """Get news for the given appid as a dict"""
    url = 'https://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/?format=json&maxlength=0&count=10&appid={}'.format(appid)
    try:
        response = urlopen(url)
        # Get value of 'expires' header as a datetime obj
        exdt = getExpiresDTFromResponse(response)
        # Parse the JSON
        news = json.loads(response.read().decode('utf-8'))
        # Add the expire time to the group as a plain unix time
        news['expires'] = int(exdt.timestamp())
        # Decorate each news item and the group with its "true" appid
        for ned in news['appnews']['newsitems']:
            ned['realappid'] = appid

        return news
    except HTTPError as e:
        return {'error': '{} {}'.format(e.code, e.reason)}


def isNewsOld(ned):
    """Is this news item more than 30 days old?"""
    newsdt = datetime.fromtimestamp(ned['date'], timezone.utc)
    thirtyago = datetime.now(timezone.utc) - timedelta(days=30)
    return newsdt < thirtyago


def saveRecentNews(news: dict, db: NewsDatabase):
    """Given a single news dict from getNewsForAppID,
    save all "recent" news items to the DB"""
    db.update_expire_time(news['appnews']['appid'], news['expires'])

    current_entries = 0
    for ned in news['appnews']['newsitems']:
        if not isNewsOld(ned):
            db.insert_news_item(ned)
            current_entries += 1
    return current_entries


def getAllRecentNews(newsids: dict, db: NewsDatabase):
    """Given a dict of appids to names, store all "recent" items, respecting the cache"""
    cachehits = 0
    newhits = 0
    fails = 0
    for aid, name in newsids.items():
        if db.is_news_cached(aid):
            logger.info('Cache for %d: %s still valid!', aid, name)
            cachehits += 1
        else:
            news = getNewsForAppID(aid)
            if 'appnews' in news: # success
                cur_entries = saveRecentNews(news, db)
                newhits += 1
                logger.info('Fetched %d: %s OK; %d current items', aid, name, cur_entries)
                time.sleep(0.25)
            else:
                fails += 1
                logger.error('%d: %s fetch error: %s', aid, name, news['error'])
                time.sleep(1)

    logger.info('Run complete. %d cached, %d fetched, %d failed',
            cachehits, newhits, fails)

def edit_fetch_games(name, db: NewsDatabase):
    logger.info('Editing games like "%s"', name)
    games = db.get_games_like(name)
    before_on = set()
    before_off = set()
    args = ['whiptail', '--title', 'Select games to fetch news for',
            '--separate-output', '--checklist',
            'Use arrow keys to move, Space to toggle, Tab to go to OK, ESC to cancel.',
            '50', '100', '43', '--']
    for game in games:
        if game['shouldFetch']:
            before_on.add(game['appid'])
            status = 'on'
        else:
            before_off.add(game['appid'])
            status = 'off'
        args.append(str(game['appid']))
        args.append(game['name'])
        args.append(status)

    proc = subprocess.run(args, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        logger.info('Cancelled editing games.')
        return
    #Convert stderr output to set of int appids...
    out = proc.stderr.strip() #mainly to remove trailing newline
    if out:
        selected = frozenset(map(int, out.split('\n')))
    else: #i.e. deselected everything, so output was empty
        selected = frozenset()
    logger.debug('Before on: %s\nBefore off: %s\nSelected (enable): %s',
            before_on, before_off, selected)
    #disable: ids in before_on that are not in selected
    disabled = before_on - selected
    #enable: ids in selected that are also in before_off
    enabled = selected & before_off
    logger.debug('Enabled %s\nDisabled: %s', enabled, disabled)

    if disabled:
        db.disable_fetching_ids(disabled)
        logger.info('Disabled %d games.', len(disabled))
    if enabled:
        db.enable_fetching_ids(enabled)
        logger.info('Enabled %d games.', len(enabled))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--first-run', action='store_true')
    parser.add_argument('-a', '--add-profile-games') # + steam ID/vanity url
    parser.add_argument('-f', '--fetch', action='store_true')
    parser.add_argument('-p', '--publish') # + path to XML output
    parser.add_argument('-g', '--edit-games-like') # + partial name of game
    parser.add_argument('-v', '--verbose', action='store_true')
    #TODO maybe arg for DB path...?
    args = parser.parse_args()

    lvl = logging.INFO if not args.verbose else logging.DEBUG
    logging.basicConfig(stream=sys.stdout,
            format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            level=lvl)

    with NewsDatabase() as db:
        if args.first_run:
            db.first_run()

        if args.add_profile_games:
            seed_database(args.add_profile_games, db)

        if args.edit_games_like:
            edit_fetch_games(args.edit_games_like, db)
        else: #editing is mutually exclusive w/ fetch & publish
            if args.fetch:
                newsids = db.get_fetch_games()
                getAllRecentNews(newsids, db)

            if args.publish:
                publish(db, args.publish)

if __name__ == '__main__':
    main()
