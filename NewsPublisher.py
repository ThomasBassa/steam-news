#!/usr/bin/env python3

import logging
from datetime import datetime, timezone
import difflib
from functools import partial

import PyRSS2Gen
import bbcode

from database import NewsDatabase

# Generate RSS, see:
# https://cyber.harvard.edu/rss/rss.html
# https://docs.python.org/3.5/library/datetime.html
# https://pypi.python.org/pypi/PyRSS2Gen
# http://dalkescientific.com/Python/PyRSS2Gen.html

logger = logging.getLogger(__name__)

def genRSSFeed(rssitems):
    pdate = datetime.now(timezone.utc)
    lbdate = rssitems[0].pubDate
    return PyRSS2Gen.RSS2(
        title='Steam Game News',
        link='http://store.steampowered.com/news/?feed=mygames',
        description='All of your Steam games\' news, combined!',
        pubDate=pdate,
        lastBuildDate=lbdate,
        items=rssitems
    )  # TODO should ttl get a value?


def rowToRSSItem(row, db: NewsDatabase):
    if row['feed_type'] == 1:
        content = convertBBCodeToHTML(row['contents'])
    else:
        content = row['contents']

    #Add the title of the game to the article title,
    #  but only if not present according to 'in' or difflib.get_close_matches.
    #get_close_matches isn't great for longer titles given the split() but /shrug
    #There are other libraries for fuzzy matching but difflib is built in...
    games = db.get_source_names_for_item(row['gid']) or ['Unknown?']
    rsstitle = row['title']
    if len(games) > 1:
        rsstitle = '[Multiple] ' + rsstitle
    elif (games[0] not in rsstitle and not
            difflib.get_close_matches(games[0].lower(), rsstitle.lower().split(),
                n=1, cutoff=0.8)):
        rsstitle = '[{}] {}'.format(games[0], rsstitle)
    #else game title is in article title, do nothing

    source = row['feedlabel']
    if not source:
        #patch over missing feedname in Steam News;
        # seems to be the only news source w/o feedlabels?
        if row['feedname'] == 'steam_community_blog':
            source = 'Steam Community Blog'
        else:
            #shrug.
            source = row['feedname'] or 'Unknown Source'
    sources = '<p><i>Via <b>{}</b> for {}</i></p>\n'.format(
            source, ', '.join(games))

    item = PyRSS2Gen.RSSItem(
        title=rsstitle,
        link=row['url'],
        description=sources + content,
        author=row['author'],
        guid=PyRSS2Gen.Guid(row['gid'], isPermaLink=False),
        pubDate=datetime.fromtimestamp(row['date'], timezone.utc)
    )  # omitted: categories, comments, enclosure, source
    return item

# RE: BBCode http://bbcode.readthedocs.org/
# note: feed_type is 1 for steam community announcements
#  (feedname usually == 'steam_community_announcements') and 0 otherwise
# this seems to be connected to the use of Steam's bbcode
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
    bb.add_simple_formatter('spoiler',
            '<span style="color: #000000;background-color: #000000;padding: 0px 8px;">%(value)s</span>')  # see bbcode 's' & above css

    return bb.format(text)

# Community img tags frequently look like
# [img]{STEAM_CLAN_IMAGE}/27357479/d1048c635a5672f8efea79138bfd105b3cae552e.jpg[/img]
# which should translate to <img src="https://steamcdn-a.akamaihd.net/steamcommunity/public/images/clans/27357479/d1048c635a5672f8efea79138bfd105b3cae552e.jpg">
# e.g. {STEAM_CLAN_IMAGE} -> https://steamcdn-a.akamaihd.net/steamcommunity/public/images/clans
# Steam News (official blog) has a newer tag type
# {STEAM_CLAN_LOC_IMAGE}/27766192/45e4984a51cabcc390f9e1c1d2345da97f744851.gif becomes...
# https://cdn.akamai.steamstatic.com/steamcommunity/public/images/clans/27766192/45e4984a51cabcc390f9e1c1d2345da97f744851.gif

#sort of makes me wonder if these are interchangable...
IMG_REPLACEMENTS = {
    '{STEAM_CLAN_IMAGE}': 'https://steamcdn-a.akamaihd.net/steamcommunity/public/images/clans',
    '{STEAM_CLAN_LOC_IMAGE}': 'https://cdn.akamai.steamstatic.com/steamcommunity/public/images/clans',
}

IMG = '<img style="display: inline-block; max-width: 100%;" src="{}"></img>'

def render_img(tag_name, value, options, parent, context):
    src = value
    for mark, replaced in IMG_REPLACEMENTS.items():
        src = src.replace(mark, replaced)
    return IMG.format(src)


YT_TAG = '<a rel="nofollow" href="https://youtu.be/{0}">https://youtu.be/{0}</a>'

def render_yt(tag_name, value, options, parent, context):
    # Youtube links in Steam posts look like
    # [previewyoutube=gJEgjiorUPo;full][/previewyoutube]
    # We *could* transform them into youtube embeds but
    # I'd rather have the choice to click on them, so just make them youtu.be links
    try:
        # grab everything between the '=' (options dict) and the ';'
        # TODO is there always a ;full component?
        yt_id = options['previewyoutube'][:options['previewyoutube'].index(';')]
        return YT_TAG.format(yt_id)
    except (KeyError, ValueError):
        # TODO uhh... look at https://dcwatson.github.io/bbcode/formatters/ again
        return ''

def publish(db: NewsDatabase, output_path=None):
    if not output_path:
        output_path = 'steam_news.xml'
    logger.info('Generating RSS feed...')
    row_func = partial(rowToRSSItem, db=db)
    rssitems = list(map(row_func, db.get_news_rows()))
    feed = genRSSFeed(rssitems)
    logger.info('Writing to %s...', output_path)
    with open(output_path, 'w') as f:
        feed.write_xml(f, 'utf-8')
    logger.info('Published!')

if __name__ == '__main__':
    import sys
    logging.basicConfig(stream=sys.stdout,
            format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            level=logging.DEBUG)
    with NewsDatabase() as db:
        publish(db)
