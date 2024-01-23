#
# SPDX-FileCopyrightText: 2024 Georg Kunz <der.schorsch@gmail.com>
# SPDX-License-Identifier: MIT
#
import cv2 as cv
import json
import os
import unittest

from gastimeter.responseparser import parse_response
from gastimeter.preprocessor import preprocess_image

class TestResponseParser(unittest.TestCase):
    '''
    Basic unit tests. 
    '''

    def test_pre_process_image(self):
        '''
        Test the image pre-processor. There is no assertion, but instead if all
        operations success, the test is assumed to pass.
        '''
        filename = os.path.join('testdata', 'test-image.jpg')
        if not os.path.exists(filename):
            self.assertTrue(False, f'Image \'{filename}\' not found.')

        image = cv.imread(filename)
        image = preprocess_image(image)


    def test_parsing_static_response(self):
        '''
        Test the response parser on a static reponse json.
        '''
        with open(os.path.join('testdata', 'test-response.json')) as f:
            content = f.read()
            response = json.loads(content)
            reading = parse_response(response)
            self.assertEqual(reading, 4663.51)


if __name__ == '__main__':
    unittest.main()
