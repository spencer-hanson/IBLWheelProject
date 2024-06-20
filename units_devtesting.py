import pickle
from main import ALL_REGIONS

all_regions = []
region_counts = {}
for k, v in ALL_REGIONS.items():
    all_regions.extend(v)

for r in all_regions:
    region_counts[r] = 0

with open("all-units.pickle", "rb") as f:
    data = pickle.load(f)

count = 0
for d in data:
    if d["acronym"] in all_regions and d["label"] == 1:
        count = count + 1
        region_counts[d["acronym"]] += 1

print(count)
print(region_counts)
tw = 2

