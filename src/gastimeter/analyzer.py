#
# SPDX-FileCopyrightText: 2024 Georg Kunz <der.schorsch@gmail.com>
# SPDX-License-Identifier: MIT
#
import cv2 as cv
import numpy as np
import http.client
import json
import logging
import urllib.request
import urllib.parse
import urllib.error

import gastimeter.configator as configator
from gastimeter.error import exit_with_error


def send_request(image):
    '''
    Sending an image to the Azure AI Vision service instance and perform OCR.
    '''
    headers = {
        'Content-Type': 'application/octet-stream',
        'Ocp-Apim-Subscription-Key': configator.subscription_key,
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

    try:
        conn = http.client.HTTPSConnection('{}.cognitiveservices.azure.com'.format(configator.service_name))
        conn.request("POST",
                    "/computervision/imageanalysis:analyze?api-version=2023-02-01-preview&%s" % params,
                    binary_image,
                    headers)
        response = conn.getresponse()

        if response.status != 200:
            logging.error('Status code of response is {}'.format(response.status()))
            exit(-1)

        data = json.loads(response.read().decode())
        logging.debug('Response data: {}'.format(data))

        conn.close()
        return data
    
    except Exception as e:
        print("[Errno {0}] {1}".format(e.errno, e.strerror))


def main():
    with open('data/20231214-1800.jpg', 'rb') as f:
        image = f.read()
    send_request(image)


if __name__ == "__main__":
    main()
 