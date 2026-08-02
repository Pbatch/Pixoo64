import os
from datetime import datetime, timezone
import json
import time

from config import GalleryMessage, MessageMode, ParkrunMessage, TflMessage, WeatherMessage
from gallery import Gallery
from weather import Weather
from parkrun import Parkrun
from pixoo import Pixoo
from caches import LocalCache
from tfl import ID_TO_STATION, TFL, Stations
import boto3
from my_config import config

pixoo = Pixoo()
cache = LocalCache()
tfl = TFL()
parkrun = Parkrun(cache)
weather = Weather(cache)

def _filter_messages(messages):
    filtered_messages = []

    weekday = datetime.now(timezone.utc).weekday()
    for message in messages:
        if message.weekday is not None and message.weekday != weekday:
            continue

        filtered_messages.append(message)
    return filtered_messages

def main():
    while True:
        messages = _filter_messages(config.messages)
        for i in range(config.messages_per_minute):
            message = messages[i % len(messages)]
            if isinstance(message, TflMessage):
                station = ID_TO_STATION[message.station_id]
                image = tfl.make_image(
                    arrivals=tfl.get_and_filter_arrivals(
                        station.station_id, message.inbound
                    ),
                    header_text=station.nickname.capitalize(),
                    underground=station.underground,
                )
            elif isinstance(message, ParkrunMessage):
                image = parkrun.make_image(message.id_to_name)
            elif isinstance(message, WeatherMessage):
                image = weather.make_image(message.lat, message.lon)
            elif isinstance(message, GalleryMessage):
                image = Gallery(message.image_directory, message.header_text).make_image()
            else:
                raise ValueError(f'Message "{message}" is not supported')

            payload = {
                "Command": "Draw/SendHttpGif",
                "PicNum": 1,
                "PicWidth": 64,
                "PicOffset": 0,
                "PicID": int(time.time()),
                "PicSpeed": 0,
                "PicData": pixoo.encode_image(image),
            }
            result = pixoo.post(payload)
            print(result)
            time.sleep(60 / config.messages_per_minute)
            

if __name__ == "__main__":
    main()
