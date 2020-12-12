import os
import re
import ctypes
from pathlib import Path

# Q: Why not using configparser module?
# A: Emmm, it raised "configparser.DuplicateOptionError".

CONF_PATH = \
    R'%localappdata%\TslGame\Saved\Config\WindowsNoEditor' \
    R'\GameUserSettings.ini'
WIDTH, HEIGHT = 1920, 1080


def msgbox(text, title=''):
    func = ctypes.windll.user32.MessageBoxW
    func(None, text, title, 0)


def change_resolution_size(conf, width, height):
    new_conf = re.sub(
        r'(\nResolutionSizeX=)(\d+)', r'\g<1>' + str(width), conf)
    new_conf = re.sub(
        r'(\nResolutionSizeY=)(\d+)', r'\g<1>' + str(height), new_conf)
    return new_conf


def modify_conf(conf_file, width, height):
    with open(conf_file, 'rb') as f:
        conf = f.read(1024 * 1024).decode()

    with open(conf_file, 'wb') as f:
        new_conf = change_resolution_size(conf, width, height)
        f.write(new_conf.encode())


def main():
    conf_path = Path(os.path.expandvars(CONF_PATH))
    width, height = WIDTH, HEIGHT
    modify_conf(conf_path, width, height)
    msgbox(f'OK, changed to: {width}x{height}', conf_path.name)


if __name__ == "__main__":
    main()
