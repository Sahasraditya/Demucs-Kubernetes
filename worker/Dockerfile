FROM xserrat/facebook-demucs:latest

RUN pip3 install jsonpickle redis minio demucs requests

RUN apt-get update && apt-get install -y ffmpeg

RUN chmod 777 /data


WORKDIR /data

COPY worker.py /data

ENTRYPOINT [ "python", "worker.py" ]