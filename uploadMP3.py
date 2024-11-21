from minio import Minio
import hashlib
import os

# Initialize MinIO client
minioClient = Minio("localhost:9000", access_key="rootuser", secret_key="rootpass123", secure=False)

# Upload an MP3 file to the waveform-song-queue bucket
def upload_mp3_to_minio(mp3_file_path):
    song_hash = hashlib.sha256(open(mp3_file_path, 'rb').read()).hexdigest()
    minioClient.fput_object("waveform-song-queue", song_hash, mp3_file_path)
    print(f"Uploaded {mp3_file_path} to MinIO with hash {song_hash}")

# Example usage
upload_mp3_to_minio("data/short-hop.mp3")
upload_mp3_to_minio("data/short-dreams.mp3")
