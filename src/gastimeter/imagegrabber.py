#
# SPDX-FileCopyrightText: 2024 Georg Kunz <der.schorsch@gmail.com>
# SPDX-License-Identifier: MIT
#
import cv2 as cv

from gastimeter.error import exit_with_error


def capture_image():
    '''
    Capture an image from a connected camera. Currently, the choice of camera is hardcoded
    to index 0.
    '''
    camindex = 0
    cam = cv.VideoCapture(camindex)
    if not cam.isOpened():
        exit_with_error('Cannot open camera using hardcoded index {}. '.format(camindex) +
                        'Check that the device exists, is connected or try ' +
                        'changing the index to pick another device.')

    result, image = cam.read()
    if result == False:
        exit_with_error('Cannot grab image from camera.')

    return image
