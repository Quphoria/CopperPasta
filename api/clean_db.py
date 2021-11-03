import server_db

server_db.database_file = os.path.join(sys.path[0], "pasta.db")

if __name__ == "__main__":
    server_db.init()
    server_db.clean_db()