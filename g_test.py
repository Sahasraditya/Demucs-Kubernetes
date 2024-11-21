from minio import Minio

client = Minio("localhost:9000", access_key="rootuser", secret_key="rootpass123", secure=False)

queue = "waveform-song-queue"
output= "waveform-separation-track-queue"

for bucket in client.list_buckets():
    print(bucket.name)

print("minio queue bucket contents:")
for item in client.list_objects(queue):
    print(item.object_name)

print("minio output bucket contents: ")
for item in client.list_objects(output):
    print(item.object_name)
