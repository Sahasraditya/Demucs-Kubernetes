import json
import os
import requests
import redis
from minio import Minio
import platform
import sys
import subprocess  # To run the demucs separation command

# Step 1: create redis client
redisHost = os.getenv("REDIS_HOST") or "localhost"
redisPort = os.getenv("REDIS_PORT") or 6379
redisQueue = os.getenv("REDIS_QUEUE") or "toWorker"

# Initialize redis client
redisClient = redis.StrictRedis(host=redisHost, port=redisPort, db=0)

# Step 2: create minio client
minioEndpoint = os.getenv("MINIO_ENDPOINT") or "localhost:9000"
minioAccessKey = os.getenv("MINIO_ACCESS_KEY") or "rootuser"
minioSecretKey = os.getenv("MINIO_SECRET_KEY") or "rootpass123"

# Initialize minio client
minioClient = Minio(minioEndpoint, access_key=minioAccessKey, secret_key=minioSecretKey, secure=False)

LOGGING_WORKER_QUEUE = os.getenv("LOGGING_WORKER_QUEUE") or "logging"
MINIO_BUCKET = "waveform-song-queue"
MINIO_SEPARATED_TRACK_BUCKET = "waveform-separation-track-queue"

infoKey = "{}.rest.info".format(platform.node())
debugKey = "{}.rest.debug".format(platform.node())

def log_debug(message, key=debugKey):
    print("DEBUG:", message, file=sys.stdout)
    redisClient.lpush(LOGGING_WORKER_QUEUE, f"{key}:{message}")

def log_info(message, key=infoKey):
    print("INFO:", message, file=sys.stdout)
    redisClient.lpush(LOGGING_WORKER_QUEUE, f"{key}:{message}")

def process_message(message):
    log_info("This has started")
    try:
        # Parse message data
        songHash = message
        log_info(f"Processing song with hash {songHash}")

        # Ensure the /data directory exists
        data_dir = 'data'
        input_dir = f"{data_dir}/input"
        output_dir = f"{data_dir}/output"

        if not os.path.exists(input_dir):
            os.makedirs(input_dir)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Download song from Minio
        minioClient.fget_object(MINIO_BUCKET, songHash, f"{input_dir}/{songHash}")
        log_info(f"Downloaded song with hash {songHash} from Minio")

        # Separate tracks using DEMUCS software
        try:
            result = subprocess.run(
                ["python", "-m", "demucs.separate", "--out", output_dir, "--mp3", f"{input_dir}/{songHash}"],
                check=True
            )
            log_info(f"Completed track separation for song with hash {songHash} using DEMUCS")

        except subprocess.CalledProcessError as e:
            log_info(f"Failed to run DEMUCS for song with hash {songHash}, error: {e}")

        # for root, dirs, files in os.walk(f"{output_dir}/"):
        #     for filename in files:
        #         log_info(f"Found file: {os.path.join(root, filename)}")
    
        # Upload separated tracks to Minio object store
        for part in ["bass", "vocals", "drums", "other"]:
            track_path = f"{output_dir}/mdx_extra_q/{songHash}/{part}.mp3"
            current_directory = os.getcwd()
# Log the current working directory
            log_info(f"Current working directory: {current_directory}")
            log_info(track_path)
            if os.path.exists(track_path):
                minioClient.fput_object(MINIO_SEPARATED_TRACK_BUCKET, f"{part}_{songHash}.mp3", track_path)
                log_info(f"Uploaded {part}.mp3 for song with hash {songHash} to Minio object store")
            else:
                pass
                log_info(f"Error: Separated track {part}.mp3 not found for song with hash {songHash}")

    except Exception as ex:
        log_debug(f"Error, received exception {ex}", debugKey)

import time
def main():
    log_info("Redis worker started, listening for messages containing mp3 track...")
    while True:
        time.sleep(5)
        # Use lrange to get the entire queue
        queue_items = redisClient.lrange(redisQueue, 0, 0)  # Get only the first item (index 0)
        log_info("redis Queue is",redisQueue)

        if queue_items:
            # Pop the first item manually
            item = queue_items[0]
            decoded_item = item.decode("utf-8")
            log_info(decoded_item)
            process_message(decoded_item)
            
            # Remove the item after processing (by trimming the list)
            redisClient.ltrim(redisQueue, 1, -1)
        else:
            log_info("No items in the queue, waiting for new messages...")

if __name__ == "__main__":
    main()
