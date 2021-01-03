#!/usr/bin/python3

import PyRSS2Gen
import bbcode
from datetime import datetime, timezone
import sqlite3

from SteamNews import DBPATH

# Generate RSS, see:
# https://cyber.harvard.edu/rss/rss.html
# https://docs.python.org/3.5/library/datetime.html
# https://pypi.python.org/pypi/PyRSS2Gen
# http://dalkescientific.com/Python/PyRSS2Gen.html


def getNewsRows():
    with sqlite3.connect(DBPATH) as db:
        db.row_factory = sqlite3.Row
        c = db.cursor()
        # TODO LIMIT #?
        c.execute('SELECT * FROM NewsItems ORDER BY date DESC')
        return c.fetchall()


def getGameSourceNamesForItem(gid):
    with sqlite3.connect(DBPATH) as db:
        c = db.cursor()
        c.execute('SELECT name FROM NewsSources NATURAL JOIN Games WHERE gid = ? ORDER BY appid', (gid,))
        # fetchall gives a bunch of tuples, so we have to unpack them with a for loop...
        return ', '.join(x[0] for x in c.fetchall())


def getSources(gid, label):
    names = getGameSourceNamesForItem(gid)
    if names == '':
        names = 'Unknown?'

    sources = '<p><i>Via <b>{}</b> for {}</i></p>\n'.format(label, names)
    return sources


def genRSSFeed(rssitems):
    pdate = datetime.now(timezone.utc)
    lbdate = rssitems[0].pubDate
    feed = PyRSS2Gen.RSS2(
        title='Steam Game News',
        link='http://store.steampowered.com/news/?feed=mygames',
        description='All of your Steam games\' news, combined!',
        pubDate=pdate,
        lastBuildDate=lbdate,
        items=rssitems
    )  # TODO should ttl get a value?
    return feed


def rowToRSSItem(row):
    if row['feed_type'] == 1:
        content = convertBBCodeToHTML(row['contents'])
    else:
        content = row['contents']

    sources = getSources(row['gid'], row['feedlabel'])

    item = PyRSS2Gen.RSSItem(
        title=row['title'],
        link=row['url'],
        description=sources + content,
        author=row['author'],
        guid=PyRSS2Gen.Guid(row['gid'], isPermaLink=False)
        pubDate=datetime.fromtimestamp(row['date'], timezone.utc)
    )  # omitted: categories, comments, enclosure, source
    return item

# RE: BBCode http://bbcode.readthedocs.org/
# TODO odd note: feed_type is 1 for steam community announcements (feedname == 'steam_community_announcements') and 0 otherwise
# this seems to be connected to the use of psuedo bbcode
# see https://steamcommunity.com/comment/Recommendation/formattinghelp

# Builtins: b, i, u, s, hr, sub, sup, list/*, quote (no author), code, center, color, url
# Steam: h1, h2, h3, b, u, i, strike, spoiler, noparse, url, list/*, olist/*, quote=author, code, table[tr[th, td]], previewyoutube
# More from Steam not in above url: img
# Adding: h1, h2, h3, strike, spoiler, noparse, olist (* already covered), table, tr, th, td, previewyoutube
# Ignoring special quote


# Spoiler CSS
'''
span.bb_spoiler {
	color: #000000;
	background-color: #000000;

	padding: 0px 8px;
}

span.bb_spoiler:hover {
	color: #ffffff;
}

span.bb_spoiler > span {
	visibility: hidden;
}

span.bb_spoiler:hover > span {
	visibility: visible;
}'''


def convertBBCodeToHTML(text):
    bb = bbcode.Parser()

    for tag in ('strike', 'table', 'tr', 'th', 'td', 'h1', 'h2', 'h3'):
        bb.add_simple_formatter(tag, '<{0}>%(value)s</{0}>'.format(tag))

    #bb.add_simple_formatter('img', '<img style="display: inline-block; max-width: 100%%;" src="%(value)s"></img>', strip=True, replace_links=False)
    bb.add_formatter('img', render_img, strip=True, replace_links=False)

    bb.add_formatter('previewyoutube', render_yt,
                     strip=True, replace_links=True)

    # The extra settings here are roughly based on the default formatters seen in the bbcode module source
    bb.add_simple_formatter(
        'noparse', '%(value)s', render_embedded=False, replace_cosmetic=False)  # see 'code'
    bb.add_simple_formatter('olist', '<ol>%(value)s</ol>', transform_newlines=False,
                            strip=True, swallow_trailing_newline=True)  # see 'list'
    bb.add_simple_formatter(
        'spoiler', '<span style="color: #000000;background-color: #000000;padding: 0px 8px;">%(value)s</span>')  # see 's' & above css

    return bb.format(text)


def render_img(tag_name, value, options, parent, context):
    # Community img tags now frequently look like
    # [img]{STEAM_CLAN_IMAGE}/27357479/d1048c635a5672f8efea79138bfd105b3cae552e.jpg[/img]
    # which should translate to <img src="https://steamcdn-a.akamaihd.net/steamcommunity/public/images/clans/27357479/d1048c635a5672f8efea79138bfd105b3cae552e.jpg">
    # e.g. {STEAM_CLAN_IMAGE} -> https://steamcdn-a.akamaihd.net/steamcommunity/public/images/clans
    CLAN_IMG_MARK = '{STEAM_CLAN_IMAGE}'
    CLAN_IMG_URL = 'https://steamcdn-a.akamaihd.net/steamcommunity/public/images/clans'
    IMG = '<img style="display: inline-block; max-width: 100%;" src="{}"></img>'

    src = value.replace(CLAN_IMG_MARK, CLAN_IMG_URL)
    return IMG.format(src)


def render_yt(tag_name, value, options, parent, context):
    # Youtube links in Steam posts look like
    # [previewyoutube=gJEgjiorUPo;full][/previewyoutube]
    # We *could* transform them into youtube embeds but
    # I'd rather have the choice to click on them, so just make them youtu.be links
    YT_TAG = '<a rel="nofollow" href="https://youtu.be/{0}">https://youtu.be/{0}</a>'
    try:
        # grab everything between the '=' (options dict) and the ';'
        # TODO is there always a ;full component?
        yt_id = options['previewyoutube'][:options['previewyoutube'].index(';')]
        return YT_TAG.format(yt_id)
    except (KeyError, ValueError):
        # TODO uhh... look at https://dcwatson.github.io/bbcode/formatters/ again
        return ''


if __name__ == '__main__':
    rssitems = list(map(rowToRSSItem, getNewsRows()))
    feed = genRSSFeed(rssitems)
    with open('MySteamNewsFeed.xml', 'w') as f:
        feed.write_xml(f, 'utf-8')
