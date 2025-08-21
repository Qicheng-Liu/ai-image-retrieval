import zipfile
import json
import os

ZIP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "Prototype Master.zip"))
OUTPUT_INDEX = os.path.join(os.path.dirname(__file__), "image_index.json")


def index_zip_images():
    jpg_files = []
    with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
        for file in zip_ref.namelist():
            if file.lower().endswith('.jpg'):
                jpg_files.append(file)

    with open(OUTPUT_INDEX, 'w') as f:
        json.dump(jpg_files, f, indent=2)

    print(f"✅ Indexed {len(jpg_files)} .jpg images to {OUTPUT_INDEX}")


def extract_images(zip_path=ZIP_PATH, output_dir="static/images"):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(output_dir)
        print(f"✅ Extracted all files to: {output_dir}")

if __name__ == "__main__":
    index_zip_images()
    extract_images()

