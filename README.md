# Steam News Feed Generator

## Motivations
Steam provides a set of news feeds at http://store.steampowered.com/news/ for information
about the games they sell.
If you're signed in, they even customize the entires to only your games at
http://store.steampowered.com/news/?feed=mygames
but this is not accessible outside of Steam short of web scraping.

However, Steam does provide an API for getting news items for individual games by their AppIDs.
The scripts in this repository allow one to fetch news for a large number of games and merge
them all into a single RSS feed, with about the same content as the `mygames` link above.
A SQLite database is used to store the list of AppIDs to fetch news for, as well as
a cache of all the news items retrieved.

## Usage
`Init.py` has utility methods to initialize a database (just a file, currently `SteamNews.db`)
with tables to store a games list and the news caches.

`SteamNews.py` fetches news from Steam's API. The AppIDs it fetches are based on what is stored
by the init script. There is an extra column in the DB to turn off fetching per-game,
but this currently needs to be done by hand with `sqlite3` or similar.
Fetching respects the `Expires` headers sent by the API and only adds
news items less than 30 days old.
(There is currently no mechanism to clean out older entries automatically.)

`NewsPublisher.py` converts all the news items in the same database file
to an RSS feed (an XML file) in the same directory.

`updateAndPublish.sh` is a sample Bash script to run the last two scripts
and copy the result where it will be published.
I run this on a Raspberry Pi, so there are some assumed directories there...

I previously used GitHub Pages on this repo to publish the feed-- this is now out of date.
I'll leave it up for historical reasons, but I don't intend to update it.

## Dependencies
This is a Python 3 project. The only external libraries in use are
[PyRSS2Gen](http://dalkescientific.com/Python/PyRSS2Gen.html)
and [bbcode](https://github.com/dcwatson/bbcode)

```bash
pip3 install -r requirements.txt
```

# Licence
MIT, go nuts.
