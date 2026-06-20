import os
from dataclasses import dataclass
from datetime import datetime

import urllib3
from pen import Colours, Pen
from PIL import Image
from caches import S3Cache, LocalCache
from urllib3 import make_headers


@dataclass
class Runner:
    name: str
    id_: str
    event: str | None = None
    date: str | None = None
    gender_position: int | None = None
    position: int | None = None
    time: int | None = None
    age_grade: float | None = None


class Parkrun:
    def __init__(self, cache: S3Cache | LocalCache):
        self.cache = cache

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.pool_manager = self._get_pool_manager()
        self.pen = Pen()
        self.logo = Image.open("assets/parkrun/logo.png")
        self.position_to_colour = {
            0: Colours.GOLD,
            1: Colours.SILVER,
            2: Colours.BRONZE,
        }
        self.now = None
        self.now_date = None
        self.now_timestamp = None
        self.now_weekday = None

    @staticmethod
    def _get_pool_manager():
        if os.environ.get("LAMBDA_ENV") is None:
            return urllib3.PoolManager()

        url = os.environ.get("PROXY_URL")
        if url is None:
            raise ValueError(
                "The PROXY_URL environment variable must be set when using the Parkrun class in an AWS Lambda"
            )

        scheme, proxy_info = url.split("://", 1)
        proxy_basic_auth, host = proxy_info.split("@", 1)
        proxy_url = f"{scheme}://{host}"
        proxy_headers = make_headers(proxy_basic_auth=proxy_basic_auth)

        return urllib3.ProxyManager(
            proxy_url=proxy_url,
            proxy_headers=proxy_headers,
        )

    @staticmethod
    def _clean_cell(cell):
        while "<" in cell:
            start = cell.find("<")
            end = cell.find(">", start)
            cell = cell[:start] + cell[end + 1 :]
        cell = cell.strip()
        return cell

    def _update_now(self):
        self.now = datetime.now()
        self.now_date = self.now.strftime("%d/%m/%Y")
        self.now_timestamp = self.now.timestamp()
        self.now_weekday = self.now.weekday()

    def _get_html(self, id_):
        url = f"https://www.parkrun.org.uk/parkrunner/{id_}"
        response = self.pool_manager.request(
            method="GET", url=url, headers=self.headers
        )
        if response.status != 200:
            print(f"Parkrun API error: {response.status}")
            return None

        html = response.data.decode("utf-8")
        return html

    def _parse_html(self, html):
        start_tbody = html.find("<tbody>")
        start_tr = html.find("<tr", start_tbody)
        end_tr = html.find("</tr>", start_tr)
        first_row_html = html[start_tr:end_tr]
        cells = first_row_html.split("<td>")[1:]
        event, date, gender_position, position, time, age_grade = [
            self._clean_cell(cell) for cell in cells
        ]
        minutes, seconds = time.split(":")
        time_in_seconds = 60 * int(minutes) + int(seconds)
        stats = {
            "event": event,
            "date": date,
            "gender_position": int(gender_position),
            "position": int(position),
            "time": time_in_seconds,
            "age_grade": float(age_grade[:-1]),
        }
        return stats

    def _get_stats(self, ids):
        key = "results.json"
        stats, last_updated = self.cache.get(key)
        if last_updated is not None:
            recently_checked = (self.now_timestamp - last_updated) < 1800
            not_saturday = self.now_weekday != 5
            if recently_checked or not_saturday:
                return stats

        update = False
        for id_ in ids:
            cached_stats = stats.get(id_)

            if cached_stats is not None:
                correct_date = cached_stats["date"] == self.now_date
                if correct_date:
                    continue

            html = self._get_html(id_)
            if html is None:
                print(f'Failed to get HTML for "{id_}"')
                continue

            stats[id_] = self._parse_html(html)
            update = True

        if update:
            self.cache.save(stats, key)

        return stats

    def _get_runners(self, id_to_name, stats):
        runners = []
        for id_, name in id_to_name.items():
            runner_stats = stats.get(id_)
            if runner_stats is None:
                continue

            if runner_stats["date"] != self.now_date:
                continue

            runners.append(Runner(name=name, id_=id_, **runner_stats))

        runners.sort(key=lambda runner: runner.time)
        return runners

    def _draw_header(self, image):
        text = "Parkrun"
        image.paste(self.logo, (1, 2), self.logo)
        self.pen.draw_text(
            image=image,
            xy=(self.logo.width + 3, 3),
            text=text,
            color=Colours.WHITE,
        )

        time = self.now.strftime("%H:%M")
        time_width = self.pen.text_width(time)
        self.pen.draw_text(
            image=image,
            xy=(63 - time_width, 4),
            text=time,
            color=Colours.WHITE,
        )

    def make_image(self, id_to_name: dict[str, str]):
        self._update_now()
        stats = self._get_stats(id_to_name.keys())
        runners = self._get_runners(id_to_name, stats)

        image = Image.new("RGB", (64, 64), color=Colours.GRAY)
        self._draw_header(image)
        y = self.pen.letter_height + 5
        for position, runner in enumerate(runners):
            colour = self.position_to_colour.get(position, Colours.WHITE)

            self.pen.draw_text(image, (1, y), runner.name, colour)

            minutes = runner.time // 60
            seconds = runner.time % 60
            text = f"{minutes:02}:{seconds:02}"
            text_width = self.pen.text_width(text)
            self.pen.draw_text(image, (63 - text_width, y + 1), text, colour)
            y += self.pen.letter_height + 2

            if y + self.pen.letter_height >= 64:
                break

        return image


def main():
    from my_config import parkrun_message

    cache = S3Cache()
    parkrun = Parkrun(cache)
    image = parkrun.make_image(parkrun_message.id_to_name)
    image.save("../parkrun.png")


if __name__ == "__main__":
    main()
