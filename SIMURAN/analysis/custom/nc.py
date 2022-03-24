import os
from collections import OrderedDict as oDict
from copy import deepcopy

import neurochat.nc_plot as ncplot
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import seaborn as sns

from neurochat.nc_utils import histogram, histogram2d, smooth_2d, find
from neurochat.nc_spatial import NSpatial
from neurochat.nc_plot import wave_property, largest_waveform


def frate(recording, tetrode_num, unit_num):
    try:
        units, _ = recording.units.group_by_property("group", tetrode_num)
        unit = units[0]
        unit.load()
        spike = unit.underlying
        spike.set_unit_no(unit_num)
        return spike.get_unit_spikes_count() / spike.get_duration()
    except:
        return -1


def frate_file(recording):
    try:
        spike = get_nc_unit(recording)
        return spike.get_unit_spikes_count() / spike.get_duration()
    except:
        return -1


def spike_width_file(recording):
    output = {}
    output["tetrode"] = 0
    output["unit"] = -1
    try:
        spike = get_nc_unit(recording)
        setup = recording.get_set_units_as_dict()
        for tetrode, unit in setup.items():
            if unit is not None:
                output["tetrode"] = tetrode
                output["unit"] = unit[0]
        spike.wave_property()
        wave_prop = spike.get_results()
        output["width_mean"] = wave_prop["Mean width"]
        output["width_std"] = wave_prop["Std width"]
        output["firing_rate"] = spike.get_unit_spikes_count() / spike.get_duration()
        return output

    except:
        output["width_mean"] = -1
        output["width_std"] = -1
        output["firing_rate"] = -1
        return output


def place_field(recording, grid_fig, tetrode_num, unit_num):
    try:
        units, _ = recording.units.group_by_property("group", tetrode_num)
        unit = units[0]
        unit.load()
        spike = unit.underlying
        spike.set_unit_no(unit_num)
        spatial = recording.spatial
        spatial.load()
        place_data = spatial.underlying.place(spike.get_unit_stamp())
        ncplot.loc_rate(place_data, ax=grid_fig.get_next())
        plt.close()
        ncplot.loc_spike(place_data, ax=grid_fig.get_next())
        plt.close()
        wave_data = spike.wave_property()
        ncplot.largest_waveform(wave_data, ax=grid_fig.get_next())
        plt.close()
    except:
        grid_fig.get_next()
        grid_fig.get_next()
        grid_fig.get_next()


def place_field_file(recording, grid_fig):
    try:
        available_units = recording.get_set_units()
        unit_num = -1
        for i, a_unit in enumerate(available_units):
            if len(a_unit) != 0:
                if unit_num != -1:
                    raise ValueError(
                        "There are two set units for {}, {}".format(recording, a_unit)
                    )
                unit = recording.units[i]
                unit_num = a_unit[0]
        if unit_num == -1:
            print("Warning: no set units for {}".format(recording))
            return
        unit.load()
        spike = unit.underlying
        spike.set_unit_no(unit_num)
        spatial = recording.spatial
        spatial.load()
    except:
        grid_fig.get_next()
        grid_fig.get_next()
        grid_fig.get_next()
        return
    place_data = spatial.underlying.place(spike.get_unit_stamp())
    ncplot.loc_rate(place_data, ax=grid_fig.get_next())
    plt.close()
    ncplot.loc_spike(place_data, ax=grid_fig.get_next())
    plt.close()
    hd_data = spatial.underlying.hd_rate(spike.get_unit_stamp())
    ncplot.hd_rate(hd_data, ax=grid_fig.get_next(circular=True), title=None)
    plt.close()


def count_cells(recording):
    output = {}
    for val in [1, 2, 3, 4, 9, 10, 11, 12]:
        output[str(val)] = 0

    try:
        for unit in recording.units:
            spike = unit.underlying
            if spike is None:
                continue
            num = len(spike.get_unit_list())
            output[str(unit.group)] = num
        return output

    except Exception as e:
        print("Error on {} was {}".format(recording, e))
        return output


def plot_isi(isi_data, pdf_file, name, **kwargs):
    title = name
    xlabel = kwargs.get("xlabel1", "ISI (ms)")
    ylabel = kwargs.get("ylabel1", "Spike count")
    burst_ms = kwargs.get("burst_ms", 5)
    s_color = kwargs.get("should_color", False)
    raster = kwargs.get("raster", True)

    if s_color:
        color = "darkblue"
        edgecolor = "darkblue"
    else:
        color = "k"
        edgecolor = "k"
    fig, ax = plt.subplots()
    width = np.mean(np.diff(isi_data["isiBins"]))
    ax.bar(
        isi_data["isiBins"],
        isi_data["isiHist"],
        color=color,
        edgecolor=edgecolor,
        rasterized=raster,
        align="edge",
        width=width,
        linewidth=0,
    )
    ax.set_title(os.path.splitext(title)[0].split("--")[-1])
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    pdf_file.savefig(fig, dpi=400)
    plt.close(fig)


def tetrode_sd(nc_unit, wave_prop, out_name, pdf_file):
    max_channel = wave_prop["Max channel"]

    waveforms = nc_unit.get_unit_waves()

    _result = oDict()

    def argpeak(data):
        data = np.array(data)
        peak_loc = [j for j in range(7, len(data)) if data[j] <= 0 and data[j - 1] > 0]
        return peak_loc[0] if peak_loc else 0

    def argtrough1(data, peak_loc):
        data = data.tolist()
        trough_loc = [
            peak_loc - j
            for j in range(peak_loc - 2)
            if data[peak_loc - j] >= 0 and data[peak_loc - j - 1] <= 0
        ]
        return trough_loc[0] if trough_loc else 0

    def wave_width(wave, peak, thresh=0.25):
        p_loc, p_val = peak
        Len = wave.size
        if p_loc:
            w_start = find(wave[:p_loc] <= thresh * p_val, 1, "last")
            w_start = w_start[0] if w_start.size else 0
            w_end = find(wave[p_loc:] <= thresh * p_val, 1, "first")
            w_end = p_loc + w_end[0] if w_end.size else Len
        else:
            w_start = 1
            w_end = Len

        return w_end - w_start

    num_spikes = nc_unit.get_unit_spikes_count()
    _waves = nc_unit.get_unit_waves()
    samples_per_spike = nc_unit.get_samples_per_spike()
    tot_chans = nc_unit.get_total_channels()
    meanWave = np.empty([samples_per_spike, tot_chans])
    stdWave = np.empty([samples_per_spike, tot_chans])

    width = np.empty([num_spikes, tot_chans])
    amp = np.empty([num_spikes, tot_chans])
    height = np.empty([num_spikes, tot_chans])
    for i, (chan, wave) in enumerate(_waves.items()):
        if wave.shape[0] == 1:
            slope = np.array([(np.gradient(wave[0]))])
        else:
            slope = np.gradient(wave, axis=1)
        meanWave[:, i] = np.mean(wave, 0)
        stdWave[:, i] = np.std(wave, 0)
        max_val = wave.max(1)

        peak_val, trough1_val = 0, 0
        if max_val.max() > 0:
            peak_loc = [argpeak(slope[I, :]) for I in range(num_spikes)]
            peak_val = [wave[I, peak_loc[I]] for I in range(num_spikes)]
            trough1_loc = [
                argtrough1(slope[I, :], peak_loc[I]) for I in range(num_spikes)
            ]
            trough1_val = [wave[I, trough1_loc[I]] for I in range(num_spikes)]
            peak_loc = np.array(peak_loc)
            peak_val = np.array(peak_val)
            trough1_loc = np.array(trough1_loc)
            trough1_val = np.array(trough1_val)
            width[:, i] = np.array(
                [
                    wave_width(wave[I, :], (peak_loc[I], peak_val[I]), 0.25)
                    for I in range(num_spikes)
                ]
            )

        amp[:, i] = peak_val - trough1_val
        height[:, i] = peak_val - wave.min(1)
    max_chan = amp.mean(0).argmax()
    # width = width[:, max_chan] * 10**6 / nc_unit.get_sampling_rate()
    # amp = amp[:, max_chan]
    # height = height[:, max_chan]

    amp_per_chan = np.abs(amp.mean(axis=0))
    max_amp = amp_per_chan[max_chan]
    diffs = np.abs(np.abs(amp_per_chan) - max_amp)
    diffs[max_chan] = 1000000000
    diff = diffs.min() / max_amp
    # average_amp = amp_per_chan.mean()
    # diff_from_avg = np.abs(amp_per_chan - average_amp)
    # diff = diff_from_avg / average_amp
    # diff = np.sum(np.abs(diff))

    fig, ax = plt.subplots()
    fig.suptitle(os.path.splitext(out_name)[0].split("--")[-1])
    ax.set_title("Difference {:.2f}".format(diff))
    # fig = wave_property(wave_prop)
    mw = wave_prop["Mean wave"]
    sw = wave_prop["Std wave"]
    max_v = np.abs(mw[:, max_chan]).max()
    x = [1000 * float(i) / nc_unit.get_sampling_rate() for i in range(50)]
    for i in range(4):
        ax.plot(x, (max_v * i * 2.1) + mw[:, i], color="black", linewidth=2.0)
        ax.plot(
            x,
            (max_v * i * 2.1) + mw[:, i] + sw[:, i],
            color="green",
            linestyle="dashed",
        )
        ax.plot(
            x,
            (max_v * i * 2.1) + mw[:, i] - sw[:, i],
            color="green",
            linestyle="dashed",
        )

    # os.makedirs("figs", exist_ok=True)
    # save_loc = os.path.join("figs", out_name)
    pdf_file.savefig(fig, dpi=400)
    plt.close(fig)

    # fig = largest_waveform(wave_prop)
    # fig.savefig("wave_biggest.png")

    return diff


def stat_per_cell(recording):
    output = {}
    all_analyse = deepcopy(recording.get_set_units())
    # os.makedirs("pdfs", exist_ok=True)
    # i = 1
    # while os.path.exists(os.path.join("pdfs", f"waveforms_{i}.pdf")):
    #     i += 1
    # pdf_file = PdfPages(os.path.join("pdfs", f"waveforms_{i}.pdf"))
    for unit, to_analyse in zip(recording.units, all_analyse):
        loaded = False
        if to_analyse is None:
            continue
        if len(to_analyse) == 0:
            continue
        if not loaded:
            unit.load()
            unit.units_to_use = to_analyse
        out_str_start = str(unit.group)
        if unit.underlying is None:
            for cell in to_analyse:
                output[out_str_start + "_" + str(cell)] = [
                    np.nan,
                    np.nan,
                    np.nan,
                    np.nan,
                    np.nan,
                ]
        else:
            for cell in to_analyse:
                if cell in unit.underlying.get_unit_list():
                    unit.underlying.set_unit_no(cell)
                    # print(unit.source_file, cell)
                    out_name = (
                        unit.source_file["Spike"][29:]
                        .replace("\\", "--")
                        .replace(".", "_tet-")
                        + "_cell-"
                        + str(cell)
                        + ".png"
                    )
                    wave_prop = unit.underlying.wave_property()
                    isi_data = unit.underlying.isi()
                    results = unit.underlying.get_results()
                    output[out_str_start + "_" + str(cell)] = [
                        results["Mean width"],
                        results["Mean Spiking Freq"],
                        results["Median ISI"],
                        results["Std ISI"],
                        results["CV ISI"],
                    ]
                    # plot_isi(isi_data, pdf_file, out_name)
                    unit.underlying.reset_results()
                else:
                    output[out_str_start + "_" + str(cell)] = [
                        np.nan,
                        np.nan,
                        np.nan,
                        np.nan,
                        np.nan,
                    ]
    # pdf_file.close()
    return output


def bin_downsample(
    self, ftimes, other_spatial, other_ftimes, final_bins, sample_bin_amt=[30, 30]
):
    bin_size = sample_bin_amt
    set_array = np.zeros(shape=(len(self._pos_x), 4), dtype=np.float64)
    set_array[:, 0] = self._pos_x
    set_array[:, 1] = self._pos_y
    spikes_in_bins = histogram(ftimes, bins=self.get_time())[0]
    set_array[:, 2] = spikes_in_bins
    set_array[:, 3] = self._time

    pos_hist = np.histogram2d(set_array[:, 0], set_array[:, 1], bin_size)
    pos_locs_x = np.searchsorted(pos_hist[1][1:], set_array[:, 0], side="left")
    pos_locs_y = np.searchsorted(pos_hist[2][1:], set_array[:, 1], side="left")

    set_array1 = np.zeros(shape=(len(other_spatial._pos_x), 2))
    set_array1[:, 0] = other_spatial._pos_x
    set_array1[:, 1] = other_spatial._pos_y
    # spikes_in_bins = histogram(other_ftimes, bins=other_spatial.get_time())[0]
    # set_array1[:, 2] = spikes_in_bins
    # set_array1[:, 3] = other_spatial._time
    pos_hist1 = np.histogram2d(set_array1[:, 0], set_array1[:, 1], bin_size)
    # pos_locs_x1 = np.searchsorted(
    #     pos_hist1[1][1:], set_array1[:, 0], side='left')
    # pos_locs_y1 = np.searchsorted(
    #     pos_hist1[2][1:], set_array1[:, 1], side='left')

    new_set = np.zeros(shape=(int(np.sum(pos_hist1[0])), 4))
    count = 0

    for i in range(pos_hist[0].shape[0]):
        for j in range(pos_hist[0].shape[1]):
            amount1 = int(pos_hist1[0][i, j])
            amount2 = int(pos_hist[0][i, j])
            amount = min(amount1, amount2)
            subset = np.nonzero(np.logical_and(pos_locs_x == i, pos_locs_y == j))[0]
            if len(subset) > amount2:
                subset = subset[:amount2]
            elif len(subset) == 0:
                continue
            new_sample_idxs = np.random.choice(subset, amount)
            new_samples = set_array[new_sample_idxs]
            new_set[count : count + amount] = new_samples
            count += amount
    # print(np.histogram2d(
    #     new_set[:, 0], new_set[:, 1], [pos_hist[1], pos_hist[2]])[0])
    spike_count = np.histogram2d(
        new_set[:, 1],
        new_set[:, 0],
        [final_bins[0], final_bins[1]],
        weights=new_set[:, 2],
    )[0]
    return new_set, spike_count


def reverse_downsample(self, ftimes, other_spatial, other_ftimes, **kwargs):
    return other_spatial.downsample_place(other_ftimes, self, ftimes, **kwargs)


def downsample_place(self, ftimes, other_spatial, other_ftimes, **kwargs):
    """
    Calculates the two-dimensional firing rate of the unit with respect to
    the location of the animal in the environment. This is called Firing map.

    Specificity indices are measured to assess the quality of location-specific firing of the unit.

    This method also plot the events of spike occurring superimposed on the
    trace of the animal in the arena, commonly known as Spike Plot.

    Parameters
    ----------
    ftimes : ndarray
        Timestamps of the spiking activity of a unit
    **kwargs
        Keyword arguments

    Returns
    -------
    dict
        Graphical data of the analysis
    """

    _results = oDict()
    graph_data = {}
    update = kwargs.get("update", True)
    pixel = kwargs.get("pixel", 3)
    chop_bound = kwargs.get("chop_bound", 5)
    filttype, filtsize = kwargs.get("filter", ["b", 5])
    lim = kwargs.get("range", [0, self.get_duration()])
    brAdjust = kwargs.get("brAdjust", True)
    thresh = kwargs.get("fieldThresh", 0.2)
    required_neighbours = kwargs.get("minPlaceFieldNeighbours", 9)
    smooth_place = kwargs.get("smoothPlace", False)
    # Can pass another NData object to estimate the border from
    # Can be useful in some cases, such as when the animal
    # only explores a subset of the arena.
    separate_border_data = kwargs.get("separateBorderData", None)

    # xedges = np.arange(0, np.ceil(np.max(self._pos_x)), pixel)
    # yedges = np.arange(0, np.ceil(np.max(self._pos_y)), pixel)

    # Update the border to match the requested pixel size
    if separate_border_data is not None:
        self.set_border(separate_border_data.calc_border(**kwargs))
        times = self._time
        lower, upper = (times.min(), times.max())
        new_times = separate_border_data._time
        sample_spatial_idx = ((new_times <= upper) & (new_times >= lower)).nonzero()
        self._border_dist = self._border_dist[sample_spatial_idx]
    else:
        self.set_border(self.calc_border(**kwargs))

    xedges = self._xbound
    yedges = self._ybound
    xedges2 = other_spatial._xbound
    yedges2 = other_spatial._ybound

    spikeLoc = self.get_event_loc(ftimes, **kwargs)[1]
    posX = self._pos_x[
        np.logical_and(self.get_time() >= lim[0], self.get_time() <= lim[1])
    ]
    posY = self._pos_y[
        np.logical_and(self.get_time() >= lim[0], self.get_time() <= lim[1])
    ]

    new_set, spike_count = self.bin_downsample(
        ftimes,
        other_spatial,
        other_ftimes,
        final_bins=[
            np.append(yedges, yedges[-1] + np.mean(np.diff(yedges))),
            np.append(xedges, xedges[-1] + np.mean(np.diff(xedges))),
        ],
        sample_bin_amt=[len(xedges2) + 1, len(yedges2) + 1],
    )
    posY = new_set[:, 1]
    posX = new_set[:, 0]

    tmap, yedges, xedges = histogram2d(posY, posX, yedges, xedges)
    if tmap.shape != spike_count.shape:
        print(tmap.shape)
        print(spike_count.shape)
        raise ValueError("Time map does not match firing map")

    tmap /= self.get_sampling_rate()

    ybin, xbin = tmap.shape
    xedges = np.arange(xbin) * pixel
    yedges = np.arange(ybin) * pixel

    fmap = np.divide(spike_count, tmap, out=np.zeros_like(spike_count), where=tmap != 0)
    if fmap.max() == 0:
        print("No firing information!")
        return -1
    if brAdjust:
        nfmap = fmap / fmap.max()
        if (
            np.sum(np.logical_and(nfmap >= 0.2, tmap != 0))
            >= 0.8 * nfmap[tmap != 0].flatten().shape[0]
        ):
            back_rate = np.mean(fmap[np.logical_and(nfmap >= 0.2, nfmap < 0.4)])
            fmap -= back_rate
            fmap[fmap < 0] = 0

    if filttype is not None:
        smoothMap = smooth_2d(fmap, filttype, filtsize)
    else:
        smoothMap = fmap

    if smooth_place:
        pmap = smoothMap
    else:
        pmap = fmap

    pmap[tmap == 0] = None
    pfield, largest_group = NSpatial.place_field(pmap, thresh, required_neighbours)
    # if largest_group == 0:
    #     if smooth_place:
    #         info = "where the place field was calculated from smoothed data"
    #     else:
    #         info = "where the place field was calculated from raw data"
    #     logging.info(
    #         "Lack of high firing neighbours to identify place field " +
    #         info)
    centroid = NSpatial.place_field_centroid(pfield, pmap, largest_group)
    # centroid is currently in co-ordinates, convert to pixels
    centroid = centroid * pixel + (pixel * 0.5)
    # flip x and y
    centroid = centroid[::-1]

    p_shape = pfield.shape
    maxes = [xedges.max(), yedges.max()]
    scales = (maxes[0] / p_shape[1], maxes[1] / p_shape[0])
    co_ords = np.array(np.where(pfield == largest_group))
    boundary = [[None, None], [None, None]]
    for i in range(2):
        j = (i + 1) % 2
        boundary[i] = (
            co_ords[j].min() * scales[i],
            np.clip((co_ords[j].max() + 1) * scales[i], 0, maxes[i]),
        )
    inside_x = (boundary[0][0] <= spikeLoc[0]) & (spikeLoc[0] <= boundary[0][1])
    inside_y = (boundary[1][0] <= spikeLoc[1]) & (spikeLoc[1] <= boundary[1][1])
    co_ords = np.nonzero(np.logical_and(inside_x, inside_y))

    if update:
        _results["Spatial Skaggs"] = self.skaggs_info(fmap, tmap)
        _results["Spatial Sparsity"] = self.spatial_sparsity(fmap, tmap)
        _results["Spatial Coherence"] = np.corrcoef(
            fmap[tmap != 0].flatten(), smoothMap[tmap != 0].flatten()
        )[0, 1]
        _results["Found strong place field"] = largest_group != 0
        _results["Place field Centroid x"] = centroid[0]
        _results["Place field Centroid y"] = centroid[1]
        _results["Place field Boundary x"] = boundary[0]
        _results["Place field Boundary y"] = boundary[1]
        _results["Number of Spikes in Place Field"] = co_ords[0].size
        _results["Percentage of Spikes in Place Field"] = (
            co_ords[0].size * 100 / ftimes.size
        )
        self.update_result(_results)

    smoothMap[tmap == 0] = None

    graph_data["posX"] = posX
    graph_data["posY"] = posY
    graph_data["fmap"] = fmap
    graph_data["smoothMap"] = smoothMap
    graph_data["firingMap"] = fmap
    graph_data["tmap"] = tmap
    graph_data["xedges"] = xedges
    graph_data["yedges"] = yedges
    graph_data["spikeLoc"] = spikeLoc
    graph_data["placeField"] = pfield
    graph_data["largestPlaceGroup"] = largest_group
    graph_data["placeBoundary"] = boundary
    graph_data["indicesInPlaceField"] = co_ords
    graph_data["centroid"] = centroid

    return graph_data


def chop_map(self, chop_edges, ftimes):
    """This is x_l, x_r, y_t, y_b."""
    x_l, x_r, y_t, y_b = np.array(chop_edges)
    x_r = max(self._pos_x) - x_r
    y_t = max(self._pos_y) - y_t
    in_range_x = np.logical_and(self._pos_x >= x_l, self._pos_x <= x_r)
    in_range_y = np.logical_and(self._pos_y >= y_b, self._pos_y <= y_t)

    spikeLoc = self.get_event_loc(ftimes)[1]
    spike_idxs = spikeLoc[0]
    spike_idxs_to_use = []

    sample_spatial_idx = np.where(np.logical_and(in_range_y, in_range_x))
    for i, val in enumerate(spike_idxs):
        if not np.any(sample_spatial_idx == val):
            spike_idxs_to_use.append(i)
    ftimes = ftimes[np.array(spike_idxs_to_use)]

    self._set_time(self._time[sample_spatial_idx])
    self._set_pos_x(self._pos_x[sample_spatial_idx] - x_l)
    self._set_pos_y(self._pos_y[sample_spatial_idx] - y_b)
    self._set_direction(self._direction[sample_spatial_idx])
    self._set_speed(self._speed[sample_spatial_idx])
    self.set_ang_vel(self._ang_vel[sample_spatial_idx])

    return ftimes


NSpatial.bin_downsample = bin_downsample
NSpatial.downsample_place = downsample_place
NSpatial.reverse_downsample = reverse_downsample
NSpatial.chop_map = chop_map


def get_nc_unit(recording):
    """

    Parameters
    ----------
    recording : simuran.recording.Recording
        The recording to get the unit from.

    Returns
    -------
    unit : neurochat.nc_spike.NSpike
        The unit obtained from the recording

    Raises
    ------
    ValueError: Two units are set on the recording

    """
    set_units = recording.get_set_units()
    unit_num = -1
    unit = None
    for i, a_unit in enumerate(set_units):
        if a_unit is None:
            continue
        if len(a_unit) != 0:
            if unit_num != -1:
                raise ValueError(
                    "There are two set units for {}, {}".format(recording, a_unit)
                )
            unit = recording.units[i]
            unit_num = a_unit[0]
    if unit_num == -1:
        print("Warning: no set units for {}".format(recording))
        return
    unit.load()
    spike = unit.underlying
    spike.set_unit_no(unit_num)

    return spike


def random_down(spat1, ftimes1, spat2, ftimes2, keys, num_iters=200):
    results = {}
    output_dict = {}
    for key in keys:
        results[key] = np.zeros(shape=(num_iters))
    for i in range(num_iters):
        p_down_data = spat1.downsample_place(ftimes1, spat2, ftimes2)
        while p_down_data == -1:
            p_down_data = spat1.downsample_place(ftimes1, spat2, ftimes2)
        for key in keys:
            results[key][i] = spat1.get_results()[key]
        spat1._results.clear()
    output_dict = {}
    for key in keys:
        output_dict[key] = np.nanmean(results[key])
    return output_dict, p_down_data


def compare_place(recording1, recording2, grid_fig, chop_bound1, chop_bound2):
    results = {}
    recording1.spatial.load()
    nspat1 = recording1.spatial.underlying
    nspike1 = get_nc_unit(recording1)
    ftimes1 = nspike1.get_unit_stamp()
    recording2.spatial.load()
    nspat2 = recording2.spatial.underlying
    nspike2 = get_nc_unit(recording2)
    ftimes2 = nspike2.get_unit_stamp()

    if chop_bound1 != None:
        ftimes1 = deepcopy(ftimes1)
        nspat1 = deepcopy(nspat1)
        ftimes1 = nspat1.chop_map(chop_bound1, ftimes1)
    if chop_bound2 != None:
        ftimes2 = deepcopy(ftimes2)
        nspat2 = deepcopy(nspat2)
        ftimes2 = nspat2.chop_map(chop_bound2, ftimes2)

    # Normal HD is here since it matters less
    hd_data = nspat1.hd_rate(ftimes1)
    results["HD_Result"] = nspat1.get_results()["HD Res Vect"]

    try:
        grid_data = nspat1.grid(ftimes1)
        results["Is_Grid"] = nspat1.get_results()["Is Grid"]
    except:
        results["Is_Grid"] = False

    # Do the downsampling
    keys = ["Spatial Coherence", "Spatial Skaggs", "Spatial Sparsity"]
    short_keys = ["Coh", "Skagg", "Spar"]
    names = ["A_A", "B_B", "B_A", "A_B"]
    place_data = nspat1.place(ftimes1)
    ncplot.loc_rate(place_data, ax=grid_fig.get_next())
    results["A_Coh"] = nspat1.get_results()["Spatial Coherence"]
    results["A_Skagg"] = nspat1.get_results()["Spatial Skaggs"]
    results["A_Spar"] = nspat1.get_results()["Spatial Sparsity"]
    nspat1._results.clear()
    nspat2.place(ftimes2)
    results["B_Coh"] = nspat2.get_results()["Spatial Coherence"]
    results["B_Skagg"] = nspat2.get_results()["Spatial Skaggs"]
    results["B_Spar"] = nspat2.get_results()["Spatial Sparsity"]
    nspat2._results.clear()
    results_aa, _ = random_down(nspat1, ftimes1, nspat1, ftimes1, keys)
    results_bb, _ = random_down(nspat2, ftimes2, nspat2, ftimes2, keys)
    results_ba, pd = random_down(nspat2, ftimes2, nspat1, ftimes1, keys)
    ncplot.loc_rate(pd, ax=grid_fig.get_next())
    results_ab, pd = random_down(nspat1, ftimes1, nspat2, ftimes2, keys)
    ncplot.loc_rate(pd, ax=grid_fig.get_next())
    all_results = [results_aa, results_bb, results_ba, results_ab]

    # Save out the results
    for (name, res) in zip(names, all_results):
        for key, short_key in zip(keys, short_keys):
            out_key = name + "_" + short_key
            results[out_key] = res[key]

    return results
