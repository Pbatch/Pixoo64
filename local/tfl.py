from datetime import datetime
import json
import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo

import urllib3
from pen import Colours, Pen
from PIL import Image


@dataclass(frozen=True)
class Station:
    station_id: str
    nickname: str
    code: str
    underground: bool


@dataclass(frozen=True)
class Stations:
    BATTERSEA_POWER_STATION: Station = Station("940GZZBPSUST", "battersea", "BPS", True)
    BELSIZE_PARK: Station = Station("940GZZLUBZP", "belsize", "BZP", True)
    GOLDERS_GREEN: Station = Station("940GZZLUGGN", "golders", "GGN", True)
    EDGWARE: Station = Station("940GZZLUEGW", "edgware", "EDG", True)
    KENNINGTON: Station = Station("940GZZLUKNG", "kennington", "KEN", True)
    MORDEN: Station = Station("940GZZLUMDN", "morden", "MDN", True)
    EUSTON: Station = Station("940GZZLUEUS", "euston", "EUS", True)
    HAMPSTEAD_HEATH: Station = Station("910GHMPSTDH", "heath", "HDH", False)
    STRATFORD: Station = Station("910GSTFD", "stratford", "SRA", False)
    CLAPHAM_JUNCTION: Station = Station("910GCLPHMJ1", "clapham", "CLJ", False)
    RICHMOND: Station = Station("910GRICHMND", "richmond", "RMD", False)
    WILLESDEN_JUNCTION: Station = Station("910GWLSDJHL", "willesden", "WIJ", False)
    KENSAL_RISE: Station = Station("910GKENR", "kensal rise", "KNR", False)


DUPLICATE_IDS = {"910GCLPHMJC": "910GCLPHMJ1"}
ID_TO_STATION = {
    v.station_id: v for k, v in Stations.__dict__.items() if isinstance(v, Station)
}

DIRECTION_EXCEPTIONS = {
    "inbound": {
        Stations.HAMPSTEAD_HEATH.station_id: {Stations.STRATFORD.station_id},
    },
    "outbound": {
        Stations.HAMPSTEAD_HEATH.station_id: {
            Stations.CLAPHAM_JUNCTION.station_id,
            Stations.RICHMOND.station_id,
            Stations.WILLESDEN_JUNCTION.station_id,
        },
    },
}


class TFL:
    def __init__(self):
        self.pool_manager = urllib3.PoolManager()
        self.app_key = os.environ["TFL_APP_KEY"]
        self.pen = Pen()

        self.underground = Image.open("assets/tfl/underground.png")
        self.overground = Image.open("assets/tfl/overground.png")
        self.bank = Image.open("assets/tfl/bank.png")
        self.cross = Image.open("assets/tfl/cross.png")
        self.tube = Image.open("assets/tfl/tube.png")

    @staticmethod
    def _filter_arrivals(arrivals, station_id, inbound):
        filtered_arrivals = []
        direction = "inbound" if inbound else "outbound"
        exceptions = DIRECTION_EXCEPTIONS[direction].get(station_id, set())
        for a in arrivals:
            a["naptanId"] = DUPLICATE_IDS.get(a["naptanId"], a["naptanId"])
            a["destinationNaptanId"] = DUPLICATE_IDS.get(
                a["destinationNaptanId"], a["destinationNaptanId"]
            )
            if a["direction"] == direction:
                filtered_arrivals.append(a)
                continue

            if a["direction"] == "" and a["destinationNaptanId"] in exceptions:
                filtered_arrivals.append(a)

        filtered_arrivals.sort(key=lambda x: x["timeToStation"])

        return filtered_arrivals

    def _draw_header(self, image, text, underground):
        roundel = self.underground if underground else self.overground

        image.paste(roundel, (1, 2), roundel)
        self.pen.draw_text(
            image=image,
            xy=(roundel.width + 2, 1),
            text=text,
            color=Colours.YELLOW,
        )

        time = datetime.now().strftime("%H:%M")
        time_width = self.pen.text_width(time)
        self.pen.draw_text(
            image=image,
            xy=(63 - time_width, 2),
            text=time,
            color=Colours.YELLOW,
        )

    def _draw_no_arrivals(self, image, y):
        image.paste(self.tube, (32 - self.tube.width // 2, y + 10), self.tube)

        y += 10 + self.tube.height
        for text in ["Service", "Closed"]:
            text_width = self.pen.text_width(
                text,
            )
            self.pen.draw_text(
                image=image,
                xy=(32 - text_width // 2, y),
                text=text,
                color=Colours.YELLOW,
            )
            y += self.pen.letter_height + 1

    def _get_arrivals(self, station_id):
        url = f"https://api.tfl.gov.uk/StopPoint/{station_id}/Arrivals?APP_KEY={self.app_key}"
        print(url)
        try:
            response = self.pool_manager.request("GET", url, timeout=5.0)

            if response.status != 200:
                print(f"TfL API Error: {response.status}")
                return []

            return json.loads(response.data.decode("utf-8"))

        except Exception as e:
            print(f"Request failed: {e}")
            return []

    def get_and_filter_arrivals(self, station_id: str, inbound: bool) -> list[dict]:
        arrivals = self._get_arrivals(station_id)
        arrivals = self._filter_arrivals(arrivals, station_id, inbound)
        return arrivals

    def make_image(
        self, arrivals: list[dict], header_text: str, underground: bool
    ) -> Image:
        image = Image.new("RGB", (64, 64), color=Colours.GRAY)

        self._draw_header(image, header_text, underground)

        # height of the header + 4 spaces
        y = self.pen.letter_height + 4
        for arrival in arrivals:
            try:
                nickname = ID_TO_STATION[arrival["destinationNaptanId"]].nickname
            except KeyError:
                print(f"Arrival is not a listed station: {arrival}")
                nickname = arrival["destinationName"].split()[0][:3]
            left_text = nickname.capitalize()
            left_width = self.pen.text_width(left_text)
            self.pen.draw_text(
                image=image,
                xy=(1, y),
                text=left_text,
                color=Colours.YELLOW,
            )

            if "via CX" in arrival["towards"]:
                image.paste(self.cross, (left_width + 2, y), self.cross)
            elif "via Bank" in arrival["towards"]:
                image.paste(self.bank, (left_width + 2, y), self.bank)

            mins_to_station = str(arrival["timeToStation"] // 60)
            text_width = self.pen.text_width(mins_to_station)
            self.pen.draw_text(
                image=image,
                xy=(
                    63 - text_width,
                    y + self.pen.letter_height - self.pen.number_height,
                ),
                text=mins_to_station,
                color=Colours.YELLOW,
            )

            y += self.pen.letter_height + 2
            if y + self.pen.letter_height >= 64:
                break

        if len(arrivals) == 0:
            self._draw_no_arrivals(image, y)

        return image


def main():
    tfl = TFL()
    station = Stations.BELSIZE_PARK
    arrivals = tfl.get_and_filter_arrivals(station.station_id, inbound=True)
    image = tfl.make_image(
        arrivals, station.nickname.capitalize(), underground=station.underground
    )
    image.save("../tfl.png")


if __name__ == "__main__":
    main()
