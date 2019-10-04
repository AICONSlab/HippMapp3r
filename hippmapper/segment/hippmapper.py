#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# coding: utf-8

import os
import sys
import glob
from datetime import datetime
from pathlib import Path
import argcomplete
import argparse
import numpy as np
import nibabel as nib
import subprocess
from nilearn.image import reorder_img, resample_img, resample_to_img, math_img, largest_connected_component_img
from hippmapper.deep.predict import run_test_case
from hippmapper.utils import endstatement
from hippmapper.preprocess import biascorr, trim_like
from hippmapper.qc import seg_qc
from nipype.interfaces.fsl import maths
from nipype.interfaces.c3 import C3d
import warnings

warnings.simplefilter("ignore")

os.environ['TF_CPP_MIN_LOG_LEVEL'] = "3"


def parsefn():
    parser = argparse.ArgumentParser(usage="%(prog)s -s [ subj ] \n\n"
                                           "Segments hippocampus using a trained CNN\n"
                                           "works best with a bias-corrected with-skull or skull-tripped image in"
                                           " standard orientation (RPI or LPI)\n\n"
                                           "Examples: \n"
                                           "    hippmapper -t1 my_subj/mprage.nii.gz \n"
                                           "OR (to bias-correct before and overwrite existing segmentation)\n"
                                           "    hippmapper -t1 my_subj/mprage.nii.gz -b -f \n"
                                           "OR (to run for subj - looks for my_subj_T1_nu.nii.gz)\n"
                                           "    hippmapper -s my_subj \n")

    optional = parser.add_argument_group('optional arguments')

    optional.add_argument('-s', '--subj', type=str, metavar='', help="input subject")
    optional.add_argument('-t1', '--t1w', type=str, metavar='', help="input T1-weighted")
    optional.add_argument('-b', '--bias', help="bias field correct image before segmentation",
                          action='store_true')
    optional.add_argument('-o', '--out', type=str, metavar='', help="output prediction")
    optional.add_argument('-f', '--force', help="overwrite existing segmentation", action='store_true')
    optional.add_argument('-ss', '--session', type=str, metavar='', help="input session for longitudinal studies")
    optional.add_argument("-ign_ort", "--ign_ort",  action='store_true',
                          help="ignore orientation if tag is wrong")
    return parser


def parse_inputs(parser, args):
    if isinstance(args, list):
        args = parser.parse_args(args)
    argcomplete.autocomplete(parser)

    # check if subj or t1w are given
    if (args.subj is None) and (args.t1w is None):
        sys.exit('subj (-s) or t1w (-t1) must be given')

    # get subj dir if cross-sectional or longitudinal
    if args.subj:
        if args.session:
            subj_dir = os.path.abspath(glob.glob(os.path.join(args.subj, '*%s*' % args.session))[0])
        else:
            subj_dir = os.path.abspath(args.subj)
    else:
        subj_dir = os.path.abspath(os.path.dirname(args.t1w))

    subj = os.path.basename(subj_dir) if args.subj is not None else os.path.basename(args.t1w).split('.')[0]
    print('\n input subject:', subj)

    bias = True if args.bias else False

    if args.t1w is not None:
        t1 = args.t1w
    else:
        # look for bias-corrected or original T1
        try:
            t1_nu = glob.glob(os.path.join(subj_dir, '%s_T1_nu.*' % subj))[0]
            t1 = t1_nu
        except IndexError:
            assert glob.glob(os.path.join(subj_dir, '%s_T1.*' % subj)), \
                "no file called: %s_T1 in the subject dir" % subj
            t1_org = glob.glob(os.path.join(subj_dir, '%s_T1.*' % subj))[0]
            t1 = t1_org
            bias = True
            print('\n reading the original T1.. will bias-field correct it before segmentation')

    assert os.path.exists(t1), "%s does not exist ... please check path and rerun script" % t1

    out = args.out if args.out is not None else None

    force = True if args.force else False

    ign_ort = True if args.ign_ort else False

    return subj_dir, subj, t1, out, bias, ign_ort, force


def orient_img(in_img_file, orient_tag, out_img_file):
    c3 = C3d()
    c3.inputs.in_file = in_img_file
    c3.inputs.args = "-orient %s" % orient_tag
    c3.inputs.out_file = out_img_file
    c3.run()


def check_orient(in_img_file, r_orient, l_orient, out_img_file):
    """
    Check image orientation and re-orient if not in standard orientation (RPI or LPI)
    :param in_img_file: input_image
    :param r_orient: right ras orientation
    :param l_orient: left las orientation
    :param out_img_file: output oriented image
    """
    res = subprocess.run('c3d %s -info' % in_img_file, shell=True, stdout=subprocess.PIPE)
    out = res.stdout.decode('utf-8')
    ort_str = out.find('orient =') + 9
    img_ort = out[ort_str:ort_str + 3]

    if (img_ort != r_orient) and (img_ort != l_orient):
        print("\n Warning: input image is not in RPI or LPI orientation.. "
              "\n re-orienting image to standard orientation based on orient tags (please make sure they are correct)")

        if img_ort == 'Obl':
            orient_tag = out[-5:-2]
        else:
            orient_tag = 'RPI' if 'R' in img_ort else 'LPI'
        orient_img(in_img_file, orient_tag, out_img_file)


def resample(image, new_shape, interpolation="continuous"):
    """
    Resample image to new shape
    :param image: input image
    :param new_shape: chosen shape
    :param interpolation: interpolation method
    :return: resampled image
    """
    input_shape = np.asarray(image.shape, dtype=image.get_data_dtype())
    ras_image = reorder_img(image, resample=interpolation)
    output_shape = np.asarray(new_shape)
    new_spacing = input_shape / output_shape
    new_affine = np.copy(ras_image.affine)
    new_affine[:3, :3] = ras_image.affine[:3, :3] * np.diag(new_spacing)

    return resample_img(ras_image, target_affine=new_affine, target_shape=output_shape, interpolation=interpolation)


def threshold_img(t1, training_mod, thresh_val, thresh_file):
    """
    Threshold image using fsl maths
    :param t1: input image
    :param training_mod: image name
    :param thresh_val: threshold value (in percentile)
    :param thresh_file: output thresholded image
    """
    threshold = maths.Threshold()
    threshold.inputs.in_file = t1
    threshold.inputs.thresh = thresh_val
    threshold.inputs.use_robust_range = True
    threshold.inputs.use_nonzero_voxels = True
    threshold.inputs.out_file = thresh_file

    if not os.path.exists(thresh_file):
        print("\n pre-processing %s" % training_mod)
        threshold.run()


def standard_img(in_file, std_file):
    """
    Orient image in standard orientation
    :param in_file: input image
    :param std_file: output oriented image
    """
    c3 = C3d()
    c3.inputs.in_file = in_file
    file_shape = nib.load(in_file).shape
    nx = int(file_shape[0] / 2.2)
    ny = int(file_shape[1] / 2.2)
    nz = int(file_shape[2] / 2.2)
    c3.inputs.args = "-binarize -as m %s -push m -nlw %sx%sx%s -push m -times -replace nan 0" % (in_file, nx, ny, nz)
    c3.inputs.out_file = std_file

    if not os.path.exists(std_file):
        c3.run()


def get_largest_two_comps(in_img, out_comps):
    """
    Get the two largest connected components
    :param in_img: input image
    :param out_comps: output image with two components
    """
    first_comp = largest_connected_component_img(in_img)
    residual = math_img('img1 - img2', img1=in_img, img2=first_comp)
    second_comp = largest_connected_component_img(residual)
    comb_comps = math_img('img1 + img2', img1=first_comp, img2=second_comp)

    nib.save(comb_comps, out_comps)


def trim_img_to_size(in_img, trimmed_img):
    """
    Trim image to specific size (112x112x64mm)
    :param in_img: input image
    :param trimmed_img: trimmed image
    """
    c3 = C3d()
    c3.inputs.in_file = in_img
    c3.inputs.args = "-trim-to-size 112x112x64mm"
    c3.inputs.out_file = trimmed_img

    if not os.path.exists(trimmed_img):
        print("\n extracting hippocampus region")
        c3.run()


def split_seg_sides(in_bin_seg_file, out_seg_file):
    """
    Split segmentation into Right/Left
    :param in_bin_seg_file: input binary segmentation
    :param out_seg_file: output segmentation with both sides
    """
    in_bin_seg = nib.load(in_bin_seg_file)
    mid = int(in_bin_seg.shape[0] / 2)
    out_seg = in_bin_seg.get_data().copy()
    seg_ort = nib.aff2axcodes(in_bin_seg.affine)

    r_orient_nii = ('R', 'A', 'S')
    l_orient_nii = ('L', 'A', 'S')

    if seg_ort == l_orient_nii:
        new = in_bin_seg.get_data()[mid:-1, :, :]
        new[new == 1] = 2
        out_seg[mid:-1, :, :] = new
    elif seg_ort == r_orient_nii:
        new = in_bin_seg.get_data()[0:mid, :, :]
        new[new == 1] = 2
        out_seg[0:mid, :, :] = new

    out_seg_nii = nib.Nifti1Image(out_seg, in_bin_seg.affine)

    nib.save(out_seg_nii, out_seg_file)


# --------------
# Main function
# --------------


def main(args):
    """
    Segment hippocampus using a trained CNN
    :param args: subj_dir, subj, t1, out, bias, force
    :return: prediction (segmentation file)
    """
    parser = parsefn()
    subj_dir, subj, t1, out, bias, ign_ort, force = parse_inputs(parser, args)
    pred_name = 'T1acq_hipp_pred' if args.subj is not None else 'hipp_pred'

    if out is None:
        prediction = os.path.join(subj_dir, "%s_%s.nii.gz" % (subj, pred_name))
    else:
        prediction = out

    if os.path.exists(prediction) and force is False:
        print("\n %s already exists" % prediction)

    else:
        start_time = datetime.now()

        hfb = os.path.realpath(__file__)
        hyper_dir = Path(hfb).parents[2]

        model_json = os.path.join(hyper_dir, 'models', 'hipp_model.json')
        model_weights = os.path.join(hyper_dir, 'models', 'hipp_model_weights.h5')

        assert os.path.exists(
            model_weights), "%s model does not exits ... please download and rerun script" % model_weights

        # pred preprocess dir
        pred_dir = os.path.join('%s' % os.path.abspath(subj_dir), 'pred_process')
        if not os.path.exists(pred_dir):
            os.mkdir(pred_dir)

        training_mod = "t1"

        if bias is True:
            t1_bias = os.path.join(subj_dir, "%s_nu.nii.gz" % os.path.basename(t1).split('.')[0])
            biascorr.main(["-i", "%s" % t1, "-o", "%s" % t1_bias])
            in_ort = t1_bias
        else:
            in_ort = t1

        # check orientation
        r_orient = 'RPI'
        l_orient = 'LPI'
        t1_ort = os.path.join(subj_dir, "%s_std_orient.nii.gz" % os.path.basename(t1).split('.')[0])

        if ign_ort is False:
            check_orient(in_ort, r_orient, l_orient, t1_ort)

        # threshold at 10 percentile of non-zero voxels
        thresh_file = os.path.join(pred_dir, "%s_thresholded.nii.gz" % os.path.basename(t1).split('.')[0])
        in_thresh = t1_ort if os.path.exists(t1_ort) else t1
        threshold_img(in_thresh, training_mod, 10, thresh_file)

        # standardize
        std_file = os.path.join(pred_dir, "%s_thresholded_standardized.nii.gz" % os.path.basename(t1).split('.')[0])
        standard_img(thresh_file, std_file)

        # resample images
        t1_img = nib.load(std_file)
        res = resample(t1_img, [160, 160, 128])
        res_file = os.path.join(pred_dir, "%s_thresholded_resampled.nii.gz" % os.path.basename(t1).split('.')[0])
        res.to_filename(res_file)

        std = nib.load(res_file)
        test_data = np.zeros((1, 1, 160, 160, 128), dtype=t1_img.get_data_dtype())
        test_data[0, 0, :, :, :] = std.get_data()

        print("\n predicting initial hippocampus segmentation")

        pred = run_test_case(test_data=test_data, model_json=model_json, model_weights=model_weights,
                             affine=res.affine, output_label_map=True, labels=1)

        # resample back
        pred_res = resample_to_img(pred, t1_img)
        pred_th = math_img('img > 0.5', img=pred_res)

        # largest conn comp
        init_pred_name = os.path.join(pred_dir, "%s_hipp_init_pred.nii.gz" % subj)
        get_largest_two_comps(pred_th, init_pred_name)

        # trim seg to size
        trim_seg = os.path.join(pred_dir, "%s_hipp_init_pred_trimmed.nii.gz" % subj)
        trim_img_to_size(init_pred_name, trim_seg)

        # trim t1
        t1_zoom = os.path.join(pred_dir, "%s_hipp_region.nii.gz" % subj)
        trim_like.main(['-i %s' % thresh_file, '-r %s' % trim_seg, '-o %s' % t1_zoom])

        # --------------
        # 2nd model
        # --------------

        pred_shape = [112, 112, 64]

        t1_zoom_img = nib.load(t1_zoom)
        test_zoom_data = np.zeros((1, 1, pred_shape[0], pred_shape[1], pred_shape[2]),
                                  dtype=t1_zoom_img.get_data_dtype())

        # standardize
        std_file_trim = os.path.join(pred_dir, "%s_trimmed_thresholded_standardized.nii.gz"
                                     % os.path.basename(t1).split('.')[0])
        standard_img(t1_zoom, std_file_trim)

        # resample images
        t1_img = nib.load(std_file_trim)
        res_zoom = resample(t1_img, pred_shape)
        res_file = os.path.join(pred_dir, "%s_trimmed_resampled.nii.gz" % os.path.basename(t1).split('.')[0])
        res_zoom.to_filename(res_file)

        test_zoom_data[0, 0, :, :, :] = res_zoom.get_data()

        model_zoom_json = os.path.join(hyper_dir, 'models', 'hipp_zoom_model.json')
        model_zoom_weights = os.path.join(hyper_dir, 'models', 'hipp_zoom_model_weights.h5')

        assert os.path.exists(
            model_zoom_weights), "%s model does not exits ... please download and rerun script" % model_zoom_weights

        print("\n predicting hippocampus segmentation")

        pred_zoom = run_test_case(test_data=test_zoom_data, model_json=model_zoom_json,
                                  model_weights=model_zoom_weights,
                                  affine=res_zoom.affine, output_label_map=True, labels=1)

        # resample back
        pred_zoom_res = resample_to_img(pred_zoom, t1_zoom_img)
        pred_zoom_name = os.path.join(pred_dir, "%s_trimmed_hipp_pred_prob.nii.gz" % subj)
        nib.save(pred_zoom_res, pred_zoom_name)
        pred_zoom_th = math_img('img > 0.5', img=pred_zoom_res)

        # largest 2 conn comp
        comb_comps_zoom_bin_name = os.path.join(pred_dir, "%s_trimmed_hipp_bin_pred.nii.gz" % subj)
        get_largest_two_comps(pred_zoom_th, comb_comps_zoom_bin_name)

        # split seg sides
        comb_comps_zoom_name = os.path.join(pred_dir, "%s_trimmed_hipp_pred.nii.gz" % subj)
        split_seg_sides(comb_comps_zoom_bin_name, comb_comps_zoom_name)

        # expand to original size
        bin_prediction = os.path.join(subj_dir, "%s_%s_bin.nii.gz" % (subj, pred_name))

        t1_ref = t1_ort if os.path.exists(t1_ort) else t1

        trim_like.main(['-i %s' % comb_comps_zoom_bin_name, '-r %s' % t1_ref, '-o %s' % bin_prediction])
        trim_like.main(['-i %s' % comb_comps_zoom_name, '-r %s' % t1_ref, '-o %s' % prediction])

        print("\n generating mosaic image for qc")

        seg_qc.main(['-i', '%s' % t1_ref, '-s', '%s' % prediction, '-d', '1', '-g', '3'])

        endstatement.main('Hippocampus prediction and mosaic generation', '%s' % (datetime.now() - start_time))


if __name__ == "__main__":
    main(sys.argv[1:])

# TODO
# add neck option -hfb t1 then trim
