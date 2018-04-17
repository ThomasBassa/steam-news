#!/usr/bin/python3

import sqlite3
from urllib.request import urlopen
import xml.dom.minidom #Maybe replace this one...

DBPATH = 'SteamNews.db'

def initDB():
	with sqlite3.connect(DBPATH) as db:
		c = db.cursor()

		c.execute('''CREATE TABLE Games (appid INTEGER PRIMARY KEY, name TEXT NOT NULL, shouldFetch INTEGER NOT NULL DEFAULT 1)''')
		c.execute('''CREATE TABLE ExpireTimes (appid INTEGER PRIMARY KEY, unixseconds INTEGER NOT NULL DEFAULT 0)''')
		c.execute('''CREATE TABLE NewsItems (
			gid TEXT NOT NULL PRIMARY KEY,
			title TEXT,
			url TEXT,
			is_external_url INTEGER,
			author TEXT,
			contents TEXT,
			feedlabel TEXT,
			date INTEGER,
			feedname TEXT,
			feed_type INTEGER,
			appid INTEGER
			)''')
		c.execute('''CREATE TABLE NewsSources (gid TEXT NOT NULL, appid INTEGER NOT NULL, PRIMARY KEY(gid, appid))''')
		db.commit()

def populateGames(gamedict):
	with sqlite3.connect(DBPATH) as db:
		c = db.cursor()
		for appid, name in gamedict.items():
			c.execute('INSERT OR IGNORE INTO Games VALUES (?, ?, 1)', (appid, name))

def seedDatabase(vanity):
	newsids = getAppIDsFromVanity(vanity)
	#Also add the hardcoded ones...
	newsids.update(getSteamNewsAppIDs())
	populateGames(newsids)

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

if __name__ == '__main__':
	import os.path
	import sys
	if not os.path.isfile(DBPATH):
		initDB()
		print("Created database " + DBPATH)
	else:
		print("Database already exists.")

	if len(sys.argv) >= 2:
		seedDatabase(sys.argv[1])
		print('Database seeded with games from ' + sys.argv[1])
	else:
		print("Run this script with a Steam ID or vanity URL as an argument to add its games to the list to fetch")
