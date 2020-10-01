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
from hippmapper.utils.sitk_utils import resample_to_spacing, calculate_origin_offset
from nipype.interfaces.fsl import maths
from nipype.interfaces.c3 import C3d
from termcolor import colored

os.environ['TF_CPP_MIN_LOG_LEVEL'] = "3"


def parsefn():
    parser = argparse.ArgumentParser(usage="%(prog)s -s [ subj ] \n\n"
                                           "Segments hippocampus using a trained CNN\n"
                                           "works best with a bias-corrected with-skull or skull-tripped image in"
                                           " standard orientation (RPI or LPI)\n\n"
                                           "Examples: \n"
                                           "    hypermatter segment_hipp -t1 my_subj/mprage.nii.gz \n"
                                           "OR (to bias-correct before and overwrite existing segmentation)\n"
                                           "    hypermatter segment_hipp -t1 my_subj/mprage.nii.gz -b -f \n"
                                           "OR (to run for subj - looks for my_subj_T1_nu.nii.gz)\n"
                                           "    hypermatter segment_hipp -s my_subj \n")

    optional = parser.add_argument_group('optional arguments')

    optional.add_argument('-s', '--subj', type=str, metavar='', help="input subject")
    optional.add_argument('-t1', '--t1w', type=str, metavar='', help="input T1-weighted")
    optional.add_argument('-b', '--bias', help="bias field correct image before segmentation",
                          action='store_true')
    optional.add_argument('-o', '--out', type=str, metavar='', help="output prediction")
    optional.add_argument('-n', '--num_mc', type=int, metavar='', help="number of Monte Carlo Dropout samples",
                          default=30)
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

    num_mc = args.num_mc

    return subj_dir, subj, t1, out, bias, ign_ort, num_mc, force


def orient_img(in_img_file, orient_tag, out_img_file):
    c3 = C3d()
    c3.inputs.in_file = in_img_file
    c3.inputs.args = "-orient %s" % orient_tag
    c3.inputs.out_file = out_img_file
    if os.path.exists(out_img_file):
        print("\n %s already exists" % out_img_file)
    else:
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
            img_ort = out[-5:-2]
            orient_tag = 'RPI' if 'R' in img_ort else 'LPI'
        else:
            orient_tag = 'RPI' if 'R' in img_ort else 'LPI'
        print(orient_tag)
        orient_img(in_img_file, orient_tag, out_img_file)

def resample(image, new_shape, interpolation="linear"):
    # """
    # Resample image to new shape
    # :param image: input image
    # :param new_shape: chosen shape
    # :param interpolation: interpolation method
    # :return: resampled image
    # """
    # input_shape = np.asarray(image.shape, dtype=image.get_data_dtype())
    # ras_image = reorder_img(image, resample=interpolation)
    # output_shape = np.asarray(new_shape)
    # new_spacing = input_shape / output_shape
    # new_affine = np.copy(ras_image.affine)
    # new_affine[:3, :3] = ras_image.affine[:3, :3] * np.diag(new_spacing)
    #
    # return resample_img(ras_image, target_affine=new_affine, target_shape=output_shape, interpolation=interpolation)

    image = reorder_img(image, resample=interpolation)
    zoom_level = np.divide(new_shape, image.shape)
    new_spacing = np.divide(image.header.get_zooms(), zoom_level)
    new_data = resample_to_spacing(image.get_data(), image.header.get_zooms(), new_spacing, interpolation=interpolation)
    new_affine = np.copy(image.affine)
    np.fill_diagonal(new_affine, new_spacing.tolist() + [1])
    new_affine[:3, 3] += calculate_origin_offset(new_spacing, image.header.get_zooms())
    return new_img_like(image, new_data, affine=new_affine)

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


def normalize_sample_wise_img(in_file, out_file):
    image = nib.load(in_file)
    img = image.get_data()
    # standardize intensity for data
    print("\n standardizing ...")
    std_img = (img - img.mean()) / img.std()
    nib.save(nib.Nifti1Image(std_img, image.affine), out_file)

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

    if os.path.exists(std_file):
        print("\n %s already exists" % std_file)
    else:
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

def reslice_like(in_img, ref_img, trimmed_img):
    c3 = C3d()
    c3.inputs.in_file = ref_img
    c3.inputs.args = "%s -reslice-identity" % in_img
    c3.inputs.out_file = trimmed_img
    c3.run()


def split_seg_sides(in_bin_seg_file, out_seg_file):
    """
    Split segmentation into Right/Left
    :param in_bin_seg_file: input binary segmentation
    :param out_seg_file: output segmentation with both sides
    """
    in_bin_seg = nib.load(in_bin_seg_file)
    out_seg = in_bin_seg.get_data().copy()
    seg_ort = nib.aff2axcodes(in_bin_seg.affine)
    # print(seg_ort)
    if 'L' in seg_ort:
        if seg_ort.index('L') == 0:
            mid = int(in_bin_seg.shape[0] / 2)
            new = in_bin_seg.get_data()[mid:-1, :, :]
            new[new == 1] = 2
            out_seg[mid:-1, :, :] = new
        elif seg_ort.index('L') == 1:
            mid = int(in_bin_seg.shape[1] / 2)
            new = in_bin_seg.get_data()[:, mid:-1, :]
            new[new == 1] = 2
            out_seg[:, mid:-1, :] = new
        elif seg_ort.index('L') == 2:
            mid = int(in_bin_seg.shape[2] / 2)
            new = in_bin_seg.get_data()[:, :, mid:-1]
            new[new == 1] = 2
            out_seg[:, :, mid:-1] = new
    elif 'R' in seg_ort:
        print(seg_ort.index('R'))
        if seg_ort.index('R') == 0:
            mid = int(in_bin_seg.shape[0] / 2)
            new = in_bin_seg.get_data()[0:mid, :, :]
            new[new == 1] = 2
            out_seg[0:mid, :, :] = new
        elif seg_ort.index('R') == 1:
            mid = int(in_bin_seg.shape[1] / 2)
            new = in_bin_seg.get_data()[:, 0:mid, :]
            new[new == 1] = 2
            out_seg[:, 0:mid, :] = new
        elif seg_ort.index('R') == 2:
            mid = int(in_bin_seg.shape[2] / 2)
            new = in_bin_seg.get_data()[:, :, 0:mid]
            new[new == 1] = 2
            out_seg[:, :, 0:mid] = new

    # r_orient_nii = ('R', 'A', 'S')
    # l_orient_nii = ('L', 'A', 'S')

    # if orient_dir == l_orient_nii:
    #     new = in_bin_seg.get_data()[mid:-1, :, :]
    #     new[new == 1] = 2
    #     out_seg[mid:-1, :, :] = new
    # elif orient_dir == r_orient_nii:
    #     new = in_bin_seg.get_data()[0:mid, :, :]
    #     new[new == 1] = 2
    #     out_seg[0:mid, :, :] = new

    out_seg_nii = nib.Nifti1Image(out_seg, in_bin_seg.affine)
    nib.save(out_seg_nii, out_seg_file)

def trim(img, out, voxels=1):
    c3 = C3d()
    c3.inputs.in_file = img
    c3.inputs.args = "-trim %svox" % voxels
    c3.inputs.out_file = out
    if not os.path.exists(out):
        print("\n cropping")
        c3.run()

def trim_like(img, ref, out, interp = 0):
    c3 = C3d()
    c3.inputs.in_file = ref
    c3.inputs.args = "-int %s %s -reslice-identity" % (interp, img)
    c3.inputs.out_file = out
    if not os.path.exists(out):
        print("\n cropping like")
        c3.run()

def trim_img_to_size(in_img, trimmed_img):
    """
    Trim image to specific size (112x112x64mm)
    :param in_img: input image
    :param trimmed_img: trimmed image
    """
    # trim(in_img, trimmed_img, voxels=20)
    # file_shape = nib.load(trimmed_img).shape
    # print(file_shape)

    c3 = C3d()
    c3.inputs.in_file = in_img
    c3.inputs.args = "-trim-to-size 112x112x64vox"
    # c3.inputs.args = "-trim-to-size %sx%sx%svox" % (file_shape[0], file_shape[0], int(file_shape[0]/2))
    c3.inputs.out_file = trimmed_img

    # if not os.path.exists(trimmed_img):
    #     print("\n extracting hippocampus region")
    c3.run()

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
    subj_dir, subj, t1, out, bias, ign_ort, num_mc, force = parse_inputs(parser, args)
    pred_name = 'T1acq_hipp_pred' if hasattr(args, 'subj') else 'hipp_pred'

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
        in_thresh = t1_ort if os.path.exists(t1_ort) else in_ort
        threshold_img(in_thresh, training_mod, 10, thresh_file)

        # standardize
        std_file = os.path.join(pred_dir, "%s_thresholded_standardized.nii.gz" % os.path.basename(t1).split('.')[0])
        standard_img(thresh_file, std_file)

        # cropping
        crop_file = os.path.join(pred_dir, "%s_thresholded_standardized_cropped.nii.gz" % os.path.basename(t1).split('.')[0])
        trim(std_file, crop_file)

        # resample images
        t1_crop_img = nib.load(crop_file)
        res = resample(t1_crop_img, [160, 160, 128])
        res_file = os.path.join(pred_dir, "%s_thresholded_resampled.nii.gz" % os.path.basename(t1).split('.')[0])
        res.to_filename(res_file)

        std = nib.load(res_file)
        test_data = np.zeros((1, 1, 160, 160, 128), dtype=t1_crop_img.get_data_dtype())
        test_data[0, 0, :, :, :] = std.get_data()

        print(colored("\n predicting initial hippocampus segmentation", 'green'))

        pred = run_test_case(test_data=test_data, model_json=model_json, model_weights=model_weights,
                             affine=res.affine, output_label_map=True, labels=1)

        # resample back
        t1_img = t1_ort if os.path.exists(t1_ort) else t1
        pred_res = resample_to_img(pred, t1_img)
        pred_th = math_img('img > 0.5', img=pred_res)

        # largest conn comp
        init_pred_name = os.path.join(pred_dir, "%s_hipp_init_pred.nii.gz" % subj)
        get_largest_two_comps(pred_th, init_pred_name)

        # trim seg to size
        trim_seg = os.path.join(pred_dir, "%s_hipp_init_pred_trimmed.nii.gz" % subj)
        trim(init_pred_name, trim_seg, voxels=10)
        #trim_img_to_size(init_pred_name, trim_seg)

        # trim t1
        t1_zoom = os.path.join(pred_dir, "%s_hipp_region.nii.gz" % subj)
        #trim_like.main(['-i %s' % thresh_file, '-r %s' % trim_seg, '-o %s' % t1_zoom])
        trim_like(in_thresh, trim_seg, t1_zoom, interp=3)

        # --------------
        # 2nd model
        # --------------

        pred_shape = [112, 112, 64]

        t1_zoom_img = nib.load(t1_zoom)
        test_zoom_data = np.zeros((1, 1, pred_shape[0], pred_shape[1], pred_shape[2]),
                                  dtype=t1_zoom_img.get_data_dtype())

        # standardize
        std_file_trim = os.path.join(pred_dir, "%s_trimmed_standardized.nii.gz"
                                     % os.path.basename(t1).split('.')[0])
        #standard_img(t1_zoom, std_file_trim)
        normalize_sample_wise_img(t1_zoom, std_file_trim)

        # resample images
        t1_img = nib.load(std_file_trim)
        res_zoom = resample(t1_img, pred_shape)
        res_file = os.path.join(pred_dir, "%s_trimmed_resampled.nii.gz" % os.path.basename(t1).split('.')[0])
        res_zoom.to_filename(res_file)

        test_zoom_data[0, 0, :, :, :] = res_zoom.get_data()

        model_zoom_json = os.path.join(hyper_dir, 'models', 'hipp_zoom_full_mcdp_model.json')
        model_zoom_weights = os.path.join(hyper_dir, 'models', 'hipp_zoom_full_mcdp_model_weights.h5')

        assert os.path.exists(
            model_zoom_weights), "%s model does not exits ... please download and rerun script" % model_zoom_weights

        print(colored("\n predicting hippocampus segmentation using MC Dropout with %s samples" % num_mc, 'green'))

        pred_zoom_s = np.zeros((num_mc, pred_shape[0], pred_shape[1], pred_shape[2]), dtype=res_zoom.get_data_dtype())

        for sample_id in range(num_mc):
            pred = run_test_case(test_data=test_zoom_data, model_json=model_zoom_json, model_weights=model_zoom_weights,
                                 affine=res_zoom.affine, output_label_map=True, labels=1)
            pred_zoom_s[sample_id, :, :, :] = pred.get_data()
            # nib.save(pred, os.path.join(pred_dir, "hipp_pred_%s.nii.gz" % sample_id))

        pred_zoom_mean = pred_zoom_s.mean(axis=0)
        # pred_zoom_mean = np.median(pred_zoom_s, axis=0)
        pred_zoom = nib.Nifti1Image(pred_zoom_mean, res_zoom.affine)

        # resample back
        pred_zoom_res = resample_to_img(pred_zoom, t1_zoom_img)
        pred_zoom_name = os.path.join(pred_dir, "%s_trimmed_hipp_pred_prob.nii.gz" % subj)
        nib.save(pred_zoom_res, pred_zoom_name)

        # reslice like
        t1_ref = t1_ort if os.path.exists(t1_ort) else t1

        pred_zoom_res_t1 = os.path.join(pred_dir, "%s_%s_hipp_pred_prob.nii.gz" % (subj, pred_name))
        reslice_like(pred_zoom_name, t1_ref, pred_zoom_res_t1)

        # thr
        pred_zoom_res_t1_img = nib.load(pred_zoom_res_t1)
        pred_zoom_th = math_img('img > 0.5', img=pred_zoom_res_t1_img)

        # largest 2 conn comp
        # comb_comps_zoom_bin_cmp = os.path.join(pred_dir, "%s_hipp_pred_mean_bin.nii.gz" % subj)
        bin_prediction = os.path.join(subj_dir, "%s_%s_bin.nii.gz" % (subj, pred_name))
        get_largest_two_comps(pred_zoom_th, bin_prediction)

        # split seg sides
        split_seg_sides(bin_prediction, prediction)

        # ##### compute and resample entropy uncertainty  ######
        # pred_zoom_s = np.unique(pred_zoom_s, axis=0)
        # uncertainty_entropy_ = -1 * np.sum(np.log(pred_zoom_s) * pred_zoom_s, axis=0)
        # uncertainty_entropy = nib.Nifti1Image(uncertainty_entropy_, res_zoom.affine)
        #
        # uncertainty_entropy_res = resample_to_img(uncertainty_entropy, t1_zoom_img)
        # uncertainty_entropy_name = os.path.join(pred_dir, "%s_trimmed_hipp_uncertainty_entropy.nii.gz" % subj)
        # nib.save(uncertainty_entropy_res, uncertainty_entropy_name)
        #
        # # expand to original size
        # uncertainty_entropy = os.path.join(subj_dir, "%s_uncertainty_entropy.nii.gz" % subj)
        # trim_like.main(['-i', '%s' % uncertainty_entropy_name, '-r', '%s' % t1_ref, '-o', '%s' % uncertainty_entropy])

        print(colored("\n generating mosaic image for qc", 'green'))

        seg_qc.main(['-i', '%s' % t1_ref, '-s', '%s' % prediction, '-d', '1', '-g', '3'])

        endstatement.main('Hippocampus prediction (Using MC Dropout) and mosaic generation', '%s' % (datetime.now() - start_time))


if __name__ == "__main__":
    main(sys.argv[1:])
