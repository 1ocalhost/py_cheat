import os
import sys
from pathlib import Path
from PIL import Image

TAB1 = ' ' * 2
TAB2 = ' ' * 4

IMPERFECT_JPEG_HEAD = bytes.fromhex(
    'FF D8 FF EE 00 0E 41 64 6F 62 65 00 64 00')


def convert_image_file(file_path):
    print(f'{TAB2} Opening...   ', end='\r')
    origin = Image.open(file_path)

    print(f'{TAB2} Converting...', end='\r')
    img_copy = origin.convert('RGB')

    print(f'{TAB2} Saving...    ', end='\r')
    img_copy.save(file_path)

    print(f'{TAB2} Converted.   ')


def is_imperfect_jpeg(path):
    if not path.endswith('.JPEG'):
        return False

    try:
        with open(path, 'rb') as f:
            data = f.read(len(IMPERFECT_JPEG_HEAD))
            return data == IMPERFECT_JPEG_HEAD
    except Exception as e:
        print(f'{TAB2} ERROR: {e}')
        return False


def convert_file_list(items):
    converted_num = 0
    for file_ in items:
        print(f'{TAB1} Checking "{file_}"...')
        if os.path.isdir(file_):
            print(f'{TAB2} Skiped (folder).')
            continue

        if is_imperfect_jpeg(file_):
            convert_image_file(file_)
            converted_num += 1
        else:
            print(f'{TAB2} Skiped (not imperfect).')
    return converted_num


def convert_file(file):
    return 1, convert_file_list([file])


def convert_folder(folder):
    children = os.listdir(folder)

    def join_path(file):
        return str(Path(folder) / file)

    children = list(map(join_path, children))
    return len(children), convert_file_list(children)


def convert_from_input(input_items):
    total_num = 0
    converted_num = 0

    for item in input_items:
        print(f'On {item}:')
        if os.path.isfile(item):
            result = convert_file(item)
            total_num += result[0]
            converted_num += result[1]
        elif os.path.isdir(item):
            result = convert_folder(item)
            total_num += result[0]
            converted_num += result[1]
        else:
            print(f'{TAB1} Skiped (not file nor folder).')
        print('\n')

    print('All complete!')
    return total_num, converted_num


def main():
    if len(sys.argv) <= 1:
        print('Please drag files or folders into the icon of this program.')
    else:
        total, converted = convert_from_input(sys.argv[1:])
        msg = f'{converted} of {total} file(s) have been converted!'
        print(msg)
    input()


main()
