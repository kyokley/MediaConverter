from main import main
from flask import (Flask,
                   jsonify,
                   request,
                   Response)
from settings import (WAITER_USERNAME,
                      WAITER_PASSWORD)

from functools import wraps

app = Flask(__name__)


def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == WAITER_USERNAME and password == WAITER_PASSWORD

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/alexa', methods=['POST'])
@requires_auth
def alexa():
    main.delay()
    return 'Success', 200

if __name__ == '__main__':
    app.run(debug=True)
