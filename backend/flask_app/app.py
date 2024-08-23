from .routes import register_routes
from flask import Flask, jsonify

app = Flask(__name__)

register_routes(app)


@app.route("/")
def home():
    return jsonify({"message": "Welcome to the Polifolio supported by Flask!"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
