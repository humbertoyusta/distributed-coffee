import time
import boto3
import os

# Initialize a new boto3 session
session = boto3.Session(
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION_NAME'),
)

# Get the SQS client from this session
sqs = session.client('sqs')

while True:
    # Get messages from the queue
    response = sqs.receive_message(
        QueueUrl=os.getenv('QUEUE_URL'),
        MaxNumberOfMessages=1,
        WaitTimeSeconds=5,
    )

    # If a message is received
    if 'Messages' in response:
        for message in response['Messages']:
            # Print out the body and ID
            print(f"Notification received for user {message['Body']}")

            # Now we must delete the message from the queue so it's not processed again
            sqs.delete_message(
                QueueUrl=os.getenv('QUEUE_URL'),
                ReceiptHandle=message['ReceiptHandle']
            )

    # Sleep for 5 seconds
    time.sleep(5)
