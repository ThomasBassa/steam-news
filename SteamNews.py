#!/usr/bin/python3

# Inspired by the likes of
# https://bendodson.com/weblog/2016/05/17/fetching-rss-feeds-for-steam-game-updates/
# http://www.getoffmalawn.com/blog/rss-feeds-for-steam-games

import time
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen
from urllib.error import HTTPError
import json
import sqlite3

from Init import DBPATH

## Date/time manipulation

def getExpiresDTFromResponse(response):
	exp = response.getheader('Expires')
	if exp is None:
		return datetime.now(timezone.utc)
	else:
		return parseExpiresAsDT(exp)

def parseExpiresAsDT(exp):
	#e.g. 'Sun, 15 Apr 2018 17:20:14 GMT'
	t = datetime.strptime(exp, '%a, %d %b %Y %H:%M:%S %Z')
	#The %Z parsing doesn't work right since it seems to expect a +##:## code on top of the GMT
	#So we're going to assume it's always GMT/UTC
	return t.replace(tzinfo=timezone.utc)

## Storage/caching related

def getGamesToFetch():
	with sqlite3.connect(DBPATH) as db:
		c = db.cursor()
		c.execute('SELECT appid, name FROM Games WHERE shouldFetch != 0')
		return dict(c.fetchall())

def insertNewsItem(ned):
	with sqlite3.connect(DBPATH) as db:
		c = db.cursor()
		c.execute('INSERT OR IGNORE INTO NewsItems VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
			(ned['gid'],
			ned['title'],
			ned['url'],
			ned['is_external_url'],
			ned['author'],
			ned['contents'],
			ned['feedlabel'],
			ned['date'],
			ned['feedname'],
			ned['feed_type'],
			ned['appid'])
		)
		c.execute('INSERT OR IGNORE INTO NewsSources VALUES (?, ?)',
			(ned['gid'], ned['realappid']))

		db.commit()

# Why are there so many variables named ned?
# I shorthanded "news element dict" to distinguish it as a single item
# vs. 'news' which is typically used for the entire JSON payload Steam gives us

# Get news for the given appid as a dict
def getNewsForAppID(appid):
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

def isNewsCached(appid):
	with sqlite3.connect(DBPATH) as db:
		c = db.cursor()
		c.execute('SELECT unixseconds FROM ExpireTimes WHERE appid = ?', (appid,))
		exptime = c.fetchone()
		if exptime is None:
			return False
		else:
			return time.time() < exptime[0]

# Is this news item more than 30 days old?
def isNewsOld(ned):
	newsdt = datetime.fromtimestamp(ned['date'], timezone.utc)
	thirtyago = datetime.now(timezone.utc) - timedelta(days=30)
	return newsdt < thirtyago

# Given a single news dict from getNewsForAppID, save all "recent" news items to the DB
def saveRecentNews(news):
	with sqlite3.connect(DBPATH) as db:
		c = db.cursor()
		c.execute('INSERT OR REPLACE INTO ExpireTimes VALUES (?, ?)', (news['appnews']['appid'], news['expires']))
		db.commit()

	for ned in news['appnews']['newsitems']:
		if not isNewsOld(ned):
			insertNewsItem(ned)

# Given a dict of appids to names, store all "recent" items, respecting the cache
def getAllRecentNews(newsids):
	cachehits = 0
	newhits = 0
	fails = 0
	for id, name in newsids.items():
		if isNewsCached(id):
			cachehits += 1
		else:
			print('Get {}: {}... '.format(id, name), end=None)
			news = getNewsForAppID(id)
			if 'appnews' in news: #success
				saveRecentNews(news)
				newhits += 1
				print('OK!')
				time.sleep(0.25)
			else:
				fails += 1
				print('Error: {}'.format(news['error']))
				time.sleep(1)

	print('Run complete. {} cached, {} fetched, {} failed'.format(cachehits, newhits, fails))


if __name__ == '__main__':
	newsids = getGamesToFetch()
	getAllRecentNews(newsids)
