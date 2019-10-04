#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# coding: utf-8

import os
import argcomplete
import argparse
import sys
from nipype.interfaces.ants.visualization import ConvertScalarImageToRGB, CreateTiledMosaic
from nipype.interfaces.c3 import C3d
import warnings

warnings.simplefilter("ignore", FutureWarning)

os.environ['TF_CPP_MIN_LOG_LEVEL'] = "3"


def parsefn():
    parser = argparse.ArgumentParser(usage='%(prog)s -i [ img ] \n\n'
                                           "Create tiled mosaic of segmentation overlaid on structural image")

    required = parser.add_argument_group('optional arguments')

    required.add_argument('-i', '--img', type=str, metavar='', help="input structural image", required=True)

    optional = parser.add_argument_group('optional arguments')

    optional.add_argument('-s', '--seg', type=str, metavar='', help="input segmentation")
    optional.add_argument('-g', '--gap', type=int, metavar='', help="gap between slices/increment",
                          default=2)
    optional.add_argument('-m', '--min', type=int, metavar='', help="min slice", default=30)
    optional.add_argument('-a', '--alpha', type=float, metavar='', help="alpha", default=0.5)
    optional.add_argument('-t', '--tile', type=str, metavar='', help="tile size", default='4x5')
    optional.add_argument('-d', '--direct', type=int, metavar='', help="direction", default=2)
    optional.add_argument('-f', '--flip', type=str, metavar='', help="flip xy", default='0x1')
    optional.add_argument('-r', '--roi', type=int, metavar='', help="roi around segmentation (isotropic)", default=30)
    optional.add_argument('-o', '--out', type=str, metavar='', help="output image")

    # optional.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    return parser


def parse_inputs(parser, args):
    if isinstance(args, list):
        args = parser.parse_args(args)
    argcomplete.autocomplete(parser)

    img = args.img
    seg = args.seg
    gap = args.gap
    tile = args.tile
    alpha = args.alpha
    ax = args.direct
    roi = args.roi
    flip = args.flip
    min_sl = args.min

    subj_dir = os.path.dirname(os.path.abspath(img))
    qc_dir = os.path.join(subj_dir, 'qc')
    if (args.out is None) and (not os.path.exists(qc_dir)):
        os.mkdir(qc_dir)

    if seg:
        seg_name = os.path.basename(seg.split('.')[0])
        if 'pred' in seg_name:
            seg_name = seg_name.split('_pred')[0].split('_')[-1]
        out = args.out if args.out is not None else '%s/%s_seg_qc.png' % (qc_dir, seg_name)
    else:
        out = args.out if args.out is not None else '%s/seg_qc.png' % qc_dir

    return subj_dir, img, seg, gap, tile, alpha, ax, roi, flip, min_sl, out


def main(args):
    parser = parsefn()
    subj_dir, img, seg, gap, tile, alpha, ax, roi, flip, min_sl, out = parse_inputs(parser, args)

    # pred preprocess dir
    pred_dir = '%s/pred_process' % os.path.abspath(subj_dir)
    if not os.path.exists(pred_dir):
        os.mkdir(pred_dir)

    # trim seg to focus
    c3 = C3d()

    mosaic_slicer = CreateTiledMosaic()

    if seg:
        c3.inputs.in_file = seg
        c3.inputs.args = "-trim %sx%sx%svox" % (roi, roi, roi)
        seg_trim_file = "%s/%s_trim_mosaic.nii.gz" % (pred_dir, os.path.basename(seg).split('.')[0])
        # seg_trim_file = "seg_trim.nii.gz"
        c3.inputs.out_file = seg_trim_file
        c3.run()

        # trim struct like seg
        c3.inputs.in_file = seg_trim_file
        c3.inputs.args = "%s -reslice-identity" % img
        struct_trim_file = "%s/%s_trim_mosaic.nii.gz" % (pred_dir, os.path.basename(img).split('.')[0])
        # struct_trim_file = "struct_trim.nii.gz"
        c3.inputs.out_file = struct_trim_file
        c3.run()

        # create rgb image from seg
        converter = ConvertScalarImageToRGB()

        converter.inputs.dimension = 3
        converter.inputs.input_image = seg_trim_file
        converter.inputs.colormap = 'jet'
        converter.inputs.minimum_input = 0
        converter.inputs.maximum_input = 10
        out_rgb = "%s/%s_trim_rgb.nii.gz" % (pred_dir, os.path.basename(seg).split('.')[0])
        converter.inputs.output_image = out_rgb
        converter.run()

        mosaic_slicer.inputs.rgb_image = out_rgb
        mosaic_slicer.inputs.mask_image = seg_trim_file
        mosaic_slicer.inputs.alpha_value = alpha

    else:
        struct_trim_file = img

        mosaic_slicer.inputs.rgb_image = struct_trim_file

    # stretch and clip intensities
    c3.inputs.in_file = struct_trim_file
    c3.inputs.args = "-stretch 2% 98% 0 255 -clip 0 255"
    c3.inputs.out_file = struct_trim_file
    c3.run()

    # slices to show
    if gap == 1:
        max_sl = 100
    elif gap == 2:
        max_sl = 220
    elif gap == 5:
        max_sl = 275
    else:
        max_sl = 300

    slices = '[%s,%s,%s]' % (gap, min_sl, max_sl)

    mosaic_slicer.inputs.input_image = struct_trim_file

    mosaic_slicer.inputs.output_image = out
    mosaic_slicer.inputs.direction = ax
    # mosaic_slicer.inputs.pad_or_crop = '[ -15x -50 , -15x -30 ,0]'
    mosaic_slicer.inputs.tile_geometry = tile
    mosaic_slicer.inputs.slices = slices
    mosaic_slicer.inputs.flip_slice = flip
    mosaic_slicer.terminal_output = "none"
    mosaic_slicer.run()


if __name__ == "__main__":
    main(sys.argv[1:])
