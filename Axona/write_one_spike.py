import numpy as np
import os
import struct
import matplotlib.pyplot as plt


def int16toint8(value):
    """Converts int16 data to int8"""
    value = np.divide(value, 256).astype(int)
    value[np.where(value > 127)] = 127
    value[np.where(value < -128)] = -128

    return value


def read_shuff_bin(location, tetrode=0):
    data = np.memmap(location, dtype="int16", offset=16, mode="r")
    num_chans = 64
    one_channel_len = int(data.size / num_chans)
    out_data = np.zeros(shape=(4, one_channel_len))
    for i in range(4):
        channel = (tetrode - 1) * 4 + i
        start_idx = channel * one_channel_len
        end_idx = start_idx + one_channel_len
        out_data[i] = data[start_idx:end_idx]
    return out_data


def get_one_spike(data, time, plot=True):
    pre_spike_samps = 10
    post_spike_samps = 40
    print("Saving a spike at {}s".format(time))
    sample_idx = int(time * 48000)
    print("Recalculated spike time is:")
    print((data.size / (4 * 48000)) * (sample_idx / (data.size / 4)))
    s_data = data[:, sample_idx -
                  pre_spike_samps:sample_idx + post_spike_samps]
    if plot:
        fig, axes = plt.subplots(4, figsize=(5, 10))
        ts = np.arange(0, 1, 0.02)
        for row, ax in zip(s_data, axes):
            # row = np.average(row, axis=0)
            ax.plot(ts, row, c="k")
        max_y = np.max(s_data) * 1.1
        min_y = np.min(s_data) * 1.1
        for ax in axes:
            ax.set_ylim(min_y, max_y)
        plt.savefig("raw_tet.png", dpi=200)
    spike = {time: np.rint(int16toint8(s_data))}
    return spike


def get_set_header(set_filename):
    with open(set_filename, 'r+') as f:
        header = ''
        for line in f:
            header += line
            if 'sw_version' in line:
                break
    return header


def write_tetrode(filepath, data, Fs):

    session_path, session_filename = os.path.split(filepath)
    tint_basename = os.path.splitext(session_filename)[0]
    set_filename = os.path.join(session_path, '%s.set' % tint_basename)

    n = len(data)

    header = get_set_header(set_filename)

    with open(filepath, 'w') as f:
        num_chans = 'num_chans 4'
        timebase_head = '\ntimebase %d hz' % (96000)
        bp_timestamp = '\nbytes_per_timestamp %d' % (4)
        # samps_per_spike = '\nsamples_per_spike %d' % (int(Fs*1e-3))
        samps_per_spike = '\nsamples_per_spike %d' % (50)
        sample_rate = '\nsample_rate %d hz' % (Fs)
        b_p_sample = '\nbytes_per_sample %d' % (1)
        # b_p_sample = '\nbytes_per_sample %d' % (4)
        spike_form = '\nspike_format t,ch1,t,ch2,t,ch3,t,ch4'
        num_spikes = '\nnum_spikes %d' % (n)
        start = '\ndata_start'

        write_order = [header, num_chans, timebase_head,
                       bp_timestamp,
                       samps_per_spike, sample_rate, b_p_sample, spike_form, num_spikes, start]

        f.writelines(write_order)

    # rearranging the data to have a flat array of t1, waveform1, t2, waveform2, t3, waveform3, etc....
    spike_times = np.asarray(sorted(data.keys())) * 96000

    # the spike times are repeated for each channel so lets tile this
    spike_times = np.tile(spike_times, (4, 1))
    spike_times = spike_times.flatten(order='F')
    print(spike_times)

    spike_values = np.asarray([value for (key, value) in sorted(data.items())])

    # create the 4nx50 channel data matrix
    spike_values = spike_values.reshape((n * 4, 50))

    # make the first column the time values
    spike_array = np.hstack(
        (spike_times.reshape(len(spike_times), 1), spike_values))
    print(spike_array)

    data = None
    spike_times = None
    spike_values = None

    spike_n = spike_array.shape[0]

    t_packed = struct.pack('>%di' % spike_n, *spike_array[:, 0].astype(int))
    # removing time data from this matrix to save memory
    spike_array = spike_array[:, 1:]

    spike_data_pack = struct.pack(
        '<%db' % (spike_n * 50), *spike_array.astype(int).flatten())

    spike_array = None

    # now we need to combine the lists by alternating

    comb_list = [None] * (2 * spike_n)
    comb_list[::2] = [t_packed[i:i + 4]
                      for i in range(0, len(t_packed), 4)]  # breaks up t_packed into a list,
    # each timestamp is one 4 byte integer
    comb_list[1::2] = [spike_data_pack[i:i + 50]
                       for i in range(0, len(spike_data_pack), 50)]  # breaks up spike_data_
    # pack and puts it into a list, each spike is 50 one byte integers

    t_packed = None
    spike_data_pack = None

    write_order = []
    print("Writing tetrode data to {}".format(filepath))
    with open(filepath, 'rb+') as f:

        write_order.extend(comb_list)
        write_order.append(bytes('\r\ndata_end\r\n', 'utf-8'))

        f.seek(0, 2)
        f.writelines(write_order)


def plot_one_spike(spike_data, fname="tet.png"):
    spike_data = list(spike_data.values())[0]
    fig, axes = plt.subplots(4, figsize=(5, 10))
    ts = np.arange(0, 1, 0.02)
    for row, ax in zip(spike_data, axes):
        # row = np.average(row, axis=0)
        ax.plot(ts, row, c="k")
    max_y = np.max(spike_data) * 1.1
    min_y = np.min(spike_data) * 1.1
    for ax in axes:
        ax.set_ylim(-126, 125)
    plt.savefig(fname, dpi=200)


def main(location, tetrode=0, time=1):
    data = read_shuff_bin(location, tetrode)
    spike_data = get_one_spike(data, time)
    out_loc = location[:-4] + "." + str(tetrode)
    write_tetrode(out_loc, spike_data, 48000)
    plot_one_spike(spike_data)


if __name__ == "__main__":
    location = r"F:\CAR-SA4_20200301_PreBox\CAR-SA4_2020-03-01_PreBox.bin"
    tetrode = 1
    time = 7.2
    main(location, tetrode=tetrode, time=time)
