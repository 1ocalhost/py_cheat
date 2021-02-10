import os
import sys
from pathlib import Path


def as_int(bytes_):
    return int.from_bytes(bytes_, 'little')


def read_color_table_flag(reader, offset):
    packed = as_int(reader.read(offset, 1))
    gct_flag = (packed & 0x80) != 0
    gct_size = 2 << (packed & 7)
    if gct_flag:
        return gct_size * 3
    return 0


def parse_gif_extension(type_, reader, block_begin):
    if type_ != 9:
        return

    block_begin += 1
    if reader.read(block_begin, 13) == b'\xff\x0bNETSCAPE2.0':
        block_begin += 18
    elif reader.read(block_begin, 2) == b'\xf9\x04' \
            and reader.read(block_begin + 6, 1) == b'\x00':
        block_begin += 7
    else:
        return

    return block_begin


def parse_gif_block(reader, block_begin):
    gct_size = read_color_table_flag(reader, block_begin + 9)
    block_begin += (10 + gct_size + 1)

    while True:
        data_size = as_int(reader.read(block_begin, 1))
        block_begin += (1 + data_size)
        if not data_size:
            break

    return block_begin


def try_parse_gif_body(type_, reader, offset):
    gct_size = read_color_table_flag(reader, offset + 4)
    block_begin = offset + 7 + gct_size
    did_find_block = False

    while True:
        first_char = reader.read(block_begin, 1)

        if first_char == b';':
            if did_find_block:
                return block_begin + 1
            else:
                return
        elif first_char == b'!':
            result = parse_gif_extension(type_, reader, block_begin)
            if result is None:
                return
            block_begin = result
        elif first_char == b',':
            if not did_find_block:
                did_find_block = True
            block_begin = parse_gif_block(reader, block_begin)
        else:
            return


def report_found(reader, type_, begin, end):
    gif_size = end - begin
    print(f'found: ver {type_}: {begin}, {gif_size}')
    path = Path(reader.file_path)
    gif_path = path.parent / (path.name + '.out') / f'{begin}.gif'
    gif_path.parent.mkdir(exist_ok=True)
    with open(gif_path, 'wb') as f:
        f.write(reader.read(begin, gif_size))


class FileReader:
    def __init__(self, path):
        self.file_path = path
        self.data_file = open(path, 'rb')

    def read(self, offset, length):
        self.data_file.seek(offset, 0)
        return self.data_file.read(length)

    def size(self):
        return os.fstat(self.data_file.fileno()).st_size


def search_gif(path):
    reader = FileReader(path)
    last_res_end = 0

    for i in range(reader.size()):
        if i < last_res_end:
            continue

        if reader.read(i, 1) != b'G':
            continue

        next_data = reader.read(i + 1, 5)
        if next_data == b'IF87a':
            type_ = 7
        elif next_data == b'IF89a':
            type_ = 9
        else:
            continue

        result = try_parse_gif_body(type_, reader, i + 6)
        if result is None:
            continue
        else:
            last_res_end = result
            report_found(reader, type_, i, result)


def main():
    path = sys.argv[1]  # such as a process dump file
    print(path)
    search_gif(path)


if __name__ == '__main__':
    main()
