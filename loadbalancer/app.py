from flask import Flask, redirect
from threading import Thread
from time import sleep
import requests
import boto3
import json

app = Flask(__name__)

# Setup AWS S3 client
s3 = boto3.client('s3')

# Define the bucket and object key
bucket = 'hyusta-example-bucket'
key = 'load-balancer-config.json'

# Retrieve object from S3
s3_object = s3.get_object(Bucket=bucket, Key=key)
config_file = s3_object['Body'].read().decode('utf-8')
config = json.loads(config_file)

# Number of backend servers
num_backends = int(config.get("number_of_backends", 1))

# Define the base name of your backend servers
base_service_name = config.get("base_service_name", "service")

print(f"Number of backends: {num_backends}")
print(f"Base service name: {base_service_name}")

# List of your backend servers
internal_services = [f"http://{base_service_name}-{i}:8080" for i in range(1, num_backends + 1)]
external_services = [f"http://localhost:{8080 + i}" for i in range(1, num_backends + 1)]
healthy_services = list(zip(internal_services, external_services))

def health_check():
    global healthy_services
    while True:
        for internal_service, external_service in zip(internal_services, external_services):
            try:
                response = requests.get(f'{internal_service}/health', timeout=2)
                if response.status_code == 200:
                    if (internal_service, external_service) not in healthy_services:
                        healthy_services.append((internal_service, external_service))
                else:
                    if (internal_service, external_service) in healthy_services:
                        healthy_services.remove((internal_service, external_service))
            except requests.exceptions.RequestException:
                if (internal_service, external_service) in healthy_services:
                    healthy_services.remove((internal_service, external_service))
        sleep(10)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE',
                                    'PATCH'])
def load_balancer(path):
    if not healthy_services:
        return 'No healthy backends', 503
    # Round-robin load balancing by rotating the list of healthy backends
    internal_service, external_service = healthy_services.pop(0)
    healthy_services.append((internal_service, external_service))

    print(f'Load balancing request to {internal_service}/{path}')
    return redirect(f'{external_service}/{path}', 307)


if __name__ == "__main__":
    # Start the service discovery and health check threads
    Thread(target=health_check).start()
    app.run(port=8080, host="0.0.0.0", debug=True)
