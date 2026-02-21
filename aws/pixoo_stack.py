import os

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_lambda_event_sources as lambda_sources
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_sqs as sqs
from aws_cdk.aws_lambda_python_alpha import PythonFunction
from constructs import Construct


class PixooStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        pixoo_queue = sqs.Queue(
            self,
            "PixooQueue",
            visibility_timeout=Duration.seconds(60),
        )

        pixoo_bucket = s3.Bucket(
            self,
            "PixooBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )

        lambda_props = {
            "runtime": _lambda.Runtime.PYTHON_3_14,
            "entry": "../local",
            "timeout": Duration.seconds(10),
            "handler": "lambda_handler",
        }

        # Lambda that is triggered by Cloudwatch
        producer_lambda = PythonFunction(
            self,
            "Producer",
            index="producer.py",
            environment={
                "QUEUE_URL": pixoo_queue.queue_url,
            },
            **lambda_props,
        )
        pixoo_queue.grant_send_messages(producer_lambda)

        # Lambda that is triggered by SQS
        consumer_lambda = PythonFunction(
            self,
            "Consumer",
            index="consumer.py",
            environment={
                "PIXOO_URL": os.environ["PIXOO_URL"],
                "TFL_APP_KEY": os.environ["TFL_APP_KEY"],
                "BUCKET_NAME": pixoo_bucket.bucket_name,
                "TZ": "Europe/London",
            },
            **lambda_props,
        )
        pixoo_bucket.grant_read_write(consumer_lambda)

        event_source = lambda_sources.SqsEventSource(pixoo_queue, batch_size=1)
        consumer_lambda.add_event_source(event_source)

        # Trigger the producer lambda once per minute
        pixoo_rule = events.Rule(
            self,
            "PixooRule",
            schedule=events.Schedule.rate(Duration.minutes(1)),
        )
        pixoo_rule.add_target(targets.LambdaFunction(producer_lambda))

        CfnOutput(self, "PixooRegion", value=self.region)
        CfnOutput(self, "PixooBucketName", value=pixoo_bucket.bucket_name)
        CfnOutput(self, "PixooQueueURL", value=pixoo_queue.queue_url)
