#!/usr/bin/env python

import argparse
import logging
import sys

from danesfield.materials.pixel_prediction.util.model import Classifier
from danesfield.materials.pixel_prediction.util.misc import save_output, Combine_Result


def main(args):
    parser = argparse.ArgumentParser(description='Classify materials in an orthorectifed image.')

    parser.add_argument('--image_paths', nargs='*', required=True,
                        help='List of image paths.')

    parser.add_argument('--info_paths', nargs='*', required=True,
                        help='List of metadata files for image files. (.tar or .imd)')

    parser.add_argument('--output_dir', required=True,
                        help='Directory where result images will be saved.')

    parser.add_argument('--model_path',
                        help='Path to model used for evaluation.')

    parser.add_argument('--cuda', action='store_true',
                        help='Use GPU. (May have to adjust batch_size value)')

    parser.add_argument('--batch_size', type=int, default=1024,
                        help='Number of pixels classified at a time.')

    args = parser.parse_args(args)

    # Load model and select option to use CUDA
    classifier = Classifier(args.cuda, args.batch_size, args.model_path)

    # Use CNN to create material map
    if len(args.image_paths) != len(args.info_paths):
        raise IOError(
            ('The number of image paths {}, '
             'does not match the number of metadata paths {}.').format(len(args.image_paths),
                                                                       len(args.info_paths)))

    combine_result = Combine_Result('max_prob')
    for image_path, info_path in zip(args.image_paths, args.info_paths):
        _, prob_output = classifier.Evaluate(image_path, info_path)
        combine_result.update(prob_output)

    # Save results
    output_path = args.output_dir + 'max_prob' + '.tif'

    combined_result = combine_result.call()

    save_output(combined_result, output_path)


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception as e:
        logging.exception(e)
        sys.exit(1)