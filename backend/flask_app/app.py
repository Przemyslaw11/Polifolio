from shared.logging_config import setup_logging
from flask import Flask, jsonify


logger = setup_logging()

app = Flask(__name__)


@app.route("/")
def home():
    logger.info("Home route accessed in Flask app")
    return jsonify({"message": "Welcome to the Polifolio supported by Flask!"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
