# Setup here
total_nb_channels = 64
radius = 100
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
    for j, c in enumerate(chans):
        geometry[c] = [i * 2 * radius, j*y]
    channel_groups[i] = {
        'channels': chans,
        'graph': [],
        'geometry': geometry}
print(channel_groups)
