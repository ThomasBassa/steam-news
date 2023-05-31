import sqlite3
import logging
import time

logger = logging.getLogger(__name__)

class NewsDatabase:
    def __init__(self, path=None):
        self.path = path or 'SteamNews.db'
        self.db = None

    def open(self):
        if not self.db:
            logger.debug('Opening DB @ %s', self.path)
            self.db = sqlite3.connect(self.path)
            self.db.row_factory = sqlite3.Row
            self.db.execute('PRAGMA foreign_keys = ON')

    def close(self, optimize=True):
        if self.db:
            if optimize:
                logger.debug('Optimizing DB before close...')
                self.db.execute('PRAGMA optimize')
            logger.debug('Closing DB @ %s', self.path)
            self.db.close()
            self.db = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        #only do sqlite optimize if we didn't close via exception
        self.close(optimize=exc_type is None)
        return False

    def first_run(self):
        #The indentation here is more for the benefit of the sqlite3 tool
        # than the python source... /shrug
        self.db.executescript('''
CREATE TABLE Games(
    appid INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    shouldFetch INTEGER NOT NULL DEFAULT 1);
CREATE TABLE ExpireTimes(
    appid INTEGER PRIMARY KEY
        REFERENCES Games(appid) ON DELETE CASCADE ON UPDATE CASCADE,
    unixseconds INTEGER NOT NULL DEFAULT 0);
CREATE TABLE NewsItems(
    gid TEXT NOT NULL PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT,
    is_external_url INTEGER,
    author TEXT,
    contents TEXT,
    feedlabel TEXT,
    date INTEGER NOT NULL DEFAULT (strftime('%s')),
    feedname TEXT,
    feed_type INTEGER,
    appid INTEGER NOT NULL);
CREATE TABLE NewsSources(
    gid TEXT NOT NULL
        REFERENCES NewsItems(gid) ON DELETE CASCADE ON UPDATE CASCADE,
    appid INTEGER NOT NULL
        REFERENCES Games(appid) ON DELETE CASCADE ON UPDATE CASCADE,
    PRIMARY KEY(gid, appid));
CREATE INDEX NewsDateIdx ON NewsItems(date);
CREATE INDEX NewsSourceAppIDIdx ON NewsSources(appid);''')

        #having news item appid foreign key on games can break,
        # since the news appid might not be the one we fetched against
        #FK in NewsSources -> Games is fine, though removing entries
        # from NewsSources could lead to loss of data useful for publishing...
        self.db.commit()
        logger.info('Created DB tables!')

    def add_games(self, games: dict):
        """Given a dict of appid: name, populate them in the database."""
        with self.db as db:
            cur = db.executemany('INSERT OR IGNORE INTO Games VALUES (?, ?, 1)',
                    games.items())
            logger.info('Added %d new games to be fetched.', cur.rowcount)

    def get_games_like(self, name: str):
        #Since you can't do '%?%' in the SQL, do that here instead
        name = name.strip().strip('%')
        if name:
            n = '%' + name + '%'
            c = self.db.execute('''SELECT * FROM Games
                WHERE name LIKE ? ORDER BY name''', (n,))
        else:
            c = self.db.execute('SELECT * FROM Games ORDER BY name')
        return c.fetchall()

    def disable_fetching_ids(self, appids):
        with self.db as db:
            #sadly can't use executemany() w/ a "bare" list-- each item needs to be a tuple
            for aid in appids:
                db.execute('UPDATE Games SET shouldFetch = 0 WHERE appid = ?', (aid,))

    def enable_fetching_ids(self, appids):
        with self.db as db:
            for aid in appids:
                db.execute('UPDATE Games SET shouldFetch = 1 WHERE appid = ?', (aid,))

    def get_fetch_games(self):
        c = self.db.execute('SELECT appid, name FROM Games WHERE shouldFetch != 0')
        return dict(c.fetchall())

    def update_expire_time(self, appid, expires):
        with self.db as db:
            db.execute('INSERT OR REPLACE INTO ExpireTimes VALUES (?, ?)',
                  (appid, expires))

    def is_news_cached(self, appid):
        c = self.db.execute('SELECT unixseconds FROM ExpireTimes WHERE appid = ?',
                (appid,))
        exptime = c.fetchone()
        if exptime is None: #i.e. appid not found
            return False
        else:
            #TODO maybe use datetime.timestamp() & now() instead?
            return time.time() < exptime[0]

    def insert_news_item(self, ned: dict):
        #TODO maybe convert the dict to a namedtuple...?
        with self.db as db:
            db.execute('''INSERT OR IGNORE INTO NewsItems
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (ned['gid'], ned['title'], ned['url'], ned['is_external_url'],
                    ned['author'], ned['contents'], ned['feedlabel'], ned['date'],
                    ned['feedname'], ned['feed_type'], ned['appid']))

            db.execute('INSERT OR IGNORE INTO NewsSources VALUES (?, ?)',
                    (ned['gid'], ned['realappid']))

    def get_news_rows(self):
        #TODO generator shenanigans instead of fetchall()?
        #sadly our sqlite3 version isn't new enough for unixepoch()
        # so we have to use strftime('%s') for sqlite to make a unix timestamp
        c = self.db.execute('''SELECT * FROM NewsItems
            WHERE date >= strftime('%s', 'now', '-30 day')
            ORDER BY date DESC''')
        return c.fetchall()

    def get_source_names_for_item(self, gid):
        c = self.db.execute('''SELECT name
            FROM NewsSources NATURAL JOIN Games
            WHERE gid = ? ORDER BY appid''', (gid,))
        #fetchall gives a bunch of tuples, so we have to unpack them with a for loop...
        return list(x[0] for x in c.fetchall())
