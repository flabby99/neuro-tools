import os 
from configparser import ConfigParser

from run_spike_interface import main_cfg
from path_utils import get_all_files_in_dir

def main(location, default_config):
    out_dir = default_config.get("path", "out_foldername")
    sort_method = default_config.get("sorting", "sort_method")

    if out_dir == "default":
        out_folder = "results_" + sort_method
        phy_out_folder = "phy_" + sort_method

    set_files = get_all_files_in_dir(
        location, recursive=True, ext=".set", case_sensitive_ext=True)
    with open(os.path.join(location, "output_log_batchclust.txt"), "w") as f:
        for set_file in set_files:
            set_dir = os.path.dirname(set_file)
            ac_out_folder = os.path.join(set_dir, out_folder)
            ac_phy_folder = os.path.join(set_dir, out_folder)
            if os.path.isdir(ac_out_folder) and os.path.isdir(ac_phy_folder):
                f.write("Skipping {} as already clustered\n".format(set_file))
            elif not os.path.isfile(set_file[:-4] + ".bin"):
                f.write("Skipping {} as no binary file available\n")
            else:
                f.write("Clustering {}\n".format(set_file))
                default_config.set("path", "in_dir", set_dir)
                default_config.set(
                    "path", "set_fname", os.path.basename(set_file))
                main_cfg(default_config)

if __name__ == "__main__":
    location = r"G:\Ham\A1"
    here = os.path.dirname(os.path.abspath(__file__))
    config_loc = os.path.join(here, "configs", "default_config.cfg")
    default_config = ConfigParser()
    default_config.read(config_loc)
    main(location, default_config)