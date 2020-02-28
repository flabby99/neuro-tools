import pandas as pd
import numpy as np

import os
import re

def has_ext(filename, ext, case_sensitive_ext=False):
    """
    Check if the filename ends in the extension.
    Parameters
    ----------
    filename : str
        The name of the file.
    ext : str
        The extension, may have leading dot (e.g txt == .txt).
    case_sensitive_ext: bool, optional. Defaults to False,
        Whether to match the case of the file extension.
    Returns
    -------
    bool
        Indicates if the filename has the extension
    """
    if ext is None:
        return True
    if ext[0] != ".":
        ext = "." + ext
    if case_sensitive_ext:
        return filename[-len(ext):] == ext
    else:
        return filename[-len(ext):].lower() == ext.lower()


def get_all_files_in_dir(
        in_dir, ext=None, return_absolute=True,
        recursive=False, verbose=False, re_filter=None,
        case_sensitive_ext=False):
    """
    Get all files in the directory with the given extensions.
    Parameters
    ----------
    in_dir : str
        The absolute path to the directory
    ext : str, optional. Defaults to None.
        The extension of files to get.
    return_absolute : bool, optional. Defaults to True.
        Whether to return the absolute filename or not.
    recursive: bool, optional. Defaults to False.
        Whether to recurse through directories.
    verbose: bool, optional. Defaults to False.
        Whether to print the files found.
    re_filter: str, optional. Defaults to None
        a regular expression used to filter the results
    case_sensitive_ext: bool, optional. Defaults to False,
        Whether to match the case of the file extension
    Returns
    -------
    List
        A list of filenames with the given parameters.
    """
    if not os.path.isdir(in_dir):
        print("Non existant directory " + str(in_dir))
        return []

    def match_filter(f):
        if re_filter is None:
            return True
        search_res = re.search(re_filter, f)
        return search_res is not None

    def ok_file(root_dir, f):
        return (
            has_ext(f, ext, case_sensitive_ext=case_sensitive_ext) and
            os.path.isfile(os.path.join(root_dir, f)) and match_filter(f))

    def convert_to_path(root_dir, f):
        return os.path.join(root_dir, f) if return_absolute else f

    if verbose:
        print("Adding following files from {}".format(in_dir))

    if recursive:
        onlyfiles = []
        for root, _, filenames in os.walk(in_dir):
            start_root = root[:len(in_dir)]

            if len(root) == len(start_root):
                end_root = ""
            else:
                end_root = root[len(in_dir + os.sep):]
            for filename in filenames:
                filename = os.path.join(end_root, filename)
                if ok_file(start_root, filename):
                    to_add = convert_to_path(start_root, filename)
                    if verbose:
                        print(to_add)
                    onlyfiles.append(to_add)

    else:
        onlyfiles = [
            convert_to_path(in_dir, f) for f in sorted(os.listdir(in_dir))
            if ok_file(in_dir, f)
        ]
        if verbose:
            for f in onlyfiles:
                print(f)

    if verbose:
        print()
    return onlyfiles

def parse_excel(excel_loc):
    df = pd.read_excel(io=excel_loc, sheet_name=0)
    df = df.iloc[:, :3]
    def split_trial_info(row):
        row = row["TRIAL"]
        TT_part = row.find("TT")
        fname = row[:TT_part-1]
        tetrode = row[TT_part+2]
        SS_part = row[TT_part:].find("SS")
        unit_num = row[TT_part:][SS_part + 3:]
        return np.array([fname, tetrode, unit_num])

    split_info = np.empty(shape=(len(df), 3), dtype=object)
    for i, row in df.iterrows():
        split_info[i] = split_trial_info(row)
    df["FileName"] = split_info[:, 0]
    df["Tetrode"] = split_info[:, 1]
    df["Unit"] = split_info[:, 2]
    df.to_csv("test.csv", index=False)
    return df

def find_files(info, data_dir):
    files = get_all_files_in_dir(
        data_dir, ext="set", verbose=False, recursive=True)
    good_files = []
    tetrode_list = []
    good_txt_files = []
    good_basenames = []
    good_spike_files = []
    units = []

    def ok_file(f):
        for fname in files:
            if f == os.path.basename(fname[:-4]):
                return True, fname
            return False

    # TODO need to match the rat name

    # Find set files that match    
    for i, f in enumerate(info["FileName"]):
        test, fname = ok_file(f)
        if test:
            good_files.append(fname)
            good_basenames.append(os.path.basename(fname)[:-4])
            tetrode_list.append(info["Tetrode"][i])
            units.append(info["Unit"][i])
    txt_files = get_all_files_in_dir(
        data_dir, ext="txt", verbose=False, recursive=True)

    # Find txt files that match
    for filename in good_files:
        filename = filename[:-4]
        for fname in txt_files:
            if fname[:(len(filename) + 1)] == filename + "_":
                pos_name = fname
                good_txt_files.append(pos_name)
                break

    # Find cut files that match
    for fname, tetrode in zip(good_files, tetrode_list):
        filename = fname[:-4]
        spike_name = filename + '.' + str(tetrode)
        cut_name = filename + '_' + str(tetrode) + ".cut"
        clu_name = filename + ".clu." + str(tetrode)
        # print(filename+"\n" + spike_name+"\n" + cut_name+"\n" + clu_name+"\n")
        if not os.path.isfile(spike_name):
            continue
            # Don't consider files that have not been clustered
        if not (os.path.isfile(cut_name) or os.path.isfile(clu_name)):
            print(
                "Skipping tetrode {} - no cluster file named {} or {}".format(tetrode, cut_name, os.path.basename(clu_name)))
            continue
        good_spike_files.append(spike_name)
        
    result = {
        "set_files": good_files,
        "txt_files": good_txt_files,
        "basenames": good_basenames,
        "spike_files": good_spike_files,
        "unit": units
    }
    return result

def to_string(str_info):
    """Alternative string representation should be prettier."""
    all_str_info = []
    for i in range(len(str_info["set_files"])):
        b_str = "{}: \n\tSpk {}\n\tUnt {}\n\tPos {}".format(
            i, str_info["spike_files"][i], str_info["unit"][i], 
            str_info["txt_files"][i])
        all_str_info.append(b_str)
    return "\n".join(all_str_info)

def main(excel_loc, data_dir):
    info = parse_excel(excel_loc)
    result = find_files(info, data_dir)
    missing_files = []
    for f in info["FileName"]:
        if f not in result["basenames"]:
            missing_files.append(f)
    result_avg_len = (
        len(result["set_files"]) + 
        len(result["txt_files"]) + 
        len(result["spike_files"])) / 3
    if result_avg_len != len(info):
        raise ValueError(
            "Failed to find some files:" +
            "found set:{}, txt:{}, spike:{} of {}, missing {}".format(
                len(result["set_files"]), len(result["txt_files"]), 
                len(result["spike_files"]), len(info), missing_files)
        )
    str_v = to_string(result)
    with open("f_info.txt", "w") as f:
        f.write(str_v)
    return result

if __name__ == "__main__":
    excel_loc = r"E:\Pawel\ALL UNITS DATA.xlsx"
    data_dir = r"E:\Pawel\PTN -border UNITS Literature\UNITS Recordings for Paper\Spatial rel"
    main(excel_loc, data_dir)
