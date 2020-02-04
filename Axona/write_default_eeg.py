import os

default_file_lines = [
    "trial_date",
    "trial_time",
    "experimenter",
    "comments",
    "duration 0",
    "sw_version 1.2.2.14",
    "num_chans 1",
    "sample_rate 250.0 hz",
    "EEG_samples_per_position 5",
    "bytes_per_sample 1",
    "num_EEG_samples 0",
    "data_start",
    "data_end",
]


def write_blank_eeg(set_fname, append="blank"):
    out_fname = set_fname[:-3] + "eeg" + append
    if os.path.isfile(out_fname):
        val = input(
            "Warning! will overwrite {}, enter y to continue: ".format(out_fname))
        if val.lower() != "y":
            return False
    with open(out_fname, "w") as f:
        changed = [x + "\n" for x in default_file_lines[:-1]]
        changed.append(default_file_lines[-1])
        f.writelines(changed)
    return out_fname


def main(set_fname, append="blank"):
    return write_blank_eeg(set_fname, append)


if __name__ == "__main__":
    set_fname = r"C:\Users\smartin5\Recordings\Matheus\ATNx_CA1\Rat1\05_04\050419B_open_arena_15min_LCA2.set"
    append = "blank"
    name = main(set_fname, append)
    print(name)
