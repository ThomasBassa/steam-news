#!/usr/bin/python3

import PyRSS2Gen
from datetime import datetime, timezone
import sqlite3

from SteamNews import DBPATH

#TODO
# Generate RSS, see:
# https://cyber.harvard.edu/rss/rss.html
# https://docs.python.org/3.5/library/datetime.html
# https://pypi.python.org/pypi/PyRSS2Gen
# http://dalkescientific.com/Python/PyRSS2Gen.html

#TODO odd note: feed_type is 1 for steam community announcements (feedname == 'steam_community_announcements') and 0 otherwise
# this seems to be connected to the use of psuedo bbcode
#see https://steamcommunity.com/comment/Recommendation/formattinghelp

def getNewsRows():
	with sqlite3.connect(DBPATH) as db:
		db.row_factory = sqlite3.Row
		c = db.cursor()
		#TODO get rid of WHERE when bbcode conv done
		c.execute('SELECT * FROM NewsItems WHERE feed_type = 0 ORDER BY date DESC') #TODO LIMIT #?
		return c.fetchall()

def getGameSourceNamesForItem(gid):
	with sqlite3.connect(DBPATH) as db:
		c = db.cursor()
		c.execute('SELECT name FROM NewsSources NATURAL JOIN Games WHERE gid = ? ORDER BY appid', (gid,))
		# fetchall gives a bunch of tuples, so we have to unpack them with a for loop...
		return ', '.join(x[0] for x in c.fetchall())

def prependSources(gid, label, content):
	names = getGameSourceNamesForItem(gid)
	if names == '':
		names = 'Unknown?'
	
	sources = '<p><i>Via <b>{}</b> for {}</i></p>\n'.format(label, names)
	return sources + content

def genRSSFeed(rssitems):
	pdate = datetime.now(timezone.utc) #TODO may want to vary with update freq? 
	lbdate = rssitems[0].pubDate #TODO might be last item instead
	feed = PyRSS2Gen.RSS2(
		title = 'Steam Game News',
		link = 'http://store.steampowered.com/news/?feed=mygames',
		description = 'All of your Steam games\' news, combined!',
		pubDate = pdate,
		lastBuildDate = lbdate,
		items = rssitems
	) # TODO should ttl get a value?
	return feed

def rowToRSSItem(row):
	if row['feed_type'] == 1:
		content = convertBBCodeToHTML(row['contents'])
	else:
		content = row['contents']
	
	content = prependSources(row['gid'], row['feedlabel'], content)
	
	item = PyRSS2Gen.RSSItem(
		title = row['title'],
		link = row['url'],
		description = content,
		author = row['author'],
		guid = row['gid'],
		pubDate = datetime.fromtimestamp(row['date'], timezone.utc)
	) #omitted: categories, comments, enclosure, source
	#TODO account for appids/names somewhere
	return item

#TODO!
def convertBBCodeToHTML(text):
	return '<p>TODO: BBCode Conversion!</p>{}'.format(text)

# gid TEXT NOT NULL PRIMARY KEY,
# title TEXT,
# url TEXT,
# is_external_url INTEGER,
# author TEXT,
# contents TEXT,
# feedlabel TEXT,
# date INTEGER,
# feedname TEXT,
# feed_type INTEGER,
# appid INTEGER

if __name__ == '__main__':
	rssitems = list(map(rowToRSSItem, getNewsRows()))
	feed = genRSSFeed(rssitems)
	feed.write_xml(open('MySteamNewsFeed.xml', 'w'), 'utf-8')
