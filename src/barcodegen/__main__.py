import io
from importlib import resources
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Generator
from .constants import *


class BarcodeChecksumError(ValueError):
    """Inherits from ValueError; thrown when a barcode contains an incorrect checksum digit."""
    def __init__(self, barcode: str, corrected_barcode: str):
        self.barcode = barcode
        self.corrected_barcode = corrected_barcode
        super().__init__(f"Invalid checksum for barcode {barcode}. Expected {corrected_barcode}.")


def generate_barcode_image(barcode: str,
                           unit_width: int = 10,
                           barcode_height: int = 200,
                           notch_height: int = 0,
                           border_width: int = 0,
                           left_border: int | None = None,
                           right_border: int | None = None,
                           top_border: int | None = None,
                           bottom_border: int | None = None,
                           draw_digits: bool = False) -> Image.Image:
    """Generates a barcode image in the Pillow format."""

    # Determines the encoding type (UPC-A, EAN-8, EAN-13)
    barcode_type = get_type(barcode)

    # If the checksum of the provided barcode is incorrect, raises an error and returns both the requested (wrong)
    # barcode as well as a corrected version (last digit changed)
    if not checksum_is_correct(barcode):
        corrected_barcode = checksum_is_correct(barcode, return_corrected=True)
        raise BarcodeChecksumError(barcode, corrected_barcode)

    # If no text notch height is specified, calculates a default value
    if notch_height is None:
        notch_height = (int(unit_width * (FONT_SIZE_FACTOR + TEXT_Y_OFFSET * 2)) // 2)

    # Sets initial border width
    border: Dict[str, int] = {"Left": border_width, "Right": border_width, "Top": border_width, "Bottom": border_width}

    # Sets individual border width, if specified
    if left_border is not None:
        border["Left"] = left_border
    if right_border is not None:
        border["Right"] = right_border
    if top_border is not None:
        border["Top"] = top_border
    if bottom_border is not None:
        border["Bottom"] = bottom_border

    # If the format is EAN-13 and digits are drawn, extends the left border to make room for the extra digit
    if draw_digits and barcode_type == "EAN-13":
        border["Left"] += (unit_width * EAN_13_LEFT_BORDER_EXTENSION_FACTOR)

    # Splits the digits into digit groups, according to type
    digit_groups = get_digit_groups(barcode,barcode_type)

    # Generates a string corresponding to the barcode, where 0 is white and 1 is black
    barcode_string = encode_barcode(*digit_groups)

    # Generates a PBM image
    pbm_data = generate_pbm_data(barcode_string,
                                 border,
                                 unit_width=unit_width,
                                 barcode_height=barcode_height,
                                 notch_height=notch_height,
                                 type=barcode_type,
                                 draw_digits=draw_digits)

    # Converts the PBM image into a Pillow image
    pillow_image = convert_to_pillow_image(pbm_data)

    # If specified, adds the human-readable digits underneath the barcode
    if draw_digits:
        draw_digit_text(pillow_image, *digit_groups, border, unit_width, barcode_height, barcode_type)
    
    # Returns the pillow image
    return pillow_image


def generate_barcode_bits(barcode: str) -> str:
    """Returns a string representing the barcode, where 0 = no bar and 1 = bar."""
    barcode_type = get_type(barcode)

    if not checksum_is_correct(barcode):
        corrected_barcode = checksum_is_correct(barcode, return_corrected=True)
        raise BarcodeChecksumError(barcode, corrected_barcode)

    digit_groups = get_digit_groups(barcode, barcode_type)
    return encode_barcode(*digit_groups)


def convert_to_pillow_image(pbm_data: str):
    """Converts a PBM string into a Pillow Image object."""
    pbm_memory_file = io.BytesIO(pbm_data.encode("utf-8"))
    pillow_image = Image.open(pbm_memory_file).convert("L")
    return pillow_image


def draw_digit_text(image,
                    leading_digit: str,
                    left_digits: str,
                    right_digits: str,
                    border: Dict[str, int],
                    unit_width: int,
                    barcode_height: int,
                    barcode_type: str):
    """Draws the human-readable digits underneath the barcode."""
    font_size: int = unit_width * FONT_SIZE_FACTOR
    leading_digit_x: int = border["Left"] - unit_width * EAN_13_LEADING_DIGIT_SHIFT
    left_text_x: int = border["Left"] + unit_width * (len(SIDE_GUARD) + 1)
    right_text_x: int = border["Left"] + unit_width * (UNITS_PER_SIDE[barcode_type] + len(SIDE_GUARD) + len(MIDDLE_GUARD))
    text_y: int = border["Top"] + barcode_height + int(unit_width * TEXT_Y_OFFSET)

    try:
        with resources.files("barcodegen.fonts").joinpath("OCR-B.ttf").open("rb") as font_file:
            font = ImageFont.truetype(font_file, font_size)
    except OSError as e:
        raise RuntimeError('Cannot load font file "OCR-B.ttf".') from e

    draw = ImageDraw.Draw(image)
    # If the barcode format is EAN-13, draws the leading digit
    if barcode_type == "EAN-13":
        draw.text((leading_digit_x, text_y), leading_digit, fill="black", anchor="lt", font=font)
    # Draws the left side digits
    draw.text((left_text_x, text_y), left_digits, fill="black", anchor="lt", font=font)
    # Draws the right side digits
    draw.text((right_text_x, text_y), right_digits, fill="black", anchor="lt", font=font)


def get_digit_groups(barcode_number: str, barcode_type: str,) -> tuple[str, str, str]:
    """Returns a tuple containing all the digit groups: the leading digit, left digits, and right digits."""

    first_digit: Dict[str, int] = {"EAN-13": 1, "UPC-A": 0, "EAN-8": 0}
    digits_per_side: Dict[str, int] = {"EAN-13": 7, "UPC-A": 6, "EAN-8": 4}

    leading_digit: str = (barcode_number[0] if barcode_type == "EAN-13" else "0")
    left_digits: str = barcode_number[first_digit[barcode_type]: digits_per_side[barcode_type]]
    right_digits: str = barcode_number[digits_per_side[barcode_type]:]

    return leading_digit, left_digits, right_digits


def checksum_is_correct(barcode_number: str, return_corrected: bool = False,) -> bool | str:
    """Returns True if the checksum number is correct. If return_corrected is True, returns a corrected barcode."""

    check_digit: int = int(barcode_number[-1])
    barcode_number = barcode_number[-2::-1]
    checksum: int = 0

    for i, digit in enumerate(barcode_number): checksum += (int(digit) * 3 if i % 2 == 0 else int(digit))
    checksum = (0 if checksum % 10 == 0 else 10 - checksum % 10)

    if check_digit == checksum:
        return True
    if return_corrected:
        return f"{barcode_number[::-1]}{checksum}"

    return False


def get_type(barcode: str) -> str:
    """If the number is a valid barcode number, returns its type."""

    if not barcode.isnumeric():
        raise ValueError("Barcode number must contain digits only.")

    match len(barcode):
        case 13:
            return "EAN-13"
        case 12:
            return "UPC-A"
        case 8:
            return "EAN-8"
        case _:
            raise ValueError("Barcode must contain 8, 12, or 13 digits.")


def get_bits(number: int, length: int,) -> Generator[int, None, None]:
    """Generates the specified number of bits of a number, starting with the least significant bit."""
    for i in range(length - 1, -1, -1):
        yield number >> i & 1


def encode_digit(digit: int, parity=None) -> str:
    """Encodes a digit into a string of 7 bits and returns it."""
    value: int = left_encoding[digit][parity] if parity is not None else right_encoding[digit]
    return "".join(str(bit) for bit in get_bits(value, 7))


def encode_left_side(leading_digit: str, left_digits: str,) -> str:
    """Encodes the left-hand side of the barcode."""
    output: str = ""

    for i, digit in enumerate(left_digits):
        parity: int = leading_digit_encoding[int(leading_digit)] >> (5 - i) & 1
        output += encode_digit(int(digit), parity)

    return output


def encode_right_side(right_digits: str,) -> str:
    """Encodes the right-hand side of the barcode."""
    return "".join(encode_digit(int(digit)) for digit in right_digits)


def encode_barcode(leading_digit: str, left_digits: str, right_digits: str,) -> str:
    """Returns the entire barcode as a string of bits."""
    left_side = encode_left_side(leading_digit, left_digits)
    right_side = encode_right_side(right_digits)
    return f"{SIDE_GUARD}{left_side}{MIDDLE_GUARD}{right_side}{SIDE_GUARD}"


def generate_notches(unit_width: int, type: str,) -> str:
    """Generates text notches."""
    side: str = "".join(bit * unit_width for bit in SIDE_GUARD)
    middle: str = "".join(bit * unit_width for bit in MIDDLE_GUARD)
    empty_space: str = "0" * UNITS_PER_SIDE[type] * unit_width
    return f"{side}{empty_space}{middle}{empty_space}{side}"


def generate_pbm_data(
    bit_string: str,
    border: Dict[str, int],
    type: str = "EAN-13",
    unit_width: int = 6,
    barcode_height: int = 400,
    notch_height: int = 0,
    draw_digits: bool = True) -> str:
    """Returns a string containing the barcode image data in PBM format."""

    width: int = len(bit_string) * unit_width + border["Left"] + border["Right"]
    height_extension: int = max(int(unit_width * (FONT_SIZE_FACTOR + TEXT_Y_OFFSET) * draw_digits), notch_height)
    height: int = barcode_height + height_extension + border["Top"] + border["Bottom"]

    left_border: str = "0" * border["Left"]
    right_border: str = "0" * border["Right"]

    top_border_lines: str = ("0" * width + "\n") * border["Top"]
    bottom_border_lines: str = ("0" * width + "\n") * (border["Bottom"] + height_extension)

    barcode_lines: str = (left_border + "".join(bit * unit_width for bit in bit_string) + right_border + "\n") * barcode_height

    pbm_data: str = f"P1\n# {type} BARCODE\n{width} {height}\n"
    pbm_data += top_border_lines
    pbm_data += barcode_lines

    if notch_height: pbm_data += "".join((left_border, generate_notches(unit_width, type,), right_border, "\n",)) * notch_height
    pbm_data += bottom_border_lines
    return pbm_data
