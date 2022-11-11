# Steam News Feed Generator

## Motivations
Steam provides a set of news feeds at http://store.steampowered.com/news/ for information
about the games they sell.
If you're signed in, they even customize the entires to only your games at
http://store.steampowered.com/news/?feed=mygames
but this is not accessible outside of Steam short of web scraping.

However, Steam does provide an API for getting news items for individual games
by their AppIDs. The scripts in this repository allow one to fetch news for
a large number of games and merge them all into a single RSS feed,
with roughly the same content as the `mygames` link above.
A SQLite database is used to store the list of AppIDs to fetch news for,
as well as a cache of all the news items retrieved.

## Usage
`SteamNews.py` is the main script. Run it with `--help` to get the command-line
arguments it works with.

On first install, run
`./SteamNews.py --first-run --add-profile-games <Steam ID/vanity URL ending>`
to create the database & seed it with a games list from a **public** Steam profile.
You can re-run with `-a`/`--add-profile-games` to combine or update from other
profiles, if you like.

From there, if you know you don't need news for some of your games, run with
`-g`/`--edit-games-like` followed by a partial name of a game in question--
you'll get a `whiptail` dialog to turn those on or off.
Other editing of the games list (e.g. adding games you don't own on Steam)
still needs to be done by hand with `sqlite3` or similar.

Once you're happy with the games list, run with `-f`/`--fetch` to pull
news from Steam's API. The AppIDs it fetches are based on the games pulled from
the profile(s) in the above steps, minus those disabled by "editing".
Fetching respects the `Expires` headers sent by the API and only adds
the 10 most recent news items, as long as they're less than 30 days old.

There is currently no mechanism to clean out older news items automatically,
but the disk space usage of the database has been small enough not to bother.
I've been using this program myself since March 2018 (according to my oldest
news item).  As of November 2022, with a library of about 300 games,
I've accumulated about 3700 news items... and the database only takes up 11 MB.
Run `VACUUM;` in SQLite once in a while and you'll be fine.

Finally, you can run `-p`/`--publish` followed by a path to an XML file to output
to convert the newest news items into an RSS feed.

`updateAndPublish.sh` is a sample Bash script to fetch, publish,
and copy the result where it will be published.
Note that you can combine `--fetch` and `--publish` to do both in the same run!

I previously used GitHub Pages on this repository to publish the feed--
this is now out of date.  I'll leave it up for historical reasons,
but I don't intend to update it.

## Dependencies
This is a Python 3 project. The only external libraries in use are
[PyRSS2Gen](http://dalkescientific.com/Python/PyRSS2Gen.html)
and [bbcode](https://github.com/dcwatson/bbcode).

```bash
python3 -m pip install -r requirements.txt
```

You'll also want the `whiptail` program installed for the terminal interface to edit
which games to fetch; otherwise you'll need to use the `sqlite3` program directly.

# Licence
MIT, go nuts.
