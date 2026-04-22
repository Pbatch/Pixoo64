import json
import os
import re
from datetime import datetime, timedelta
from urllib.parse import urlencode

import urllib3
from pen import Colours, Pen
from PIL import Image
from s3_cache import S3Cache


class Weather:
    def __init__(self, cache: S3Cache):
        self.cache = cache

        self.pool_manager = urllib3.PoolManager()
        self.pen = Pen()
        self.api_key = os.environ.get("MET_OFFICE_API_KEY")
        if self.api_key is None:
            raise ValueError(
                "The MET_OFFICE_API_KEY environment variable must be set to use the Weather class"
            )

        self.now = None
        self.now_timestamp = None

        self.rain = Image.open("assets/weather/rain.png")
        self.duck = Image.open("assets/weather/duck.png")
        self.thermometer = Image.open("assets/weather/thermometer.png")
        self.droplet = Image.open("assets/weather/droplet.png")

    def _update_now(self):
        self.now = datetime.now()
        self.now_timestamp = self.now.timestamp()

    def _get_weather(self, lat, lon):
        key = f"weather_lat={lat}_lon={lon}.json"
        weather, last_updated = self.cache.get(key)
        if last_updated is not None:
            recently_checked = (self.now_timestamp - last_updated) < 3600
            if recently_checked:
                return weather

        timesteps = "hourly"
        params = {
            "excludeParameterMetadata": "true",
            "includeLocationName": "true",
            "latitude": lat,
            "longitude": lon,
        }

        encoded_params = urlencode(params)
        full_url = f"https://data.hub.api.metoffice.gov.uk/sitespecific/v0/point/{timesteps}?{encoded_params}"

        headers = {
            "accept": "application/json",
            "apikey": self.api_key,
        }

        response = self.pool_manager.request("GET", full_url, headers=headers)
        if response.status != 200:
            print(f"Error: {response.status}")
            print(response.data.decode("utf-8"))
            return None

        data = json.loads(response.data.decode("utf-8"))
        weather = data["features"][0]["properties"]["timeSeries"][0]

        self.cache.save(weather, key)

        return weather

    def _get_pond_temperature(self):
        key = "pond_temperature.json"
        temperature, last_updated = self.cache.get(key)
        if last_updated is not None:
            recently_checked = (self.now_timestamp - last_updated) < 3600
            if recently_checked and False:
                return temperature

        response = self.pool_manager.request("GET", "https://nw3weather.co.uk/wxdataday.php?vartype=pond")
        data = response.data.decode("utf-8")
        if response.status != 200:
            print(f"Error: {response.status}")
            print(data)
            return -99

        yesterday = self.now - timedelta(days=1)
        rows = data.split('<tr>')
        for row in rows:
            if f'>{yesterday.day!s}</td>' not in row:
                continue

            cells = row.split('</td>')
            if len(cells) <= yesterday.month:
                continue

            target_cell = cells[yesterday.month]

            value = re.sub('<[^<]+?>', '', target_cell).replace('&nbsp;', '').strip()
            if value and value != "-":
                temperature = round(float(value))
                self.cache.save(temperature, key)
                return temperature

        return -99

    def _draw_header(self, image):
        text = "Weather"
        self.pen.draw_text(
            image=image,
            xy=(3, 3),
            text=text,
            color=Colours.WHITE,
        )

        time = datetime.now().strftime("%H:%M")
        time_width = self.pen.text_width(time)
        self.pen.draw_text(
            image=image,
            xy=(63 - time_width, 4),
            text=time,
            color=Colours.WHITE,
        )

    def make_image(self, lat: str, lon: str):
        self._update_now()
        weather = self._get_weather(lat, lon)

        pond_temperature = self._get_pond_temperature()
        if pond_temperature is not None:
            weather["pondTemperature"] = pond_temperature

        image = Image.new("RGB", (64, 64), color=Colours.GRAY)
        self._draw_header(image)

        row_1_y = 35 + self.pen.letter_height // 2
        for x, y, icon, key in [
            [1, row_1_y, self.thermometer, "screenTemperature"],
            [33, row_1_y, self.duck, "pondTemperature"],
            [1, 64, self.rain, "probOfPrecipitation"],
            [33, 64, self.droplet, "screenRelativeHumidity"],
        ]:
            image.paste(icon, (x + (32 - icon.width) // 2, y - self.pen.letter_height - icon.height - 2), icon)

            text = str(int(weather[key]))
            if key in {"pondTemperature", "screenTemperature"}:
                text += "°"
            if key in {"probOfPrecipitation", "screenRelativeHumidity"}:
                text += "%"
            text_width = self.pen.text_width(text)
            self.pen.draw_text(image, (x + (32 - text_width) // 2, y - self.pen.letter_height), text, Colours.YELLOW)

        return image


def main():
    from my_config import weather_message

    cache = S3Cache()
    weather = Weather(cache)
    image = weather.make_image(weather_message.lat, weather_message.lon)
    image.save("../weather.png")


if __name__ == "__main__":
    main()
