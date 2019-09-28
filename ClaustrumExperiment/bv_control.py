"""Control script for MEDPC behaviour analysis."""
import os
import math
import numpy as np
import pandas as pd
import seaborn as sns
from bvmpc.bv_parse_sessions import SessionExtractor, Session
import bvmpc.bv_analyse as bv_an
from bvmpc.bv_utils import make_dir_if_not_exists, print_h5, mycolors, daterange, split_list
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from adjustText import adjust_text
from scipy import interpolate
from datetime import date, timedelta


def plot_raster_trials(trial_df, sub, date, start_dir, align_rw=True):
    out_dir = os.path.join(start_dir, "Plots")

    norm_lever = []
    norm_err = []
    norm_dr = []
    norm_pell = []
    norm_rw = []
    schedule_type = []
    
    # Extract data from pandas_df
    norm_lever[:] = trial_df['Levers (ts)']
    norm_err[:] = trial_df['Err (ts)']
    norm_dr[:] = trial_df['D_Pellet (ts)']
    norm_pell[:] = trial_df['Pellet (ts)']
    norm_rw[:] = trial_df['Reward (ts)']
    schedule_type[:] = trial_df['Schedule']
        
    color = []  
    if align_rw:       
        for i, _ in enumerate(norm_rw):
            norm_lever[i] -= norm_rw[i]
            norm_err[i] -= norm_rw[i]
            norm_dr[i] -= norm_rw[i]
            norm_pell[i] -= norm_rw[i]
            norm_rw[i] -= norm_rw[i]
            if schedule_type[i] == 'FR':
                color.append('black')
            elif schedule_type[i] == 'FI':
                color.append('b')

    # Figure Details
    rows, cols = [2, 4]
    size_multiplier = 5
    fig = plt.figure(
        figsize=(cols * size_multiplier, rows * size_multiplier),
        tight_layout=False)
    gs = gridspec.GridSpec(rows, cols, wspace=0.2, hspace=0.3)
    ax = fig.add_subplot(gs[:, :])
    out_name = "Raster_" + date + '_'+ sub

    # Plotting of raster
    plt.eventplot(norm_lever[:], color=color)
    plt.eventplot(norm_err[:], color='red', label='Errors')
    plt.eventplot(norm_dr[:], color='pink', label='Double Reward')
    
    # Figure labels
    if align_rw:       
        plot_name = 'Reward-Aligned'
        plt.axvline(0, linestyle='-', color='k', linewidth='.5')
        ax.set_xlabel('Time (s)', fontsize=20)
        ax.set_ylabel('Trials', fontsize=20)

    ax.set_title('\nSubject {} Raster ({})'.format(sub, plot_name), y=1.05, fontsize=25, color=mycolors(sub))
    out_name += ".png"
    print("Saved figure to {}".format(
        os.path.join(out_dir, out_name)))
    fig.savefig(os.path.join(out_dir, out_name), dpi=400)
    plt.close()

def struc_session(d_list, sub_list, in_dir):
    """ Structure sessions into a pandas dataframe based on trials"""
    out_dir = os.path.join(start_dir, "pandas")
    in_dir = os.path.join(start_dir, "hdf5")
    d_list, s_list, sub_list = [['09-17'], ['7'], ['3']]
    s_grp = extract_hdf5s(in_dir, out_dir, sub_list, s_list, d_list)
    
    for s in s_grp:
        subject = s.get_metadata('subject')
        date = s.get_metadata("start_date").replace("/", "-")[:5]
        session_type = s.get_metadata('name')
        stage = session_type[:2].replace('_', '')  # Obtain stage number w/o _
        timestamps = s.get_arrays()
        pell_ts = timestamps["Reward"]
        dpell_bool = np.diff(pell_ts) < 0.5
        # Provides index of double pell in pell_ts
        dpell_idx = np.nonzero(dpell_bool)[0] + 1
        dpell = pell_ts[dpell_idx]

        # pell drop ts excluding double ts
        pell_ts_exdouble = np.delete(pell_ts, dpell_idx)
        reward_times = timestamps["Nosepoke"]
        schedule_type = []

        grp_session_df = []
        grp_trial_df = []
        df_sub = []
        df_date = []

        if stage == '7':
            # Check if trial switched before reward collection -> Adds collection as switch time
            blocks = np.arange(5, 1830, 305)
            last_pell_ts = pell_ts_exdouble[np.searchsorted(
                pell_ts_exdouble, blocks)]
            last_reward_ts = reward_times[np.searchsorted(
                reward_times, blocks)]

            for i, (pell, reward) in enumerate(zip(last_pell_ts, last_reward_ts)):
                if pell > reward:
                    np.insert(reward_times, np.searchsorted(
                        reward_times, blocks)[i], blocks[i])

            norm_r_ts, _, _, _, _ = bv_an.split_sess(
                s, norm=False, plot_all=True)
            sch_type = s.get_arrays('Trial Type')

            for i, block in enumerate(norm_r_ts):
                if sch_type[i] == 1:
                    b_type = 'FR'
                elif sch_type[i] == 0:
                    b_type = 'FI'
                for l, _ in enumerate(block):
                    schedule_type.append(b_type)

        # rearrange lever timestamps based on trial per row
        lever_ts = s.get_lever_ts(True)
        err_ts = s.get_err_lever_ts(True)
        trial_lever_ts = np.split(lever_ts,(np.searchsorted(lever_ts, reward_times)[:-1]))
        trial_err_ts = np.split(err_ts,(np.searchsorted(err_ts, reward_times)[:-1])) 
        trial_dr_ts = np.split(dpell,(np.searchsorted(dpell, reward_times)[:-1])) 

        # Initialize array for lever timestamps
        trials_max_l = len(max(trial_lever_ts, key=len))  # Max lever press per trial
        lever_arr = np.empty((len(reward_times), trials_max_l,))
        lever_arr.fill(np.nan)
        trials_max_err = len(max(trial_err_ts, key=len))  # Max err press per trial
        err_arr = np.empty((len(reward_times), trials_max_err,))
        err_arr.fill(np.nan)
        
        # Arrays used for normalization of timestamps to trials
        trial_norm = np.insert(reward_times, 0, 0)
        norm_lever = np.copy(trial_lever_ts)
        norm_err = np.copy(trial_err_ts)
        norm_dr = np.copy(trial_dr_ts)
        norm_rw = np.copy(reward_times)
        norm_pell = np.copy(pell_ts_exdouble)

        # Normalize timestamps based on start of trial
        for i, _ in enumerate(norm_rw):
            norm_lever[i] -= trial_norm[i]
            norm_err[i] -= trial_norm[i]
            norm_dr[i] -= trial_norm[i]
            norm_pell[i] -= trial_norm[i]
            norm_rw[i] -= trial_norm[i]

        # 2D array of lever timestamps
        for i, (l, err) in enumerate(zip(trial_lever_ts, trial_err_ts)):
            l_end = len(l)
            lever_arr[i,:l_end] = l[:]
            err_end = len(err)
            err_arr[i,:err_end] = err[:]

    session_dict = {
            'Reward (ts)': reward_times,
            'Pellet (ts)': pell_ts_exdouble,
            'D_Pellet (ts)': trial_dr_ts,
            'Schedule': schedule_type,
            'Levers (ts)': trial_lever_ts,
            'Err (ts)': trial_err_ts
        }
    trial_dict = {
            'Reward (ts)': norm_rw,
            'Pellet (ts)': norm_pell,
            'D_Pellet (ts)': norm_dr,
            'Schedule': schedule_type,
            'Levers (ts)': norm_lever,
            'Err (ts)': norm_err
        }

    session_df = pd.DataFrame(session_dict)
    trial_df = pd.DataFrame(trial_dict)
    grp_session_df.append(session_df)
    grp_trial_df.append(trial_df)
    df_sub.append(subject)
    df_date.append(date)

    return grp_session_df, grp_trial_df, df_sub, df_date


def compare_variables():
    """ Temporary Function to plot difference between errors"""
    # Only works for stage 7
    start_dir = r"F:\PhD (Shane O'Mara)\Operant Data\IR Discrimination Pilot 1"
    # start_dir = r"G:\!Operant Data\Ham"
    in_dir = os.path.join(start_dir, "hdf5")
    out_dir = os.path.join(start_dir, "Plots")
    sub_list = ['1', '2', '3', '4']
    s_list = ['7']
    grpA_d_list = ['08-10', '08-11', '08-12']
    grpB_d_list = ['08-17', '08-18', '08-19']
    grpC_d_list = ['09-15', '09-16', '09-17']

    s_grpA = extract_hdf5s(in_dir, out_dir, sub_list, s_list, grpA_d_list)
    s_grpB = extract_hdf5s(in_dir, out_dir, sub_list, s_list, grpB_d_list)
    s_grpC = extract_hdf5s(in_dir, out_dir, sub_list, s_list, grpC_d_list)
    s_grpA.pop()
    s_grpA.pop(-4)
    s_grpA.pop(-7)
    s_grpA.pop(-10)
    s_grps = [s_grpA, s_grpB, s_grpC]
    FR_means = []
    FI_means = []
    FR_stds = []
    FI_stds = []

    for s in s_grps:
        grp_FRerr, grp_FIerr = grp_errors(s)
        FRerr_arr = np.array(grp_FRerr)
        FIerr_arr = np.array(grp_FIerr)
        FR_mean = np.mean(FRerr_arr, axis=0)
        FI_mean = np.mean(FIerr_arr, axis=0)
        FR_means.append(FR_mean)
        FI_means.append(FI_mean)
        FR_std = np.std(FRerr_arr, axis=0)
        FI_std = np.std(FIerr_arr, axis=0)
        FR_stds.append(FR_std)
        FI_stds.append(FI_std)

    # x_label = ['FR6_noDP-Ratio', 'FR6_NoDP-Int', 'FR8-Ratio',
    #            'FR8-Int', 'FR18-Ratio', 'FR18-Int']
    ratio_c = plt.cm.get_cmap('Wistia')
    interval_c = plt.cm.get_cmap('winter')

    _, ax = plt.subplots()
    ind = np.arange(len(FR_means))  # the x locations for the groups
    width = 0.35  # the width of the bars
    ax.bar(ind - width/2, FR_means, width,
           yerr=FR_stds, label='FR', color=ratio_c(10*45), align='center')
    ax.bar(ind + width/2, FI_means, width,
           yerr=FI_stds, label='FI', color=interval_c(4*45), align='center')
    # ax.bar(ind - width/2, np.mean(err_arr, axis=1), tick_label=x_label,
    #        yerr=np.std(err_arr, axis=1), align='center',
    #        alpha=0.5, ecolor='black', capsize=10)
    ax.set_xticks(ind)
    ax.set_xticklabels(('FR6_noDP', 'FR8', 'FR18'))
    ax.set_ylabel('Error Presses')
    ax.set_xlabel('Sessions-Type')
    ax.set_title('Errors Comparison')
    ax.legend()
    plt.show()


def grp_errors(s_grp):
    grp_FRerr = []
    grp_FIerr = []
    for i, s in enumerate(s_grp):
        # timestamps = s.get_arrays()
        # pell_ts = timestamps["Reward"]
        # c_ratio = 'R' + str(int(timestamps["Experiment Variables"][3]))
        # c_interval = 'I' + \
        #     str(int(timestamps["Experiment Variables"][5] / 100))
        err_FI = 0
        err_FR = 0
        _, _, norm_err_ts, _, _ = bv_an.split_sess(
            s, plot_all=True)
        sch_type = s.get_arrays('Trial Type')
        for i, _ in enumerate(norm_err_ts):
            if sch_type[i] == 1:
                err_FR = err_FR + len(norm_err_ts[i])
            elif sch_type[i] == 0:
                err_FI = err_FI + len(norm_err_ts[i])
        grp_FRerr.append(err_FR)
        grp_FIerr.append(err_FI)
    return grp_FRerr, grp_FIerr


def plot_batch_sessions():
    # Folder details
    start_dir = r"F:\PhD (Shane O'Mara)\Operant Data\IR Discrimination Pilot 1"
    in_dir = os.path.join(start_dir, "hdf5")
    
    # Parameters for specifying session
    # sub_list = ['1', '2']
    sub = ['3', '4']
    # sub_list = ['6']
    # sub_list = ['1', '2', '3', '4']
    # sub_list = ['5', '6']
    
    # start_date = date(2019, 7, 15)  # date(year, mth, day)
    # start_date = date(2019, 8, 30)  # date(year, mth, day)
    start_date = date.today() - timedelta(days=1)
    end_date = date.today()
    # end_date = date(2019, 8, 28)

    for single_date in daterange(start_date, end_date):
        d = [single_date.isoformat()[-5:]]

        # Quick control of plotting
        timeline, summary, raster = [0, 0, 1]

        if raster:
            grp_session_df, grp_trial_df, df_sub, df_date = struc_session(
                d, sub, in_dir)
            for i, t_df in enumerate(grp_trial_df):
                plot_raster_trials(t_df, df_sub[i], df_date[i], start_dir)




        # plot cumulative response graphs
        if summary == 1:
            # plot_sessions(d, sub, summary=True, single=True,
            #               corr_only=True)  # Single animal breakdown
            # Group with corr_only breakdown
            plot_sessions(d, sub, summary=True, single=False, corr_only=True)
            # plot_sessions(d, sub, summary=True, single=False, corr_only=False)  # Group with complete breakdown

        # plot all 4 timeline types
        if timeline == 1:
            single = False  # plots seperate graphs for each animal if True
            show_date = True  # Sets x-axis as dates if True
            # plot_sessions(d, sub timeline=True, single=single, details=True, recent=True,
            #               show_date=show_date)  # Timeline_recent_details
            # plot_sessions(d, sub timeline=True, single=single, details=True, det_err=True, det_corr=False, recent=True,
            #               show_date=show_date)  # Timeline_recent_details_Err **Need to fix with ax.remove() instead**
            # plot_sessions(d, sub, timeline=True, single=single, details=True, det_err=False, det_corr=True, recent=True,
            #               show_date=show_date)  # Timeline_recent_details_Corr **Need to fix with ax.remove() instead**
            plot_sessions(d, sub, timeline=True, single=single, details=True, det_err=True, det_corr=False,
                          show_date=show_date)  # Timeline_recent_details_Err
            plot_sessions(d, sub, timeline=True, single=single, details=True, det_err=False, det_corr=True,
                          show_date=show_date)  # Timeline_recent_details_Corr
            plot_sessions(d, sub, timeline=True, single=single, details=True,
                          recent=False, show_date=show_date)  # Timeline_details
            plot_sessions(d, sub, timeline=True, single=single, details=False,
                          recent=True, show_date=show_date)  # Timeline_recent
            plot_sessions(d, sub, timeline=True, single=single, details=False,
                          recent=False, show_date=show_date)  # Timeline

    # # Multiple dates in single plot; Doesnt work yet
    # d = []
    # for single_date in daterange(start_date, end_date):
    #     d.append(single_date.isoformat()[-5:])
    # print(d)
    # plot_sessions(d)


def plot_sessions(d_list, sub_list, summary=False, single=False, timeline=False,
                  details=False, det_err=False, det_corr=False, recent=False, show_date=False,
                  int_only=False, corr_only=False):
    ''' Plots session summaries
    summary = True: Plots all sessions in a single plot, up to 6
    single = True: Plots single session summaries with breakdown of single blocks
    Timeline = True: Plots total rewards from beginining of first session
    int_only = True: Plots only interval trials in zoomed schedule plot
    corr_only = True: Plots seperate summary plot with correct only trials
    '''
    s_list = ['4', '5a', '5b', '6', '7']

    start_dir = r"F:\PhD (Shane O'Mara)\Operant Data\IR Discrimination Pilot 1"
    # start_dir = r"G:\!Operant Data\Ham"
    in_dir = os.path.join(start_dir, "hdf5")
    out_dir = os.path.join(start_dir, "Plots")
    make_dir_if_not_exists(out_dir)

    if summary and not corr_only:
        #  extracts hdf5 session based on specification
        max_plot = 4  # Set max plots per figure
        s_grp = extract_hdf5s(in_dir, out_dir, sub_list, s_list, d_list)
        if s_grp == []:
            return print("***No Files Extracted***")
        idx = 0
        if len(s_grp) > max_plot:
            j = 0
            s_grp_split = []
            s_grp_idx = np.arange(len(s_grp))
            for i in s_grp_idx[max_plot-1::max_plot]:
                s_grp_split.append(s_grp[j:i+1])
                j = i+1

            mv = len(s_grp) % max_plot
            if mv != 0:
                s_grp_split.append(s_grp[-mv:])
            for s_grp in s_grp_split:
                idx += 1
                sum_plot(s_grp, idx, out_dir)
        else:
            sum_plot(s_grp, idx, out_dir)

    if summary and corr_only:
        # plots corr_only plots
        max_plot = 4  # Set max plots per figure
        s_grp = extract_hdf5s(in_dir, out_dir, sub_list, s_list, d_list)
        if s_grp == []:
            return print("***No Files Extracted***")

        idx = 0
        if len(s_grp) > max_plot:
            j = 0
            s_grp_split = []
            s_grp_idx = np.arange(len(s_grp))
            for i in s_grp_idx[max_plot-1::max_plot]:
                s_grp_split.append(s_grp[j:i+1])
                j = i+1

            mv = len(s_grp) % max_plot
            if mv != 0:
                s_grp_split.append(s_grp[-mv:])
            for s_grp in s_grp_split:
                idx += 1
                sum_plot(s_grp, idx, out_dir, corr_only=True)
        else:
            sum_plot(s_grp, idx, out_dir, corr_only=True)

    if single and summary:
        # Single Subject Plots
        idx = 0
        for sub in sub_list:
            s_grp = extract_hdf5s(in_dir, out_dir, sub, s_list, d_list)
            if s_grp == []:
                return print("***No Files Extracted***")
            s_passed = []
            d_passed = []
            for s in s_grp:
                stage = s.get_metadata('name')[:2].replace('_', '')
                s_passed.append(stage)
                date = s.get_metadata("start_date").replace("/", "-")
                d_passed.append(date[:5])
                subject = s.get_metadata('subject')
            if '7' in s_passed:
                size_multiplier = 5
                rows, cols = [len(s_grp), 4]
                fig = plt.figure(
                    figsize=(cols * size_multiplier,
                             rows * size_multiplier), tight_layout=True)
                gs = gridspec.GridSpec(rows, cols, wspace=0.3, hspace=0.3)
                if len(s_grp) == 1:
                    fig.tight_layout(rect=[0, 0.03, 0.8, 0.95])
                for i, s in enumerate(s_grp):
                    ax1 = fig.add_subplot(gs[i, 0])
                    bv_an.cumplot(s, out_dir, ax1, int_only,
                                  zoom=False, zoom_sch=False)
                    ax2 = fig.add_subplot(gs[i, 1])
                    bv_an.cumplot(s, out_dir, ax2, int_only, zoom=False, zoom_sch=True,
                                  plot_error=False, plot_all=True)
                    ax3 = fig.add_subplot(gs[i, 2])
                    bv_an.cumplot(s, out_dir, ax3, int_only, zoom=False, zoom_sch=True,
                                  plot_error=False, plot_all=False)
                    ax4 = fig.add_subplot(gs[i, 3])
                    bv_an.cumplot(s, out_dir, ax4, int_only, zoom=False, zoom_sch=True,
                                  plot_error=True, plot_all=False)
                plt.subplots_adjust(top=0.85)
                fig.suptitle(('Subject ' + subject + ' Performance'),
                             color=mycolors(subject), fontsize=30)

                # # Seperate plots w line
                # ax1.hlines(1.13, -0, 4.9, clip_on=False,
                #             transform=ax1.transAxes, linewidth=0.7)
                s_print = np.array_str(np.unique(np.array(s_passed)))
                d_print = np.array_str(np.unique(np.array(d_passed)))
                out_name = "Sum_" + subject + "_" + d_print + "_" + s_print + ".png"
                print("Saved figure to {}".format(
                    os.path.join(out_dir, out_name)))
                fig.savefig(os.path.join(out_dir, out_name), dpi=400)
                plt.close()
            else:
                sum_plot(s_grp, idx, out_dir, single=single)

    if timeline:
        if not single:
            plot_limit = 4
            sub_list = split_list(sub_list, plot_limit)
            for l in sub_list:
                timeline_plot(l, in_dir, out_dir, single_plot=single, det_err=det_err, det_corr=det_corr,
                              recent=recent, show_date=show_date, details=details)
        else:
            # Plots timeline for specified subjects
            timeline_plot(sub_list, in_dir, out_dir, single_plot=single, det_err=det_err, det_corr=det_corr,
                          recent=recent, show_date=show_date, details=details)


def sum_plot(s_grp, idx, out_dir, zoom=True, single=False,
             int_only=False, corr_only=False):
    # Plots summary of day
    if zoom:
        if len(s_grp) > 2:
            cols = 2*math.ceil(len(s_grp)/2)
            rows = 2
        else:
            rows = len(s_grp)
            cols = 2
    else:
        if len(s_grp) > 4:
            rows = math.ceil(len(s_grp)/4)
            cols = 4
        else:
            cols = len(s_grp)
            rows = 1
    size_multiplier = 5
    fig = plt.figure(
        figsize=(cols * size_multiplier, rows * size_multiplier),
        tight_layout=False)
    gs = gridspec.GridSpec(rows, cols, wspace=0.2, hspace=0.3)
    s_passed = []
    d_passed = []

    for i, s in enumerate(s_grp):
        subject = s.get_metadata('subject')
        stage = s.get_metadata('name')[:2].replace('_', '')
        date = s.get_metadata("start_date").replace("/", "-")
        s_passed.append(stage)
        d_passed.append(date[:5])

        if zoom:
            ax1 = fig.add_subplot(gs[(i+2) % 2, int(i/2)*2])
        else:
            ax1 = fig.add_subplot(gs[0, i])

        if corr_only and stage == '7':
            bv_an.cumplot(s, out_dir, ax1, int_only, zoom=False,
                          zoom_sch=False, plot_all=False)
        else:
            bv_an.cumplot(s, out_dir, ax1, int_only, zoom=False,
                          zoom_sch=False)

        if stage == '2' or stage == '3' or stage == '4':
            IRT = True
        elif stage == '5a' or stage == '5b':
            IRT = True  # Change to False for zoomed plot instead of IRT
        else:
            IRT = False

        if IRT:
            ax2 = fig.add_subplot(gs[(i+2) % 2, int(i/2)*2+1])
            bv_an.IRT(s, out_dir, ax2)
        elif zoom:
            ax2 = fig.add_subplot(gs[(i+2) % 2, int(i/2)*2+1])
            if corr_only and stage == '7':
                bv_an.cumplot(s, out_dir, ax2, int_only, zoom=False, zoom_sch=True,
                              plot_error=False, plot_all=False)
            else:
                bv_an.cumplot(s, out_dir, ax2, int_only, zoom=False, zoom_sch=True,
                              plot_error=False, plot_all=True)
        plt.subplots_adjust(top=0.85)
    d_print = np.array_str(np.unique(np.array(d_passed)))
    d_title = np.array2string(np.unique(np.array(d_passed)))
    s_print = np.array_str(np.unique(np.array(s_passed)))

    if single:
        fig.suptitle(('Subject ' + subject + ' Performance'), fontsize=30)
        out_name = "Sum_" + subject + "_" + d_print + "_" + s_print + ".png"
    elif corr_only and stage == '7':
        if idx == 0:
            fig.suptitle(('Summary across animals ' + d_title +
                          '_Correct Only'), fontsize=30)
            out_name = "Sum_" + d_print + "_" + s_print + "_Corr.png"
        else:
            fig.suptitle(('Summary across animals ' + d_title +
                          '_Correct Only' + " p" + str(idx)), fontsize=30)
            out_name = "Sum_" + d_print + "_" + \
                s_print + "_" + str(idx) + "_Corr.png"
    else:
        if idx == 0:
            fig.suptitle(('Summary across animals ' + d_title), fontsize=30)
            out_name = "Sum_" + d_print + "_" + s_print + ".png"
        else:
            fig.suptitle(('Summary across animals ' +
                          d_title + " p" + str(idx)), fontsize=30)
            out_name = "Sum_" + d_print + "_" + \
                s_print + "_" + str(idx) + ".png"
    print("Saved figure to {}".format(
        os.path.join(out_dir, out_name)))
    fig.savefig(os.path.join(out_dir, out_name), dpi=400)
    plt.close()


def timeline_plot(sub_list, in_dir, out_dir, single_plot=False, det_err=False, det_corr=False,
                  recent=False, show_date=True, details=False):
    # Plot size
    rows, cols = [len(sub_list), 4]
    size_multiplier = 5
    fig = plt.figure(
        figsize=(cols * size_multiplier, rows * size_multiplier),
        tight_layout=False)
    gs = gridspec.GridSpec(rows, cols, wspace=0.4, hspace=0.5)
    for c, sub in enumerate(sub_list):
        # Plot total pellets across sessions
        s_grp = extract_hdf5s(in_dir, out_dir, sub)
        s_list = []
        r_list = []
        err_FR_list = []
        err_FI_list = []
        rw_FR_list = []
        rw_FI_list = []
        rw_double_list = []
        changes = []
        stage_change = []
        change_idx = []
        prev_ratio = []
        prev_interval = []
        c_ratio = []
        c_interval = []
        type_list = []
        dpell_change = []
        dpell_old = []
        prev_name = '2'
        d_list = []
        if recent:
            number_sessions_ago = -31  # change value to set number of sessions ago
            s_grp = s_grp[number_sessions_ago:]
        else:
            pass

        for i, s in enumerate(s_grp):
            s_type = s.get_metadata('name')[:2]
            timestamps = s.get_arrays()
            date = s.get_metadata('start_date')[3:5]
            subject = s.get_metadata('subject')
            pell_ts = timestamps["Reward"]
            pell_double = np.nonzero(np.diff(pell_ts) < 0.5)[0]
            d_list.append(date)
            if len(pell_double):
                dpell_change = 1
            if s_type == '5a':
                s_name = 'R' + str(int(timestamps["Experiment Variables"][3]))
                c_ratio = s_name
            elif s_type == '5b':
                s_name = 'I' + str(int(timestamps[
                    "Experiment Variables"][3]/100))
                c_interval = s_name
            else:
                s_name = s_type.replace('_', '').replace('2', 'M').replace(
                    '3', 'Lh').replace('4', 'Lt').replace(
                    '6', 'B1').replace('7', 'B2')
            if 'B' in s_name:
                c_ratio = 'R' + str(int(timestamps["Experiment Variables"][3]))
                c_interval = 'I' + \
                    str(int(timestamps["Experiment Variables"][5] / 100))
            if not prev_name[0] == s_type[0]:
                stage_change.append(1)
                changes.append(0)
                change_idx.append(0)
            else:
                stage_change.append(0)
                if not c_ratio == prev_ratio and not c_interval == prev_interval:
                    changes.append([c_ratio, c_interval])
                    change_idx.append(1)
                elif not c_ratio == prev_ratio:
                    changes.append(c_ratio)
                    change_idx.append(1)
                elif not c_interval == prev_interval:
                    changes.append(c_interval)
                    change_idx.append(1)
                elif not dpell_change == dpell_old:
                    changes.append("DPell")
                    change_idx.append(1)
                else:
                    changes.append(0)
                    change_idx.append(0)
            # Calculates total reward (y axis variable)
            rewards_t = len(timestamps["Reward"])
            r_list.append(rewards_t)

            # Calculates FR & FI rewards and errors (alternative y axis variables)
            err_FI = 0
            err_FR = 0
            rw_FR = 0
            rw_FI = 0
            rw_double = 0
            err_plotted = 0
            corr_plotted = 0
            if s_type == '7_' or s_type == '6_':
                norm_r_ts, _, norm_err_ts, norm_dr_ts, _ = bv_an.split_sess(
                    s, plot_all=True)
                sch_type = s.get_arrays('Trial Type')
                if s_type == '7_':
                    for i, _ in enumerate(norm_err_ts):
                        if sch_type[i] == 1:
                            err_FR = err_FR + len(norm_err_ts[i])
                        elif sch_type[i] == 0:
                            err_FI = err_FI + len(norm_err_ts[i])
                else:
                    err_FR = None
                    err_FI = None
                for i, _ in enumerate(norm_r_ts):
                    rw_double += len(norm_dr_ts[i])
                    if sch_type[i] == 1:
                        rw_FR = rw_FR + len(norm_r_ts[i])
                    elif sch_type[i] == 0:
                        rw_FI = rw_FI + len(norm_r_ts[i])
            elif s_type == '5a':
                err_FI = None
                err_FR = None
                rw_FR = len(pell_ts)
                rw_FI = None
                rw_double = None
            elif s_type == '5b':
                err_FI = None
                err_FR = None
                rw_FR = None
                rw_FI = len(pell_ts)
                rw_double = None

            else:
                err_FI = None
                err_FR = None
                rw_FR = None
                rw_FI = None
                rw_double = None

            # Updates list arrays with new session
            rw_FR_list.append(rw_FR)
            rw_FI_list.append(rw_FI)
            err_FR_list.append(err_FR)
            err_FI_list.append(err_FI)
            rw_double_list.append(rw_double)
            s_list.append(s_name)
            type_list.append('S-'+s_type[0])

            # Updates current iteration variables for next loop
            dpell_old = dpell_change
            prev_ratio = c_ratio
            prev_interval = c_interval
            prev_name = s_type
        if single_plot:
            rows, cols = [1, 4]
            size_multiplier = 5
            fig = plt.figure(
                figsize=(cols * size_multiplier, rows * size_multiplier),
                tight_layout=False)
            gs = gridspec.GridSpec(rows, cols, wspace=0.2, hspace=0.3)
            ax = fig.add_subplot(gs[0, :])
            out_name = "Timeline_" + subject
            if recent:
                out_name += "_recent"
            if details:
                out_name += "_details"
        else:
            ax = fig.add_subplot(gs[int(c), :])

        s_idx = np.arange(0, len(s_list))
        if details:
            ratio_c = plt.cm.get_cmap('Wistia')
            interval_c = plt.cm.get_cmap('winter')
            # Change value to increase height of annotation
            # note_height = 0
            # y_axis = np.zeros((1, len(s_idx)))[0] + note_height
            y_axis = []
            # Sets line on which annotations appear
            for i, l in enumerate(rw_FR_list):
                if l is None:
                    y_axis.append(0)  # Hides non-stage 7 annotations
                else:
                    y_axis.append(l)
            plots = []
            labels = []
            # Dict controls lines to be plot. Set keys to 1 in plot_dict to include line in plot
            if det_err:
                plot_styles = {
                    "FR_Corr": [rw_FR_list, '*-', ratio_c(3*45), 0],
                    "FR_Err": [err_FR_list, 'x-', ratio_c(10*45), 1],
                    "FI_Corr": [rw_FI_list, '*-', interval_c(2*45), 0],
                    "FI_Err": [err_FI_list, 'x-', interval_c(4*45), 1],
                    "FI_DoubleR": [rw_double_list, '*-', 'hotpink', 0]}
                err_plotted = 1
            elif det_corr:
                plot_styles = {
                    "FR_Corr": [rw_FR_list, '*-', ratio_c(3*45), 1],
                    "FR_Err": [err_FR_list, 'x-', ratio_c(10*45), 0],
                    "FI_Corr": [rw_FI_list, '*-', interval_c(2*45), 1],
                    "FI_Err": [err_FI_list, 'x-', interval_c(4*45), 0],
                    "FI_DoubleR": [rw_double_list, '*-', 'hotpink', 1]}
                corr_plotted = 1
            else:
                plot_styles = {
                    "FR_Corr": [rw_FR_list, '*-', ratio_c(3*45), 1],
                    "FR_Err": [err_FR_list, 'x-', ratio_c(10*45), 1],
                    "FI_Corr": [rw_FI_list, '*-', interval_c(2*45), 1],
                    "FI_Err": [err_FI_list, 'x-', interval_c(4*45), 1],
                    "FI_DoubleR": [rw_double_list, '*-', 'hotpink', 1]}
                err_plotted = 1
                corr_plotted = 1

            plot_dict = {"FR_Corr": 1, "FR_Err": 1,
                         "FI_Corr": 1, "FI_Err": 1, "FI_DoubleR": 1}
            ax2 = ax.twinx()
            for k, val in plot_dict.items():
                if val:
                    s = plot_styles[k]
                    if k[-3:] == "Err":
                        ax_used = ax2
                    else:
                        ax_used = ax
                    h, = ax_used.plot(s_idx, s[0], s[1], label=k, linewidth='2',
                                      markersize=10, color=s[2], alpha=s[3])
                    plots.append(h)
                    labels.append(h.get_label())
            ax.set_title('\nSubject {} Timeline_Details'.format(
                subject), y=1.05, fontsize=25, color=mycolors(subject))
        else:
            y_axis = r_list
            h1, = plt.plot(s_idx, y_axis, label='Animal'+subject, linewidth='4',
                           color=mycolors(subject))
            ax.set_title('\nSubject {} Timeline'.format(subject), y=1.05,
                         fontsize=25, color=mycolors(subject))

        # Annotated changes in protocol
        annotate_fontsize = 12
        h2 = None
        h3 = None
        for i, c in enumerate(changes):
            if stage_change[i] == 1:
                h2 = ax.annotate(type_list[i], xy=(s_idx[i], y_axis[i]),
                                 ha='center', xytext=(0, (.2*max(y_axis))),
                                 textcoords='offset points',
                                 arrowprops=dict(facecolor='blue', shrink=0.05), size=annotate_fontsize)
            elif change_idx[i] == 1:
                h3 = ax.annotate(str(c), xy=(s_idx[i], y_axis[i]),
                                 ha='center', xytext=(0, (.2*max(y_axis))),
                                 textcoords='offset points',
                                 arrowprops=dict(facecolor='Red', shrink=0.05), size=annotate_fontsize)
        ax.set_xlim(0, len(s_idx))
        if show_date:
            # plots x-axis ticks as dates
            plt.xticks(s_idx, d_list, fontsize=10)
            ax.set_xlabel('Sessions (Dates)', fontsize=20)
        else:
            # plots x-axis ticks as stages
            plt.xticks(s_idx, s_list, fontsize=13)
            ax.set_xlabel('Sessions (Type)', fontsize=20)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(axis='y', labelsize=15)
        if details:
            if 'S-6' in type_list:
                ax.axhline(45, xmax=(type_list.index('S-6')/len(type_list)), color=interval_c(2*45),
                           linestyle='-.', linewidth='.5')
                ax.axhline(30, xmin=(type_list.index('S-6')/len(type_list)), color=interval_c(2*45),
                           linestyle='-.', linewidth='.5')
                ax.text(type_list.index('S-6'), 31, ' Max FI', fontsize=8,
                        color=interval_c(2*45), ha='left', va='bottom')
                ax.text(s_idx[0], 46, ' Max FI', fontsize=8,
                        color=interval_c(2*45), ha='left', va='bottom')
            else:
                ax.axhline(30, color=interval_c(2*45),
                           linestyle='-.', linewidth='.5')
                ax.text(s_idx[0], 31, ' Max FI', fontsize=8,
                        color=interval_c(2*45), ha='left', va='bottom')
            loc = 'top left'
            ax.set_ylabel('Correct Trials', fontsize=20)
            # set second y-axis labels
            ax2.tick_params(axis='y', labelsize=15)
            ax2.set_ylabel('Error Presses', fontsize=20)
        else:
            plt.axhline(45, color='g', linestyle='-.', linewidth='.5')
            plt.axhline(90, color='r', linestyle='-.', linewidth='.5')
            ax.set_ylabel('Total Rewards', fontsize=20)
            plots = [h1]
            labels = [h1.get_label()]
            loc = 'lower right'
        if h2 is not None and h3 is not None:
            plots.extend([h2.arrow_patch, h3.arrow_patch])
            labels.extend(['Stage Changes', 'Protocol Mod.'])
        elif h2 is not None:
            plots.append(h2.arrow_patch)
            labels.append('Stage Changes')
        elif h3 is not None:
            plots.append(h3.arrow_patch)
            labels.append('Protocol Mod.')
        plt.legend(plots, labels, loc=loc, ncol=2)
        if single_plot:
            out_name += ".png"
            print("Saved figure to {}".format(
                os.path.join(out_dir, out_name)))
            fig.savefig(os.path.join(out_dir, out_name), dpi=400)
            plt.close()

    if not single_plot:
        out_name = "Timeline_Sum_" + "-".join(sub_list)
        if recent:
            out_name += "_recent"
        if details:
            out_name += "_details"
            if corr_plotted == 1 and err_plotted == 1:
                pass
            elif corr_plotted == 1:
                out_name += "_corr"
            elif err_plotted == 1:
                out_name += "_err"
        out_name += ".png"
        print("Saved figure to {}".format(
            os.path.join(out_dir, out_name)))
        fig.savefig(os.path.join(out_dir, out_name), dpi=400)
        plt.close()


def extract_hdf5s(in_dir, out_dir, sub_list=None, s_list=None, d_list=None):
    '''Extracts specified sessions from hdf5 files '''

    def should_use(val, vlist):
        if vlist is None:
            return True
        if val in vlist:
            return True
        return False

    in_files = os.listdir(in_dir)
    s_grp = []
    for file in in_files:
        splits = file.split('_')
        subject = splits[0]
        date = splits[1][:5]
        s_type = splits[3]
        subject_ok = should_use(subject, sub_list)
        type_ok = should_use(s_type, s_list)
        date_ok = should_use(date, d_list)
        if subject_ok and type_ok and date_ok:
            filename = os.path.join(in_dir, file)
            if os.path.isfile(filename):
                session = load_hdf5(filename, out_dir)
                s_grp.append(session)
    print('Total Files extracted: {}'.format(len(s_grp)))
    return s_grp


def convert_to_hdf5(filename, out_dir):
    """Convert all sessions in filename to hdf5 and store in out_dir."""
    make_dir_if_not_exists(out_dir)

    s_extractor = SessionExtractor(filename, verbose=True)

    for s in s_extractor:  # Batch run for file
        stage = s.get_metadata('name')
        if stage not in s.session_info.session_info_dict.keys():
            continue
        else:
            s.save_to_h5(out_dir)


def load_hdf5(filename, out_dir):
    print_h5(filename)
    session = Session(h5_file=filename)
    print(session)

    # bv_an.IRT(session, out_dir, False)
    # bv_an.cumplot(session, out_dir, False)
    return session


def run_mpc_file(filename, out_dir):
    """Take in a filename and out_dir then run the main control logic."""
    make_dir_if_not_exists(out_dir)

    s_extractor = SessionExtractor(filename, verbose=True)

    for s in s_extractor:  # Batch run for file

        time_taken = s.time_taken()
        timestamps = s.get_arrays()

        print("Session duration {} mins".format(time_taken))
        if len(timestamps.keys()) == 0:
            print('Not ready for analysis!')
            continue

        bv_an.cumplot(s, out_dir, False)
        # bv_an.IRT(s, out_dir, False)  # Doesnt work with stage 6


if __name__ == "__main__":
    """Main control."""
    start_dir = r"F:\PhD (Shane O'Mara)\Operant Data\IR Discrimination Pilot 1"  # from Ham Personal HD
    # start_dir = r"G:\!Operant Data\Ham"  # from Ham Personal Thumbdrive

    # # Batch processing of sessions in folder
    # in_dir = start_dir
    # out_dir = os.path.join(start_dir, "hdf5")
    # in_files = os.listdir(in_dir)
    # for file in in_files:
    #     filename = os.path.join(in_dir, file)
    #     if os.path.isfile(filename):
    #         convert_to_hdf5(filename, out_dir)  # Uncomment to convert to hdf5

    # # Processing of single sessions
    # filename = os.path.join(start_dir, "!2019-08-31")
    # out_dir = os.path.join(start_dir, "hdf5")
    # convert_to_hdf5(filename, out_dir)  # Uncomment to convert to hdf5

    # Processing specific sessions from hdf5

    # plot_sessions([date.today().isoformat()[-5:]])
    # plot_sessions(['09-03'])
    plot_batch_sessions()
    # compare_variables()

    # # Running single session files
    # filename = r"F:\PhD (Shane O'Mara)\Operant Data\IR Discrimination Pilot 1\!2019-08-04"
    # filename = r"G:\test"
    # filename = r"/home/sean/Documents/Data/!2019-07-22"

    # out_dir = r"G:\out_plots"
    # out_dir = r"/home/sean/Documents/Data/results"

    # run_mpc_file(filename, out_dir)

    # load_hdf5(filename, out_dir)
