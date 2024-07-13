from typing import Generator

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

# Values for encoding the right-hand side of the barcode, in decimal. For both EAN-13 and UPC.
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

# Values for encoding the very first digit of EAN-13 barcodes. The digit is encoded within the following 6 digits as a
# combination of their parity, where odd parity = 0 and even parity = 1.
# For example, the digit one is encoded as 11, that is binary 001011, or "odd", "odd", "even", "odd", "even", "even".
ean_13_encoding = {
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

SIDE_GUARD = "101"
MIDDLE_GUARD = "01010"
UNITS_PER_SIDE = 42


def checksum_is_correct(barcode_number: str) -> bool:
    """Returns True if the checksum number is correct."""
    check_digit = int(barcode_number[-1])
    barcode_number = barcode_number[:-1]
    checksum = 0
    for i, digit in enumerate(barcode_number):
        # Note: because of 0-based indexing, we're adding to odd_sum when i is even and vice versa.
        if i % 2 == 0:
            checksum += int(digit)
        else:
            checksum += int(digit) * 3
    checksum = 0 if (checksum % 10) == 0 else 10 - (checksum % 10)
    return check_digit == checksum


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
    value = left_encoding[digit][parity] if parity is not None else right_encoding[digit]
    bit_string = ""
    for bit in get_bits(value, 7):
        bit_string += str(bit)
    return bit_string


def encode_left_side(barcode_number: str) -> str:
    """
    Encodes the left-hand side of the barcode (the first 7 digits) and returns a string of bits.
    The first digit is encoded as a combination of left and right parity values of the other 6 digits.
    The encoding follows the values of bits of the numbers in ean_13_encoding.
    For example, 5 would translate to 101, or "even", "odd", "even".
    Then uses the bit as the key to get the correct value from left_encoding.
    """
    leading_digit = int(barcode_number[0])
    left_digits = barcode_number[1:7]
    output = ""
    for i, digit in enumerate(left_digits):
        # Gets the bit to be used as the key to get the correct value from left_encoding
        parity = ean_13_encoding[leading_digit] >> (5 - i) & 1
        output += encode_digit(int(digit), parity)
    return output


def encode_right_side(barcode_number: str) -> str:
    """Encodes the right-hand side of the barcode (the final 6 digits) and returns a string of bits."""
    right_digits = barcode_number[7:]
    output = ""
    for digit in right_digits:
        output += encode_digit(int(digit))
    return output


def encode_barcode(barcode_number: str) -> str:
    """Returns the entire barcode as a string of bits."""
    left_side = encode_left_side(barcode_number)
    right_side = encode_right_side(barcode_number)
    return f"{SIDE_GUARD}{left_side}{MIDDLE_GUARD}{right_side}{SIDE_GUARD}"


def generate_notches(unit_width: int) -> str:
    side: str = "".join(bit * unit_width for bit in SIDE_GUARD)
    middle: str = "".join(bit * unit_width for bit in MIDDLE_GUARD)
    empty_space: str = "0" * UNITS_PER_SIDE * unit_width
    return f"{side}{empty_space}{middle}{empty_space}{side}"
    

def generate_pbm_file(bit_string: str, unit_width: int=1, barcode_height: int=40, notch_height: int=0, border: int=0):
    """Generates a temporary graphical file with the barcode."""
    width: int = len(bit_string) * unit_width + border * 2
    height: int = barcode_height + notch_height + border * 2
    side_border: str = "0" * border
    top_and_bottom_border_lines = ("0" * width + "\n") * border
    barcode_lines = (side_border + "".join(bit * unit_width for bit in bit_string) + side_border + "\n") * barcode_height
    
    with open("barcode.pbm", "w") as output_file:
        output_file.write(f"P1\n# Barcode\n{width} {height}\n")
        output_file.writelines(top_and_bottom_border_lines)
        output_file.writelines(barcode_lines)
        if notch_height:
            notch_lines = ("".join((side_border, generate_notches(unit_width), side_border, "\n"))) * notch_height
            output_file.writelines(notch_lines) 
        output_file.writelines(top_and_bottom_border_lines)


generate_pbm_file(encode_barcode("9312345678907"), unit_width=6, barcode_height=350, notch_height=35, border=0)
