"""
You should install osfclient from GITHUB to use this script.
The github version of osfclient is better than the PYPI version.
"""

import subprocess
import os

from send2trash import send2trash

from utils import get_all_files_in_dir, log_exception, write_blank_eeg


def run_osf(args):
    """Run osf args from command line."""
    subprocess.run(["osf", *args])


def run_capture_osf(args):
    """Run osf args from command line but capture the output in python."""
    result = subprocess.run(["osf", *args], stdout=subprocess.PIPE)
    return result.stdout.decode('utf-8')


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
        line[len("osfstorage\\"):].replace("/", "\\")
        for line in result.splitlines()]


def list_extensions(folder):
    file_list = get_all_files_in_dir(folder, recursive=True)
    return get_extensions(file_list)


def get_extensions(l):
    ext_list = []
    for item in l:
        ext = os.path.splitext(item)[1][1:]
        if not ext in ext_list:
            ext_list.append(ext)
    return ext_list


def list_osf_extensions():
    l = get_osf_files()
    return get_extensions(l)


def should_use_file(filename, ext_ignore_list):
    """Returns True if filename extension not in ext_ignore_list."""
    ext = os.path.splitext(filename)[1][1:]
    for ignore in ext_ignore_list:
        if ext.startswith(ignore):
            return False
    return True


def is_temp_file(filename):
    """Temp file is file is like A.B.C.D."""
    base_without_ext = os.path.splitext(os.path.basename(filename))[0]
    ignore_list = ["fmask", "fet", "klg", "initialclusters", "temp"]
    bad_ext = not should_use_file(base_without_ext, ignore_list)
    num_dots = len(base_without_ext.split(".")) - 1
    bad_dots = (num_dots > 1)
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
        if (not su) or tf:
            if verbose:
                print("Should have ignored {} - bad ext {}, temp {}".format(
                    f, not su, tf))
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


def upload_folder(folder, ignore_list, recursive=True):
    """Upload everything in folder to OSF."""
    file_list = get_all_files_in_dir(folder, recursive=recursive)
    remote_list = [fname[len(folder + os.sep):] for fname in file_list]
    current_remote = get_osf_files()
    print("Beginning upload process ignoring extensions {} and temp files".format(
        ignore_list))
    with open(os.path.join(folder, "uploaded_files.txt"), "w") as f:
        for i, (local, remote) in enumerate(zip(file_list, remote_list)):
            su = should_use_file(local, ignore_list)
            tf = is_temp_file(local)
            if su and (not tf):
                if not remote in current_remote:
                    info = {"local": local, "remote": remote,
                            "f": f, "current_remote": current_remote}
                    custom_function(info)
                    upload_file(local, remote)
                    s = "Uploaded {} to {}".format(local, remote)
                else:
                    s = "Skipped upload of {} to {} - already in OSF".format(
                        local, remote)
            else:
                s = "Not uploading {} - does not meet upload conditions".format(
                    local)
            print(s)
            f.write(s + "\n")


def clear_osf():
    """
    Remove all files from this OSF repository. 

    You will need to clear directories after manually.
    """
    val = input(
        "WARNING Will delete everything in OSF project, continue? (y/n)... ")
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


if __name__ == "__main__":
    # NOTE please change this to be your password and change .osfcli.config
    your_osf_password = "Can't Steal this!"
    os.environ["OSF_PASSWORD"] = your_osf_password
    ignore_list = []
    location = r"D:\CopyPawel"
    upload_folder(location, ignore_list)
    files = get_osf_files()
    with open(os.path.join(location, "all_files.txt"), "w") as f:
        for item in files:
            f.write(item + "\n")
    # list_files()
    # upload_folder(location, ignore_list)
    # location = r"C:\Users\smartin5\Recordings\Matheus"
    # print(list_extensions(location))
    # print(list_osf_extensions())
    # for f in check_files(ignore_list, verbose=False):
    #     print("removing {}".format(f))
    #     remove_file(f)
    # clear_osf()
