FROM ubuntu
USER root

RUN apt update

RUN apt install -y python3 wget unzip pip

ENV LANG ja_JP.UTF-8
ENV LANGUAGE ja_JP:ja
ENV LC_ALL ja_JP.UTF-8
ENV TZ JST-9
ENV TERM xterm

RUN wget https://github.com/VOICEVOX/voicevox_core/releases/download/0.14.3/voicevox_core-linux-x64-cpu-0.14.3.zip
RUN unzip voicevox_core-linux-x64-cpu-0.14.3.zip
RUN mv voicevox_core-linux-x64-cpu-0.14.3 /root/src

RUN mkdir -p /root/src
COPY requirements.txt /root/src
COPY . /root/src
WORKDIR /root/src

RUN pip install --upgrade pip
RUN pip install --upgrade setuptools
RUN pip install -r requirements.txt
RUN wget https://github.com/VOICEVOX/voicevox_core/releases/download/0.14.3/voicevox_core-0.14.3+cuda-cp38-abi3-linux_x86_64.whl
RUN pip install voicevox_core-0.14.3+cuda-cp38-abi3-linux_x86_64.whl

CMD ["python3","app.py"]
