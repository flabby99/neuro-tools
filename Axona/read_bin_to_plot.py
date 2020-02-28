import numpy as np
import matplotlib.pyplot as plt
import math

def read_shuff_bin(location, channels=[0]):
    data = np.memmap(location, dtype="int16", offset=16, mode="r")
    num_chans = 64
    one_channel_len = int(data.size / num_chans)
    us = (0.000001)
    time = 11.4632
    back_us = 200
    forward_us = 800
    s_back = int(math.floor(back_us * (us) * 48000))
    s_forward = int(math.ceil(forward_us * (us) * 48000))
    print(s_forward + s_back)
    s_mid = int(time * 48000)
    print(s_mid-s_back, s_mid+s_forward, s_mid)
    print(time - back_us*us, time + forward_us*us)
    ts = np.arange(time - back_us*us, time + forward_us*us, step=(1/48000))
    ts = ts[:s_forward+s_back]
    out_data = np.zeros(shape=(len(channels), len(ts)))
    for i, channel in enumerate(channels):
        start_idx = (channel * one_channel_len) + (s_mid - s_back)
        end_idx = (channel * one_channel_len) + (s_mid + s_forward)
        print(start_idx, end_idx)
        one_channel = data[start_idx:end_idx]
        out_data[i] = one_channel
    fig, axes = plt.subplots(3)
    for row, ax in zip(out_data, axes):
        ax.plot(ts, row)
    plt.show()

if __name__ == "__main__":
    location = r"C:\Users\smartin5\Recordings\Raw\2min\CS1_18_02_open_2_bin_shuff.bin"
    location = r"G:\Ham\A10_CAR-SA2\CAR-SA2_20200109_PreBox\CAR-SA2_2020-01-09_PreBox_shuff.bin"
    channels = [60, 61, 62]
    read_shuff_bin(location, channels)
