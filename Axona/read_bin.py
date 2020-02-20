import numpy as np


def read_shuff_bin(location, channel=0):
    data = np.memmap(location, dtype="int16", offset=16, mode="r")
    num_chans = 64
    one_channel_len = int(data.size / num_chans)
    start_idx = channel * one_channel_len
    end_idx = start_idx + one_channel_len
    one_channel = data[start_idx:end_idx]
    print(one_channel[:16])
    with open(location[:-4] + "_" + str(channel + 1) + ".txt", "w") as f:
        for i in range(one_channel_len):
            if (i % 16 == 0) and i != 0:
                f.write("\n")
            if (i != one_channel_len - 1):
                f.write("{}, ".format(one_channel[i]))
            else:
                f.write("{}\n".format(one_channel[i]))


if __name__ == "__main__":
    location = r"C:\Users\smartin5\Recordings\Raw\2min\CS1_18_02_open_2_bin_shuff.bin"
    channel = 3
    read_shuff_bin(location, channel)
