import os
import shutil

from skm_pyutils.py_path import make_dir_if_not_exists
from neurochat.nc_data import NData
from neurochat.nc_spike import NSpike
from get_files_from_list import main as get_files


def my_copy(f, t, only_check=True, verbose=False):
    if only_check:
        print("Would copy from {} to {}".format(f, t))
    else:
        if verbose:
            print("Copying from {} to {}".format(f, t))
        if not os.path.isfile(f):
            raise ValueError("{} is not a file".format(f))
        shutil.copy(f, t)


def get_spike_times(spike_file, unit_num):
    spike = NSpike()
    spike.set_filename(spike_file)
    spike.set_system("Axona")
    spike.load()
    spike.set_unit_no(unit_num)
    spike_times = spike.get_unit_stamp()
    return spike_times


def analyse_all_data(file_list):
    ndata = NData()
    results = []
    for i in range(len(file_list["set_files"])):
        print("Working on {}: {}".format(i, file_list["set_files"][i]))
        ndata.set_spatial_file(file_list["txt_files"][i])
        ndata.set_spike_file(file_list["spike_files"][i])
        ndata.load_spike()
        ndata.load_spatial()
        ndata.set_unit_no(int(file_list["unit"][i]))
        num_spikes = ndata.get_unit_spikes_count()
        results.append(num_spikes / ndata.get_duration())


def write(main_dir, df, only_check=True, verbose=False):
    """
    I’ll structure the data we share with you as RAT_NAME/UNIT_NUM/RECORDING_NAME/RAW_DATA unless something else suits you better.
    """
    for row in df.itertuples():
        print(row)
        base_dir = os.path.join(
            main_dir,
            row.RAT.strip(" "),
            row.UNITNUM.replace("#", "UNIT_"),
            row.FileName
        )
        make_dir_if_not_exists(base_dir)

        set_file = row.full_set_file
        pos_file = set_file[:-3] + "pos"
        eeg_file = set_file[:-3] + "eeg"
        cut_file = set_file[:-4] + "_" + row.Tetrode + ".cut"
        txt_file = row.full_spatial_path
        tetrode_file = row.full_spike_file
        all_files = (
            set_file, pos_file, eeg_file, cut_file, txt_file, tetrode_file)
        unit_num = int(row.Unit)

        # Files to merely copy
        for fname in all_files:
            out_name = os.path.join(base_dir, os.path.basename(fname))
            my_copy(fname, out_name, only_check=only_check, verbose=verbose)

        # Files created
        spike_times = get_spike_times(tetrode_file, unit_num)
        time_name = os.path.join(base_dir, row.FileName + ".csv")
        spikes_as_csv = ""
        for spike_time in spike_times:
            spikes_as_csv = "{}, {:.4f}".format(spikes_as_csv, spike_time)
        spikes_as_csv = spikes_as_csv[1:]
        if only_check:
            print("Would write spike times to {}".format(time_name))
        else:
            if verbose:
                print("Writing spike times to {}".format(time_name))
            with open(time_name, "w") as f:
                f.write(spikes_as_csv)


def main(excel_loc, data_dir):
    ndata = NData()
    results = []
    file_list, excel_info = get_files(
        excel_loc, data_dir, write=False)
    write(r"D:\CopyPawel", excel_info, only_check=False, verbose=True)


if __name__ == "__main__":
    excel_loc = r"D:\Pawel\ALL UNITS DATA.xlsx"
    data_dir = r"D:\Pawel\Spatial rel"
    main(excel_loc, data_dir)
