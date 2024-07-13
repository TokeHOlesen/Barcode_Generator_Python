from typing import Generator

SIDE_GUARD = "101"
MIDDLE_GUARD = "01010"
DIGITS_PER_SIDE = {"EAN-13": 6, "UPC": 6, "EAN-8": 4}
UNITS_PER_SIDE = {"EAN-13": 42, "UPC": 42, "EAN-8": 28}

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


def main():
    barcode = "812345678901"
    barcode_type = get_type(barcode)
    barcode_string = encode_barcode(barcode, type=barcode_type)
    generate_pbm_file(barcode_string, unit_width=6, barcode_height=350, notch_height=35, border=50, type=barcode_type)


def checksum_is_correct(barcode_number: str) -> bool:
    """Returns True if the checksum number is correct."""
    # Gets the last digit of the barcode, which is the check digit
    check_digit = int(barcode_number[-1])
    # Removes the last digit and reverses the order of the remaining numbers
    barcode_number = barcode_number[-2::-1]
    checksum = 0
    for i, digit in enumerate(barcode_number):
        if i % 2 == 0:
            checksum += int(digit) * 3
        else:
            checksum += int(digit) * 1
    checksum = 0 if (checksum % 10) == 0 else 10 - (checksum % 10)
    return check_digit == checksum


def get_type(barcode: str) -> str:
    """If the number is a valid barcode number, returns its type."""
    if not barcode.isnumeric():
        raise ValueError("Barcode number must be numeric.")
    number_of_digits = len(barcode)
    match number_of_digits:
        case 13:
            return "EAN-13"
        case 12:
            return "UPC"
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
    value = left_encoding[digit][parity] if parity is not None else right_encoding[digit]
    return "".join(str(bit) for bit in get_bits(value, 7))


def encode_left_side(barcode_number: str, type: str) -> str:
    """
    Encodes the left-hand side of the barcode (the first 7 digits) and returns a string of bits.
    The first digit is encoded as a combination of left and right parity values of the other 6 digits.
    The encoding follows the values of bits of the numbers in ean_13_encoding.
    For example, 5 would translate to 101, or "even", "odd", "even".
    Then uses the bit as the key to get the correct value from left_encoding.
    """
    leading_digit = int(barcode_number[0])
    left_digits = barcode_number[1:(DIGITS_PER_SIDE[type] + 1)]
    
    output = ""
    for i, digit in enumerate(left_digits):
        # Gets the bit to be used as the key to get the correct value from left_encoding.
        parity = ean_13_encoding[leading_digit] >> (5 - i) & 1
        output += encode_digit(int(digit), parity)
    return output


def encode_right_side(barcode_number: str, type: str) -> str:
    """Encodes the right-hand side of the barcode (the final 6 digits) and returns a string of bits."""
    right_digits = barcode_number[(DIGITS_PER_SIDE[type] + 1):]
    return "".join(encode_digit(int(digit)) for digit in right_digits)


def encode_barcode(barcode_number: str, type: str="EAN-13") -> str:
    """Returns the entire barcode as a string of bits."""
    # Adds a leading zero if the barcode is in UPC or EAN-13 format.
    barcode_number = "0" + barcode_number if type in ["UPC", "EAN-8"] else barcode_number
    left_side = encode_left_side(barcode_number, type)
    right_side = encode_right_side(barcode_number, type)
    return f"{SIDE_GUARD}{left_side}{MIDDLE_GUARD}{right_side}{SIDE_GUARD}"


def generate_notches(unit_width: int, type="EAN-13") -> str:
    """Generates text notches (extensions of the side and middle guards making room for optional text.)"""
    side: str = "".join(bit * unit_width for bit in SIDE_GUARD)
    middle: str = "".join(bit * unit_width for bit in MIDDLE_GUARD)
    empty_space: str = "0" * UNITS_PER_SIDE[type] * unit_width
    return f"{side}{empty_space}{middle}{empty_space}{side}"
    

def generate_pbm_file(bit_string: str,
                      type: str="EAN-13",
                      unit_width: int=1,
                      barcode_height: int=40,
                      notch_height: int=0,
                      border: int=0):
    """Generates a PBM graphical file with the barcode."""
    width: int = len(bit_string) * unit_width + border * 2
    height: int = barcode_height + notch_height + border * 2
    side_border: str = "0" * border
    top_and_bottom_border_lines = ["0" * width + "\n"] * border
    barcode_lines = [side_border + "".join(bit * unit_width for bit in bit_string) + side_border + "\n"] * barcode_height
    
    with open("barcode.pbm", "w") as output_file:
        output_file.write(f"P1\n# {type} BARCODE\n{width} {height}\n")
        output_file.writelines(top_and_bottom_border_lines)
        output_file.writelines(barcode_lines)
        if notch_height:
            notch_lines = ["".join((side_border, generate_notches(unit_width, type), side_border, "\n"))] * notch_height
            output_file.writelines(notch_lines) 
        output_file.writelines(top_and_bottom_border_lines)


if __name__ == "__main__":
    main()
    