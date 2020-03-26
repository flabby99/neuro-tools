import os

def make_folder_structure(main_dir, out_folder="results_klusta"):
    dirs = []
    for i in range(16):
        to_create = os.path.join(main_dir, out_folder, str(i)) 
        dirs.append(to_create)
        os.makedirs(to_create, exist_ok=True)
    return dirs

if __name__ == "__main__":
    loc = r"D:\Ham\Batch_3\A13_CAR-SA5\CAR-SA5_20200212_PreBox"
    make_folder_structure(loc, "test")