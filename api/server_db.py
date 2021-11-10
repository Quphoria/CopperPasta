import mysql.connector, json
import time
from contextlib import contextmanager

config_file = 'pasta.conf'

def connect(): 
    return sl.connect(database_file)

host = "MYSQL_HOST"
user = "MYSQL_USERNAME"
password = "MYSQL_PASSWORD"
database = "pasta"

@contextmanager
def closing(thing):
    try:
        yield thing
    finally:
        thing.close()

def load_config():
    global host, user, password, database
    try:
        with open(config_file) as f:
            config = json.load(f)
            host = config["host"]
            user = config["user"]
            password = config["password"]
            database = config["database"]
    except Exception as ex:
        with open(config_file, "w") as f:
            json.dump({
                "host": host,
                "user": user,
                "password": password,
                "database": database
            }, f, indent=4)
        print("Error with mysql config")
        raise ex

def connect():
    try:
        con = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
    except Exception as ex:
        print("Error connecting to database", ex)
        raise ex
    return con

def get_time():
    return int(time.time()*1000)

threshold_dt = 60*60*24 # threshold in seconds

def get_default_threshold():
    return get_time() - (threshold_dt*1000)

def init_db():
    con = connect()
    with closing(con.cursor()) as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Scrapbooks (
                ScrapbookID INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT,
                name TEXT NOT NULL,
                time BIGINT NOT NULL DEFAULT 0
            );
            """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Pastes (
                PasteID INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT,
                ScrapbookID INTEGER NOT NULL,
                type TEXT NOT NULL,
                data TEXT NOT NULL,
                client_uuid TEXT NOT NULL,
                time BIGINT NOT NULL DEFAULT 0,
                FOREIGN KEY (ScrapbookID) REFERENCES Scrapbooks(ScrapbookID),

                CHECK (length(type) > 0 AND
                    length(data) > 0 AND
                    length(client_uuid) > 0)
            );
        """)
        con.commit()
    con.close()

def delete_table():
    con = connect()
    with closing(con.cursor()) as cur:
        cur.execute("DROP TABLE IF EXISTS Pastes;")
        cur.execute("DROP TABLE IF EXISTS Scrapbooks;")
    con.commit()
    con.close()

def clean_db(threshold_time=get_default_threshold()):
    con = connect()
    with closing(con.cursor()) as cur:
        cur.execute("DELETE FROM Pastes WHERE ScrapbookID NOT IN (SELECT ScrapbookID FROM Scrapbooks);")
        cur.execute("DELETE FROM Pastes WHERE time < %s", (threshold_time,))
        cur.execute("DELETE FROM Scrapbooks WHERE time < %s AND ScrapbookID NOT IN (SELECT ScrapbookID FROM Pastes);", (threshold_time,))
        con.commit()
    con.close()

def delete_empty_scrapbooks():
    con = connect()
    with closing(con.cursor()) as cur:
        cur.execute("DELETE FROM Scrapbooks WHERE ScrapbookID NOT IN (SELECT ScrapbookID FROM Pastes);")
        con.commit()
    con.close()

def create_scrapbook(name):
    con = connect()
    with closing(con.cursor()) as cur:
        t = get_time()
        cur.execute("""INSERT INTO Scrapbooks (name, time) SELECT * FROM (SELECT %s, %s) AS tmp
            WHERE NOT EXISTS (SELECT name FROM Scrapbooks WHERE name = %s) LIMIT 1;""", (name, t, name))
        con.commit()
    con.close()

def check_scrapbook_exists(name):
    con = connect()
    exists = False
    with closing(con.cursor()) as cur:
        cur.execute("SELECT ScrapbookID FROM Scrapbooks WHERE name = %s;", (name,))
        exists = len(cur.fetchall()) > 0
    con.close()
    return exists

def delete_scrapbook(name):
    con = connect()
    with closing(con.cursor()) as cur:
        cur.execute("DELETE FROM Scrapbooks WHERE name = %s;", (name,))
        # Delete orphaned pastes
        cur.execute("DELETE FROM Pastes WHERE ScrapbookID NOT IN (SELECT ScrapbookID FROM Scrapbooks);")
        con.commit()
    con.close()

def create_post(scrapbook_name, post_type, data, client_uuid):
    con = connect()
    new_row = None
    with closing(con.cursor()) as cur:
        t = get_time()
        cur.execute("""INSERT INTO Pastes (ScrapbookID, type, data, client_uuid, time)
            values((SELECT ScrapbookID FROM Scrapbooks WHERE name = %s),%s,%s,%s,%s);""",
            (scrapbook_name, post_type, data, client_uuid, t))
        data = cur.fetchall()
        if len(data) > 0:
            new_row = data[0]
        con.commit()
    con.close()
    if new_row and len(new_row) > 0:
        return new_row

def get_pastes(scrapbook_name, start_id=0):
    con = connect()
    pastes = []
    with closing(con.cursor()) as cur:
        cur.execute("""SELECT PasteID, type, data, client_uuid, time FROM Pastes
            WHERE PasteID > %s AND ScrapbookID = (SELECT ScrapbookID FROM Scrapbooks WHERE name = %s) ORDER BY PasteID ASC LIMIT 10;""", (start_id, scrapbook_name))
        for paste in cur.fetchall():
            pastes.append(paste)
    con.close()
    return pastes


if __name__ == "__main__":
    load_config()
    init_db()
    delete_empty_scrapbooks()
    # delete_table()
    # init_db()
    # create_scrapbook("bruh")
    # create_scrapbook("bruh2")
    # create_scrapbook("bruh") # This shouldn't create the scrapbook
    # create_post("bruh", "test", "hello world!", "test_client_uuid")
    # d = get_pastes("bruh", 0)
    # print(d)
