#!/bin/bash

/usr/bin/python3 /home/pi/SteamNews/NewsPublisher.py
cp MySteamNewsFeed.xml /home/pi/NewsSite/SteamNews.xml
cd /home/pi/NewsSite
git add SteamNews.xml
git commit -m ":pager: Auto news update @ $(date)"
git push origin gh-pages
