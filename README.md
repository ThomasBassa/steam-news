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
`SteamNews.py` has utility methods to initialize a database (just a file, currently `SteamNews.db`)
and fetch news from Steam's API. It respects the `Expires` headers sent by the API and only stores
news items less than 30 days old.

`NewsPublisher.py` converts the news items in the same database file to an RSS feed (an XML file)
in the same directory.

`Publish.bash` is a sample Bash script to run NewsPublisher and commit the resulting feed to a Git repo
(since I'm using GitHub Pages to publish my feed). The script runs with the assumption that
`git push` won't require authorization (use an SSH key). It also assumes all of the directories
in use for the project, which are running on a Raspberry Pi.

# Licence
MIT, go nuts.
