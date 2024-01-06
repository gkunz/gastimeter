#
# SPDX-FileCopyrightText: 2024 Georg Kunz <der.schorsch@gmail.com>
# SPDX-License-Identifier: MIT
#
import argparse
import cv2 as cv
import datetime
import logging
import os

from gastimeter.error import exit_with_error

import gastimeter.analyzer as analyzer
import gastimeter.configator as configator
import gastimeter.imagegrabber as imagegrabber
import gastimeter.preprocessor as preprocessor
import gastimeter.responseparser as responseparser


def process_command_line_arguments() -> any:
    '''
    Define and process command line arguments.
    '''
    parser = argparse.ArgumentParser(
                        prog='gastimeter',
                        description='Extract a meter reading from an image.')
    parser.add_argument('-i',
                        '--image',
                        help='An image to extract a meter reading from. Either this or the --capture flag must be provided.')
    parser.add_argument('-c',
                        '--capture',
                        action='store_true',
                        help='Capture an image from a camera. Either this flag must be set or an image provided using the --image option.')
    parser.add_argument('-o',
                        '--output',
                        default=os.path.curdir,
                        help='Output directory for captured images, readings, and log files. If not provided, the current directory is used.')
    parser.add_argument('-p',
                        '--preprocess',
                        action='store_true',
                        help='If set, apply preprocessing to the image before the OCR analysis.')
    parser.add_argument('-v',
                        '--verbose',
                        action='store_true',
                        help='Enable verbose logging.')

    return parser.parse_args()


def configure_logging(args) -> None:
    '''
    Set-up logging
    '''
    level = logging.INFO
    if args.verbose:
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
    if args.image != None and args.capture ==  True:
        exit_with_error('Either the --image or the --capture option must be set, but not both.')
        
    if args.image == None and args.capture ==  False:
        exit_with_error('Either the --image or the --capture option must be set.')

    configator.init_config(args)


def main():
    args = process_command_line_arguments()
    configure_logging(args)
    validate_configuration(args)
    
    #
    # process existing image
    #
    if args.image != None:
        filename = args.image
        if not os.path.exists(filename):
            exit_with_error('Image \'{}\' not found.'.format(filename))

        logging.debug('Processing image {}'.format(args.image))
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
    # run image through OCR processing
    #
    response = analyzer.send_request(image)
    reading = responseparser.parse_response(response)

    #
    # write captured image and reading to disk
    #
    timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    cv.imwrite(os.path.join(args.output, timestamp + '.jpg'), image)

    with open(os.path.join(args.output, 'readings.csv'), '+at') as f:
        f.writelines(timestamp + ',' + str(reading))

    #
    # just print the reading to stdout for further processing by other tools
    #  
    print(reading)

if __name__ == "__main__":
    main()
