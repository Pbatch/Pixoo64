import os
from datetime import datetime, timezone

import boto3
from my_config import config

sqs = boto3.client("sqs")


def _filter_messages(messages):
    filtered_messages = []

    weekday = datetime.now(timezone.utc).weekday()
    for message in messages:
        if message.weekday is not None and message.weekday != weekday:
            continue

        filtered_messages.append(message)
    return filtered_messages


def lambda_handler(event, context):
    messages = _filter_messages(config.messages)
    for i in range(config.messages_per_minute):
        sqs.send_message(
            QueueUrl=os.environ["QUEUE_URL"],
            MessageBody=messages[i % len(messages)].to_message_body(),
            DelaySeconds=int(60 * i / config.messages_per_minute),
        )
    return None
