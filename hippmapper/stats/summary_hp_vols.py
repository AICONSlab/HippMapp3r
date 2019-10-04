import numpy as np
import nibabel as nib
import os
import pandas as pd
import warnings
import argcomplete
import argparse
import sys
import glob

warnings.filterwarnings("ignore")


def parsefn():
    parser = argparse.ArgumentParser(description='Generates volumetric summary of hippocampus segmentations',
                                     usage="%(prog)s -i [ in_dir ] -o [ out_csv ]")

    required = parser.add_argument_group('required arguments')

    required.add_argument('-i', '--in_dir', type=str, required=True, metavar='',
                          help='input directory containing subjects')
    required.add_argument('-o', '--out_csv', type=str, metavar='',
                          help='output stats ex: hp_vols_summary.csv', default='hipp_volumes.csv')

    return parser


def parse_inputs(parser, args):
    if isinstance(args, list):
        args = parser.parse_args(args)
    argcomplete.autocomplete(parser)

    input_dir = args.in_dir
    out_csv = args.out_csv

    return input_dir, out_csv


def main(args):
    parser = parsefn()
    input_dir, out_csv = parse_inputs(parser, args)

    hp_label = [1, 2]
    hp_abb = ['Right_HP', 'Left_HP']
    mask_name = 'hipp_pred.nii.gz'

    subjs_dirs = [subj for subj in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, subj))]
    index = []
    my_index = []
    volume = np.zeros([len(subjs_dirs), len(hp_abb)])
    for i in range(0, len(subjs_dirs)):
        my_index.append(i)
        if glob.glob(os.path.join(input_dir, subjs_dirs[i], '*%s' % mask_name)):
            # if os.path.isfile(os.path.join(input_dir, subjs_dirs[i], subjs_dirs[i] + mask_name)):
            print('reading ', subjs_dirs[i])
            index.append(subjs_dirs[i])
            # mask = nib.load(os.path.join(input_dir, subjs_dirs[i], subjs_dirs[i] + mask_name))
            mask = nib.load(glob.glob(os.path.join(input_dir, subjs_dirs[i], '*%s' % mask_name))[0])
            mask_data = mask.get_data()
            mask_hdr = mask.get_header()
            voxel_size = mask_hdr.get_zooms()
            voxel_volume = voxel_size[0] * voxel_size[1] * voxel_size[2]
            for j in range(0, len(hp_label)):
                volume[i, j] = np.shape(np.nonzero(mask_data == hp_label[j]))[1] * voxel_volume
        else:
            print(subjs_dirs[i], ' is missing')

    cols = ['%s_Volume' % hp_abb[0], '%s_Volume' % hp_abb[1]]

    df = pd.DataFrame(volume, index=subjs_dirs, columns=cols)
    df.index.name = 'Subjects'
    df = df[(df.T != 0).any()]
    print('saving hippocampus volumetric csv')
    df.round(3).to_csv(out_csv)


if __name__ == "__main__":
    main(sys.argv[1:])
