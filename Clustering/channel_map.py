def write_prb_file(
        nchans=64, radius=1, y=1, num_tetrodes=16, 
        tetrodes_to_use=[], out_loc="channel_map.prb",
        num_chans_for_clust=4):
    """
    Write a .prb file for use with sorters.

    if tetrodes_to_use is [], uses all tetrodes.
    if out_loc is default, saves to channel_map.prb
    in the folder that the code is run from.

    """
    if tetrodes_to_use == []:
        tetrodes_to_use = [j+1 for j in range(num_tetrodes+1)]

    # Actual code here
    channel_groups = {}
    for i in range(num_tetrodes):
        # Skip tetrodes which should not be clustered
        if not i + 1 in tetrodes_to_use:
            continue
        start = i*4
        chans = [j for j in range(start, start + num_chans_for_clust)]
        geometry = {}
        label_letters = ["a", "b", "c", "d"]
        label = [str(i+1) + label_letters[k] for k in range(num_chans_for_clust)]
        graph = []
        for j, c in enumerate(chans):
            geometry[c] = [i * 2 * radius, j*y]
        for j in range(len(chans)):
            for k in range(j+1, len(chans)):
                graph.append((chans[j], chans[k]))
        channel_groups[i] = {
            'channels': chans,
            'geometry': geometry,
            'label': label,
            'graph': graph}

    with open(out_loc, "w") as f:
        f.write("channel_groups = {\n")
        for k, v in channel_groups.items():
            f.write("\t{}:\n".format(k))
            f.write("\t\t{\n")
            for k2, v2 in v.items():
                f.write("\t\t \'{}\': {},\n".format(k2, v2))
            f.write("\t\t},\n")
        f.write("\n\t}")

if __name__ == "__main__":
    write_prb_file(
        tetrodes_to_use=[], num_chans_for_clust=3, radius=1)
