import api

api.debug = True
api.secure_cookies = False
api.cookie_path = "/"
api.cors_origin = "http://localhost:8000"

if __name__ == "__main__":
    api.main()