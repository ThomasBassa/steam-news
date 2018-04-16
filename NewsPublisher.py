#!/usr/bin/python3

import PyRSS2Gen
from datetime import datetime, timezone
import sqlite3

#TODO
# Generate RSS, see:
# https://cyber.harvard.edu/rss/rss.html
# https://docs.python.org/3.5/library/datetime.html
# https://pypi.python.org/pypi/PyRSS2Gen
# http://dalkescientific.com/Python/PyRSS2Gen.html

#TODO odd note: feed_type is 1 for steam community announcements (feedname == 'steam_community_announcements') and 0 otherwise
# this seems to be connected to the use of psuedo bbcode
#see https://steamcommunity.com/comment/Recommendation/formattinghelp

def genRSSFeed(rssitems):
	pdate = datetime.now(timezone.utc) #TODO may want to vary with update freq? 
	bdate = rssitems[0].pubDate #TODO might be last item instead
	feed = PyRSS2Gen.RSS2(
		title = 'Test Feed',
		link = 'http://store.steampowered.com/news/?feed=mygames',
		description = 'Brilliance',
		pubDate = pdate,
		lastBuildDate = bdate
		items = rssitems
	) # TODO should ttl get a value?
	return feed

def rowToRSSItem(row):
	if row['feed_type'] == 1:
		content = convertBBCodeToHTML(row['contents'])
	else:
		content = row['contents']
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
	pass