#!/usr/bin/env python3.9
# -*- coding: utf-8 -*-

"""
File : CountIncidents.py
Copyright (c) 2024 Abakus Sécurité
Version tested : V43 of IBM SOAR (directly on a dev platform)
Author : Abakus Sécurité / Pascal Weber
Version : 1.0.0
Description : This script retrieves and prints the count of incidents from a Resilient SOAR platform.

Input : config.txt
The script requires a configuration file with the following parameters:
- org_name: the name of the Resilient organization
- base_url: the URL of the Resilient SOAR platform
- api_key_id: the API key ID for accessing the Resilient API
- api_key_secret: the API key secret for accessing the Resilient API

Output : Console with the count of incidents.
"""

import codecs
import logging
import urllib3
import resilient
import sys

# Disable insecure request warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Set up logging
logging.basicConfig(filename='CountIncidents.log', level=logging.DEBUG)
logging.info('Starting script')

def load_config(filename='config.txt'):
    """Load configuration from file."""
    try:
        with codecs.open(filename, 'r', encoding='utf-8') as f:
            return dict(line.strip().split('=') for line in f)
    except IOError as e:
        logging.error("Error reading config file: %s", e)
        sys.exit("Error reading config file: {}".format(e))
    except ValueError as e:
        logging.error("Error parsing config file: %s", e)
        sys.exit("Error parsing config file: {}".format(e))

def connect_to_resilient(config):
    """Connect to the Resilient platform using the API key and URL."""
    try:
        res_client = resilient.SimpleClient(org_name=config['org_name'], base_url=config['base_url'], verify=False)
        res_client.set_api_key(api_key_id=config['api_key_id'], api_key_secret=config['api_key_secret'])
        return res_client
    except Exception as e:
        logging.error("Error connecting to Resilient platform: %s", e)
        sys.exit("Error connecting to Resilient platform: {}".format(e))

def fetch_incidents(res_client):
    """Fetch incidents from the Resilient platform."""
    try:
        payload = {
            "filters": [
                {
                    "conditions": [{"field_name": "plan_status", "method": "equals", "value": "A"}]
                }
            ]
        }
        #response = res_client.post("/incidents/query_paged?return_level=full", payload=payload)
        response = res_client.post("/incidents/query_paged?field_handle=-1", payload=payload)
        return response.get("data", [])
    except Exception as e:
        logging.error("Error fetching incidents: %s", e)
        sys.exit("Error fetching incidents: {}".format(e))

def main():
    """Main function to retrieve and print the count of incidents."""
    try:
        # Load configuration and connect to Resilient platform
        config = load_config()
        res_client = connect_to_resilient(config)
        incidents = fetch_incidents(res_client)

        # Print the number of incidents
        incident_count = len(incidents)
        print(f"Total number of incidents: {incident_count}")

    except Exception as e:
        logging.error("An unexpected error occurred: %s", e)
        print('An unexpected error occurred. Please check the log file for more details.')

if __name__ == "__main__":
    main()

