import difflib
import os

in_dir = r"C:\Users\smartin5\Recordings\Raw\2min"

name1 = "CS1_18_02_open_2_bin_shuff_1.txt"
name2 = "1.txt"
# name1 = "1.txt"
# name2 = "1_cpp.txt"
in1 = os.path.join(in_dir, name1)
in2 = os.path.join(in_dir, name2)
ou2 = os.path.join(in_dir, "diff_" + name1[:-4] + "--" + name2[:-4] + ".txt")

in1 = open(in1, "r")
in2 = open(in2, "r")
with open(ou2, "w") as f:
    for line in difflib.unified_diff(
            in1.readlines(), in2.readlines(),
            fromfile='file1', tofile='file2', lineterm=''):
        f.write(line + "\n")
