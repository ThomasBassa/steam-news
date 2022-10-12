#!/bin/bash
set -e

cd -- "$(dirname -- "${BASH_SOURCE[0]}" )"
source bin/activate
./SteamNews.py &> steam_fetch.log
./NewsPublisher.py &> steam_publish.log
cp MySteamNewsFeed.xml /mnt/dav/news/steam_news.xml
