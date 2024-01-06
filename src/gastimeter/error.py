#
# SPDX-FileCopyrightText: 2024 Georg Kunz <der.schorsch@gmail.com>
# SPDX-License-Identifier: MIT
#
'''
Provide simple error handler functions.
'''
import logging
import sys

def exit_with_error(message):
    '''
    A simple error handler function which logs an error and prints a 0 to stdout
    so that any consumers have a value to work with which indicates an error, if
    not checking the exit code.
    '''
    logging.error(message)
    print(0)
    sys.exit(-1)
