from flask import Blueprint, jsonify

bp = Blueprint('routes', __name__)

@bp.route('/portfolio', methods=['GET'])
def get_portfolio():
    portfolio_data = {
        'obligations': [{'name': 'hello', 'value': 400}],
        'stocks': [{'name': 'world', 'quantity': 1, 'price': 4}],
        'total_value': 404
    }
    return jsonify(portfolio_data)

def register_routes(app):
    app.register_blueprint(bp)