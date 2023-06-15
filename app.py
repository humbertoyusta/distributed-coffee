from flask import Flask, Blueprint, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
import os
import base64

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')  # e.g. postgresql://user:pass@localhost/dbname
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Define a model for Users
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    coffee = db.Column(db.String(80), nullable=True)

# Define a blueprint for version 1 of our API
v1_blueprint = Blueprint('v1', __name__, url_prefix='/v1')

@v1_blueprint.route('/coffee/favourite', methods=['GET', 'POST'])
def favourite_coffee():
    # Basic auth token handling - getting user
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Basic '):
        return jsonify({'error': 'Invalid or missing authorization'}), 401
    auth_string = base64.b64decode(auth_header[6:]).decode('utf-8')
    user_name, password = auth_string.split(':')

    if request.method == 'POST':
        # Get favourite coffee from JSON body
        coffee = request.json.get('favouriteCoffee')
        if not coffee:
            return jsonify({'error': 'Missing favouriteCoffee in JSON body'}), 400

        # Find user in database or create a new one
        user = User.query.filter_by(username=user_name).first()
        if user is None:
            user = User(username=user_name)
            db.session.add(user)

        # Update user's favourite coffee
        user.coffee = coffee
        db.session.commit()

        return leaderboard()

    elif request.method == 'GET':
        # Return user's favourite coffee
        user = User.query.filter_by(username=user_name).first()
        if user is not None:
            return jsonify({'favouriteCoffee': user.coffee})
        else:
            return jsonify({'error': 'User not found'}), 404

@v1_blueprint.route('/admin/coffee/favourite/leadeboard', methods=['GET'])
def leaderboard():
    # Show the top 3 most popular coffees
    top_coffees = db.session.query(User.coffee, func.count(User.coffee))\
                             .group_by(User.coffee)\
                             .order_by(func.count(User.coffee).desc())\
                             .limit(3)\
                             .all()
    return jsonify({'top3': [{coffee: count} for coffee, count in top_coffees]})

# Register our blueprint under the url_prefix /v1
app.register_blueprint(v1_blueprint)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

if __name__ == "__main__":
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=8080)
