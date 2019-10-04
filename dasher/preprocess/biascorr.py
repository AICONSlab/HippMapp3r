#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# coding: utf-8

import argparse
import argcomplete
import sys
import multiprocessing
import os
from datetime import datetime
from hippmapper.utils import endstatement

from nipype.interfaces.ants import N4BiasFieldCorrection

os.environ['TF_CPP_MIN_LOG_LEVEL'] = "3"


def parsefn():
    parser = argparse.ArgumentParser(usage="%(prog)s -i [ in_img ] \n\n"
                                           "Bias field correct images using N4")

    required = parser.add_argument_group('required arguments')
    required.add_argument('-i', '--in_img', type=str, required=True, metavar='',
                          help="input image")

    optional = parser.add_argument_group('optional arguments')

    optional.add_argument('-m', '--mask_img', type=str, metavar='', default=None,
                          help="mask image before correction (default: %(default)s)")
    optional.add_argument('-s', '--shrink', type=int, metavar='', default=3,
                          help="shrink factor (default: %(default)s)")

    optional.add_argument('-n', '--noise', type=float, metavar='', default=0.005,
                          help="Noise parameter for histogram sharpening - deconvolution (default: %(default)s)")
    optional.add_argument('-b', '--bspline', type=int, metavar='', default=300,
                          help="Bspline distance (default: %(default)s)")
    optional.add_argument('-k', '--fwhm', type=float, metavar='', default=0.3,
                          help="FWHM for histogram sharpening - deconvolution (default: %(default)s)")
    optional.add_argument('-it', '--iters', type=int, nargs='+', metavar='', default=[50, 50, 30, 20],
                          help="Number of iterations for convergence (default: %(default)s)")
    optional.add_argument('-t', '--thresh', type=int, metavar='', default=1e-6,
                          help="Threshold for convergence (default: %(default)s)")
    optional.add_argument('-o', '--out_img', type=str, metavar='', default=None,
                          help="output image (default: %(default)s)")

    # optional.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    return parser


def parse_inputs(parser, args):

    if isinstance(args, list):
        args = parser.parse_args(args)
    argcomplete.autocomplete(parser)

    in_img = args.in_img.strip()
    mask_img = args.mask_img
    shrink = args.shrink
    bspline = args.bspline
    iters = args.iters
    thresh = args.thresh
    out_img = args.out_img.strip() if args.out_img is not None else None

    return in_img, mask_img, shrink, bspline, iters, thresh, out_img


def main(args):
    parser = parsefn()
    [in_img, mask_img, shrink, bspline, iters, thresh, out_img] = parse_inputs(parser, args)

    if out_img is not None and os.path.exists(out_img):
        print("\n %s already exists" % out_img)

    else:

        start_time = datetime.now()

        n4 = N4BiasFieldCorrection()
        n4.inputs.dimension = 3
        n4.inputs.input_image = in_img
        n4.inputs.bspline_fitting_distance = bspline
        n4.inputs.shrink_factor = shrink
        n4.inputs.n_iterations = iters
        n4.inputs.convergence_threshold = thresh

        cpu_load = 0.9
        cpus = multiprocessing.cpu_count()
        ncpus = int(cpu_load * cpus)

        n4.inputs.num_threads = ncpus

        if mask_img is not None:
            n4.inputs.args = "--mask-image %s" % mask_img.strip()

        if out_img is not None:
            n4.inputs.output_image = out_img.strip()

        print("\n bias field correcting %s " % in_img)
        n4.terminal_output = "none"
        n4.run()

        endstatement.main('Bias field correction', '%s' % (datetime.now() - start_time))

if __name__ == '__main__':
    main(sys.argv[1:])

