import spikeinterface.extractors as se
import spikeinterface.toolkit as st
import spikeinterface.sorters as ss
import spikeinterface.comparison as sc
import spikeinterface.widgets as sw

import os

import matplotlib.pyplot as plt
import subprocess

def list_extractors():
    print("Available recording extractors", se.installed_recording_extractor_list)
    print("Available sorting extractors", se.installed_sorting_extractor_list)
    print('Available sorters', ss.available_sorters())
    print('Installed sorters', ss.installed_sorter_list)

def print_default_params():
    print(ss.get_default_params('mountainsort4'))
    print(ss.get_default_params('klusta'))

def run(location, sorter=ss.run_spyking_circus, sorting_kwargs={}):
    recording = se.BinDatRecordingExtractor(location)

    # This bit loads a probe file
    recording_prb = get_info(recording)
    w_ts = sw.plot_timeseries(recording_prb, trange=[0, 5])
    plt.show()

    # Do pre-processing pipeline
    recording_f = st.preprocessing.bandpass_filter(recording_prb, freq_min=300, freq_max=6000)
    recording_cmr = st.preprocessing.common_reference(recording_f, reference='median')

    sorted_s = sorter(recording_cmr, **sorting_kwargs)
    w_rs = sw.plot_rasters(sorted_s, trange=[0, 5])
    plt.show()

    get_sort_info(sorted_s)

    snrs = st.validation.compute_snrs(sorted_s, recording_cmr)
    isi_violations = st.validation.compute_isi_violations(sorted_s)
    isolations = st.validation.compute_isolation_distances(sorted_s, recording)

    print('SNR', snrs)
    print('ISI violation ratios', isi_violations)
    print('Isolation distances', isolations)

    sorting_curated_snr = st.curation.threshold_snr(
        sorted_s, recording, threshold=5, threshold_sign='less')
    snrs_above = st.validation.compute_snrs(sorting_curated_snr, recording_cmr)

    print('Curated SNR', snrs_above)

    st.postprocessing.export_to_phy(
        recording, sorting_curated_snr, output_folder='phy')
    subprocess.run(["phy", "template-gui", "phy/params.py"])

def get_sort_info(sorting):
    unit_ids = sorting.get_unit_ids()
    spike_train = sorting.get_unit_spike_train(unit_id=unit_ids[0])

    print('Unit ids:', unit_ids)
    print('Spike train of first unit:', spike_train)

def get_info(recording, prb_fname="channel_map.py"):
    channel_ids = recording.get_channel_ids()
    fs = recording.get_sampling_frequency()
    num_chan = recording.get_num_channels()

    print('Channel ids:', channel_ids)
    print('Sampling frequency:', fs)
    print('Number of channels:', num_chan)

    recording_prb = recording.load_probe_file('custom_probe.prb')
    print('Channel ids:', recording_prb.get_channel_ids())
    print('Loaded properties', recording_prb.get_shared_channel_property_names())
    print('Label of channel 0:', recording_prb.get_channel_property(channel_id=0, property_name='label'))

    # 'group' and 'location' can be returned as lists:
    print(recording_prb.get_channel_groups())
    print(recording_prb.get_channel_locations())

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
    list_extractors()
    print_default_params()
