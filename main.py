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


def checksum_is_correct(barcode_number: int) -> bool:
    """Returns True if the checksum number is correct."""
    check_digit = barcode_number % 10
    number_string = str(barcode_number)[:-1]
    # If the number is in the UPC format, appends a leading zero.
    number_string = f"0{number_string}" if len(number_string) == 11 else number_string
    sum = 0
    for i in range(len(number_string)):
        # Note: because of 0-based indexing, we're adding to odd_sum when i is even and vice versa.
        if i % 2 == 0:
            sum += int(number_string[i])
        else:
            sum += int(number_string[i]) * 3
    result = 0 if (sum % 10) == 0 else 10 - (sum % 10)
    return check_digit == result
    

def encode_digit(digit: int, parity=None) -> str:
    """
    Encodes a digit into a string of 7 bits and returns it. If the optional keyword argument "parity" is provided (0 or
    1), uses left-hand encoding and returns a bit string with the requested parity.
    If no "parity" keyword argument is provided, uses right-hand encoding.
    """
    if not parity is None:
        value = left_encoding[digit][parity]
    else:
        value = right_encoding[digit]
    bit_string = ""
    for i in range(6, -1, -1):
        bit_string += str(value >> i & 1)
    return bit_string
