import socket
import ipaddress

def rev_lookup_true(lookup_value):

    try:
        if ipaddress.ip_address(lookup_value):
            result = "ipad"
    except ValueError:
        result = "dns"

    return result


def parse_dns_string(reader, data):
    res = ''
    to_resue = None
    bytes_left = 0

    for ch in data:
        if not ch:
            break

        if to_resue is not None:
            resue_pos = chr(to_resue) + chr(ch)
            res += reader.reuse(resue_pos)
            break

        if bytes_left:
            res += chr(ch)
            bytes_left -= 1
            continue

        if (ch >> 6) == 0b11 and reader is not None:
            to_resue = ch - 0b11000000
        else:
            bytes_left = ch

        if res:
            res += '.'

    return res


class StreamReader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def read(self, len_):
        pos = self.pos
        if pos >= len(self.data):
            raise

        res = self.data[pos: pos+len_]
        self.pos += len_
        return res

    def reuse(self, pos):
        pos = int.from_bytes(pos.encode(), 'big')
        return parse_dns_string(None, self.data[pos:])



def make_dns_query_lookup_value(lookup_value, lookup_type):

    def f(s):
        return chr(len(s)) + s

    if lookup_type == "dns":

        parts = lookup_value.split('.')
        parts = list(map(f, parts))
    else:
        ipad_reverse_pointer = ipaddress.ip_address(lookup_value).reverse_pointer
        parts = ipad_reverse_pointer.split('.')
        parts = list(map(f, parts))

    return ''.join(parts).encode()


def make_dns_request_data(dns_query, lookup_type):

    req = b'\xaa\xbb\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00'
    req += dns_query

    if lookup_type == "dns":   
       req += b'\x00\x00\x01\x00\x01'
    else: 
        req += b'\x00\x00\x0c\x00\x01'

    return req


def add_record_to_result(result, type_, data, reader):
    if type_ == 'A':
        item = str(ipaddress.IPv4Address(data))
    elif type_ == 'CNAME':
        item = parse_dns_string(reader, data)
    elif type_ == 'PTR':
        item = parse_dns_string(reader, data)
    else:
        return

    result.setdefault(type_, []).append(item)


def parse_dns_response(res, dq_len, req):
    reader = StreamReader(res)

    def get_query(s):
        return s[12:12+dq_len]

    data = reader.read(len(req))
    assert(get_query(data) == get_query(req))

    def to_int(bytes_):
        return int.from_bytes(bytes_, 'big')

    result = {}
    res_num = to_int(data[6:8])

    for i in range(res_num):
        reader.read(2)
        type_num = to_int(reader.read(2))

        type_ = None
        if type_num == 1:
            type_ = 'A'
        elif type_num == 5:
            type_ = 'CNAME'
        elif type_num == 12:
            type_ = 'PTR'

        reader.read(6)
        data = reader.read(2)
        data = reader.read(to_int(data))
        add_record_to_result(result, type_, data, reader)

    return result


def dns_lookup(lookup_value, dns_server_address):

    lookup_type = rev_lookup_true(lookup_value)

    dns_query = make_dns_query_lookup_value(lookup_value, lookup_type)
    dq_len = len(dns_query)
    req = make_dns_request_data(dns_query, lookup_type)
       
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2)

    try:
        sock.sendto(req, (dns_server_address, 53))
        res, _ = sock.recvfrom(1024 * 4)
        result = parse_dns_response(res, dq_len, req)

    except Exception:
        return
    finally:
        sock.close()

    return result

if __name__ == '__main__':
    print(dns_lookup('www.stackoverflow.com', "8.8.8.8"))
    print(dns_lookup('8.8.8.8', "1.1.1.1"))
