import os, sys
import server_db

server_db.config_file = os.path.join(sys.path[0], "pasta.conf")

if __name__ == "__main__":
    server_db.load_config()
    server_db.init_db()
    server_db.clean_db()