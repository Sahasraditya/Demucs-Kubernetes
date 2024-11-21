import hashlib
import os
import io
from flask import Flask, request, Response, jsonify, send_file
import base64
import redis
import json
from minio import Minio

# Step 1: create redis client
redisHost = os.getenv("REDIS_HOST") or "localhost"
redisPort = os.getenv("REDIS_PORT") or 6379

# Initialize redis client
redisClient = redis.StrictRedis(host=redisHost, port=redisPort, db=0)

# Step 2: Flask server
flaskHost = os.getenv("FLASK_HOST") or "localhost"
flaskPort = os.getenv("FLASK_PORT") or 5000

app = Flask(__name__)

# Step 3: create minio client
minioEndpoint = os.getenv("MINIO_ENDPOINT") or "localhost:9000"
minioAccessKey = os.getenv("MINIO_ACCESS_KEY") or "rootuser"
minioSecretKey = os.getenv("MINIO_SECRET_KEY") or "rootpass123"

# Initialize minio client
minioClient = Minio(minioEndpoint, access_key=minioAccessKey, secret_key=minioSecretKey, secure=False)
MINIO_BUCKET = "waveform-song-queue"
MINIO_SEPARATED_TRACK_BUCKET = "waveform-separation-track-queue"

# Define Redis queue name
REDIS_QUEUE = "toWorker"

# Create buckets if they do not exist
for bucket in [MINIO_BUCKET, MINIO_SEPARATED_TRACK_BUCKET]:
    if not minioClient.bucket_exists(bucket):
        print(f"Creating bucket: {bucket}")
        minioClient.make_bucket(bucket)

@app.route('/apiv1/separate', methods=['POST'])
def separate():
    try:
        data = json.loads(request.get_data())
        mp3_base64 = data['mp3']
        callback = data['callback']

        # Decode MP3 data from base64
        mp3 = base64.b64decode(mp3_base64)
        mp3_length = len(mp3)

        # Generate a unique hash for the file
        mp3_hash = hashlib.sha256(mp3).hexdigest()

        # Add the hash to Redis queue
        redisClient.rpush(REDIS_QUEUE, mp3_hash)

        # Store MP3 in Minio
        minioClient.put_object(MINIO_BUCKET, mp3_hash, io.BytesIO(mp3), mp3_length, content_type="audio/mpeg")

        # Respond with the unique identifier
        response = {'hash': mp3_hash, 'message': 'Song enqueued for separation'}
        return Response(json.dumps(response), status=200, mimetype="application/json")

    except Exception as err:
        # Return an error response with details
        error_response = {'message': 'Error occurred', 'details': str(err)}
        return Response(json.dumps(error_response), status=500, mimetype="application/json")

# Route to retrieve queue status
@app.route('/apiv1/queue', methods=['GET'])
def get_queue():
    try:
        # Get all items in the Redis queue
        queue_items = redisClient.lrange(REDIS_QUEUE, 0, -1)
        queue_hashes = [item.decode("utf-8") for item in queue_items]
        return jsonify({"queue": queue_hashes}), 200

    except Exception as err:
        error_response = {'message': 'Error retrieving queue', 'details': str(err)}
        return jsonify(error_response), 500

# Route to retrieve a track
@app.route('/apiv1/track/<songhash>/<track>', methods=['GET'])
def get_track(songhash, track):
    track_path = f"/tmp/{songhash}_{track}.mp3"
    if os.path.exists(track_path):
        return send_file(track_path, as_attachment=True, mimetype='audio/mpeg')
    else:
        return jsonify({"error": "Track not found"}), 404

# Route to remove a track
@app.route('/apiv1/remove/<songhash>/<track>', methods=['DELETE'])
def remove_track(songhash, track):
    track_path = f"/tmp/{songhash}_{track}.mp3"
    if os.path.exists(track_path):
        os.remove(track_path)
        return jsonify({"message": "Track removed"}), 200
    else:
        return jsonify({"error": "Track not found"}), 404

if __name__ == "__main__":
    app.run(host=flaskHost, port=int(flaskPort), debug=True)
