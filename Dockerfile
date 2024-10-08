FROM python:3-slim-bullseye

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN apt-get update && apt-get -y install whiptail
ADD . /app

WORKDIR /app


RUN pip install -r requirements.txt

RUN mkdir /feed /db 


ENTRYPOINT ["python", "SteamNews.py", "--database", "/db/SteamNews.db"]

CMD ["-f", "-p", "/feed/steam-news.xml"]

