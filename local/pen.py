import string
from dataclasses import dataclass

from PIL import Image


@dataclass(frozen=True)
class Colours:
    RED = (220, 36, 31)
    WHITE = (255, 255, 255)
    BLUE = (0, 25, 168)
    YELLOW = (255, 211, 0)
    GRAY = (20, 20, 20)
    GOLD = (255, 215, 0)
    SILVER = (192, 192, 192)
    BRONZE = (205, 127, 50)

class Pen:
    def __init__(self):
        self.glyphs = {letter: Image.open(f"assets/letters/{letter}.png") for letter in string.ascii_uppercase}
        self.glyphs.update({str(number): Image.open(f"assets/numbers/{number}.png") for number in range(10)})
        self.glyphs[":"] = Image.open("assets/letters/colon.png")
        self.letter_height = self.glyphs["A"].height
        self.number_height = self.glyphs["0"].height

    def text_width(self, text):
        text_width = len(text) - 1
        for char in text.upper():
            if char == " ":
                text_width += 1
            else:
                text_width += self.glyphs[char].width
        return text_width

    def draw_text(self, image: Image, xy: tuple[int, int], text: str, color: tuple[int, int, int]):
        x, y = xy
        for char in text.upper():
            if char == " ":
                x += 2
                continue

            glyph = self.glyphs[char]
            background = Image.new("RGBA", glyph.size, color=color)
            image.paste(background, (x, y), glyph)

            x += glyph.width + 1
