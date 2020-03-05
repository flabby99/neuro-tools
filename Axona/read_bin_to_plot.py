import numpy as np
import matplotlib.pyplot as plt
import math
import os


def int16toint8(value):
    """Converts int16 data to int8"""
    value = np.divide(value, 256).astype(int)
    value[np.where(value > 127)] = 127
    value[np.where(value < -128)] = -128

    return value

def read_shuff_bin(location, channels=[0], times=[1], fname="fig.png"):
    bytes_size = os.path.getsize(location)
    one_channel_len = int((bytes_size - 16) / 128)
    num_chans = 64
    data = np.memmap(
        location, dtype="int16", offset=0, mode="r", 
        shape=(num_chans, one_channel_len)[::-1]).transpose()
    ts = np.arange(0, 1, 0.02)
    out_data = np.zeros(
        shape=(len(channels), len(times), len(ts)), dtype=np.int16)
    s_back = 10
    s_forward = 40

    for i, channel in enumerate(channels):
        for j, time in enumerate(times):
            s_mid = int(time * 48000)
            start_idx = s_mid - s_back
            end_idx = start_idx + len(ts)
            one_channel = data[channel, start_idx:end_idx]
            out_data[i][j] = one_channel
    fig, axes = plt.subplots(len(channels), figsize=(5, 10))
    for row, ax in zip(out_data, axes):
        # row = np.average(row, axis=0)
        if len(times) == 1:
            ax.plot(ts, row[0], c="k")
        else:
            for r2 in row:
                ax.plot(ts, r2, c="k")
    max_y = np.max(out_data) * 1.1
    min_y = np.min(out_data) * 1.1
    for ax in axes:
        ax.set_ylim(-32768, 32767)
    plt.savefig(fname, dpi=200)

if __name__ == "__main__":
    location = r"C:\Users\smartin5\Recordings\Raw\2min\CS1_18_02_open_2_bin_shuff.bin"
    location = r"G:\Ham\A10_CAR-SA2\CAR-SA2_20200109_PreBox\CAR-SA2_2020-01-09_PreBox_shuff_t.bin"
    # location = r"F:\CAR-SA4_20200301_PreBox\CAR-SA4_2020-03-01_PreBox.bin"
    tetrode = 12
    channels = [4 * (tetrode-1) + i for i in range(4)]
    times = []
    n_times = 10
    # spike_names = "CAR-SA4_2020-03-01_PreBox_12_c1_times.txt"
    # with open(os.path.join(os.path.dirname(location), spike_names), "r") as f:
    #     for i in range(n_times):
    #         line = f.readline()
    #         time = float(line[:-1].strip())
    #         times.append(time)
    # This is a temp
    from neurochat.nc_spike import NSpike
    import neurochat.nc_plot as nc_plot
    ns = NSpike()
    ns.load(
        os.path.join(
            os.path.dirname(location), 
            "CAR-SA2_2020-01-09_PreBox.12"), "Axona")
    ns.set_unit_no(unit_no=1)
    times = []
    for i in range(n_times):
        t = ns.get_unit_stamp()[i]
        times.append(t)
    nc_plot.wave_property(ns.wave_property())
    plt.savefig("wave.png")
    read_shuff_bin(location, channels, times, fname="test12_1_ac_new_t.png")
