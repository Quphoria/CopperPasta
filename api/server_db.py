import sqlite3 as sl
import time

database_file = 'pasta.db'

def connect(): 
    return sl.connect(database_file)

def get_time():
    return int(time.time()*1000)

threshold_dt = 60*60*24 # threshold in seconds

def get_default_threshold():
    return get_time() - (threshold_dt*1000)

def init_db():
    print("Database located at:", database_file)
    con = connect()
    with con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS Scrapbooks (
                ScrapbookID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                time INTEGER NOT NULL DEFAULT 0
            );
            """);
        con.execute("""
            CREATE TABLE IF NOT EXISTS Pastes (
                PasteID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                ScrapbookID INTEGER NOT NULL,
                type TEXT NOT NULL,
                data TEXT NOT NULL,
                client_uuid TEXT NOT NULL DEFAULT '',
                time INTEGER NOT NULL DEFAULT 0,
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
    with con:
        con.execute("DROP TABLE IF EXISTS Pastes;")
        con.execute("DROP TABLE IF EXISTS Scrapbooks;")
    con.close()

def clean_db(threshold_time=get_default_threshold()):
    con = connect()
    with con:
        con.execute("DELETE FROM Pastes WHERE ScrapbookID NOT IN (SELECT ScrapbookID FROM Scrapbooks);")
        con.execute("DELETE FROM Pastes WHERE time < ?;", (threshold_time,))
        con.execute("DELETE FROM Scrapbooks WHERE time < ? AND ScrapbookID NOT IN (SELECT ScrapbookID FROM Pastes);", (threshold_time,))
    con.close()

def delete_empty_scrapbooks():
    con = connect()
    with con:
        con.execute("DELETE FROM Scrapbooks WHERE ScrapbookID NOT IN (SELECT ScrapbookID FROM Pastes);")
    con.close()

def create_scrapbook(name):
    con = connect()
    with con:
        t = get_time()
        con.execute("""INSERT INTO Scrapbooks (name, time) SELECT * FROM (SELECT ?, ?) AS tmp
            WHERE NOT EXISTS (SELECT name FROM Scrapbooks WHERE name = ?) LIMIT 1;""", (name, t, name))
    con.close()
    clean_db()

def check_scrapbook_exists(name):
    con = connect()
    exists = False
    with con:
        d = con.execute("SELECT ScrapbookID FROM Scrapbooks WHERE name = ?;", (name,))
        exists = len(d.fetchall()) > 0
    con.close()
    clean_db()
    return exists

def delete_scrapbook(name):
    con = connect()
    with con:
        con.execute("DELETE FROM Scrapbooks WHERE name = ?;", (name,))
        # Delete orphaned pastes
        con.execute("DELETE FROM Pastes WHERE ScrapbookID NOT IN (SELECT ScrapbookID FROM Scrapbooks);")
    con.close()
    clean_db()

def create_post(scrapbook_name, post_type, data, client_uuid):
    con = connect()
    new_row = None
    with con:
        t = get_time()
        d = con.execute("""INSERT INTO Pastes (ScrapbookID, type, data, client_uuid, time)
            values((SELECT ScrapbookID FROM Scrapbooks WHERE name = ?),?,?,?,?)
            RETURNING PasteID, type, data, client_uuid, time;""", (scrapbook_name, post_type, data, client_uuid, t))
        data = d.fetchall()
        if len(data) > 0:
            new_row = data[0]
    con.close()
    clean_db()
    if new_row and len(new_row) > 0:
        return new_row

def get_pastes(scrapbook_name, start_id=0):
    con = connect()
    pastes = []
    with con:
        data = con.execute("""SELECT PasteID, type, data, client_uuid, time FROM Pastes
            WHERE PasteID > ? AND ScrapbookID = (SELECT ScrapbookID FROM Scrapbooks WHERE name = ?) ORDER BY PasteID ASC LIMIT 10;""", (start_id, scrapbook_name))
        for paste in data:
            pastes.append(paste)
    con.close()
    clean_db()
    return pastes


if __name__ == "__main__":
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
