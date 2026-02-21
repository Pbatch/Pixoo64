import json
import os
from dataclasses import dataclass
from datetime import datetime

import boto3
import urllib3
from PIL import Image

from my_config import parkrun_message
from pen import Colours, Pen


class S3Cache:
    def __init__(self):
        self.s3 = boto3.client("s3")
        self.bucket_name = os.environ["BUCKET_NAME"]
        self.key = "results.json"

    def get(self):
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=self.key)
        except self.s3.exceptions.NoSuchKey:
            return {}, None

        last_updated = response['LastModified'].timestamp()
        results = json.loads(response['Body'].read().decode('utf-8'))
        return results, last_updated

    def save(self, results):
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=self.key,
            Body=json.dumps(results),
            ContentType="application/json",
        )

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
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        self.pool_manager = urllib3.PoolManager()
        self.cache = S3Cache()
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
    def _clean_cell(cell):
        while '<' in cell:
            start = cell.find('<')
            end = cell.find('>', start)
            cell = cell[:start] + cell[end + 1:]
        cell = cell.strip()
        return cell

    def _update_now(self):
        self.now = datetime.now()
        self.now_date = self.now.strftime("%d/%m/%Y")
        self.now_timestamp = self.now.timestamp()
        self.now_weekday = self.now.weekday()

    def _get_html(self, id_):
        url = f"https://www.parkrun.org.uk/parkrunner/{id_}"
        response = self.pool_manager.request(method="GET", url=url, headers=self.headers)
        if response.status != 200:
            print(f"Parkrun API error: {response.status}")
            return None

        html = response.data.decode('utf-8')
        return html

    def _parse_html(self, html):
        start_tbody = html.find('<tbody>')
        start_tr = html.find('<tr', start_tbody)
        end_tr = html.find('</tr>', start_tr)
        first_row_html = html[start_tr:end_tr]
        cells = first_row_html.split('<td>')[1:]
        event, date, gender_position, position, time, age_grade = [self._clean_cell(cell) for cell in cells]
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
        stats, last_updated = self.cache.get()
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
            self.cache.save(stats)

        return stats

    def _get_runners(self, id_to_name, stats):
        runners = []
        for id_, name in id_to_name.items():
            runner_stats = stats.get(id_)
            if runner_stats is None:
                continue

            if runner_stats["date"] != self.now_date:
                continue

            runners.append(
                Runner(name=name, id_=id_, **runner_stats)
            )

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

        time = datetime.now().strftime("%H:%M")
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
            self.pen.draw_text(image, (63 - text_width, y), text, colour)
            y += self.pen.letter_height + 2

            if y + self.pen.letter_height >= 64:
                break

        return image


def main():
    parkrun = Parkrun()
    image = parkrun.make_image(parkrun_message.id_to_name)
    image.save("../parkrun.png")

if __name__ == "__main__":
    main()