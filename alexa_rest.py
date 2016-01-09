from main import main
from flask import (Flask,
                   request,
                   )
from settings import ALEXA_AUTH

app = Flask(__name__)

@app.route('/alexa', methods=['POST'])
def alexa():
    if request.form['pass'] == ALEXA_AUTH:
        main.delay()
        return 'Success', 200
    else:
        return 'FAIL', 400

if __name__ == '__main__':
    app.run(debug=True)
