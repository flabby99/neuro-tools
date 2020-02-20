import numpy as np


def read_shuff_bin(location):
    data = np.memmap(location, dtype="int16", offset=16, mode="r")
    num_chans = 64
    one_channel_len = int(data.size / num_chans)
    one_channel = data[:one_channel_len]
    print(one_channel[:16])
    with open(location[:-4] + "_1.txt", "w") as f:
        for i in range(one_channel_len):
            if (i % 16 == 0) and i != 0:
                f.write("\n")
            f.write("{}, ".format(one_channel[i]))


if __name__ == "__main__":
    location = r"C:\Users\smartin5\Recordings\Raw\2min\CS1_18_02_open_2_bin_shuff.bin"
    read_shuff_bin(location)
