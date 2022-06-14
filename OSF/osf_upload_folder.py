"""
You should install osfclient from GITHUB to use this script.
The github version of osfclient is better than the PYPI version.
"""

import subprocess
import os
from argparse import ArgumentParser
import csv

from utils import get_all_files_in_dir


def run_osf(args):
    """Run osf args from command line."""
    subprocess.run(["osf", *args])


def run_capture_osf(args):
    """Run osf args from command line but capture the output in python."""
    result = subprocess.run(["osf", *args], stdout=subprocess.PIPE)
    return result.stdout.decode("utf-8")


def get_help():
    """Get help on an osf command line function."""
    run_osf(["-h"])


def remove_file(remote):
    """
    Remove the file remote from the project if it exists.

    NOTE this requires installing osfclient from Github source
    As osf remove is broken in the PyPI release.
    """
    run_osf(["remove", remote])


def upload_file(local, remote):
    """Upload the filename at local to remote."""
    run_osf(["upload", local, remote])


def list_files():
    """Print all the files in this OSF project."""
    run_osf(["ls"])


def get_osf_files():
    """Get a list of all files in this OSF project."""
    result = run_capture_osf(["ls"])
    return [
        line[len("osfstorage\\") :].replace("/", "\\") for line in result.splitlines()
    ]


def list_extensions(folder):
    file_list = get_all_files_in_dir(folder, recursive=True)
    return get_extensions(file_list)


def get_extensions(l):
    ext_list = []
    for item in l:
        ext = os.path.splitext(item)[1][1:]
        if ext not in ext_list:
            ext_list.append(ext)
    return ext_list


def list_osf_extensions():
    l = get_osf_files()
    return get_extensions(l)


def should_use_file(filename, ext_ignore_list):
    """Returns True if filename extension not in ext_ignore_list."""
    ext = os.path.splitext(filename)[1][1:]
    return not any(ext.startswith(ignore) for ignore in ext_ignore_list)


def is_temp_file(filename):
    """Temp file is file is like A.B.C.D."""
    base_without_ext = os.path.splitext(os.path.basename(filename))[0]
    ignore_list = ["fmask", "fet", "klg", "initialclusters", "temp"]
    bad_ext = not should_use_file(base_without_ext, ignore_list)
    num_dots = len(base_without_ext.split(".")) - 1
    bad_dots = num_dots > 1
    return bad_dots or bad_ext


def check_files(ext_ignore_list, verbose=True):
    """Check if the files in the repository are ok."""
    files = get_osf_files()
    files_to_ignore = []
    for f in files:
        if f[-3:] == "eeg":
            continue
        su = should_use_file(f, ext_ignore_list)
        tf = is_temp_file(f)
        if not su or tf:
            if verbose:
                print(f"Should have ignored {f} - bad ext {not su}, temp {tf}")
            files_to_ignore.append(f)
    return files_to_ignore


def custom_function(info):
    """Use this to do anything you like in upload_folder."""
    pass
    # local = info["local"]
    # remote = info["remote"]
    # f = info["f"]
    # current_remote = info["current_remote"]
    # if local[-4:] == ".set":
    #     if not (remote[:-3] + "eeg") in info["current_remote"]:
    #         eeg_file = write_blank_eeg(local, ".temp")
    #         s = "Uploaded {} to {}".format(eeg_file, remote[:-3] + "eeg")
    #         print(s)
    #         f.write(s + "\n")
    #         upload_file(eeg_file, remote[:-3] + "eeg")
    #         send2trash(eeg_file)


def get_files_to_upload(folder, ignore_list, recursive=True):
    """Upload everything in folder to OSF."""
    file_list = get_all_files_in_dir(folder, recursive=recursive)
    remote_list = [fname[len(folder + os.sep) :] for fname in file_list]
    current_remote = read_files(os.path.join(folder, "all_files.txt"))
    print(f"Beginning upload process ignoring extensions {ignore_list} and temp files")

    locals_, remotes_ = [], []
    with open(os.path.join(folder, "uploaded_files.txt"), "w") as f:
        for local, remote in zip(file_list, remote_list):
            if remote not in current_remote:
                tf = is_temp_file(local)
                su = should_use_file(local, ignore_list)
                if su and (not tf):
                    s = f"Will upload {local} to {remote}"
                    locals_.append(local)
                    remotes_.append(remote)
                else:
                    s = f"Not uploading {local} - does not meet upload conditions"
            else:
                s = f"Skipped upload of {local} to {remote} - already in OSF"
            f.write(s + "\n")

    return locals_, remotes_


def upload_files(locals_, remotes_, verbose=True):
    for local, remote in zip(locals_, remotes_):
        info = {"local": local, "remote": remote}
        custom_function(info)
        if verbose:
            print(f"Uploading {local} to {remote}")
        upload_file(local, remote)


def clear_osf():
    """
    Remove all files from this OSF repository.

    You will need to clear directories after manually.
    """
    val = input("WARNING Will delete everything in OSF project, continue? (y/n)... ")
    if val.lower() == "y":
        files = get_osf_files()
        for f in files:
            remove_file(f)
    elif val.lower() == "n":
        return
    else:
        print("Please enter y or n")
        clear_osf()
        return


def generate_list_of_files(location):
    files = get_osf_files()
    with open(os.path.join(location, "all_files.txt"), "w") as f:
        for item in files:
            f.write(item + "\n")


def generate_list_of_excludes(location):
    files = check_files(ignore_list, verbose=False)
    with open(os.path.join(location, "extra.txt"), "w") as f:
        for item in files:
            f.write(item + "\n")


def write_locations(location, locals_, remotes_):
    with open(os.path.join(location, "output.txt"), "w") as f:
        for local, remote in zip(locals_, remotes_):
            f.write(f"{local};{remote}\n")


def read_files(location):
    with open(location, "r") as f:
        lines = [line.strip() for line in f.readlines()]
    return lines


def read_local_remotes(location):
    locals_, remotes_ = [], []
    with open(location, "r") as f:
        csv_file = csv.reader(f, delimiter=";")
        for row in csv_file:
            locals_.append(row[0])
            remotes_.append(row[1])
    return locals_, remotes_


if __name__ == "__main__":
    # NOTE please change this to be your password and change .osfcli.config
    your_osf_password = "Can't Steal this!"
    os.environ["OSF_PASSWORD"] = your_osf_password
    location = r"H:\Emanuela Rizzello data"
    ignore_list = [
        "enl",
        "SET",
        "xlsx",
        "pdf",
        "egf",
        "plx",
        "PNG",
        "log",
        "hdf5",
        "mat",
        "svg",
        "png",
        "PLX",
        "bmp",
        "JPG",
        "exe",
        "ini",
        "xml",
        "bas",
    ]

    parser = ArgumentParser()
    parser.add_argument(
        "--generate",
        "-g",
        action="store_true",
    )
    parser.add_argument(
        "--find",
        "-f",
        action="store_true",
    )
    parser.add_argument(
        "--upload",
        "-u",
        action="store_true",
    )
    parser.add_argument(
        "--verify",
        "-v",
        action="store_true",
    )
    parser.add_argument(
        "--remove",
        "-r",
        action="store_true",
    )

    parsed = parser.parse_args()
    if parsed.generate:
        generate_list_of_files(location)

    if parsed.find:
        locals_, remotes_ = get_files_to_upload(location, ignore_list)
        write_locations(location, locals_, remotes_)

    if parsed.upload:
        locals_, remotes_ = read_local_remotes(os.path.join(location, "output.txt"))
        upload_files(locals_, remotes_)

    if parsed.verify:
        generate_list_of_excludes(location)

    if parsed.remove:
        files = read_files(os.path.join(location, "extra.txt"))
        for f in files:
            print(f"removing {f}")
            remove_file(f)
