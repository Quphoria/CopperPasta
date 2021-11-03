import api
app = api.web_api

# https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-18-04

if __name__ == "__main__":
    app.run()