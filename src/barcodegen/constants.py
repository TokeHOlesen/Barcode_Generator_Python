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