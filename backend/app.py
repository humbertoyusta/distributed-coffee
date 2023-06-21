from flask import Flask, Blueprint, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
import os
import base64
import json
import boto3

app = Flask(__name__)

# Database configuration
DATABASE_HOST = os.getenv('DATABASE_HOST')
DATABASE_PORT = os.getenv('DATABASE_PORT')
DATABASE_USERNAME = os.getenv('DATABASE_USERNAME')
DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD')
DATABASE_NAME = os.getenv('DATABASE_NAME')

app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DATABASE_USERNAME}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app) # Initialize SQLAlchemy
sqs = boto3.client('sqs') # Initialize SQS client
QUEUE_URL = os.getenv('QUEUE_URL')  # Get your SQS Queue URL from environment variable


# Define a model for Users
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    coffee = db.Column(db.String(80), nullable=True)


# Define a blueprint for version 1 of our API
v1_blueprint = Blueprint('v1', __name__, url_prefix='/v1')


@v1_blueprint.route('/user', methods=['POST'])
def create_user():
    username = request.json.get('username')
    if not username:
        return jsonify({'error': 'Missing username in JSON body'}), 400

    user = User.query.filter_by(username=username).first()
    if user is not None:
        return jsonify({'error': 'User already exists'}), 400

    user = User(username=username)
    db.session.add(user)
    db.session.commit()

    # Send a message to SQS queue
    sqs.send_message(
        QueueUrl=QUEUE_URL,
        MessageBody=json.dumps({
            'userId': user.id,
            'username': user.username,
            'event': 'User Created'
        })
    )

    return jsonify({'message': 'User created successfully'}), 201


@v1_blueprint.route('/coffee/favourite', methods=['GET', 'POST'])
def favourite_coffee():
    # Basic auth token handling - getting user
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Basic '):
        return jsonify({'error': 'Invalid or missing authorization'}), 401
    auth_string = base64.b64decode(auth_header[6:]).decode('utf-8')
    user_name, password = auth_string.split(':')

    user = User.query.filter_by(username=user_name).first()
    if user is None:
        return jsonify({'error': 'Invalid or missing authorization'}), 401

    if request.method == 'POST':
        # Get favourite coffee from JSON body
        coffee = request.json.get('favouriteCoffee')
        if not coffee:
            return jsonify({'error': 'Missing favouriteCoffee in JSON body'}), 400

        # Update user's favourite coffee
        user.coffee = coffee
        db.session.commit()

        return leaderboard()

    elif request.method == 'GET':
        # Return user's favourite coffee
        return jsonify({'favouriteCoffee': user.coffee})


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