#
# SPDX-FileCopyrightText: 2024 Georg Kunz <der.schorsch@gmail.com>
# SPDX-License-Identifier: MIT
#
'''
Parsing the result of an OCR analysis with the goal of reconstructing a
single float value as meter reading.
'''
import logging
from gastimeter.error import exit_with_error

def parse_response(response):
    '''
    Parse the result.
    '''
    # get all words found on line 1
    line = response['readResult']['blocks'][0]['lines'][0]['text']
    logging.debug('raw list of words: %s', line)

    meter_reading_string = line.replace(' ', '')
    logging.debug('concatenated string of words: %s', meter_reading_string)

    float_meter_reading_string = 0.0
    if '.' in meter_reading_string or ',' in meter_reading_string:
        # check for a comma or decimal point
        if len(meter_reading_string) != 8:
            exit_with_error(
                'A comma or decimal point was found, but not all 7 decimals ' +
                f'were found: {meter_reading_string}')
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
            'No comma or decimal point was found and not all 7 decimals ' +
            f'were found: {meter_reading_string}')

    logging.debug('meter reading with decimal point: %s', float_meter_reading_string)

    try:
        reading = float(float_meter_reading_string)
    except ValueError:
        exit_with_error(f'Cannot convert {float_meter_reading_string} to float.')

    logging.info('meter reading with decimal point as float: %f', reading)

    return reading
