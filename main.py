import json
import os.path
import pickle

import numpy as np
from one.api import ONE
from brainbox.io.one import SessionLoader, SpikeSortingLoader
from ibllib.atlas import AllenAtlas
from brainwidemap import bwm_query, bwm_units
from pathlib import Path
from one.api import ONE

ALL_REGIONS = {
    "superficial": ["SCs", "SCop", "SCsg", "SCzo"],  # Superficial
    "deep": ["SCm", "SCdg", "SCdw", "SCiw", "SCig", "SCig-a", "SCig-b", "SCig-c"],  # Intermediate/Deep]
    "snr": ["SNr", "csc"]  # SNr
}
REGION_NOT_DEFINED = "not_defined"


def region_lookup(region):
    for k, v in ALL_REGIONS.items():
        if region in v:
            return k
    return REGION_NOT_DEFINED


def get_dataset_metadata(one, dataset_tag):
    all_tags_meta = one.alyx.rest('tags', 'list')
    dataset_metadata = None
    all_tags = []
    for tagdata in all_tags_meta:
        if tagdata["name"] == dataset_tag:
            dataset_metadata = tagdata
        all_tags.append(tagdata["name"])

    if dataset_metadata is None:
        raise ValueError(f"Could not find dataset tag '{dataset_tag}'! Available tags '{all_tags}'")
    return dataset_metadata


def brainregion_check(one, ba: AllenAtlas, pid: str):
    # Ensure that this probe recording is from the brain regions we're interested in

    # Convert PID (probe id) to session EID (experiment id) and probe name
    [eid, pname] = one.pid2eid(pid)

    # alfdata = one.list_datasets(eid, collection="alf")
    # alfprobedata = one.list_datasets(eid, collection=f'alf/{pname}')
    electrode_data = one.load_object(eid, "electrodeSites", collection=f'alf/{pname}')
    region_ids = electrode_data["brainLocationIds_ccf_2017"]
    region_acronyms = ba.regions.id2acronym(region_ids)

    passes = False
    # region_setlist = set(region_acronyms)
    relevant_regions = set()
    for acronym in region_acronyms:
        result = region_lookup(acronym)
        if result != REGION_NOT_DEFINED:
            relevant_regions.add(result)
            passes = True

    if passes:
        return {
            "region_by_electrode": list(region_acronyms),
            "relevant_region_labels": list(relevant_regions),
            "probe_id": pid,
            "experiment_id": eid
        }
    else:
        return False


def download_session_data(one, ba):
    filename = "passing-sessions.json"
    if os.path.exists(filename):
        fp = open(filename, "r")
        data = json.load(fp)
        return data

    df_bw = bwm_query(one)
    all_pids = df_bw["pid"]  # All probe ids in this experiment

    results = []
    for idx, pid in enumerate(all_pids):
        print(f"Checking out pid ({idx} / {len(all_pids)})'{pid}'..", end="")
        result = brainregion_check(one, ba, pid)
        if result:
            results.append(result)
            print(" pass")
        else:
            print(" fail")

    fp = open(filename, "w")
    json.dump(results, fp)
    fp.close()
    return results


def load_spike_data(eid, pid, one, ba):
    print(" preparing spikesorter..", end="")
    ssl = SpikeSortingLoader(pid=pid, one=one, atlas=ba)
    spikes, clusters, channels = ssl.load_spike_sorting()
    clusters = ssl.merge_clusters(spikes, clusters, channels)
    num_good_units = np.where(clusters["label"] == 1)[0]

    unitdata = []
    num_units = len(clusters["cluster_id"])

    keys_to_check = []
    for k, v in clusters.items():
        if isinstance(v, np.ndarray):
            if len(v) == num_units:  # Attribute is indexed by unit, want to include
                keys_to_check.append(k)

    print(" adding units..", end="")
    for uidx in range(num_units):
        unit = {}
        for k in keys_to_check:
            unit[k] = clusters[k].tolist()[uidx]
        unit["probe_id"] = pid
        unit["experiment_id"] = eid
        unitdata.append(unit)

    print(" adding spikes..", end="")
    spike_keys = ["amps", "clusters", "depths", "times"]
    spikedata = {}
    for k in spike_keys:
        spikedata[k] = list(spikes[k])

    spikedata["probe_id"] = pid
    spikedata["experiment_id"] = eid

    return unitdata, spikedata


def get_spike_data(pid):
    with open(f"{pid}-spikes.pickle", "rb") as f:
        return pickle.load(f)


def download_unit_and_spike_data(one, ba, relevant_datas):
    filename = "all-units.pickle"
    if os.path.exists(filename):
        with open(filename, "rb") as f:
            data = pickle.load(f)
        return data  # Comment me out if not generated

    all_units = []
    for i, data in enumerate(relevant_datas):
        print(f"Processing ({i}/{len(relevant_datas)})", end="")
        eid = data["experiment_id"]
        pid = data["probe_id"]
        unitdata, spikedata = load_spike_data(eid, pid, one, ba)
        all_units.extend(unitdata)
        print(" dumping spikedata..")
        with open(f"{pid}-spikes.pickle", "wb") as f:
            pickle.dump(spikedata, f, protocol=pickle.HIGHEST_PROTOCOL)

        print("")

    with open(filename, "wb") as f:
        pickle.dump(all_units, f, protocol=pickle.HIGHEST_PROTOCOL)

    return all_units


def download_trial_data(one, all_session_datas):
    trials = []
    for sess in all_session_datas:
        trials.append(get_trial_data(one, sess["experiment_id"]))
    return trials


def get_trial_data(one, eid):
    filename = f"{eid}-trials.pickle"
    if os.path.exists(filename):
        with open(filename, "rb") as f:
            return pickle.load(f)

    sl = SessionLoader(eid=eid, one=one)
    sl.load_trials()
    eventdata = {}

    for k in list(sl.trials):
        eventdata[k] = list(sl.trials[k])

    with open(filename, "wb") as f:
        pickle.dump(eventdata, f)

    return eventdata


def main():
    # Download https://github.com/int-brain-lab/paper-brain-wide-map/tree/main
    ONE.setup(base_url='https://openalyx.internationalbrainlab.org', silent=True)
    one = ONE(password='international')

    ba = AllenAtlas()

    ibl_cache = Path.home() / 'Downloads' / 'IBL_Cache'
    ibl_cache.mkdir(exist_ok=True, parents=True)

    df_bw = bwm_query(one)
    unit_df = bwm_units(one)

    all_session_data = download_session_data(one, ba)
    all_trial_data = download_trial_data(one, all_session_data)
    sess = all_session_data[0]

    spikedata = get_spike_data(sess["probe_id"])
    trialdata = get_trial_data(one, sess["experiment_id"])

    tw = 2
    # 96/699 experiments match brain region criteria
    #

    # """
    #
    # ephysData.raw.meta
    # one.list_datasets(eid, collection="alf")
    # one.list_datasets(eid, collection=f'alf/{pname}')
    # bb = one.load_object(eid, "electrodeSites", collection=f'alf/{pname}')
    # ba.regions.id2acronym(gg["brainLocationIds_ccf_2017"])
    # """
    #
    # # ---------------------------------------------------
    # # Load spike data
    # ssl = SpikeSortingLoader(pid=pid, one=one, atlas=ba)
    # spikes, clusters, channels = ssl.load_spike_sorting()
    # clusters = ssl.merge_clusters(spikes, clusters, channels)
    #
    # import matplotlib.pyplot as plt
    # import matplotlib
    #
    # matplotlib.use('TkAgg')
    # x = channels["x"]
    # y = channels["y"]
    # z = channels["z"]
    #
    # fig = plt.figure()
    # ax = fig.add_subplot(projection='3d')
    #
    # ax.scatter(x, y, z)
    # plt.show()
    # tw = 2
    #
    # # ---------------------------------------------------
    # # Restrict to only good clusters
    # # Find the good cluster index:
    # good_cluster_idx = clusters['label'] == 1
    # good_cluster_IDs = clusters['cluster_id'][good_cluster_idx]
    # # Filter the clusters accordingly:
    # clusters_g = {key: val[good_cluster_idx] for key, val in clusters.items()}
    # # Filter the spikes accordingly:
    # good_spk_indx = np.where(np.isin(spikes['clusters'], good_cluster_IDs))
    # spikes_g = {key: val[good_spk_indx] for key, val in spikes.items()}
    #
    # # ---------------------------------------------------
    # # N neuronal units in total
    # num_neuron = len(np.unique(spikes_g['clusters']))
    #
    # # ---------------------------------------------------
    # # Load trial data
    # sl = SessionLoader(eid=eid, one=one)
    # sl.load_trials()
    # events = sl.trials['firstMovement_times']
    #
    # # If event == NaN, remove the trial from the analysis
    # nan_index = np.where(np.isnan(events))[0]
    # events = events.drop(index=nan_index).to_numpy()
    # contrast_R = sl.trials.contrastRight.drop(index=nan_index).to_numpy()
    # contrast_L = sl.trials.contrastLeft.drop(index=nan_index).to_numpy()
    # choice = sl.trials.choice.drop(index=nan_index).to_numpy()
    # block = sl.trials.probabilityLeft.drop(index=nan_index).to_numpy()
    #
    # # N trial count
    # num_trial = len(events)
    #
    # # Find "trials" that go in one direction and the other direction
    # # Note: This is not a pure indexing on the *task trials* as we removed trials with nan values previously
    # indx_choice_a = np.where(choice == -1)[0]
    # indx_choice_b = np.where(choice == 1)[0]
    #
    # # ---------------------------------------------------
    # # Load wheel data
    # wheel = one.load_object(eid, 'wheel', collection='alf')
    # # speed = velocity(wheel.timestamps, wheel.position)
    # tw = 2


if __name__ == "__main__":
    main()

tw = 2

