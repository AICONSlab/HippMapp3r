#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# coding: utf-8

import argcomplete
import argparse
import logging
import os
import sys
import warnings

from hypermatter import __version__
from hypermatter import hypergui
from hypermatter.convert import convert_to_standard
from hypermatter.convert import filetype
from hypermatter.preprocess import biascorr, trim_like
from hypermatter.qc import reg_qc, seg_qc
from hypermatter.register import aladin
from hypermatter.segment import hipp, hfb, stroke, vent, tissue, wmh, atrophy_penumbra
from hypermatter.stats import summary_globalvolume, summary_pvs, model_performance, summary_hp_vols
from hypermatter.workflow import n4reg, brainlab_stg1, brainlab_stg2, brainlab_stg4, run_group

warnings.simplefilter("ignore", RuntimeWarning)
warnings.simplefilter("ignore", FutureWarning)

os.environ['TF_CPP_MIN_LOG_LEVEL'] = "3"


# --------------
# functions


def run_filetype(args):
    filetype.main(args)


def run_pvs_summary(args):
    summary_pvs.main(args)


def run_reg_alad(args):
    aladin.main(args)


def run_reg_qc(args):
    reg_qc.main(args)


def run_seg_hipp(args):
    hipp.main(args)


def run_seg_hfb(args):
    hfb.main(args)


def run_seg_stroke(args):
    stroke.main(args)


def run_seg_tissue(args):
    tissue.main(args)


def run_hp_seg_summary(args):
    summary_hp_vols.main(args)


def run_seg_summary(args):
    summary_globalvolume.main(args)


def run_seg_wmh(args):
    wmh.main(args)


def run_seg_vent(args):
    vent.main(args)


def run_seg_qc(args):
    seg_qc.main(args)


def run_utils_biascorr(args):
    biascorr.main(args)


def run_trim_like(args):
    trim_like.main(args)


def run_workflow_n4reg(args):
    n4reg.main(args)


def run_workflow_stg1(args):
    brainlab_stg1.main(args)


def run_workflow_stg2(args):
    brainlab_stg2.main(args)


def run_workflow_stg4(args):
    brainlab_stg4.main(args)


def run_model_performance(args):
    model_performance.main(args)


def run_penumbra(args):
    atrophy_penumbra.main(args)


def run_run_group(args):
    run_group.main(args)


# --------------
# parser

def get_parser():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    # --------------

    # reg aladin
    aladin_parser = aladin.parsefn()
    parser_reg_alad = subparsers.add_parser('reg_aladin', add_help=False, parents=[aladin_parser],
                                            help="Registers two images with an affine or rigid transform",
                                            usage=aladin_parser.usage)
    parser_reg_alad.set_defaults(func=run_reg_alad)

    # --------------

    # reg qc
    reg_qc_parser = reg_qc.parsefn()
    parser_reg_qc = subparsers.add_parser('reg_qc', add_help=False, parents=[reg_qc_parser],
                                          help="Create tiled mosaic of moving image from registration overlaid on"
                                               "reference image",
                                          usage=reg_qc_parser.usage)
    parser_reg_qc.set_defaults(func=run_reg_qc)

    # --------------

    # seg hippocampus (hipp)
    hipp_parser = hipp.parsefn()
    parser_seg_hipp = subparsers.add_parser('seg_hipp', add_help=False, parents=[hipp_parser],
                                            help="Segment hippocampus using a trained CNN",
                                            usage=hipp_parser.usage)
    parser_seg_hipp.set_defaults(func=run_seg_hipp)

    # --------------

    # seg head from brain (hfb)
    hfb_parser = hfb.parsefn()
    parser_seg_hfb = subparsers.add_parser('seg_hfb', add_help=False, parents=[hfb_parser],
                                           help="Brain extraction (skull-striping) using a trained CNN",
                                           usage=hfb_parser.usage)
    parser_seg_hfb.set_defaults(func=run_seg_hfb)

    # --------------

    # seg stroke
    stroke_parser = stroke.parsefn()
    parser_seg_stroke = subparsers.add_parser('seg_stroke', add_help=False, parents=[stroke_parser],
                                              help="Segment stroke using a trained CNN",
                                              usage=stroke_parser.usage)
    parser_seg_stroke.set_defaults(func=run_seg_stroke)

    # --------------

    # seg tissue
    tissue_parser = tissue.parsefn()
    parser_seg_tissue = subparsers.add_parser('seg_tissue', add_help=False, parents=[tissue_parser],
                                              help='Applies tissue segmentation using FSL FAST',
                                              usage=tissue_parser.usage)
    parser_seg_tissue.set_defaults(func=run_seg_tissue)

    # --------------

    # seg ventricles (vent)
    vent_parser = vent.parsefn()
    parser_seg_vent = subparsers.add_parser('seg_vent', add_help=False, parents=[vent_parser],
                                            help="Segment ventricles using a trained CNN",
                                            usage=vent_parser.usage)
    parser_seg_vent.set_defaults(func=run_seg_vent)

    # --------------

    # seg wmh
    wmh_parser = wmh.parsefn()
    parser_seg_wmh = subparsers.add_parser('seg_wmh', add_help=False, parents=[wmh_parser],
                                           help="Segment WMH using a trained CNN",
                                           usage=wmh_parser.usage)
    parser_seg_wmh.set_defaults(func=run_seg_wmh)

    # --------------

    # seg qc
    seg_qc_parser = seg_qc.parsefn()
    parser_seg_qc = subparsers.add_parser('seg_qc', add_help=False, parents=[seg_qc_parser],
                                          help="Create tiled mosaic of segmentation overlaid on structural image",
                                          usage=seg_qc_parser.usage)
    parser_seg_qc.set_defaults(func=run_seg_qc)

    # --------------

    # utils biascorr
    biascorr_parser = biascorr.parsefn()
    parser_utils_biascorr = subparsers.add_parser('bias_corr', add_help=False, parents=[biascorr_parser],
                                                  help="Bias field correct images using N4",
                                                  usage=biascorr_parser.usage)
    parser_utils_biascorr.set_defaults(func=run_utils_biascorr)

    # --------------

    # workflow n4reg
    n4reg_parser = n4reg.parsefn()
    parser_workflow_n4reg = subparsers.add_parser('flow_n4reg', add_help=False, parents=[n4reg_parser],
                                                  help="Bias correct and registers multiple structural sequences"
                                                       "to T1-weighted",
                                                  usage=n4reg_parser.usage)
    parser_workflow_n4reg.set_defaults(func=run_workflow_n4reg)

    # --------------

    # filetype
    filetype_parser=filetype.parsefn()
    parser_filetype = subparsers.add_parser('filetype', add_help=False, parents=[filetype_parser],
                                            help="Convert the Analyse format to Nifti",
                                            usage=filetype_parser.usage)
    parser_filetype.set_defaults(func=run_filetype)

    # --------------

    # hipp vol seg
    hp_vol_parser = summary_hp_vols.parsefn()
    parser_stats_hp = subparsers.add_parser('stats_hp', add_help=False, parents=[hp_vol_parser],
                                            help="Generates volumetric summary of hippocampus segmentations",
                                            usage=hp_vol_parser.usage)
    parser_stats_hp.set_defaults(func=run_hp_seg_summary)

    # --------------

    # seg_summary
    seg_summary_parser=summary_globalvolume.parsefn()
    parser_seg_summary = subparsers.add_parser('seg_summary', add_help=False, parents=[seg_summary_parser],
                                               help='generate volumetric summary of segmentation',
                                               usage=seg_summary_parser.usage)
    parser_seg_summary.set_defaults(func=run_seg_summary)

    # --------------

    # pvs_summary
    pvs_summary_parser=summary_pvs.parsefn()
    parser_pvs_summary = subparsers.add_parser('pvs_summary', add_help=False,parents=[pvs_summary_parser],
                                               help='generate volumetric summary of segmentation',
                                               usage=pvs_summary_parser.usage)
    parser_pvs_summary.set_defaults(func=run_pvs_summary)

    # --------------

    # convert_to_standard
    convert_to_standard_parser=convert_to_standard.parsefn()
    parser_convert_to_standard = subparsers.add_parser('convert_to_standard', add_help=False,parents=[convert_to_standard_parser],
                                                       help='Convert the segmented file to SABR standard',
                                                       usage=convert_to_standard_parser.usage)
    parser_convert_to_standard.set_defaults(func=run_convert_to_standard)

    # --------------

    # trim like
    trim_parser = trim_like.parsefn()

    parser_trim_like = subparsers.add_parser('trim_like', help='Trim or expand image in same space like reference',
                                             add_help=False, parents=[trim_parser],
                                             usage='%(prog)s -i [ img ] -r [ ref ] -o [ out ] \n\n'
                                                   'Trim or expand image in same space like reference')
    parser_trim_like.set_defaults(func=run_trim_like)

    # --------------------

    # workflow brainlab stage1
    stg1_parser = brainlab_stg1.parsefn()
    parser_workflow_stg1 = subparsers.add_parser('flow_stg1', parents=[stg1_parser],
                                                 help='BrainLab pipeline stage1: Bias field correct, register to T1,'
                                                      'brain extract and remove cerebellum', add_help=False,
                                                 usage=stg1_parser.usage)
    parser_workflow_stg1.set_defaults(func=run_workflow_stg1)

    # --------------------

    # workflow brainlab stage2
    stg2_parser = brainlab_stg2.parsefn()
    parser_workflow_stg2 = subparsers.add_parser('flow_stg2', parents=[stg2_parser],
                                                 help='BrainLab pipeline stage2: Segment tissue classes (GM, WM, CSF),'
                                                      'ventricles and hippocampus', add_help=False,
                                                 usage=stg2_parser.usage)
    parser_workflow_stg2.set_defaults(func=run_workflow_stg2)

    # --------------------

    # workflow brainlab stage4

    parser_workflow_stg4 = subparsers.add_parser('flow_stg4',
                                                 help='BrainLab pipeline stage4: '
                                                      'Generate the parcellation Masks (Exactly as C_Script)',
                                                 add_help=False)

    required = parser_workflow_stg4.add_argument_group('required arguments')

    required.add_argument('-r', '--root_dir', type=str, required=True, metavar='',
                          help="root directory contains all subjects")

    required.add_argument('-s', '--session', type=str, metavar='', required=True,
                          help="Subject ID with the wild cards ex:OND01_HGH*")
    optional = parser_workflow_stg4.add_argument_group('optional arguments')
    optional.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    parser_workflow_stg4.set_defaults(func=run_workflow_stg4)

    # -------------------------

    # Model performance
    model_performance_parser=model_performance.parsefn()
    parser_model_performance = subparsers.add_parser('model_performance',
                                                     help='Report Model performance',
                                                     parents=[model_performance_parser],
                                                     add_help=False,
                                                     usage=model_performance_parser.usage)
    parser_model_performance.set_defaults(func=run_model_performance)

    # -------------------------------------

    # penumbra
    seg_pnumbra_parser=atrophy_penumbra.parsefn()
    parser_seg_penumbra = subparsers.add_parser('seg_penumbra', add_help=False,parents=[seg_pnumbra_parser],
                                                help="Generates penumbra mask for the target atrophy based on topology",
                                                usage=seg_pnumbra_parser.usage)
    parser_seg_penumbra.set_defaults(func=run_penumbra)

    # --------------

    # run group
    run_group_parser = run_group.parsefn()
    parser_run_group = subparsers.add_parser('run_group', add_help=False, parents=[run_group_parser],
                                             help="Runs a specific hypermatter function over a group of subjects",
                                             usage=run_group_parser.usage)
    parser_run_group.set_defaults(func=run_run_group)

    # ----------------------

    # version
    parser.add_argument('-v', '--version', action='version',
                        version='%(prog)s {version}'.format(version=__version__))

    return parser


# --------------
# main fn

def main(args=None):
    """ main cli call"""
    if args is None:
        args = sys.argv[1:]

    parser = get_parser()
    argcomplete.autocomplete(parser)
    args = parser.parse_args(args)

    if hasattr(args, 'func'):

        # set filename, file path for the log file
        log_filename = args.func.__name__.split('run_')[1]
        if hasattr(args, 'subj'):
            if args.subj:
                log_filepath = os.path.join(args.subj, 'logs', '{}.log'.format(log_filename))

            elif hasattr(args, 't1w'):
                if args.t1w:
                    log_filepath = os.path.join(os.path.dirname(args.t1w), 'logs', '{}.log'.format(log_filename))

        else:
            log_filepath = os.path.join(os.getcwd(), '{}.log'.format(log_filename))

        os.makedirs(os.path.dirname(log_filepath), exist_ok=True)

        # log keeps console output and redirects to file
        root = logging.getLogger('interface')
        formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
        handler = logging.FileHandler(filename=log_filepath)
        handler.setFormatter(formatter)
        root.addHandler(handler)

        args.func(args)

    else:

        hypergui.main()


if __name__ == '__main__':
    main()
