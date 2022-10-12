#!/usr/bin/env python3

import sqlite3
from urllib.request import urlopen
from urllib.error import HTTPError
import json

APPLIST_URL = 'https://api.steampowered.com/ISteamApps/GetAppList/v0002/'

def capture_and_save():
    try:
        applist_resp = urlopen(APPLIST_URL)
        applist = json.loads(applist_resp.read().decode('utf-8'))
        del applist_resp #probably unnecessary memory saving
    except HTTPError as e:
        print('Failed to get the app list: ' + str(e))
        return

    print('Got the app list.')
    #note: The raw JSON is about 8 MB large as of October 2022;
    # even after filtering appids with empty names, the SQLite db is about 11 MB
    # running VACUUM after the fact reduced it to 5.4 MB
    
    #Remove apps with no name; convert the rest into nice tuples for db insertion
    al = [(app['appid'], app['name']) for app in applist['applist']['apps'] if app['name']]
    
    print(f'Simplified the app list; has {len(al)} entries; converting to db...')

    try:
        #Doing this on disk is oddly slow, so do it in memory, then write to disk after
        db = sqlite3.connect(':memory:', isolation_level=None)
        c = db.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS AppIDs (appid INTEGER PRIMARY KEY, name TEXT NOT NULL)')
        c.executemany('INSERT OR REPLACE INTO AppIDs VALUES (?, ?)', al)

        print('Writing to disk...')
        c.execute('VACUUM INTO "appids.db"')
    finally:
        db.close()
    print('Done!')


#TODO search...?

if __name__ == '__main__':
    capture_and_save()
