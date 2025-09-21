import pytest
from main import checksum_is_correct, get_type, get_bits, encode_digit, encode_left_side, encode_right_side


def test_checksum_is_correct():
    assert checksum_is_correct("0000000000000")
    assert checksum_is_correct("4101450004474")
    assert checksum_is_correct("697929110035")
    assert checksum_is_correct("96385074")
    assert not checksum_is_correct("1234567891234")
    assert not checksum_is_correct("44444444")
    assert not checksum_is_correct("458123648745")
    

def test_get_type():
    assert get_type("9002236311037") == "EAN-13"
    assert get_type("044670012826") == "UPC-A"
    assert get_type("00550246") == "EAN-8"
    with pytest.raises(ValueError):
        get_type("123ABC")
    with pytest.raises(ValueError):
        get_type("12345")
    with pytest.raises(ValueError):
        get_type("43518432135497")
        

def test_get_bits():
    assert "".join(str(bit) for bit in get_bits(15, 8)) == "00001111"
    assert "".join(str(bit) for bit in get_bits(115, 8)) == "01110011"
    assert "".join(str(bit) for bit in get_bits(26, 5)) == "11010"


def test_encode_digit():
    assert encode_digit(4) == "1011100"
    assert encode_digit(4, 0) == "0100011"
    assert encode_digit(4, 1) == "0011101"
    
    
def test_encode_left_side():
    assert encode_left_side("4", "101450") == "001100101001110011001010001101110010100111"
    assert encode_left_side("7", "501054") == "011000101001110011001010011101100010011101"
    assert encode_left_side("0", "697929") == "010111100010110111011000101100100110001011"
    

def test_encode_right_side():
    assert encode_right_side("004474") == "111001011100101011100101110010001001011100"
    assert encode_right_side("530107") == "100111010000101110010110011011100101000100"
    assert encode_right_side("110035") == "110011011001101110010111001010000101001110"
