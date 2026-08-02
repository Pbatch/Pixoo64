from datetime import datetime
from pathlib import Path

from pen import Colours, Pen
from PIL import Image


class Gallery:
    image_padding = 4

    def __init__(self, image_directory, header_text="Gallery"):
        self.image_directory = Path(image_directory)
        if not self.image_directory.is_dir():
            raise FileNotFoundError(f"Image directory does not exist: {self.image_directory}")

        self.header_text = header_text
        self.pen = Pen()

    def _draw_header(self, image):
        self.pen.draw_text(
            image=image,
            xy=(3, 3),
            text=self.header_text,
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

    def _get_latest_image(self):
        image_paths = (
            image_path
            for image_path in self.image_directory.iterdir()
            if image_path.is_file()
            and image_path.suffix.lower() in Image.registered_extensions()
        )
        return max(image_paths, key=lambda image_path: image_path.stat().st_mtime, default=None)

    def _draw_latest_image(self, image):
        image_path = self._get_latest_image()
        if image_path is None:
            return

        with Image.open(image_path) as latest_image:
            latest_image = latest_image.convert("RGBA")
            top = self.pen.letter_height + 5
            max_width = image.width - 2 * self.image_padding
            max_height = image.height - top - self.image_padding
            scale = min(
                max_width / latest_image.width,
                max_height / latest_image.height,
                1,
            )
            size = (round(latest_image.width * scale), round(latest_image.height * scale))
            latest_image = latest_image.resize(size, Image.Resampling.LANCZOS)

            x = (image.width - latest_image.width) // 2
            y = top + (max_height - latest_image.height) // 2
            image.paste(latest_image, (x, y), latest_image)

    def make_image(self):
        image = Image.new("RGB", (64, 64), color=Colours.GRAY)
        self._draw_header(image)
        self._draw_latest_image(image)

        return image


def main():
    gallery = Gallery("../../BirdSpotter/segmented", header_text="Birds")
    image = gallery.make_image()
    image.save("../birdspotter.png")


if __name__ == "__main__":
    main()
