#
# SPDX-FileCopyrightText: 2024 Georg Kunz <der.schorsch@gmail.com>
# SPDX-License-Identifier: MIT
#
import os
from gastimeter.error import exit_with_error

# the command line arguments
args = None

# Azure subzcription key
subscription_key = None

# Name of the Azure AI service instance
service_name = None

def init_config(args):
    args = args

    key = os.environ.get('AZURE_SUBSCRIPTION_KEY')
    if key == None:
        exit_with_error('AZURE_SUBSCRIPTION_KEY not found in environment.')
    global subscription_key
    subscription_key = key

    name = os.environ.get('AZURE_SERVICE_NAME')
    if name == None:
        exit_with_error('AZURE_SERVICE_NAME not found in environment.')
    global service_name
    service_name = name
