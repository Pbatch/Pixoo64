import json
import os
from datetime import datetime
from urllib.parse import urlencode

import urllib3
from pen import Colours, Pen
from PIL import Image
from s3_cache import S3Cache


class MetOffice:
    def __init__(self, cache: S3Cache):
        self.cache = cache

        self.pool_manager = urllib3.PoolManager()
        self.pen = Pen()
        self.api_key = os.environ.get("MET_OFFICE_API_KEY")
        if self.api_key is None:
            raise ValueError(
                "The MET_OFFICE_API_KEY environment variable must be set to use the MetOffice class"
            )

        self.now = None
        self.now_timestamp = None

        self.sunny = Image.open("assets/met_office/sun.png")
        self.cloudy = Image.open("assets/met_office/cloud.png")
        self.rain = Image.open("assets/met_office/rain.png")
        self.heavy_rain = Image.open("assets/met_office/heavy_rain.png")
        self.sleet = Image.open("assets/met_office/sleet.png")
        self.snow = Image.open("assets/met_office/snow.png")
        self.thunder = Image.open("assets/met_office/thunder.png")

    def _get_icon_for_code(self, code):
        """
        Met Office Weather Symbols (significantWeatherCode):

        0  - Clear night
        1  - Sunny day
        2  - Partly cloudy (night)
        3  - Sunny intervals
        4  - Not used
        5  - Mist
        6  - Fog
        7  - Cloudy
        8  - Overcast
        9  - Light rain shower (night)
        10 - Light rain shower (day)
        11 - Drizzle
        12 - Light rain
        13 - Heavy rain shower (night)
        14 - Heavy rain shower (day)
        15 - Heavy rain
        16 - Sleet shower (night)
        17 - Sleet shower (day)
        18 - Sleet
        19 - Hail shower (night)
        20 - Hail shower (day)
        21 - Hail
        22 - Light snow shower (night)
        23 - Light snow shower (day)
        24 - Light snow
        25 - Heavy snow shower (night)
        26 - Heavy snow shower (day)
        27 - Heavy snow
        28 - Thundershower (night)
        29 - Thundershower (day)
        30 - Thunder
        """
        if 0 <= code <= 1:
            return self.sunny

        if 2 <= code <= 8:
            return self.cloudy

        if 9 <= code <= 12:
            return self.rain

        if 13 <= code <= 15:
            return self.heavy_rain

        if 16 <= code <= 21:
            return self.sleet

        if 22 <= code <= 27:
            return self.snow

        if 28 <= code <= 30:
            return self.thunder

        print(f"Missing icon for code={code}")
        return None

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

        image = Image.new("RGB", (64, 64), color=Colours.GRAY)
        self._draw_header(image)

        y = self.pen.letter_height + 5

        for prefix, key in [
            ["Outdoors", "screenTemperature"],
            ["Rain", "probOfPrecipitation"],
            ["Humidity", "screenRelativeHumidity"],
        ]:
            self.pen.draw_text(image, (1, y), prefix, color=Colours.YELLOW)

            text = str(int(weather[key]))
            if prefix == "Outdoors":
                text += "°"
            if prefix == "Rain":
                text += "%"
            text_width = self.pen.text_width(text)
            self.pen.draw_text(image, (63 - text_width, y + 1), text, Colours.YELLOW)
            y += self.pen.letter_height + 2

        code = weather["significantWeatherCode"]
        icon = self._get_icon_for_code(code)
        if icon is not None:
            image.paste(icon, (32 - icon.width // 2, (64 + y - icon.height) // 2), icon)

        return image


def main():
    from my_config import met_office_message

    cache = S3Cache()
    met_office = MetOffice(cache)
    image = met_office.make_image(met_office_message.lat, met_office_message.lon)
    image.save("../met_office.png")


if __name__ == "__main__":
    main()
