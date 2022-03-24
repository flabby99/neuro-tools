import numpy as np


from simuran.plot.base_plot import setup_ax


def vis_lfp(
    signals, sample_rate, names=None, in_range=None, split_len=100, save=False, **kwargs
):
    """
    Visualise LFP signals.

    Parameters
    ----------
    signals : Iterable of lfp signals
        The lfp signals to visualize. Input assumed to have shape N chans * N samples
    sample_rate : float
        The sampling rate of the LFP signals.
    names : Iterable of strings, optional
        The names of the signals. Defaults to their index in signals.
    in_range : tuple of int
        The range in seconds to plot over. Defaults to the whole range.
    split_len : float
        The length of the LFP to visualize in a single plot.
    save : bool, optional
        Whether to save the plots or show them.
    **kwargs : keyword arguments
        These can be used to override plot appearances.

    Returns
    -------
    None

    """
    # Change optional parameters
    if names is None:
        names = ["Channel" + str(i) for i in range(len(signals))]

    if in_range is None:
        in_range = (0, max([int(len(lfp) // sample_rate) for lfp in signals]))

    y_axis_max = max([max(lfp) for lfp in signals])
    y_axis_min = min([min(lfp) for lfp in signals])

    seg_splits = np.arange(in_range[0], in_range[1], split_len)

    convert = recording.signals[0].get_sampling_rate()
    c_start, c_end = math.floor(a * convert), math.floor(b * convert)
    lfp_sample = lfp[c_start:c_end]
    x_pos = recording.signals[i].get_timestamps()[c_start:c_end]
    axes[i].plot(x_pos, lfp_sample, color="k")
    axes[i].text(
        0.03,
        1.02,
        "Channel " + str(i + 1),
        transform=axes[i].transAxes,
        color="k",
        fontsize=15,
    )
    axes[i].set_ylim(y_axis_min, y_axis_max)
    axes[i].tick_params(labelsize=12)
    axes[i].set_xlim(a, a + max_split_len)

    default = {
        "title": "LFP Difference",
        "xlabel": "LFP Channels",
        "ylabel": "LFP Channels",
        "xticks": np.arange(0.5, ch + 0.5),
        "xticklabels": chans,
        "yticks": np.arange(0.5, ch + 0.5),
        "yticklabels": chans,
        "labelsize": 6,
    }

    fig, ax = plt.subplots()
    reshaped = np.reshape(matrix_data, newshape=[ch, ch])
    sns.heatmap(reshaped, ax=ax)
    setup_ax(ax, default, **kwargs)
