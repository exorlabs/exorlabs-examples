"""Create a complete Arduino sketch using the exact reviewed vendor port.
Usage: python3 tools/prepare_firmware.py /path/to/vendor-demo.zip
Copies original project code + vendor support files and LVGL into ignored build/.
"""
import argparse
import hashlib
from pathlib import Path
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "ESP32-S3-LCD-3.16-Demo/Arduino/examples/08_LVGL_V9_Test/"
LIBRARY = "ESP32-S3-LCD-3.16-Demo/Arduino/libraries/lvgl9/"
PORT_SHA256 = "d494f7e290c0e2ec7fd2d5998ffd3ef12e4bbe29bb08b4456caa6f18169f4fcd"


def prepare(archive, build, portrait=False):
    build = Path(build).resolve()
    sketch = build / "ExorRackStats"
    if build.exists(): raise ValueError("Build directory already exists; choose a new --build-dir")
    with zipfile.ZipFile(archive) as vendor:
        original = vendor.read(PREFIX + "lvgl_port.c")
        if hashlib.sha256(original).hexdigest() != PORT_SHA256:
            raise ValueError("Vendor port changed; review it before updating the pinned hash")
        port = original.decode().replace("\r\n", "\n")
        port = port.replace('#include "demos/lv_demos.h"', '#include "model.h"')
        port, count = re.subn(r"(?m)^(\s*)lv_demo_music\(\);", r"\1rackstats_ui_create();", port)
        if count != 1: raise ValueError("Unexpected vendor UI creation site")
        for entry in vendor.infolist():
            if entry.is_dir(): continue
            if entry.filename.startswith(PREFIX):
                relative = Path(entry.filename[len(PREFIX):])
                if relative.suffix == ".ino": continue
                destination = sketch / relative
            elif entry.filename.startswith(LIBRARY):
                relative = Path(entry.filename[len(LIBRARY):])
                destination = build / "libraries" / relative
            else: continue
            if relative.is_absolute() or ".." in relative.parts: raise ValueError("Unsafe vendor archive path")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(vendor.read(entry))
        (sketch / "lvgl_port.c").write_text(port)
    config = (sketch / "user_config.h").read_text()
    config = re.sub(r"(?m)^#define Backlight_Testing.*$", "// Backlight test disabled", config)
    if portrait: config = re.sub(r"(?m)^#define EXAMPLE_Rotate_90.*$", "// Portrait", config)
    (sketch / "user_config.h").write_text(config)
    for item in (ROOT / "firmware").iterdir():
        if item.is_file() and item.name != "config.h.example": shutil.copyfile(item, sketch / item.name)
    source_config = ROOT / "firmware/config.h"
    shutil.copyfile(source_config if source_config.exists() else ROOT / "firmware/config.h.example", sketch / "config.h")
    lvconf = build / "libraries/lv_conf.h"
    text = lvconf.read_text()
    text = re.sub(r"(#define LV_FONT_MONTSERRAT_(?:24|32))\s+0", r"\1 1", text)
    lvconf.write_text(text)
    return sketch


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("vendor_zip")
    parser.add_argument("--build-dir", default=str(ROOT / "build"))
    parser.add_argument("--portrait", action="store_true")
    args = parser.parse_args()
    try: print(prepare(args.vendor_zip, args.build_dir, args.portrait))
    except (ValueError, KeyError, zipfile.BadZipFile) as error: parser.exit(1, str(error) + "\n")
