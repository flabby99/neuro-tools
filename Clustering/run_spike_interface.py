import spikeinterface.extractors as se
import spikeinterface.toolkit as st
import spikeinterface.sorters as ss
import spikeinterface.comparison as sc
import spikeinterface.widgets as sw

import os

import matplotlib.pyplot as plt
import subprocess

import numpy as np

from channel_map import write_prb_file

from time import time
import subprocess

def list_sorters():
    """Print a list of spikeinterface sorters."""
    print('Available sorters', ss.available_sorters())
    print('Installed sorters', ss.installed_sorter_list)

def custom_default_params_list(sorter_name, check=False):
    """
    Get a dictionary of params for a sorter.
    
    if check if True just return default.
    """
    default_params = ss.get_default_params(sorter_name)
    if check:
        default_params = default_params
    elif sorter_name == "klusta":
        default_params["detect_sign"] = 1
        default_params["extract_s_before"] = 10
        default_params["extract_s_after"] = 40
        default_params["num_starting_clusters"] = 50
        default_params["threshold_strong_std_factor"] = 4.5
    elif sorter_name == "spykingcircus":
        default_params["detect_sign"] = 1
        default_params["adjacency_radius"] = 0.2
        default_params["detect_threshold"] = 4.5
        default_params["template_width_ms"] = 3
        default_params["filter"] = False
        default_params["num_workers"] = 8
    elif sorter_name == "herdingspikes":
        default_params["filter"] = False
    return default_params

def run(location, sorter="klusta", output_folder="result", 
        verbose=False, view=False, phy_out_folder="phy",
        remove_last_chan=False, do_validate=False, 
        do_parallel=False, **sorting_kwargs):
    """
    Run spike interface on a _shuff.bin file.

    if verbose is True prints more information.

    """
    # Do setup
    o_start = time()
    print("Starting the sorting pipeline from bin data on {}".format(
        os.path.basename(location)))
    in_dir = os.path.dirname(location)
    o_dir = os.path.join(in_dir, output_folder)
    probe_loc = os.path.join(o_dir, "channel_map.prb")
    
    # Load the recording data
    start_time = time()
    recording = se.BinDatRecordingExtractor(
        file_path=location, offset=16, dtype=np.int16,
        sampling_frequency=48000, numchan=64, time_axis=1)
    recording_prb = recording.load_probe_file(probe_loc)
    get_info(recording, probe_loc)

    # Plot a trace of the raw data
    t_len = 10
    o_loc = os.path.join(o_dir, "trace_" + str(t_len) + "s.png")
    print("Plotting a {}s trace of the raw data to {}".format(
        t_len, o_loc))
    w_ts = sw.plot_timeseries(recording_prb, trange=[0, t_len])
    plt.savefig(o_loc, dpi=200)

    # Do the pre-processing pipeline
    print("Running preprocessing")
    recording_f = st.preprocessing.bandpass_filter(
        recording_prb, freq_min=300, freq_max=6000)
    bad_chans = [
            i for i in range(3, 64, 4) 
            if i in recording_f.get_channel_ids()]
    print("Removing {}".format(bad_chans))
    recording_rm_noise = st.preprocessing.remove_bad_channels(
        recording_f, bad_channel_ids=bad_chans)
    print('Channel ids after preprocess:',
          recording_rm_noise.get_channel_ids())
    print('Channel groups after preprocess:',
          recording_rm_noise.get_channel_groups())
    preproc_recording = recording_rm_noise

    # Get sorting params and run the sorting
    params = custom_default_params_list(sorter, check=False)
    for k, v in sorting_kwargs.items():
        params[k] = v
    print("Loaded and preprocessed data in {:.2f}s".format(time() - start_time))
    start_time = time()
    print("Running {} with parameters {}".format(
        sorter, params))
    sorted_s = ss.run_sorter(
        sorter, preproc_recording, 
        grouping_property="group", output_folder=o_dir,
        parallel=do_parallel, verbose=verbose, **params)
    print("Sorted in {:.2f}mins".format((time() - start_time)/60.0))
    
    # Some validation statistics
    if do_validate:
        print("Spike sorting completed, running validation")
        start_time = time()
        sorting_curated_snr = st.curation.threshold_snr(
            sorted_s, recording, threshold=5, threshold_sign='less')
        
        # Extra stats that can be printed but takes time
        # snrs = st.validation.compute_snrs(sorted_s, preproc_recording)
        # isi_violations = st.validation.compute_isi_violations(sorted_s)
        # isolations = st.validation.compute_isolation_distances(
        #     sorted_s, preproc_recording)

        # print('SNR', snrs)
        # print('ISI violation ratios', isi_violations)
        # print('Isolation distances', isolations)

        # Do automatic curation based on the snr
        # snrs_above = st.validation.compute_snrs(
        #     sorting_curated_snr, preproc_recording)
        # print('Curated SNR', snrs_above)

        print("Validated in {:.2f}mins".format((time() - start_time)/60.0))
    else:
        sorting_curated_snr = sorted_s

    # Export the result to phy for manual curation
    start_time = time()
    phy_out = os.path.join(in_dir, phy_out_folder)
    print("Exporting to phy")
    st.postprocessing.export_to_phy(
        recording, sorting_curated_snr,
        output_folder=phy_out, grouping_property='group',
        verbose=verbose, ms_before=0.2, ms_after=0.8, dtype=None,
        max_channels_per_template=8, max_spikes_for_pca=5000)
    print("Exported in {:.2f}s".format(time() - start_time))
    pipeline_time = (time() - o_start) / 60.0
    print("Whole pipeline took {:.2f}mins".format(pipeline_time))
    
    do_plot = False
    print("Showing some extra information")
    start_time = time()
    if do_plot:
        get_sort_info(sorting_curated_snr, preproc_recording, o_dir)
    else:
        unit_ids = sorting_curated_snr.get_unit_ids()
        print("Found", len(unit_ids), 'units')
        plot_all_forms(sorting_curated_snr, preproc_recording, o_dir)
    print(
        "Summarised recording in {:.2f}mins".format((time() - start_time)/60.0))

    phy_final = os.path.join(phy_out, "params.py")
    if view:
        subprocess.run(["phy", "template-gui", phy_final])
    else:
        print(
            "To view the data in phy, run: phy template-gui {}".format(
            phy_final))

    # If you need to process the data further!
    # sorting_phy_curated = se.PhySortingExtractor("phy")

    # Here you could do some comparisons with other things
    # See the ending part of 
    # https://github.com/SpikeInterface/spiketutorials/blob/master/Spike_sorting_workshop_2019/SpikeInterface_Tutorial.ipynb

def get_sort_info(sorting, recording, out_loc):
    unit_ids = sorting.get_unit_ids()
    print("Found", len(unit_ids), 'units')
    print('Unit ids:', unit_ids)

    spike_train = sorting.get_unit_spike_train(unit_id=unit_ids[0])
    print('Spike train of first unit:', np.asarray(spike_train) / 48000)

    # Spike raster plot
    t_len = 10
    o_loc = os.path.join(out_loc, "raster_" + str(t_len) + "s.png")
    print("Saving {}s rasters to {}".format(t_len, o_loc))
    w_rs = sw.plot_rasters(sorting, trange=[0, t_len])
    plt.savefig(o_loc, dpi=200)

    w_isi = sw.plot_isi_distribution(sorting, bins=10, window=1)
    o_loc = os.path.join(out_loc, "isi.png")
    print("Saving isi to {}".format(o_loc))
    plt.savefig(o_loc, dpi=200)

    # Can plot cross corr using - ignore for now
    # w_cch = sw.plot_crosscorrelograms(
    # sorting, unit_ids=[1, 5, 8], bin_size=0.1, window=5)
    w_feat = sw.plot_pca_features(
        recording, sorting, colormap='rainbow', nproj=3, max_spikes_per_unit=100)
    o_loc = os.path.join(out_loc, "pca.png")
    print("Plotting pca to {}".format(o_loc))
    plt.savefig(o_loc, dpi=200)

    # See also spiketoolkit.postprocessing.get_unit_waveforms
    num_samps = min(20, len(unit_ids))
    w_wf = sw.plot_unit_waveforms(
        sorting=sorting, recording=recording, unit_ids=unit_ids[:num_samps],
        max_spikes_per_unit=20)
    o_loc = os.path.join(out_loc, "waveforms_" + str(num_samps) + ".png")
    print("Saving {} waveforms to {}".format(num_samps, o_loc))
    plt.savefig(o_loc, dpi=200)

    wf_by_group = st.postprocessing.get_unit_waveforms(
        recording, sorting, ms_before=1, ms_after=2,
        save_as_features=False, verbose=True, grouping_property="group",
        compute_property_from_recording=True)
    o_loc = os.path.join(out_loc, "chan0_forms.png")
    fig, ax = plt.subplots()
    wf = wf_by_group[0]
    colors = ["k", "r", "b", "g"]
    for i in range(wf.shape[1]):
        wave = wf[:, i, :]
        c = colors[i]
        ax.plot(wave.T, color=c, lw=0.3)
    print("Saving first waveform on the first tetrode to {}".format(
        o_loc))
    fig.savefig(o_loc, dpi=200)

def plot_all_forms(sorting, recording, out_loc):
    wf_by_group = st.postprocessing.get_unit_waveforms(
        recording, sorting, ms_before=0.2, ms_after=0.8,
        save_as_features=False, verbose=False, grouping_property="group",
        compute_property_from_recording=True, max_spikes_per_unit=100)
    unit_ids = sorting.get_unit_ids()
    for i, wf in enumerate(wf_by_group):
        try:
            tetrode = sorting.get_unit_property(unit_ids[i], "group")
        except Exception:
            try:
                tetrode = sorting.get_unit_property(
                    unit_ids[i], "ch_group")
            except Exception:
                print("Unable to find cluster group or group in units")
                print(sorting.get_shared_unit_property_names())
                return

        fig, axes = plt.subplots(3)
        for j in range(3):
            try:
                wave = wf[:, j, :]
            except Exception:
                wave = wf[j, :]
            axes[j].plot(wave.T, color="k", lw=0.3)
        o_loc = os.path.join(
            out_loc, "tet{}_unit{}_forms.png".format(
                tetrode, i))
        print("Saving waveform {} on tetrode {} to {}".format(
            i, tetrode, o_loc))
        fig.savefig(o_loc, dpi=200)
        plt.close("all")

def get_info(recording, prb_fname="channel_map.prb"):
    fs = recording.get_sampling_frequency()
    num_chan = recording.get_num_channels()
    recording_prb = recording.load_probe_file(prb_fname)

    print("Recording information:")
    print('Sampling frequency:', fs)
    print('Number of channels:', num_chan)
    print(
        'Channels after loading the probe file:', 
        recording_prb.get_channel_ids())
    print('Channel groups after loading the probe file:',
        recording_prb.get_channel_groups())

def compare_sorters(sort1, sort2):
    comp_KL_MS4 = sc.compare_two_sorters(
        sorting1=sort1, sorting2=sort2)
    mapped_units = comp_KL_MS4.get_mapped_sorting1().get_mapped_unit_ids()

    print('Klusta units:', sort1.get_unit_ids())
    print('Mapped Mountainsort4 units:', mapped_units)

    comp_multi = sc.compare_multiple_sorters(
        sorting_list=[sort1, sort2],
        name_list=['klusta', 'ms4'])

    sorting_agreement = comp_multi.get_agreement_sorting(minimum_matching=2)

    print(
        'Units in agreement between Klusta and Mountainsort4:', sorting_agreement.get_unit_ids())

    w_multi = sw.plot_multicomp_graph(comp_multi)
    plt.show()

def main(
    location, sort_method, out_folder, tetrodes_to_use, 
    remove_last_chan, phy_out_folder, do_validate, do_parallel):
    print("Starting to run spike interface!")
    in_dir = os.path.dirname(location)
    out_loc = os.path.join(in_dir, out_folder, "channel_map.prb")
    os.makedirs(os.path.dirname(out_loc), exist_ok=True)

    write_prb_file(tetrodes_to_use=tetrodes_to_use, out_loc=out_loc)
    # TODO can actually set channel gains on a recording
    run(location, sort_method, output_folder=out_folder, verbose=False,
        remove_last_chan=remove_last_chan, phy_out_folder=phy_out_folder,
        view=False, do_validate=do_validate, do_parallel=do_parallel)

def load_sorting(in_dir, extract_method="phy"):
    sorting_curated = None
    if extract_method == "phy":
        sorting_curated = se.PhySortingExtractor(in_dir)
    return sorting_curated

def make_folder_structure(main_dir, out_folder="results_klusta"):
    for i in range(16):
        os.makedirs(os.path.join(main_dir, out_folder, str(i)), exist_ok=True)

if __name__ == "__main__":
    check_params_only = False
    load_sort = True
    
    sort_method = "klusta"
    if sort_method == "klusta":
        do_parallel = True
    elif sort_method == "spykingcircus":
        do_parallel = False
    elif sort_method == "herdingspikes":
        do_parallel = True

    # in_dir = r"G:\Ham\A10_CAR-SA2\CAR-SA2_20200110"
    in_dir = r"G:\Ham\A10_CAR-SA2\CAR-SA2_20200109_PreBox"
    make_folder_structure(in_dir, "results_klusta2")
    fname = "CAR-SA2_2020-01-10.set"
    overwrite = False
    set_fullname = os.path.join(in_dir, fname)
    bin_fname = fname[:-4] + "_shuff.bin"
    bin_fullname = os.path.join(in_dir, bin_fname)
    if (not os.path.exists(bin_fullname)) or overwrite:
        print("Writing binary info to {}".format(bin_fullname))
        subprocess.run(["AxonaBinary", set_fullname, "read"])

    else:
        print("Reading binary info from {}".format(bin_fullname))
    default_out_names = True
    
    if default_out_names:
        out_folder = "results_" + sort_method
        phy_out_folder = "phy_" + sort_method
    else:
        out_folder = "res"
        phy_out_folder = "phy"
    
    tetrodes_to_use = [] # [] uses all 16
    remove_last_chan = True # Set to true for last chan on tetrode = eeg
    do_validate = True
    
    # Actual execution here
    if check_params_only:
        print(custom_default_params_list(sort_method, check=False))
        exit(-1)
    if load_sort:
        location = os.path.join(in_dir, phy_out_folder)
        sorting = load_sorting(location)
        # recording = se.BinDatRecordingExtractor(
        #     file_path=bin_fullname, offset=16, dtype=np.int16,
        #     sampling_frequency=48000, numchan=64, time_axis=1)
        recording_name = os.path.join(in_dir, phy_out_folder)
        recording = se.PhyRecordingExtractor(recording_name)
        recording_prb = recording.load_probe_file(
            os.path.join(in_dir, out_folder, "channel_map.prb"))
        plot_all_forms(sorting, recording_prb, os.path.join(in_dir, out_folder))
        # spike_train = sorting.get_unit_spike_train(unit_id=35)
        # print(len(spike_train))
        # print(spike_train[:20] / 48000)
        # print(spike_train[-20:] / 48000)
        exit(-1)

    main(
        bin_fullname, sort_method, out_folder, tetrodes_to_use,
        remove_last_chan, phy_out_folder, do_validate, do_parallel)
