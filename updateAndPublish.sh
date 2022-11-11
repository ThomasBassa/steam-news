#!/bin/bash
set -e

cd -- "$(dirname -- "${BASH_SOURCE[0]}" )"
source bin/activate
./SteamNews.py --verbose --fetch --publish steam_news.xml &> log_steam_news.log
cp steam_news.xml /mnt/dav/news/steam_news.xml
