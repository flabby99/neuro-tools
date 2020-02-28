import numpy as np
import matplotlib.pyplot as plt
import math
import os

def read_shuff_bin(location, channels=[0], times=[1]):
    data = np.memmap(location, dtype="int16", offset=16, mode="r")
    num_chans = 64
    one_channel_len = int(data.size / num_chans)
    ts = np.arange(0, 0.001000001, step=(1/48000))
    out_data = np.zeros(shape=(len(channels), len(times), len(ts)))
    us = (0.000001)
    back_us = 200
    forward_us = 800
    s_back = int(math.floor(back_us * (us) * 48000))
    s_forward = int(math.ceil(forward_us * (us) * 48000))

    for i, channel in enumerate(channels):
        for j, time in enumerate(times):
            s_mid = int(time * 48000)
            start_idx = (channel * one_channel_len) + (s_mid - s_back)
            end_idx = start_idx + len(ts)
            one_channel = data[start_idx:end_idx]
            out_data[i][j] = one_channel
    fig, axes = plt.subplots(3)
    for row, ax in zip(out_data, axes):
        # row = np.average(row, axis=0)
        for r2 in row:
            ax.plot(ts, r2, c="k")
    plt.show()

if __name__ == "__main__":
    location = r"C:\Users\smartin5\Recordings\Raw\2min\CS1_18_02_open_2_bin_shuff.bin"
    location = r"G:\Ham\A10_CAR-SA2\CAR-SA2_20200109_PreBox\CAR-SA2_2020-01-09_PreBox_shuff.bin"
    spike_names = "CAR-SA2_2020-01-09_PreBox_12_c5_times.txt"
    channels = [60, 61, 62]
    times = []
    n_times = 9
    with open(os.path.join(os.path.dirname(location), spike_names), "r") as f:
        for i in range(n_times):
            line = f.readline()
            time = float(line[:-1].strip())
            times.append(time)
    print(times)
    read_shuff_bin(location, channels, times)
