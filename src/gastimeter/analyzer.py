#
# SPDX-FileCopyrightText: 2024 Georg Kunz <der.schorsch@gmail.com>
# SPDX-License-Identifier: MIT
#
'''
Utilizing Azure AI services to perform OCR on an image.
'''
import http.client
import json
import logging
import urllib.request
import urllib.parse
import urllib.error
import cv2 as cv
import numpy as np

from gastimeter.configator import Config
from gastimeter.error import exit_with_error


def send_request(image):
    '''
    Sending an image to the Azure AI Vision service instance and perform OCR.
    '''
    headers = {
        'Content-Type': 'application/octet-stream',
        'Ocp-Apim-Subscription-Key': Config.subscription_key,
    }

    params = urllib.parse.urlencode({
        'features': 'read',
        #'model-name': '{string}',
        'language': 'en',
        #'smartcrops-aspect-ratios': '{string}',
        #'gender-neutral-caption': 'False',
    })

    encoded_image = cv.imencode('.jpg', image)[1]
    binary_image = np.array(encoded_image).tobytes()

    conn = http.client.HTTPSConnection(f'{Config.service_name}.cognitiveservices.azure.com')
    conn.request("POST",
                f"/computervision/imageanalysis:analyze?api-version=2024-02-01&{params}",
                binary_image,
                headers)
    response = conn.getresponse()

    if response.status != 200:
        exit_with_error(f'Status code {response.status}. Response is {response.read()}')

    data = json.loads(response.read().decode())
    logging.debug('Response data: %s', data)

    conn.close()
    return data
