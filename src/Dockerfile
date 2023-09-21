FROM python:3

RUN apt update
RUN apt install ffmpeg -y

RUN mkdir -p /root/src
COPY requirements.txt /root/src
COPY . /root/src
WORKDIR /root/src

RUN pip install --upgrade pip
RUN pip install --upgrade setuptools
RUN pip install -r requirements.txt

CMD ["python3","app.py"]
