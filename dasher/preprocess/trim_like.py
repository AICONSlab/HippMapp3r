#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# coding: utf-8

import numpy as np
import nibabel as nib
import argcomplete
import argparse
import sys


def parsefn():
    parser = argparse.ArgumentParser()

    required = parser.add_argument_group('required arguments')

    required.add_argument('-r', '--ref', type=str, metavar='', help="input reference (trimmed or expanded)",
                          required=True)
    required.add_argument('-i', '--img', type=str, metavar='', help="input image", required=True)
    required.add_argument('-o', '--out', type=str, metavar='', help="output image", required=True)

    # optional = parser.add_argument_group('optional arguments')

    # optional.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    return parser

def parse_inputs(parser, args):

    if isinstance(args, list):
        args = parser.parse_args(args)
    argcomplete.autocomplete(parser)

    img = args.img.strip()
    ref = args.ref.strip()
    out = args.out.strip()

    return img, ref, out


def main(in_args):
    parser = parsefn()
    img, ref, out = parse_inputs(parser, in_args)

    in_img = nib.load(img)
    in_img_data = in_img.get_data()
    in_ref = nib.load(ref)

    in_img_aff = in_img.affine
    in_ref_aff = in_ref.affine

    vxi = in_img.header.get_zooms()[0]
    vyi = in_img.header.get_zooms()[1]
    vzi = in_img.header.get_zooms()[2]

    vxr = in_img.header.get_zooms()[0]
    vyr = in_img.header.get_zooms()[1]
    vzr = in_img.header.get_zooms()[2]

    if min(in_ref.shape) < min(in_img.shape):
        # trim
        dimx = in_ref.shape[0]
        dimy = in_ref.shape[1]
        dimz = in_ref.shape[2]

        x = np.abs(in_img_aff[0, 3]) - np.abs(in_ref_aff[0, 3])
        y = np.abs(in_img_aff[1, 3]) - np.abs(in_ref_aff[1, 3])
        z = np.abs(in_img_aff[2, 3]) - np.abs(in_ref_aff[2, 3])

        x = int(np.round(np.abs(x) / np.abs(vxi)))
        y = int(np.round(np.abs(y) / np.abs(vyi)))
        z = int(np.round(np.abs(z) / np.abs(vzi)))

        # x = int( ( np.abs(in_img_aff[0,3]) / np.abs(vx) ) - ( np.abs(in_ref_aff[0,3]) / np.abs(vx) ) )
        # y = int( ( np.abs(in_img_aff[1,3]) / np.abs(vy) ) - ( np.abs(in_ref_aff[1,3]) / np.abs(vy) ) )
        # z = int( ( np.abs(in_img_aff[2,3]) / np.abs(vz) ) - ( np.abs(in_ref_aff[2,3]) / np.abs(vz) ) )

        img_trim = in_img_data[x:x + dimx, y:y + dimy, z:z + dimz]
        nii = nib.Nifti1Image(img_trim, affine=in_ref.affine)

    elif min(in_ref.shape) > min(in_img.shape):
        # expand with zero padding
        dimx = in_img.shape[0]
        dimy = in_img.shape[1]
        dimz = in_img.shape[2]

        x = np.abs(in_ref_aff[0, 3]) - np.abs(in_img_aff[0, 3])
        y = np.abs(in_ref_aff[1, 3]) - np.abs(in_img_aff[1, 3])
        z = np.abs(in_ref_aff[2, 3]) - np.abs(in_img_aff[2, 3])

        x = int(np.round(np.abs(x) / np.abs(vxi)))
        y = int(np.round(np.abs(y) / np.abs(vyi)))
        z = int(np.round(np.abs(z) / np.abs(vzi)))

        img_expand = np.zeros(in_ref.shape)
        img_expand[x:x + dimx, y:y + dimy, z:z + dimz] = in_img.get_data()
        nii = nib.Nifti1Image(img_expand, affine=in_ref.affine)

    nib.save(nii, out)


if __name__ == "__main__":
    main(sys.argv[1:])
