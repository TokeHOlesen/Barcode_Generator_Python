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

side_guard = "101"
middle_guard = "01010"


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


def encode_digit(digit: int, parity=None) -> str:
    """
    Encodes a digit into a string of 7 bits and returns it. If the optional keyword argument "parity" is provided
    (0 or 1), uses left-hand encoding and returns a bit string with the requested parity.
    If no "parity" keyword argument is provided, uses right-hand encoding.
    """
    if parity is not None:
        value = left_encoding[digit][parity]
    else:
        value = right_encoding[digit]
    bit_string = ""
    for i in range(6, -1, -1):
        bit_string += str(value >> i & 1)
    return bit_string


def encode_left_side(barcode_number: str) -> str:
    """
    Encodes the left-hand side of the barcode (the first 7 digits) and returns a string of bits.
    The first digit is encoded as a combination of left and right parity values of the other 6 digits.
    The encoding follows the values of bits of the numbers in ean_13_encoding.
    For example, 5 would translate to 101, or "even", "odd", "even".
    Then uses the bit as the key to get the correct value from left_encoding.
    """
    country_digit = int(barcode_number[0])
    left_digits = barcode_number[1:7]
    output = ""
    for i, digit in enumerate(left_digits):
        # Gets the bit to be used as the key to get the correct value from left_encoding
        parity = ean_13_encoding[country_digit] >> (5 - i) & 1
        output += encode_digit(int(digit), parity)
    return output


def encode_right_side(barcode_number: str) -> str:
    """Encodes the right-hand side of the barcode (the final 6 digits) and returns a string of bits."""
    right_digits = barcode_number[7:]
    print(right_digits)
    output = ""
    for digit in right_digits:
        output += encode_digit(int(digit))
    return output


def encode_barcode(barcode_number: str) -> str:
    """Returns the entire barcode as a string of bits."""
    left_side = encode_left_side(barcode_number)
    right_side = encode_right_side(barcode_number)
    return f"{side_guard}{left_side}{middle_guard}{right_side}{side_guard}"


def generate_pbm_file(bit_string: str):
    """Generates a temporary graphical file with the barcode, with a given height and a width of 95 pixels."""
    height = 40
    with open("barcode.pbm", "w") as output_file:
        output_file.write("P1\n")
        output_file.write("# Barcode\n")
        output_file.write(f"95 {height}\n")
        for _ in range(height):
            output_file.write(f"{bit_string}\n")
