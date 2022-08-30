FROM mcr.microsoft.com/playwright/python:v1.24.0-focal

#apt update

RUN apt update

#install java runtime

RUN apt install -y openjdk-8-jre

WORKDIR /app

COPY . .

#install python packages

RUN pip3 install -r requirements.txt

CMD xvfb-run --auto-servernum --server-num=1 --server-args='-screen 0, 1920x1080x24' python getdockets.py