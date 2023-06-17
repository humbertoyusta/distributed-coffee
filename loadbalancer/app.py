from flask import Flask, redirect
from threading import Thread
from time import sleep
import requests
import os

app = Flask(__name__)

# Number of backend servers
num_backends = int(os.getenv("NUM_BACKENDS", 1))

# Define the base name of your backend servers
base_service_name = 'backend'

# List of your backend servers
services = [f"http://{base_service_name}-{i}:8080" for i in range(1, num_backends + 1)]
healthy_services = list(services)


def health_check():
    global healthy_services
    while True:
        for service in services:
            try:
                response = requests.get(f'{service}/health', timeout=2)
                if response.status_code == 200:
                    if service not in healthy_services:
                        healthy_services.append(service)
                else:
                    if service in healthy_services:
                        healthy_services.remove(service)
            except requests.exceptions.RequestException:
                if service in healthy_services:
                    healthy_services.remove(service)
        sleep(10)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 
'PATCH'])
def load_balancer(path):
    if not healthy_services:
        return 'No healthy backends', 503
    # Round-robin load balancing by rotating the list of healthy backends
    service = healthy_services.pop(0)
    healthy_services.append(service)
    # log the backend we are sending traffic to and send to a file app.log
    with open('app.log', 'a') as f:
        f.write(f'Sending traffic to {service}/{path}\n')
    return redirect(f'{service}/{path}', 307)


if __name__ == "__main__":
    # Start the service discovery and health check threads
    Thread(target=service_discovery).start()
    Thread(target=health_check).start()
    app.run(port=8080, host="0.0.0.0", debug=True)
