import string

BASE62_ALPHABET = string.ascii_uppercase + string.ascii_lowercase + string.digits

def base62_encode(num):
    if num == 0:
        return BASE62_ALPHABET[0]
    base62 = []
    while num:
        num, rem = divmod(num, 62)
        base62.append(BASE62_ALPHABET[rem])
    return ''.join(reversed(base62))

def base62_decode(string):
    num = 0
    for char in string:
        num = num * 62 + BASE62_ALPHABET.index(char)
    return num

def encode(flight_no, date, origin, destination):
    combined_string = f'{flight_no}|{date}|{origin}|{destination}'
    num_representation = int.from_bytes(combined_string.encode('utf-8'), 'big')
    return base62_encode(num_representation)

def decode(string):
    num_representation = base62_decode(string)
    combined_string = num_representation.to_bytes((num_representation.bit_length() + 7) // 8, 'big').decode('utf-8')
    flight_no, date, origin, destination = combined_string.split('|')
    return flight_no, date, origin, destination