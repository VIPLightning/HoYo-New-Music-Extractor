import argparse
import hashlib
import os
import shutil
import subprocess
from pathlib import Path

# CONSTANTS
MD5_HASH_FILES = True

HDIFF_DIR = "./Hdiff Files"
ORIGINAL_DIR = "./Original Game Files"
NEW_DIR = "./New Game Files"

WAV_DIR = "./Temp/WAV"
ORIGINAL_DECODE_DIR = "./Temp/Original Decoding"
NEW_DECODE_DIR = "./Temp/New Decoding"

TOOLS_DIR = "./Tools"
OUTPUT_DIR = "./Output AAC/"

# Check if running on Windows and append .exe if so
EXECUTABLE_EXTENSION = ""
if os.name == 'nt':
    EXECUTABLE_EXTENSION = ".exe"

# FUNCTIONS

# Walk directory and return list of .hdiff files in root of directory
def walk_dir(path):
    file_list = []
    # Get file list at root of path
    for (dirpath, dirnames, filenames) in os.walk(path):
        file_list.extend(filenames)
        break
    return list(filter(lambda name: Path(name).suffix == ".hdiff", file_list))

# Run hpatch for all hdiff files listed in file_list
# Patches files in original_dir with patches in patch_dir and output result to output_dir
def hpatch_files(original_dir, patch_dir, output_dir, file_list):
    hpatch_exec = Path.joinpath(Path(TOOLS_DIR).resolve(), "hpatchz" + EXECUTABLE_EXTENSION)
    original_dir_abs = Path(original_dir).resolve()
    patch_dir_abs = Path(patch_dir).resolve()
    output_dir_abs = Path(output_dir).resolve()
    total = len(file_list)
    iteration = 0
    for file_name in file_list:
        iteration += 1
        show_progress(iteration, total, "", "Patching Files")
        # Get original file name without .hdiff extension
        file_name_stem = Path(file_name).stem
        subprocess.call([hpatch_exec, Path.joinpath(original_dir_abs, file_name_stem), Path.joinpath(patch_dir_abs, file_name), Path.joinpath(output_dir_abs, file_name_stem)])

# Extract individual audio files from Wwise PCK files with quickbms
def extract_files(original_dir, output_dir):
    tools_dir_abs = Path(TOOLS_DIR).resolve()
    subprocess.call([Path.joinpath(tools_dir_abs, "quickbms" + EXECUTABLE_EXTENSION), Path.joinpath(tools_dir_abs, "wavescan.bms"), Path(original_dir).resolve(), Path(output_dir).resolve()])

# Find and return list of all files in new_dir that are not also present in original_dir
def filter_diff_files(original_dir, new_dir):
    original_dir_abs = Path(original_dir).resolve()
    new_dir_abs = Path(new_dir).resolve()
    # Calculate list of new files
    original_file_list = []
    for (dirpath, dirnames, filenames) in os.walk(original_dir):
        original_file_list.extend(filenames)
        break
    original_file_list = list(filter(lambda name: Path(name).suffix == ".wem", original_file_list))
    new_file_list = []
    for (dirpath, dirnames, filenames) in os.walk(new_dir):
        new_file_list.extend(filenames)
        break
    new_file_list = list(filter(lambda name: Path(name).suffix == ".wem", new_file_list))
    return_list = []
    iteration = 0
    if MD5_HASH_FILES:
        total = len(original_file_list) + len(new_file_list)
        old_file_hashes = {}
        new_file_hashes = {}
        # Take MD5 hashes of both new and old music files
        for file_name in original_file_list:
            iteration += 1
            show_progress(iteration, total, "", "Filtering New Files")
            old_file = Path.joinpath(original_dir_abs, file_name)
            file_hash = get_md5(old_file)
            if file_hash:
                old_file_hashes[file_hash + "," + str(old_file.stat().st_size)] = file_name
        for file_name in new_file_list:
            iteration += 1
            show_progress(iteration, total, "", "Filtering New Files")
            new_file = Path.joinpath(new_dir_abs, file_name)
            file_hash = get_md5(new_file)
            if file_hash:
                new_file_hashes[file_hash + "," + str(new_file.stat().st_size)] = file_name
            else:
                return_list.append(file_name)
        # Take the difference, keeping only new file hashes
        diff_keys = set(new_file_hashes.keys()) - set(old_file_hashes.keys())
        total = len(diff_keys)
        iteration = 0
        # Iterate over all new file hashes to get the file names associated with them
        for key in diff_keys:
            iteration += 1
            show_progress(iteration, total, "", "Finalizing")
            return_list.append(new_file_hashes[key])
    else:
        total = len(new_file_list)
        # Iterate over all patched files to find ones that weren't present before
        for file_name in new_file_list:
            iteration += 1
            show_progress(iteration, total, "", "Filtering New Files")
            old_file = Path.joinpath(original_dir_abs, file_name)
            new_file = Path.joinpath(new_dir_abs, file_name)
            # If file name exised in old directory, check sizes
            if old_file.exists():
                old_file_size = old_file.stat().st_size
                new_file_size = new_file.stat().st_size
                if old_file_size != new_file_size:
                    return_list.append(file_name)
            # If file didn't exist in old directory, add to new list
            else:
                return_list.append(file_name)
    return return_list

def get_md5(file):
    try:
        return hashlib.md5(file.read_bytes()).hexdigest()
    except:
        return False

# Convert all files from file_dir with names in file_list to WAV format
def convert_to_wav(file_dir, file_list, output_dir):
    total = len(file_list)
    iteration = 0
    vgmstream_exec = Path.joinpath(Path(TOOLS_DIR).resolve(), "vgmstream-cli" + EXECUTABLE_EXTENSION)
    file_dir_abs = Path(file_dir).resolve()
    output_dir_abs = Path(output_dir).resolve()
    for file_name in file_list:
        iteration += 1
        show_progress(iteration, total, "", "Converting to WAV")
        file = Path.joinpath(file_dir_abs, file_name)
        output_file = Path.joinpath(output_dir_abs, file.stem + ".wav")
        subprocess.call([vgmstream_exec, "-o", output_file, file])

# Convert all files from file_dir with names in file_list to AAC format
def convert_to_aac(file_dir, file_list, output_dir):
    total = len(file_list)
    iteration = 0
    neroaac_exec = Path.joinpath(Path(TOOLS_DIR).resolve(), "neroAacEnc" + EXECUTABLE_EXTENSION)
    file_dir_abs = Path(file_dir).resolve()
    output_dir_abs = Path(output_dir).resolve()
    for file_name in file_list:
        iteration += 1
        show_progress(iteration, total, "", "Converting to AAC")
        file = Path.joinpath(file_dir_abs, file_name[:-4] + ".wav")
        output_file = Path.joinpath(output_dir_abs, file.stem + ".m4a")
        subprocess.call([neroaac_exec, "-q", "0.69", "-if", file,"-of",output_file])

def show_progress(iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    # Print New Line on Complete
    if iteration == total: 
        print()

def check_temp_folders():
    print("Checking folders for temporary files")
    folders = [WAV_DIR, ORIGINAL_DECODE_DIR, NEW_DECODE_DIR]

    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)

def delete_temp_files(new_file_flag):
    print("Deleting existing temporary files")
    if new_file_flag:
        folders = [WAV_DIR, ORIGINAL_DECODE_DIR, NEW_DECODE_DIR, NEW_DIR]
    elif not new_file_flag:
        folders = [WAV_DIR, ORIGINAL_DECODE_DIR, NEW_DECODE_DIR]

    for folder in folders:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')

def main():

    parser = argparse.ArgumentParser(description="Example argument parser")
    
    parser.add_argument("--no-hdiff", action="store_false",
                        help="Disable hdiff (default: enabled)")

    args = parser.parse_args()
    
    hdiff_flag = args.no_hdiff

    check_temp_folders()
    
    if hdiff_flag:
        delete_temp_files(hdiff_flag)
        file_list = walk_dir(HDIFF_DIR) # Gets list of all .hdiff files
        hpatch_files(ORIGINAL_DIR, HDIFF_DIR, NEW_DIR, file_list) # Patch all Wwise PCK audio files
    elif not hdiff_flag:
        delete_temp_files(hdiff_flag)
        if not os.listdir(NEW_DIR):
            print(f"{NEW_DIR} is empty.")
            return
    
    extract_files(ORIGINAL_DIR, ORIGINAL_DECODE_DIR) # Extract all original audio files
    extract_files(NEW_DIR, NEW_DECODE_DIR) # Extract all patched audio files
    
    new_file_list = filter_diff_files(ORIGINAL_DECODE_DIR, NEW_DECODE_DIR) # Find any new audio files that were not present in original PCK
    convert_to_wav(NEW_DECODE_DIR, new_file_list, WAV_DIR) # Convert all new audio files to WAV
    convert_to_aac(WAV_DIR, new_file_list, OUTPUT_DIR) # Convert all WAV to AAC
    
    delete_temp_files(hdiff_flag)
    print("Finished!")

if __name__ == "__main__":
    main()
