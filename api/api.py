import json, os, sys, secrets, re, datetime
from flask import Flask, request
from json.decoder import JSONDecodeError

import server_db

debug = False
debug_port = 5000
secure_cookies = True
cookie_path = "/api/"
cors_origin = "https://pasta.quphoria.co.uk"
require_auth = True

MAX_CONTENT_LENGTH = 64 * 1024 * 1024 # 64MB max content length

server_db.config_file = os.path.join(sys.path[0], "pasta.conf")

words = []
# Load wordlist from https://raw.githubusercontent.com/sapbmw/The-Oxford-3000/master/The_Oxford_3000.txt
# With some words removed, approx 3181 words left
with open(os.path.join(sys.path[0], "words.txt"), "r") as f:
    words = [l.strip() for l in f.readlines()]

sortedwords = sorted(words, key=len)
print("The longest word in the wordlist is:", sortedwords[-1], len(sortedwords[-1]))

web_api = Flask(__name__)
web_api.config["CORS_HEADERS"] = "Content-Type"

def build_cors_headers(response):
    response.headers.add("Access-Control-Allow-Credentials", "true")
    response.headers.add("Access-Control-Allow-Origin", cors_origin)
    response.headers.add('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept')
    response.headers.add('Access-Control-Allow-Methods', "*")

def getCookieExpiration(days=1):
    return datetime.datetime.now() + datetime.timedelta(days=days)

def _build_cors_preflight_response():
    response = web_api.response_class()
    build_cors_headers(response)
    return response

app_username = "user"
app_password = ""
try:
    with open(os.path.join(sys.path[0], "auth.json.secret"), "r") as f:
        auth_config = json.load(f)
        app_password = auth_config["app_password"]
        assert len(app_password) > 0, "app_password empty"
        require_auth = auth_config["require_auth"]
except:
    print("Error loading auth config: (app_password cannot be empty)")
    default_auth_config = {
        "app_password": "",
        "require_auth": True
    }
    with open(os.path.join(sys.path[0], "auth.json.secret"), "w") as f:
        json.dump(default_auth_config, f)
    sys.exit(1)

def check_auth_headers(request):
    if not require_auth:
        return True
    auth = request.cookies.get("auth")

    return (request.authorization and \
        request.authorization.username == app_username and \
        request.authorization.password == app_password) or \
        (auth and auth == app_password)

def validate_uuid(uuid):
    # min length is 4 * 4 + 3 - 1 = 18   1 less than minimim possible for safety
    # max length is 16 * 4 + 3 + 1 = 68  1 longer than maximum possible for safety
    return uuid and re.match(r"^[a-z\-]{18,68}$", uuid)
    
def gen_resp(status, data):
    response = web_api.response_class(
        response=json.dumps(data),
        status=status,
        mimetype='application/json'
    )
    build_cors_headers(response)
    return response

@web_api.before_request
def handle_chunking():
    """
    Sets the "wsgi.input_terminated" environment flag, thus enabling
    Werkzeug to pass chunked requests as streams; this makes the API
    compliant with the HTTP/1.1 standard.  The gunicorn server should set
    the flag, but this feature has not been implemented.
    """

    transfer_encoding = request.headers.get("Transfer-Encoding", None)
    if transfer_encoding == "chunked":
        request.environ["wsgi.input_terminated"] = True

@web_api.route('/', methods=['GET', 'OPTIONS'])
def api_root():
    resp = _build_cors_preflight_response()
    resp.headers.add('Access-Control-Allow-Methods', "GET, OPTIONS")
    return resp

@web_api.route('/paste', methods=['PUT', 'OPTIONS'])
def api_paste():
    if request.method == "OPTIONS": # CORS preflight
        resp = _build_cors_preflight_response()
        resp.headers.add('Access-Control-Allow-Methods', "PUT, OPTIONS")
        return resp
    elif request.method == "PUT" and check_auth_headers(request) and request.content_length < MAX_CONTENT_LENGTH:
        data = request.get_json()
        uuid = request.cookies.get("uuid")
        if data and "scrapbook" in data and "type" in data and "data" in data and validate_uuid(uuid):
            try:
                assert data["type"] in ["text", "image", "file"], "Invalid type: " + data["type"]
                new_post = server_db.create_post(data["scrapbook"], data["type"], data["data"], uuid)
                if new_post:
                    # Just return post id
                    return gen_resp(201, {"created": new_post[0]})
            except Exception as ex:
                print("Error creating paste:", ex)    
    return gen_resp(500, None)

@web_api.route('/pastes', methods=['POST', 'OPTIONS'])
def api_pastes():
    if request.method == "OPTIONS": # CORS preflight
        return _build_cors_preflight_response()
    elif request.method == "POST" and check_auth_headers(request):
        data = request.get_json()
        if data and "scrapbook" in data:
            try:
                start_id = 0
                if "start_id" in data:
                    start_id = int(data["start_id"])
                pastes = server_db.get_pastes(data["scrapbook"], start_id)
                if len(pastes) == 0:
                    if not server_db.check_scrapbook_exists(data["scrapbook"]):
                        return gen_resp(200, {"error": "deleted"})
                return gen_resp(200, pastes)
            except Exception as ex:
                print("Error gettings pastes:", ex)  
    return gen_resp(500, None)

@web_api.route('/scrapbook', methods=['POST', 'DELETE', 'OPTIONS'])
def api_scrapbook():
    if request.method == "OPTIONS": # CORS preflight
        resp = _build_cors_preflight_response()
        resp.headers.add('Access-Control-Allow-Methods', "POST, DELETE, OPTIONS")
        return resp
    elif request.method == "POST" and check_auth_headers(request):
        data = request.get_json()
        if data and "scrapbook" in data:
            try:
                if server_db.check_scrapbook_exists(data["scrapbook"]):
                    return gen_resp(200, {"scrapbook": data["scrapbook"]})
                else:
                    return gen_resp(404, None)
            except Exception as ex:
                print("Error fetching scrapbook:", ex)
        else:
            try:
                scrapbook_uuid = gen_uuid()
                server_db.create_scrapbook(scrapbook_uuid)
                return gen_resp(201, {"scrapbook": scrapbook_uuid})
            except Exception as ex:
                print("Error creating scrapbook:", ex)
    elif request.method == "DELETE" and check_auth_headers(request):
        data = request.get_json()
        if data and "scrapbook" in data:
            try:
                server_db.delete_scrapbook(data["scrapbook"])
                return gen_resp(200, None)
            except Exception as ex:
                print("Error deleting scrapbook:", ex)
    return gen_resp(500, None)

@web_api.route('/uuid', methods=['GET', 'OPTIONS'])
def api_uuid():
    if request.method == "OPTIONS": # CORS preflight
        return _build_cors_preflight_response()
    elif request.method == "GET" and check_auth_headers(request):
        uuid = request.cookies.get("uuid")
        # Min length 19 as 4*4 + 3 = 19
        if not validate_uuid(uuid):
            uuid = gen_uuid()
        resp = gen_resp(200, {"uuid": uuid})
        resp.set_cookie("uuid", uuid, expires=getCookieExpiration(30), secure=secure_cookies, path=cookie_path)
        return resp
    return gen_resp(500, None)

@web_api.route('/auth', methods=['GET', 'OPTIONS'])
def api_auth():
    if request.method == "OPTIONS": # CORS preflight
        return _build_cors_preflight_response()
    elif request.method == "GET":
        auth = request.args.get('auth')
        if check_auth_headers(request) or (auth and auth == app_password):
            resp = gen_resp(200, None)
            if require_auth: # don't leak app_password when auth is not required
                resp.set_cookie("auth", app_password, expires=getCookieExpiration(), secure=secure_cookies, path=cookie_path)
            return resp
    return gen_resp(500, None)

def gen_uuid(length=4):
    uuid = ""
    assert length > 0, "Why do you want a 0 word uuid??" # assertion to prevent accidentally security flaws
    for i in range(length):
        uuid += secrets.choice(words) + "-"
    if length > 0:
        uuid = uuid[:-1] # remove trailing -
    return uuid

def init():
    server_db.load_config()
    server_db.init_db()

def main():
    web_api.run(host="0.0.0.0", port=debug_port, debug=debug, use_reloader=False)

init() # init even if not main
if __name__ == "__main__":
    main()