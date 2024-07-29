import pickle
import os
import scipy


def convert_to_matlab(filename, output_filename):
    print(f"Converting '{filename}' to '{output_filename}'")
    with open(filename, "rb") as f:
        pkl = pickle.load(f)
        scipy.io.savemat(output_filename, pkl)


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

            if os.path.exists(save_fn):
                print(f"File '{save_fn}' already exists, skipping..")
            else:
                convert_to_matlab(filename, os.path.join(output_folder, save_fn))

    tw = 2


if __name__ == "__main__":
    main()

