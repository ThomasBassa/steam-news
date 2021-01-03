#!/bin/bash
set -e

/usr/bin/python3 /home/pi/SteamNews/SteamNews.py &> steam_fetch.log
/usr/bin/python3 /home/pi/SteamNews/NewsPublisher.py &> steam_publish.log
cp MySteamNewsFeed.xml /mnt/dav/news/steam_news.xml

#Old mechanism to push to GitHub Pages
#cp MySteamNewsFeed.xml /home/pi/NewsSite/SteamNews.xml
#cd /home/pi/NewsSite
#git add SteamNews.xml
#git commit -m ":pager: Auto news update @ $(date -Idate)"
#git push origin gh-pages
