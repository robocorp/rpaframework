FROM ubuntu:18.04

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

RUN apt-get update --fix-missing && \
    apt-get install -y wget bzip2 ca-certificates curl bash chromium-browser chromium-chromedriver firefox python3.8 python3-pip nano && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.26.0/geckodriver-v0.26.0-linux64.tar.gz
RUN tar xvf geckodriver*
RUN chmod +x geckodriver
RUN mv geckodriver /usr/bin

RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.6 1
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 2

RUN ln -s /usr/bin/python3 /usr/bin/python
RUN ln -s /usr/bin/pip3 /usr/bin/pip

ENV ROBOT_OPTIONS="-L INFO -d /dist"
