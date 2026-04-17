#
# SPDX-FileCopyrightText: 2024 Georg Kunz <der.schorsch@gmail.com>
# SPDX-License-Identifier: MIT
#
'''
Very basic configuration handler.
'''
import dataclasses
import os
from gastimeter.error import exit_with_error

@dataclasses.dataclass
class Config:
    '''
    Very basic configuration handler.
    '''
    # the command line arguments
    args = None

    # Azure subscription key
    subscription_key = None

    # Name of the Azure AI service instance
    service_name = None

    @classmethod
    def init_config(cls, args):
        '''
        Initialize configuration.
        '''
        cls.args = args

        key = os.environ.get('AZURE_SUBSCRIPTION_KEY')
        if not key:
            exit_with_error('AZURE_SUBSCRIPTION_KEY not found or empty in environment.')
        cls.subscription_key = key

        name = os.environ.get('AZURE_SERVICE_NAME')
        if not name:
            exit_with_error('AZURE_SERVICE_NAME not found or empty in environment.')
        cls.service_name = name
