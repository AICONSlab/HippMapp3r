#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb  8 14:20:38 2019

@author: mgoubran
"""
import os
import glob
import pandas as pd
import numpy as np
import datetime
import sys


proj_dir = sys.argv[1]

# read geom dataframe
list_of_files = glob.glob('%s/label_geom*' % proj_dir)
df = pd.read_csv(max(list_of_files, key=os.path.getctime))

# paras
stds = [2, 2]
min_vol = 1000

# norm volumes
df['Vol_norm_R'] = df['Vol_R'] / df['HfB_Vol']
df['Vol_norm_L'] = df['Vol_L'] / df['HfB_Vol']

# threshold by 1000
r_fil = df[df.Vol_R > min_vol]
l_fil = df[df.Vol_L > min_vol]

# add ones less than 1000
r_less = df.Subject[df.Vol_R < min_vol].values
l_less = df.Subject[df.Vol_L < min_vol].values

rp_less = df.Path[df.Vol_R < min_vol].values
lp_less = df.Path[df.Vol_L < min_vol].values

# metrics = ['Vol', 'SA', 'ECC', 'Elong']
metrics = ['Vol_norm', 'SA']

out_subjs_std = {}
for s, std in enumerate(stds):

    std_off_ass = std  # std dev
    std_off_vol = std

    r_outs = []
    rp_outs = []
    l_outs = []
    lp_outs = []
    d_outs = []
    dp_outs = []

    for m, met in enumerate(metrics):
        # get means
        r_m = r_fil['%s_R' % met].mean()
        l_m = r_fil['%s_L' % met].mean()

        # get stds
        r_s = r_fil['%s_R' % met].std()
        l_s = r_fil['%s_L' % met].std()

        # extract subjects with less than 2 std from mean
        r_out = df.Subject[df['%s_R' % met] < (r_m - std_off_vol * r_s)].values
        rp_out = df.Path[df['%s_R' % met] < (r_m - std_off_vol * r_s)].values
        r_outs.append(r_out)
        rp_outs.append(rp_out)

        l_out = df.Subject[df['%s_L' % met] < (l_m - std_off_vol * l_s)].values
        lp_out = df.Path[df['%s_L' % met] < (l_m - std_off_vol * l_s)].values
        l_outs.append(l_out)
        lp_outs.append(lp_out)

        # outliers by left/right assymetry
        fil = df[(df.Vol_R > min_vol) & (df.Vol_L > min_vol)]
        diff = np.abs(fil['%s_R' % met].values - fil['%s_L' % met].values)
        fil['diff'] = diff
        d_m = diff.mean()
        d_s = diff.std()
        d_out = fil.Subject[fil['diff'] > (d_m + (d_s * std_off_ass))].values
        dp_out = fil.Path[fil['diff'] > (d_m + (d_s * std_off_ass))].values
        d_outs.append(d_out)
        dp_outs.append(dp_out)

    r_outs = np.hstack(r_outs)
    l_outs = np.hstack(l_outs)
    d_outs = np.hstack(d_outs)

    rp_outs = np.hstack(rp_outs)
    lp_outs = np.hstack(lp_outs)
    dp_outs = np.hstack(dp_outs)

    # add all lists
    all_out = np.hstack((r_outs, l_outs, d_outs, r_less, l_less))
    all_p_out = np.hstack((rp_outs, lp_outs, dp_outs, rp_less, lp_less))

    # get unique
    out_subjs_std[std] = np.unique(all_out)


# ---  outlier prob
out_subjs_std_low = out_subjs_std[stds[0]]
out_subjs_std_high = out_subjs_std[stds[1]]

med_prob_subjs = np.setdiff1d(out_subjs_std_low, out_subjs_std_high)
prob_subjs = np.hstack([med_prob_subjs, out_subjs_std_high])

med_probs = np.repeat('M', len(med_prob_subjs))
high_probs = np.repeat('H', len(out_subjs_std_high))
probs = np.hstack([med_probs, high_probs])

probs_dict = dict(zip(prob_subjs, probs))

df['Outlier_Prob'] = df.Subject.map(probs_dict)
df['Outlier_Prob'] = df.Outlier_Prob.fillna('L')

date_str = datetime.date.today().strftime("%d%m%y")
df.to_csv('%s/hippocampal_volumes_with_outlier_prob_%s.csv' % (proj_dir, date_str), index=False)
