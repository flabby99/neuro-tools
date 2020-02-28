from neurochat.nc_data import NData
from get_files_from_list import main as get_files


def main(excel_loc, data_dir):
    ndata = NData()
    results = []
    file_list = get_files(excel_loc, data_dir)
    for i in range(len(file_list["set_files"])):
        print("Working on {}: {}".format(i, file_list["set_files"][i]))
        ndata.set_spatial_file(file_list["txt_files"][i])
        ndata.set_spike_file(file_list["spike_files"][i])
        ndata.load_spike()
        ndata.load_spatial()
        ndata.set_unit_no(int(file_list["unit"][i]))
        num_spikes = ndata.get_unit_spikes_count()
        results.append(num_spikes / ndata.get_duration())
        print("Frequency: {:.4f}".format(num_spikes / ndata.get_duration()))
    with open("freq.txt", "w") as f:
        for val in results:
            f.write("{:.4f}\n".format(val))

if __name__ == "__main__":
    excel_loc = r"E:\Pawel\ALL UNITS DATA.xlsx"
    data_dir = r"E:\Pawel\PTN -border UNITS Literature\UNITS Recordings for Paper\Spatial rel"
    main(excel_loc, data_dir)
