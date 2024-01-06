#
# SPDX-FileCopyrightText: 2024 Georg Kunz <der.schorsch@gmail.com>
# SPDX-License-Identifier: MIT
#
import json
import logging
from gastimeter.error import exit_with_error

def parse_response(response):
    # get all words found on page 1
    words = response['readResult']['pages'][0]['words']
    logging.debug('raw list of words: {}'.format(words))

    # sort words by the upper left x-coordinate of the bounding box
    sorted_words = sorted(words, key=lambda word: word['boundingBox'][0])
    logging.debug('sorted list of words: {}'.format(sorted_words))

    # iterate over words
    meter_reading_string = ''
    for word in sorted_words:
        # remove all whitespace (if any)
        chars = word['content'].replace(' ', '')

        # concatenate all individual words
        meter_reading_string += chars

    logging.debug('concatenated string of words: {}'.format(meter_reading_string))

    if '.' in meter_reading_string or ',' in meter_reading_string:
        # check for a comma or decimal point
        if len(meter_reading_string) != 8:
            exit_with_error('A comma or decimal point was found, but not all 7 decimals were found: {}'.format(meter_reading_string))
        # simply replace all commas with decimal points to allow conversion to float
        float_meter_reading_string = meter_reading_string.replace(',', '.')

    elif len(meter_reading_string) == 8:
        # gastimate: if the reading is 8 digits, then assume that the comma
        # was misinterpreted as a digit
        meter_reading_list = list(meter_reading_string)
        meter_reading_list[5] = '.'
        float_meter_reading_string = ''.join(meter_reading_list)
        
    elif len(meter_reading_string) == 7:
        # add a decimal point
        float_meter_reading_string = meter_reading_string[:5] + '.' + meter_reading_string[-2:]
    
    else:
        exit_with_error(
            'No comma or decimal point was found and not all 7 decimals were found: {}'.format(meter_reading_string))

    logging.debug('meter reading with decimal point: {}'.format(float_meter_reading_string))

    try:
        reading = float(float_meter_reading_string)
    except ValueError as e:
        exit_with_error('Cannot convert {} to float.'.format(float_meter_reading_string))

    logging.info('meter reading with decimal point as float: {}'.format(reading))

    return reading


def main():
    logging.basicConfig(level=logging.INFO)
    with open('data/20231214-1800-response.json', 'r') as f:
        response = json.load(f)

    parse_response(response)


if __name__ == "__main__":
    main()
