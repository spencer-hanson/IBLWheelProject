import numpy as np
from one.api import ONE
from brainbox.io.one import SessionLoader, SpikeSortingLoader
from ibllib.atlas import AllenAtlas
from brainwidemap import bwm_query, bwm_units
from pathlib import Path
from one.api import ONE


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


def main():
    ONE.setup(base_url='https://openalyx.internationalbrainlab.org', silent=True)
    one = ONE(password='international')

    ba = AllenAtlas()

    ibl_cache = Path.home() / 'Downloads' / 'IBL_Cache'
    ibl_cache.mkdir(exist_ok=True, parents=True)

    df_bw = bwm_query(one)
    unit_df = bwm_units(one)

    pid = '3675290c-8134-4598-b924-83edb7940269'

    # ---------------------------------------------------
    # Convert probe PID to session EID and probe name

    [eid, pname] = one.pid2eid(pid)

    """
    ephysData.raw.meta
    one.list_datasets(eid, collection="alf")
    one.list_datasets(eid, collection=f'alf/{pname}')
    bb = one.load_object(eid, "electrodeSites", collection=f'alf/{pname}')
    ba.regions.id2acronym(gg["brainLocationIds_ccf_2017"])
    """
    
    # ---------------------------------------------------
    # Load spike data
    ssl = SpikeSortingLoader(pid=pid, one=one, atlas=ba)
    spikes, clusters, channels = ssl.load_spike_sorting()
    clusters = ssl.merge_clusters(spikes, clusters, channels)

    # ---------------------------------------------------
    # Restrict to only good clusters
    # Find the good cluster index:
    good_cluster_idx = clusters['label'] == 1
    good_cluster_IDs = clusters['cluster_id'][good_cluster_idx]
    # Filter the clusters accordingly:
    clusters_g = {key: val[good_cluster_idx] for key, val in clusters.items()}
    # Filter the spikes accordingly:
    good_spk_indx = np.where(np.isin(spikes['clusters'], good_cluster_IDs))
    spikes_g = {key: val[good_spk_indx] for key, val in spikes.items()}

    # ---------------------------------------------------
    # N neuronal units in total
    num_neuron = len(np.unique(spikes_g['clusters']))

    # ---------------------------------------------------
    # Load trial data
    sl = SessionLoader(eid=eid, one=one)
    sl.load_trials()
    events = sl.trials['firstMovement_times']

    # If event == NaN, remove the trial from the analysis
    nan_index = np.where(np.isnan(events))[0]
    events = events.drop(index=nan_index).to_numpy()
    contrast_R = sl.trials.contrastRight.drop(index=nan_index).to_numpy()
    contrast_L = sl.trials.contrastLeft.drop(index=nan_index).to_numpy()
    choice = sl.trials.choice.drop(index=nan_index).to_numpy()
    block = sl.trials.probabilityLeft.drop(index=nan_index).to_numpy()

    # N trial count
    num_trial = len(events)

    # Find "trials" that go in one direction and the other direction
    # Note: This is not a pure indexing on the *task trials* as we removed trials with nan values previously
    indx_choice_a = np.where(choice == -1)[0]
    indx_choice_b = np.where(choice == 1)[0]

    # ---------------------------------------------------
    # Load wheel data
    wheel = one.load_object(eid, 'wheel', collection='alf')
    # speed = velocity(wheel.timestamps, wheel.position)
    tw = 2


if __name__ == "__main__":
    main()

tw = 2

