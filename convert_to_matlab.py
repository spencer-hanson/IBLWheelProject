import pickle
import os

import numpy as np
import scipy


def convert_to_matlab(filename, output_filename):
    try:
        with open(filename, "rb") as f:
            print(f"Converting '{filename}' to '{output_filename}'")
            pkl = pickle.load(f)
            if filename == "all-units.pickle":
                all_units_dict = {}
                for key in pkl[0].keys():
                    if key not in all_units_dict:
                        all_units_dict[key] = []
                    for item in pkl:
                        all_units_dict[key].append(item[key])
                scipy.io.savemat(output_filename, all_units_dict)
            else:
                scipy.io.savemat(output_filename, pkl)
    except Exception as e:
        raise e
        with open(f"{output_filename}-error.txt", "w") as f2:
            f2.write(str(e))
        print(f"Error! Skipping '{str(e)}'")


def main():
    output_folder = "D:\\SpencerProcessedWheelData"
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)

    for filename in os.listdir():
        if filename.endswith(".pickle"):
            if filename.endswith("-spikes.pickle"):
                save_fn = "spikes-" + filename[:-len("-spikes.pickle")] + ".pickle"
            elif filename.startswith("trials-"):
                save_fn = filename
            else:
                save_fn = filename
            save_fn = save_fn[:-len(".pickle")] + ".mat"

            save_path = os.path.join(output_folder, save_fn)
            if os.path.exists(save_path):
                print(f"File '{save_path}' already exists, skipping..")
            else:
                convert_to_matlab(filename, save_path)

    tw = 2


if __name__ == "__main__":
    main()

