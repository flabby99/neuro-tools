# Setup here
total_nb_channels = 64
radius = 1
y = 1
num_tetrodes = 16
tetrodes_to_use = []
if tetrodes_to_use == []:
    tetrodes_to_use = [j+1 for j in range(num_tetrodes+1)]
num_chans_for_clust = 3

# Actual code here
channel_groups = {}
for i in range(num_tetrodes):
    # Skip tetrodes which should not be clustered
    if not i + 1 in tetrodes_to_use:
        continue
    start = i*4 + 1
    chans = [j for j in range(start, start + num_chans_for_clust)]
    geometry = {}
    label_letters = ["a", "b", "c", "d"]
    label = [str(i+1) + label_letters[k] for k in range(num_chans_for_clust)]
    for j, c in enumerate(chans):
        geometry[c] = [i * 2 * radius, j*y]
    channel_groups[i] = {
        'channels': chans,
        'geometry': geometry,
        'label': label}

with open("channel_map.prb", "w") as f:
    f.write("channel_groups = {\n")
    for k, v in channel_groups.items():
        f.write("\t{}:\n".format(k))
        f.write("\t\t{\n")
        for k2, v2 in v.items():
            f.write("\t\t \'{}\': {},\n".format(k2, v2))
        f.write("\t\t},\n")
    f.write("\n\t}")
