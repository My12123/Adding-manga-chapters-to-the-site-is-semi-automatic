import os
import zipfile
import time
import argparse
from tqdm import tqdm

def parse_arguments():
    parser = argparse.ArgumentParser(description='Bulk archive directories')
    parser.add_argument('source_dir', type=str, help='The source directory to archive')
    parser.add_argument('-i', '--install', action='store_true', default=False, help='Install zip and tqdm if not already installed')
    args = parser.parse_args()
    return args

def install_packages(packages):
    for package in packages:
        os.system(f"pip install {package}")

def archive_directories(source_dir):
    start_time = time.time()

    # Create a list of directories to archive
    directories = os.listdir(source_dir)

    # Install zip and progressbar if they are not already installed
    if args.install:
        install_packages(['tqdm'])

    # Archive each directory separately
    for directory in tqdm(directories):
        # Create a zip file object
        with zipfile.ZipFile(os.path.join(source_dir, f"{directory}.zip"), "w") as zip_file:
            # Iterate over the files in the directory
            for root, _, filenames in os.walk(os.path.join(source_dir, directory)):
                for filename in filenames:
                    # Create a path to the file
                    file_path = os.path.join(root, filename)

                    # Check if the file is a regular file (not a directory)
                    if os.path.isfile(file_path):
                        # Add the file to the zip archive
                        zip_file.write(file_path, arcname=filename)

    # Calculate the total execution time
    execution_time = time.time() - start_time
    print(f"Total execution time: {execution_time:.2f} seconds")

if __name__ == '__main__':
    args = parse_arguments()
    source_dir = args.source_dir
    archive_directories(source_dir)
