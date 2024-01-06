#
# SPDX-FileCopyrightText: 2024 Georg Kunz <der.schorsch@gmail.com>
# SPDX-License-Identifier: MIT
#
'''
Apply a predefined and currently not configurable set of transformations
to a provided image.
'''
import cv2 as cv


def contrast_and_brightness(image):
    '''
    Apply basic contrast and brightness adjustments.
    '''
    contrast = 1.2
    brightness = 10
    contrasted = cv.addWeighted(image, contrast, image, 0, brightness)
    return contrasted

def preprocess_image(image):
    '''
    Apply a predefined and currently not configurable set of transformations
    to a provided image.
    '''
    # remove distortion -- currently not implemented
    # https://kushalvyas.github.io/calib.html
    # Opencv cv2.calibrateCamera() function Camera Matrix:
    # [
    #     [532.79536563, 0, 342.4582516],
    #     [0, 532.91928339, 233.90060514],
    #     [0, 0, 1]
    # ]
    # image = undistort(image)

    # convert to gray scale
    image = cv.cvtColor(image, cv.COLOR_BGR2GRAY)

    # contrast and brightness
    image = contrast_and_brightness(image)

    # flip and flop image -- camera is upside down
    image = cv.flip(image, -1)

    return image
