#!/usr/bin/env python3

# Inspired by the likes of
# https://bendodson.com/weblog/2016/05/17/fetching-rss-feeds-for-steam-game-updates/
# http://www.getoffmalawn.com/blog/rss-feeds-for-steam-games

import logging
import time
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen
from urllib.error import HTTPError
import json

from database import NewsDatabase

logger = logging.getLogger(__name__)

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
    url = 'https://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/?format=json&maxlength=0&count=5&appid={}'.format(appid)
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

    for ned in news['appnews']['newsitems']:
        if not isNewsOld(ned):
            db.insert_news_item(ned)


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
                saveRecentNews(news, db)
                newhits += 1
                logger.info('Fetched %d: %s OK!', aid, name)
                time.sleep(0.25)
            else:
                fails += 1
                logger.error('%d: %s fetch error: %s', aid, name, news['error'])
                time.sleep(1)

    logger.info('Run complete. %d cached, %d fetched, %d failed',
            cachehits, newhits, fails)


if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout,
            format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            level=logging.DEBUG)
    with NewsDatabase() as db:
        newsids = db.get_fetch_games()
        getAllRecentNews(newsids, db)
