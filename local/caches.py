import json
import os

import boto3


class S3Cache:
    def __init__(self):
        self.s3 = boto3.client("s3")
        self.bucket_name = os.environ["BUCKET_NAME"]

    def get(self, key):
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=key)
        except self.s3.exceptions.NoSuchKey:
            return {}, None

        last_updated = response["LastModified"].timestamp()
        results = json.loads(response["Body"].read().decode("utf-8"))
        return results, last_updated

    def save(self, results, key):
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=json.dumps(results),
            ContentType="application/json",
        )

class LocalCache:
    def __init__(self, cache_dir="pixoo64_cache"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_path(self, key):
        return os.path.join(self.cache_dir, key)

    def get(self, key):
        file_path = self._get_path(key)
        
        if not os.path.exists(file_path):
            return {}, None

        try:
            last_updated = os.path.getmtime(file_path)
            with open(file_path, "r", encoding="utf-8") as f:
                results = json.load(f)
                
            return results, last_updated
        except (json.JSONDecodeError, IOError):
            return {}, None

    def save(self, results, key):
        file_path = self._get_path(key)
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(results, f)
