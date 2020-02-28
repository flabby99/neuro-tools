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
    return default_params

def run(location, sorter="klusta", output_folder="result", 
        verbose=False, view=False, **sorting_kwargs):
    """
    Run spike interface on a _shuff.bin file.

    if verbose is True prints more information.

    """
    # Do setup
    print("Starting the sorting pipeline from bin data on {}".format(
        os.path.basename(location)))
    in_dir = os.path.dirname(location)
    o_dir = os.path.join(in_dir, output_folder)
    probe_loc = os.path.join(o_dir, "channel_map.prb")
    
    # Load the recording data
    recording = se.BinDatRecordingExtractor(
        file_path=location, offset=16, dtype=np.int16,
        sampling_frequency=48000, numchan=64)
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
            i for i in range(3, 63, 4) 
            if i in recording_f.get_channel_ids()]
    print("Removing {}".format(bad_chans))
    recording_rm_noise = st.preprocessing.remove_bad_channels(
        recording_f, bad_channel_ids=bad_chans)
    print('Channel ids after preprocess:',
          recording_rm_noise.get_channel_ids())
    preproc_recording = recording_rm_noise

    # Get sorting params and run the sorting
    params = custom_default_params_list(sorter, check=False)
    for k, v in sorting_kwargs.items():
        params[k] = v
    print("Running {} with parameters {}".format(
        sorter, params))
    sorted_s = ss.run_sorter(
        sorter, preproc_recording, 
        grouping_property="group", output_folder=o_dir,
        parallel=True, verbose=verbose, **params)
    
    # Some validation statistics
    snrs = st.validation.compute_snrs(sorted_s, preproc_recording)
    isi_violations = st.validation.compute_isi_violations(sorted_s)
    isolations = st.validation.compute_isolation_distances(
        sorted_s, preproc_recording)

    print('SNR', snrs)
    print('ISI violation ratios', isi_violations)
    print('Isolation distances', isolations)

    # Do automatic curation based on the snr
    sorting_curated_snr = st.curation.threshold_snr(
        sorted_s, recording, threshold=5, threshold_sign='less')
    snrs_above = st.validation.compute_snrs(
        sorting_curated_snr, preproc_recording)

    print('Curated SNR', snrs_above)
    get_sort_info(sorting_curated_snr, preproc_recording, o_dir)

    # Export the result to phy for manual curation
    phy_out = os.path.join(in_dir, "phy")
    st.postprocessing.export_to_phy(
        recording, sorting_curated_snr, 
        output_folder=phy_out, grouping_property='group')
    
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

    # See also spiketoolkit.postprocessing.get_unit_waveforms
    num_samps = min(5, len(unit_ids))
    w_wf = sw.plot_unit_waveforms(
        sorting=sorting, recording=recording, unit_ids=unit_ids[:num_samps])
    o_loc = os.path.join(out_loc, "waveforms_" + str(num_samps) + ".png")
    print("Saving {} waveforms to {}".format(num_samps, o_loc))
    plt.savefig(o_loc, dpi=200)

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

if __name__ == "__main__":
    # list_extractors()
    # print_default_params()
    print("Starting to run spike interface!")
    in_dir = r"G:\Ham\A10_CAR-SA2\CAR-SA2_20200109_PreBox"
    fname = "CAR-SA2_2020-01-09_PreBox_shuff.bin"
    location = os.path.join(in_dir, fname)
    out_folder = "results_tet12_klusta"
    out_loc = os.path.join(in_dir, out_folder, "channel_map.prb")
    os.makedirs(os.path.dirname(out_loc), exist_ok=True)

    # Remove this if you don't want a new channel_map
    write_prb_file(tetrodes_to_use=[12], out_loc=out_loc)

    # grouping_property = group controls whether clustering is ran
    # per tetrode, or on the entire recording
    run(location, "klusta", output_folder=out_folder, verbose=True)

    # TODO can actually set channel gains on a recording
