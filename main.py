import argparse
import io
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Generator, Tuple

SIDE_GUARD = "101"
MIDDLE_GUARD = "01010"
UNITS_PER_SIDE = {"EAN-13": 42, "UPC-A": 42, "EAN-8": 28}
FONT_SIZE_FACTOR = 8
EAN_13_LEADING_DIGIT_SHIFT = 7
EAN_13_LEFT_BORDER_EXTENSION_FACTOR = 6
TEXT_Y_OFFSET = 1.5

# Values for encoding the left-hand side of the barcode, in decimal.
# For EAN-13, the values with key 0 have odd parity (Set A), while those with key 1 have even parity (Set B).
# For UPC, always use key 0 values.
left_encoding = {
    0: {0: 13, 1: 39},
    1: {0: 25, 1: 51},
    2: {0: 19, 1: 27},
    3: {0: 61, 1: 33},
    4: {0: 35, 1: 29},
    5: {0: 49, 1: 57},
    6: {0: 47, 1: 5},
    7: {0: 59, 1: 17},
    8: {0: 55, 1: 9},
    9: {0: 11, 1: 23}
}

# Values for encoding the right-hand side of the barcode, in decimal. For both EAN and UPC.
right_encoding = {
    0: 114,
    1: 102,
    2: 108,
    3: 66,
    4: 92,
    5: 78,
    6: 80,
    7: 68,
    8: 72,
    9: 116
}

# Values for encoding the very first digit of EAN-13 barcodes. The digit is encoded within the left-side 6 digits as a
# combination of their parity, where odd parity = 0 and even parity = 1.
# For example, the digit one is encoded as 11, that is binary 001011, or "odd", "odd", "even", "odd", "even", "even".
leading_digit_encoding = {
    0: 0,
    1: 11,
    2: 13,
    3: 14,
    4: 19,
    5: 25,
    6: 28,
    7: 21,
    8: 22,
    9: 26
}


def main():
    arg_parser = argparse.ArgumentParser(description="EAN and UPC Barcode Generator")
    arg_parser.add_argument("barcode_number", type=str,
                            help="The numeric value of the barcode to be generated")
    arg_parser.add_argument("-o", "--outputpath", type=str,
                            help="The output path for the barcode file")
    arg_parser.add_argument("-w", "--unitwidth", type=positive_int, default=6,
                            help="The width of a single encoding unit (bar) in pixels")
    arg_parser.add_argument("-v", "--verticalsize",type=positive_int, default=400,
                            help="The height of the barcode itself (excluding optional text and text notches), "
                            "in pixels")
    arg_parser.add_argument("-n", "--notch", type=non_negative_int,
                            help="The length of the text notches, in pixels")
    arg_parser.add_argument("-B", "--border", type=non_negative_int, default=20,
                            help="The width of the border (quiet area) on all sides")
    arg_parser.add_argument("-l", "--leftborder", type=non_negative_int,
                            help="The width of the border (quiet area) on the left side")
    arg_parser.add_argument("-r", "--rightborder", type=non_negative_int,
                            help="The width of the border (quiet area) on the right side")
    arg_parser.add_argument("-t", "--topborder", type=non_negative_int,
                            help="The width of the border (quiet area) at the top")
    arg_parser.add_argument("-b", "--bottomborder", type=non_negative_int,
                            help="The width of the border (quiet area) on the bottom")
    arg_parser.add_argument("-d", "--nodigits", action="store_false",
                            help="Do not draw human-readable digits underneath the barcode")
    arg_parser.add_argument("-s", "--bitstring", action="store_true",
                            help="Output a string of bits, where 0 and 1 correspond to white and black bars, "
                            "respectively")
    args = arg_parser.parse_args()
    
    barcode: str = args.barcode_number
    
    # Attempts to recognize the barcode format. If it's incorrect, raises an exception and exits.
    try:
        barcode_type: str = get_type(barcode)
    except ValueError:
        sys.exit("Error: incorrect barcode number (must consist of 8, 12 or 13 digits, no spaces, numeric only).")
    
    # Checks if the checksum in the provided number is correct. If not, asks the user if they want to correct the
    # checksum number and proceed anyway.
    if not checksum_is_correct(barcode):
        print(f"Warning: the entered {barcode_type} barcode number is incorrect and won't be scannable "
              "(checksum failed).")
        corrected_barcode: str = checksum_is_correct(barcode, return_corrected=True)
        print("If you are sure that only the check digit (the final digit) is incorrect, "
              f"you can use \"{corrected_barcode}\" instead.")
        print("Please keep in mind that an incorrect checksum indicates that any part of the number can be "
              "incorrect, not just the checksum digit.")
        while True:
            use_corrected: str = input("Do you want to use the corrected number? (Y/N) ").upper().strip()
            if use_corrected == "Y":
                barcode = corrected_barcode
                break
            elif use_corrected == "N":
                sys.exit()
    
    # If no output path has been passed, sets it to the currect working directory using the default file naming format.
    output_path: Path = Path(args.outputpath) if args.outputpath is not None else Path.cwd(
        ) / f"barcode_{barcode_type}_{barcode}.png"
    unit_width: int = args.unitwidth
    barcode_height: int = args.verticalsize
    # If the height of the notch is not specified, it will reach halfway down the digits, even if they're not visible.
    default_notch_height: int = int(unit_width * (FONT_SIZE_FACTOR + TEXT_Y_OFFSET * 2)) // 2
    notch_height: int = args.notch if args.notch is not None else default_notch_height
    # Sets the width of all individual borders to args.border
    border: Dict[str, int] = {side: args.border for side in ["Left", "Right", "Top", "Bottom"]}
    # If a value has been provided for any individual border, changes it; this overwrites args.border's global setting.
    border["Left"] = args.leftborder if args.leftborder is not None else border["Left"]
    border["Right"] = args.rightborder if args.rightborder is not None else border["Right"]
    border["Top"] = args.topborder if args.topborder is not None else border["Top"]
    border["Bottom"] = args.bottomborder if args.bottomborder is not None else border["Bottom"]
    
    # If the text is to be drawn underneath the barcode and the barcode type is EAN-13, extends the left border to make
    # room for the extra digit.
    draw_digits: bool = args.nodigits
    if draw_digits and barcode_type == "EAN-13":
        border["Left"] += unit_width * EAN_13_LEFT_BORDER_EXTENSION_FACTOR
        
    # Splits the barcode into groups of digits according to the barcode's type.
    # Element [0] is the EAN-13 leading digit ("0" if not EAN-13), [1] is left side digits, [2] is right side digits.
    digit_groups: Tuple[str, str, str] = get_digit_groups(barcode, barcode_type)
    
    # Generates a string of 1s and 0s corresponding to the barcode's bars: 0 for white, 1 for black.
    barcode_string = encode_barcode(*digit_groups)
    
    # If the user passed the -s | --bitstring parameter, outputs barcode_string and exits.
    if args.bitstring:
        print(barcode_string)
        sys.exit()
    
    # Generates a string that encodes the barcode image (without any text) in the PBM format (1-bit monochrome).
    pbm_data = generate_pbm_data(barcode_string,
                                 border,
                                 unit_width=unit_width,
                                 barcode_height=barcode_height,
                                 notch_height=notch_height,
                                 type=barcode_type,
                                 draw_digits=draw_digits)
    
    # Loads the PBM data into Pillow and gets an Image object.
    pillow_image = convert_to_pillow_image(pbm_data)
    
    # Unless the user passed the -d | --nodigits parameter, draws the digits as text onto the Pillow Image.
    if draw_digits:
        draw_digit_text(pillow_image, *digit_groups, border, unit_width, barcode_height, barcode_type)
    
    # Converts the Pillow Image and saves it to file; the format is determined by the file's extension (PNG by default).
    save_pillow_image(pillow_image, output_path)
    
    # If we made it this far, outputs a confirmation for the user.
    print(f"Barcode number: {barcode}.")
    print(f"Encoding format: {barcode_type}.")
    print(f'File saved successfully to "{output_path}".')


def positive_int(n: int) -> int:
    """A custom type for use with argparse: if the entered number is not a positive integer, raises an exception."""
    try:
        n = int(n)
        if n <= 0:
            raise argparse.ArgumentTypeError(f"{n} is not a positive integer.")
    except ValueError:
        raise argparse.ArgumentTypeError(f"{n} is not a positive integer.")
    return n


def non_negative_int(n: int) -> int:
    """A custom type for use with argparse: if the entered number is not a non-negative integer, raises an exception."""
    try:
        n = int(n)
        if n < 0:
            raise argparse.ArgumentTypeError(f"{n} is not a non-negative integer.")
    except ValueError:
        raise argparse.ArgumentTypeError(f"{n} is not a non-negative integer.")
    return n


def convert_to_pillow_image(pbm_data: str) -> Image:
    """Converts a PBM string into a Pillow Image object."""
    pbm_memory_file = io.BytesIO(pbm_data.encode("utf-8"))        
    pillow_image = Image.open(pbm_memory_file)
    pillow_image = pillow_image.convert("L") # Converts pillow_image to 8-bit grayscale
    return pillow_image


def save_pillow_image(image: Image, path: Path):
    """
    Saves the Pillow Image object to file, in the format specified in the file's extension.
    If a file with the specified name already exists, asks if it's ok to overwrite.
    If the file's entension doesn't indicate a correct image format, or if the provided path is incorrect,
    raises an exception and exits.
    """
    if path.is_dir():
            sys.exit("Error: no filename provided.")
    if path.suffix == "":
            sys.exit("Error: filename has no extension.")
    if path.exists():
        while True:
            reply = input(f"The file \"{path}\" already exists. Do you want to overwrite it? (Y/N) ").upper().strip()
            if reply == "Y":
                break
            elif reply == "N":
                sys.exit()
    try:
        image.save(path)
    except ValueError:
        sys.exit(f"Error: \"{path.suffix}\": incorrect or unsupported file format.")
    except OSError as e:
        if str(e)[0:9] == "[Errno 2]":
            sys.exit("Error: incorrect path: no such directory.")
        else:
            sys.exit("Error: file could not be written.")


def draw_digit_text(image: Image,
                    leading_digit: str,
                    left_digits: str,
                    right_digits: str,
                    border: Dict[str, int],
                    unit_width: int,
                    barcode_height: int,
                    barcode_type: str):
    """Draws the optional text underneath the barcode."""
    font_size: int = unit_width * FONT_SIZE_FACTOR
    leading_digit_x: int = border["Left"] - (unit_width * EAN_13_LEADING_DIGIT_SHIFT)
    # Shifts the text to the right by +1 unit because the side guard ends with a black bar and would touch the text.
    left_text_x: int = border["Left"] + unit_width * (len(SIDE_GUARD) + 1)
    right_text_x: int = border["Left"] + unit_width * (UNITS_PER_SIDE[barcode_type] + len(SIDE_GUARD) +
                                                       len(MIDDLE_GUARD))
    text_y: int = border["Top"] + barcode_height + int(unit_width * TEXT_Y_OFFSET)
    
    try:
        font: ImageFont = ImageFont.truetype("OCR-B.ttf", font_size)
    except OSError:
        sys.exit("Error: cannot find the font file \"OCR-B.ttf\". "
                 "Make sure that it's in the same directory as the script.\n"
                 "You can still generate the barcode without text, by using the -d or --nodigits parameter.")
    draw: ImageDraw = ImageDraw.Draw(image)
    
    if barcode_type == "EAN-13":
        draw.text((leading_digit_x, text_y), leading_digit, fill="black", anchor="lt", font=font)
    draw.text((left_text_x, text_y), left_digits, fill="black", anchor="lt", font=font)
    draw.text((right_text_x, text_y), right_digits, fill="black", anchor="lt", font=font)


def get_digit_groups(barcode_number: str, barcode_type: str) -> tuple[str, str, str]:
    """Returns a tuple containing all the digit groups: the leading digit, left digits, and right digits."""
    first_digit: Dict[str, int] = {"EAN-13": 1, "UPC-A": 0, "EAN-8": 0}
    digits_per_side: Dict[str, int] = {"EAN-13": 7, "UPC-A": 6, "EAN-8": 4}
    leading_digit: str = barcode_number[0] if barcode_type == "EAN-13" else "0"
    left_digits: str = barcode_number[first_digit[barcode_type]:digits_per_side[barcode_type]]
    right_digits: str = barcode_number[digits_per_side[barcode_type]:]
    return leading_digit, left_digits, right_digits


def checksum_is_correct(barcode_number: str, return_corrected: bool=False) -> bool | str:
    """Returns True if the checksum number is correct. If return_corrected is True, returns a corrected barcode."""
    # Gets the last digit of the barcode, which is the check digit
    check_digit: int = int(barcode_number[-1])
    # Removes the last digit and reverses the order of the remaining numbers
    barcode_number: str = barcode_number[-2::-1]
    checksum: int = 0
    for i, digit in enumerate(barcode_number):
        checksum += int(digit) * 3 if i % 2 == 0 else int(digit)
    checksum = 0 if (checksum % 10) == 0 else 10 - (checksum % 10)
    if check_digit == checksum:
        return True
    else:
        if return_corrected:
            return f"{barcode_number[::-1]}{checksum}"
        return False


def get_type(barcode: str) -> str:
    """If the number is a valid barcode number, returns its type."""
    if not barcode.isnumeric():
        raise ValueError("Barcode number must be numeric and a positive integer.")
    number_of_digits: int = len(barcode)
    match number_of_digits:
        case 13:
            return "EAN-13"
        case 12:
            return "UPC-A"
        case 8:
            return "EAN-8"
        case _:
            raise ValueError("Incorrect number of digits.")
        

def get_bits(number: int, length: int) -> Generator[bool, None, None]:
    """Generates the specified number of bits of a number, starting with the least significant bit."""
    for i in range(length - 1, -1, -1):
        yield number >> i & 1


def encode_digit(digit: int, parity=None) -> str:
    """
    Encodes a digit into a string of 7 bits and returns it. If the optional keyword argument "parity" is provided
    (0 or 1), uses left-hand encoding and returns a bit string with the requested parity.
    If no "parity" keyword argument is provided, uses right-hand encoding.
    """
    value: int = left_encoding[digit][parity] if parity is not None else right_encoding[digit]
    return "".join(str(bit) for bit in get_bits(value, 7))


def encode_left_side(leading_digit: str, left_digits: str) -> str:
    """
    Encodes the left-hand side of the barcode (the first 7 digits) and returns a string of bits.
    The leading digit is encoded as a combination of left and right parity values of the other 6 digits.
    The encoding follows the values of bits of the numbers in ean_13_encoding.
    For example, 5 would translate to 101, or "even", "odd", "even".
    Then uses the bit as the key to get the correct value from left_encoding.
    """
    output: str = ""
    for i, digit in enumerate(left_digits):
        # Gets the bit to be used as the key to get the correct value from left_encoding.
        parity: int = leading_digit_encoding[int(leading_digit)] >> (5 - i) & 1
        output += encode_digit(int(digit), parity)
    return output


def encode_right_side(right_digits: str) -> str:
    """Encodes the right-hand side of the barcode (the final 6 digits) and returns a string of bits."""
    return "".join(encode_digit(int(digit)) for digit in right_digits)


def encode_barcode(leading_digit: int, left_digits: str, right_digits: str) -> str:
    """Returns the entire barcode as a string of bits."""
    left_side: str = encode_left_side(leading_digit, left_digits)
    right_side: str = encode_right_side(right_digits)
    return f"{SIDE_GUARD}{left_side}{MIDDLE_GUARD}{right_side}{SIDE_GUARD}"


def generate_notches(unit_width: int, type: str) -> str:
    """Generates text notches (extensions of the side and middle guards making room for the optional text.)"""
    side: str = "".join(bit * unit_width for bit in SIDE_GUARD)
    middle: str = "".join(bit * unit_width for bit in MIDDLE_GUARD)
    empty_space: str = "0" * UNITS_PER_SIDE[type] * unit_width
    return f"{side}{empty_space}{middle}{empty_space}{side}"
    

def generate_pbm_data(bit_string: str,
                      border: Dict[str, int],
                      type: str="EAN-13",
                      unit_width: int=6,
                      barcode_height: int=400,
                      notch_height: int=0,
                      draw_digits: bool=True) -> str:
    """
    Returns a string containing the barcode image data in PBM format.
    This data can be saved to a .pbm file directly or loaded into Pillow for further enhancement or format conversion.
    """
    width: int = len(bit_string) * unit_width + border["Left"] + border["Right"]
    height_extension: int = max(int(unit_width * (FONT_SIZE_FACTOR + TEXT_Y_OFFSET) * draw_digits), notch_height)
    height: int = barcode_height + height_extension + border["Top"] + border["Bottom"]
    left_border: str = "0" * border["Left"]
    right_border: str = "0" * border["Right"]
    top_border_lines: str = (("0" * width) + "\n") * border["Top"]
    bottom_border_lines: str = (("0" * width) + "\n") * (border["Bottom"] + height_extension)
    barcode_lines: str = (left_border + "".join(bit * unit_width for bit in bit_string) + right_border +
                          "\n") * barcode_height
    
    pbm_data: str = f"P1\n# {type} BARCODE\n{width} {height}\n"
    pbm_data += top_border_lines
    pbm_data += barcode_lines
    if notch_height:
        pbm_data += ("".join((left_border, generate_notches(unit_width, type), right_border, "\n"))) * notch_height
    pbm_data += bottom_border_lines
    return pbm_data
    

if __name__ == "__main__":
    main()
    