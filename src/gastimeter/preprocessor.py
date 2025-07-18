#
# SPDX-FileCopyrightText: 2024 Georg Kunz <der.schorsch@gmail.com>
# SPDX-License-Identifier: MIT
#
'''
Apply a predefined and currently not configurable set of transformations
to a provided image.
'''
import cv2 as cv
import numpy as np


def contrast_and_brightness(image):
    '''
    Apply basic contrast and brightness adjustments.
    '''
    contrast = 1.2
    brightness = 10
    contrasted = cv.addWeighted(image, contrast, image, 0, brightness)
    return contrasted

def correct_rotation(image):
    '''
    Use Hough lines to detect and correct the rotation of the image
    '''
    # Focus on horizontal/vertical lines typical in meter displays
    edges = cv.Canny(image, 50, 150)

    # Use probabilistic Hough transform for better line segments
    lines = cv.HoughLinesP(edges, 1, np.pi/180, threshold=50, 
                           minLineLength=50, maxLineGap=10)

    if lines is None:
        return image, 0

    # Filter for mostly horizontal lines (meter bezels, digit separators)
    horizontal_angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if -45 < angle < 45:  # Consider as horizontal
            horizontal_angles.append(angle)

    if not horizontal_angles:
        return image

    # Use median angle to avoid outliers
    rotation_angle = np.median(horizontal_angles)

    # Apply rotation
    height, width = image.shape[:2]
    center = (width // 2, height // 2)
    rotation_matrix = cv.getRotationMatrix2D(center, rotation_angle, 1.0)

    rotated = cv.warpAffine(image, rotation_matrix, (width, height))
    return rotated

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
    image = correct_rotation(image)

    # flip and flop image -- camera is upside down
    image = cv.flip(image, -1)

    return image
