import sys
import nibabel as nib
import argcomplete
import argparse
import os
# from nipype.interfaces.c3 import C3d


def parsefn():
    parser = argparse.ArgumentParser(usage='Converts image format/type')

    parser.add_argument('-i', '--in_img', type=str, required=True, metavar='',
                        help="input image, ex:MM.img")
    parser.add_argument('-o', '--out_img', type=str, required=True, metavar='',
                        help="output image, ex:MM.nii")
    return parser

def parse_inputs(parser, args):
    if isinstance(args, list):
        args = parser.parse_args(args)
    argcomplete.autocomplete(parser)

    return args.in_img, args.out_img

def main(args):
    parser = parsefn()
    [in_img, out_img] = parse_inputs(parser, args)
    DTYPES = {
    'uint8': 'uchar',
    'int16': 'short',
    '>i2': 'short',
    'float32': 'float',
    '>f4': 'float',
    }
    img = nib.analyze.AnalyzeImage.load(in_img)
    dtype=DTYPES[str(img.get_data_dtype())]

    # c3 = C3d()
    # c3.inputs.in_file = in_img
    # c3.inputs.out_file = out_img
    # c3d.inputs.pix_type = dtype

    print('\n converting image and orienting to RPI \n')

    cmd='c3d -verbose '+in_img+' -orient RPI -type '+dtype+' -o '+out_img
    os.system(cmd)

if __name__ == '__main__':
    main(sys.argv[1:])

# TODO
# use nipype w c3d or mri_convert
# option to not reorient to RPI

