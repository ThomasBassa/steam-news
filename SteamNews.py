#!/usr/bin/python3

import time
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen
import urllib.error
import json
import sqlite3
import xml.dom.minidom #Maybe replace this one...

DBPATH = 'SteamNews.db'

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

def initDB():
	db = sqlite3.connect(DBPATH)
	c = db.cursor()
	
	#TODO odd note: feed_type is 1 for steam community announcements (feedname == 'steam_community_announcements') and 0 otherwise
	# this seems to be connected to the use of psuedo bbcode
	#see https://steamcommunity.com/comment/Recommendation/formattinghelp
	
	c.execute('''CREATE TABLE AppIDsCache (appid INTEGER PRIMARY KEY, name TEXT)''')
	c.execute('''CREATE TABLE LastFetchStatus (appid INTEGER PRIMARY KEY, status)''')
	c.execute('''CREATE TABLE NewsItems (
		gid TEXT PRIMARY KEY,
		title TEXT,
		url TEXT, 
		is_external_url TEXT,
		author TEXT,
		contents TEXT,
		feedlabel TEXT,
		date INTEGER,
		feedname TEXT,
		feed_type INTEGER,
		appid INTEGER,
		realappid INTEGER
		)''')
	
	db.commit()
	db.close()
	
def insertNewsItem(ned):
	db = sqlite3.connect(DBPATH)
	db.row_factory = sqlite3.Row
	c = db.cursor()
	try:
		c.execute('''INSERT OR ABORT INTO NewsItems VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
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
			ned['appid'],
			ned['realappid'])
		)
		db.commit()
	except sqlite3.IntegrityError:
		del ned['contents']
		ned['is_external_url'] = '1' if ned['is_external_url'] else '0'
		
		print('failed to insert:')
		print(ned)
		
		c.execute('select * from NewsItems WHERE gid = ?', (ned['gid'],))
		row = c.fetchone()
		d = dict(row)
		del d['contents']
		
		if d == ned:
			print('it\'s a perfect dupe')
		else:
			print('already present:')
			print(d)
	
	db.close()

# given vanity url, produce a dict of appids to names of games owned (appids are strings)
# parses unofficial XML API of a Steam user's game list
def getAppIDsFromVanity(vanity):
	url = 'https://steamcommunity.com/id/{}/games?xml=1'.format(vanity)
	xmlstr = urlopen(url).read().decode('utf-8')
	dom = xml.dom.minidom.parseString(xmlstr)
	gameEls = dom.getElementsByTagName('game')

	gameTuples = []
	for ge in gameEls:
		appid = ge.getElementsByTagName('appID')[0].firstChild.data
		name = ge.getElementsByTagName('name')[0].firstChild.data
		gameTuples.append((appid, name))

	return dict(gameTuples)

# Hardcoded list of AppIDs that return news related to Steam as a whole (not games)
# returns a dict of appids to names (appids are strings)
def getSteamNewsAppIDs():
	return dict([('753', 'Steam'),
		('221410', 'Steam for Linux'),
		('223300', 'Steam Hardware'),
		('250820', 'SteamVR'),
		('353370', 'Steam Controller'),
		('353380', 'Steam Link'),
		('358720', 'SteamVR Developer Hardware'),
		('596420', 'Steam Audio'),
		('613220', 'Steam 360 Video Player')
	])

# Just read IDs from a hardcoded file into a list
def getTestNewsIDs():
	ids = []
	with open('SteamNewsIDs.txt') as f:
		ids = f.read().splitlines()
	return ids

# Get news for the given appid as a dict
def getNewsForAppID(appid):
	url = 'https://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/?format=json&maxlength=0&count=5&appid={}'.format(appid)
	try:
		jsonstr = urlopen(url).read().decode('utf-8')
		return json.loads(jsonstr)
	except urllib.error.HTTPError as e:
		return {'error': '{} {}'.format(e.code, e.reason)}
	
	
#TODO
# Generate RSS, see:
# https://stackoverflow.com/questions/17229544/how-to-dynamically-generate-xml-file-for-rss-feed#17254864
# https://cyber.harvard.edu/rss/rss.html
# https://docs.python.org/3.5/library/datetime.html
# https://pypi.python.org/pypi/PyRSS2Gen

# https://bendodson.com/weblog/2016/05/17/fetching-rss-feeds-for-steam-game-updates/
# http://www.getoffmalawn.com/blog/rss-feeds-for-steam-games


if __name__ == '__main__':
	# print(getAppIDsFromVanity('vidios'))
	# print(getSteamNewsAppIDs())
	# initDB()
	# news = getNewsForAppID(105600)
	
	
	# NewsIDs test
	# newsids = getTestNewsIDs()
	# Using real info
	newsids = getAppIDsFromVanity('vidios')
	newsids.update(getSteamNewsAppIDs())
	
	good = []
	empty = []
	block = []
	for id, name in newsids.items():
		print('{} ({})'.format(name, id))
		news = getNewsForAppID(id)
		if 'appnews' in news: #success
			for ned in news['appnews']['newsitems']:
				ned['realappid'] = id
				insertNewsItem(ned)
				
			count = news['appnews']['count']
			if count == 0:
				print('OK, but empty')
				empty.append(id)
			else:
				print('OK, count = {}'.format(count))
				good.append(id)
			
			time.sleep(0.5)
		else:
			print(news)
			block.append(id)
			time.sleep(3)

	print('Good:')
	print('\n'.join(good))
	print('Empty:')
	print('\n'.join(empty))
	print('Blocked:')
	print('\n'.join(block))