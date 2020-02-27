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

def list_extractors():
    print("Available recording extractors", se.installed_recording_extractor_list)
    print("Available sorting extractors", se.installed_sorting_extractor_list)
    print('Available sorters', ss.available_sorters())
    print('Installed sorters', ss.installed_sorter_list)

def print_default_params():
    print(ss.get_default_params('mountainsort4'))
    print(ss.get_default_params('klusta'))
    print(ss.get_default_params('spykingcircus'))

def custom_default_params_list(sorter_name, check=False):
    if check:
        return ss.get_default_params(sorter_name)
    elif sorter_name == "klusta":
        return {}
    return {}

def run(location, sorter="klusta", **sorting_kwargs):
    print("Starting the sorting pipeline from bin data on {}".format(
        os.path.basename(location)))
    recording = se.BinDatRecordingExtractor(
        file_path=location, offset=16, dtype=np.int16,
        sampling_frequency=48000, numchan=64)
    # get_info(recording)
    # exit(-1)

    # This bit loads a probe file
    recording_prb = recording.load_probe_file('channel_map.prb')
    get_info(recording)

    # Plot a bit of the raw data
    print("Plotting a trace of the raw data to t5s.png")
    w_ts = sw.plot_timeseries(recording_prb, trange=[0, 5])
    plt.savefig("t5s.png", dpi=200)

    # Do pre-processing pipeline
    print("Running preprocessing")
    recording_f = st.preprocessing.bandpass_filter(recording_prb, freq_min=300, freq_max=6000)
    recording_rm_noise = st.preprocessing.remove_bad_channels(
        recording_f, bad_channel_ids=[i for i in range(3, 63, 4)])
    print('Channel ids after preprocess:',
          recording_rm_noise.get_channel_ids())

    # Get sorting params and run the sorting
    params = custom_default_params_list(sorter, check=True)
    for k, v in sorting_kwargs.items():
        params[k] = v
    print("Running {} with parameters {}".format(
        sorter, params))
    sorted_s = ss.run_sorter(sorter, recording_rm_noise, **params)
    
    # Some validation statistics
    snrs = st.validation.compute_snrs(sorted_s, recording_rm_noise)
    isi_violations = st.validation.compute_isi_violations(sorted_s)
    isolations = st.validation.compute_isolation_distances(sorted_s, recording)

    print('SNR', snrs)
    print('ISI violation ratios', isi_violations)
    print('Isolation distances', isolations)

    # Do automatic curation based on the snr
    sorting_curated_snr = st.curation.threshold_snr(
        sorted_s, recording, threshold=5, threshold_sign='less')
    snrs_above = st.validation.compute_snrs(
        sorting_curated_snr, recording_rm_noise)

    print('Curated SNR', snrs_above)
    get_sort_info(sorting_curated_snr, recording_rm_noise)

    # Export the result to phy for manual curation
    st.postprocessing.export_to_phy(
        recording, sorting_curated_snr, output_folder='phy',
        grouping_property='group')
    subprocess.run(["phy", "template-gui", "phy/params.py"])

    # If you need to process the data further!
    # sorting_phy_curated = se.PhySortingExtractor("phy")


    # Here you could do some comparisons with other things
    # See the ending part of 
    # https://github.com/SpikeInterface/spiketutorials/blob/master/Spike_sorting_workshop_2019/SpikeInterface_Tutorial.ipynb

def get_sort_info(sorting, recording):
    unit_ids = sorting.get_unit_ids()
    spike_train = sorting.get_unit_spike_train(unit_id=unit_ids[0])

    print("Found", len(unit_ids), 'units')
    print('Unit ids:', unit_ids)
    w_rs = sw.plot_rasters(sorting, trange=[0, 5])
    plt.savefig("raster5s.png", dpi=200)

    print('Spike train of first unit:', spike_train)
    w_wf = sw.plot_unit_waveforms(
        sorting=sorting, recording=recording, unit_ids=range(5))
    plt.savefig("5waveforms.png", dpi=200)

def get_info(recording, prb_fname="channel_map.prb"):
    print("Recording information:")
    fs = recording.get_sampling_frequency()
    num_chan = recording.get_num_channels()

    print('Sampling frequency:', fs)
    print('Number of channels:', num_chan)

    recording_prb = recording.load_probe_file(prb_fname)
    # print('Original channels:', recording.get_channel_ids())
    print('Channels after loading the probe file:', recording_prb.get_channel_ids())
    print('Channel groups after loading the probe file:',
        recording_prb.get_channel_groups())
    # print(recording_prb.get_channel_locations())

    return recording_prb

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
    in_dir = r"G:\Ham Data\A10_CAR-SA2\CAR-SA2_20200109_PreBox"
    fname = "CAR-SA2_2020-01-09_PreBox_shuff.bin"
    location = os.path.join(in_dir, fname)
    out_folder = "results_tet12_klusta"

    # Remove this if you don't want a new channel_map
    write_prb_file(tetrodes_to_use=[])

    # grouping_property = group controls whether clustering is ran
    # per tetrode, or on the entire recording
    run(location, "klusta", 
        output_folder=out_folder,
        grouping_property="group")
