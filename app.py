from flask import Flask, Blueprint, request, jsonify
from collections import Counter
import random
import base64

app = Flask(__name__)

# Define a blueprint for version 1 of our API
v1_blueprint = Blueprint('v1', __name__, url_prefix='/v1')

# Define some sample users and coffees
sample_users = ['Alice', 'Bob', 'Charlie', 'Dave', 'Eve', 'Frank', 'Grace', 'Heidi', 'Ivan', 'Judy']
sample_coffees = ['Espresso', 'Latte', 'Cappuccino', 'Americano']

# Initialize in memory storage for users and their favourite coffees
users = {user: random.choice(sample_coffees) for user in sample_users}
coffee_counter = Counter(users.values())

@v1_blueprint.route('/coffee/favourite', methods=['GET', 'POST'])
def favourite_coffee():
    # Basic auth token handling - getting user
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Basic '):
        return jsonify({'error': 'Invalid or missing authorization'}), 401
    auth_string = base64.b64decode(auth_header[6:]).decode('utf-8')
    user, password = auth_string.split(':')

    if request.method == 'POST':
        # Get favourite coffee from JSON body
        coffee = request.json.get('favouriteCoffee')
        if not coffee:
            return jsonify({'error': 'Missing favouriteCoffee in JSON body'}), 400

        # If user has already a favourite coffee, decrease its count
        if user in users and users[user] in coffee_counter:
            coffee_counter[users[user]] -= 1

        # Update user's favourite coffee and increase its count
        users[user] = coffee
        coffee_counter[coffee] += 1
        return leaderboard()

    elif request.method == 'GET':
        # Return user's favourite coffee
        return jsonify({'favouriteCoffee': users.get(user)})


@v1_blueprint.route('/admin/coffee/favourite/leadeboard', methods=['GET'])
def leaderboard():
    # Show the top 3 most popular coffees
    top_coffees = coffee_counter.most_common(3)
    return jsonify({'top3': [{coffee: count} for coffee, count in top_coffees]})

# Register our blueprint under the url_prefix /v1
app.register_blueprint(v1_blueprint)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
