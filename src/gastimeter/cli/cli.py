#
# SPDX-FileCopyrightText: 2024 Georg Kunz <der.schorsch@gmail.com>
# SPDX-License-Identifier: MIT
#
'''
Basic CLI interface.
'''
import argparse
import datetime
import logging
import os
import cv2 as cv

from gastimeter.error import exit_with_error

from gastimeter import analyzer
from gastimeter.configator import Config
from gastimeter import imagegrabber
from gastimeter import preprocessor
from gastimeter import responseparser
from gastimeter import __version__


def process_command_line_arguments() -> any:
    '''
    Define and process command line arguments.
    '''
    parser = argparse.ArgumentParser(
                        prog='gastimeter',
                        description='Extract a meter reading from an image.')
    parser.add_argument('-i',
                        '--image',
                        help='An image to extract a meter reading from. ' +
                             'Either this or the --capture flag must be provided.')
    parser.add_argument('-c',
                        '--capture',
                        action='store_true',
                        help='Capture an image from a camera. Either this flag '+
                             'must be set or an image provided using the --image option.')
    parser.add_argument('-o',
                        '--output',
                        default=os.path.curdir,
                        help='Output directory for captured images, readings, and log ' +
                             'files. If not provided, the current directory is used.')
    parser.add_argument('-p',
                        '--preprocess',
                        action='store_true',
                        help='If set, apply preprocessing to the image before the OCR analysis.')
    parser.add_argument('-d',
                        '--debug',
                        action='store_true',
                        help='Enable debug logging.')
    parser.add_argument('-v',
                        '--version',
                        action='version',
                        version=__version__,
                        help='Display the version of this program.')

    return parser.parse_args()


def configure_logging(args) -> None:
    '''
    Set-up logging
    '''
    level = logging.INFO
    if args.debug:
        level = logging.DEBUG

    if not os.path.exists(args.output):
        os.mkdir(args.output)

    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                        level=level,
                        filename=os.path.join(args.output, 'gastimeter.log'))


def validate_configuration(args) -> None:
    ''''
    Validate configuration
    '''
    if args.image is not None and args.capture is True:
        exit_with_error('Either the --image or the --capture option must be set, but not both.')

    if args.image is None and args.capture is False:
        exit_with_error('Either the --image or the --capture option must be set.')

    Config.init_config(args)


def main():
    '''
    Main logic.
    '''
    args = process_command_line_arguments()
    configure_logging(args)
    validate_configuration(args)

    #
    # process existing image
    #
    if args.image is not None:
        filename = args.image
        if not os.path.exists(filename):
            exit_with_error(f'Image \'{filename}\' not found.')

        logging.debug('Processing image %s', args.image)
        image = cv.imread(filename)

    #
    # capture image from camera
    #
    if args.capture:
        image = imagegrabber.capture_image()

    #
    # preprocess image if selected
    #
    if args.preprocess:
        logging.info('Capturing image from camera.')
        image = preprocessor.preprocess_image(image)

    #
    # write captured image to disk. If any of the following steps fail,
    # at least the raw image has been saved for later processing.
    #
    timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    cv.imwrite(os.path.join(args.output, timestamp + '.jpg'), image)

    #
    # run image through OCR processing
    #
    response = analyzer.send_request(image)

    #
    # parse image
    #
    reading = responseparser.parse_response(response)

    #
    # write reading to disk
    #
    with open(os.path.join(args.output, 'readings.csv'), '+at', encoding="utf-8") as f:
        f.writelines(timestamp + ',' + str(reading) + '\n')

    #
    # just print the reading to stdout for further processing by other tools
    #
    print(reading)

if __name__ == "__main__":
    main()
