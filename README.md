# QuickResilientSOARstatistics

This script retrieves artifact, note, attachment, and incident data from a Resilient SOAR platform and prints the count of artifacts, notes, attachments, and incidents. The script includes a progress bar to follow the % of the completion of the export.

## Table of Contents

1. [Details](#details)
2. [Description](#description)
3. [Usage](#usage)
4. [Requirements](#requirements)
5. [Inputs](#inputs)
6. [Outputs](#outputs)
7. [Configuration](#configuration)
8. [Error Handling](#error-handling)
9. [Notes](#notes)
10. [Disclaimer](#disclaimer)

## Details

- **File**: QuickResilientSOARstatistics.py
- **Copyright**: 2023 Abakus Sécurité
- **Version Tested**: V43 of IBM SOAR (directly on a dev platform)
- **Author**: Abakus Sécurité
- **Version**: 1.0

## Description

This script is designed to retrieve and count various elements such as artifacts, notes, attachments, and incidents from a Resilient SOAR platform. It provides a quick overview of the number of these elements and displays the progress of the data retrieval process.

## Usage

Run the script using the following command:

    python QuickResilientSOARstatistics.py

Ensure that you have the `config.txt` file in the same directory as the script.

## Requirements

- Python 2.x
- Resilient SimpleClient library
- A `config.txt` file with the necessary configurations

## Inputs

- **config.txt**: The script requires a configuration file with the following parameters:
  - `org_name`: the name of the Resilient organization
  - `base_url`: the URL of the Resilient SOAR platform
  - `api_key_id`: the API key ID for accessing the Resilient API
  - `api_key_secret`: the API key secret for accessing the Resilient API

## Outputs

- **Log File**: QuickResilientSOARstatistics.log
  - Logs error handling and debugging information.

- **Console Output**: 
  - Displays the total count of incidents, artifacts, notes, and attachments.
  - Displays the progress bar showing the percentage completion of the export.

## Configuration

Create a `config.txt` file with the following content:

    org_name=YourOrganizationName
    base_url=https://your-resilient-platform-url
    api_key_id=your-api-key-id
    api_key_secret=your-api-key-secret

Place this `config.txt` file in the same directory as the script.

## Error Handling

- **Configuration File Errors**:
  - If the `config.txt` file is missing or has parsing errors, the script logs the error and exits.

- **Connection Errors**:
  - If there are issues connecting to the Resilient platform, the script logs the error and exits.

- **Data Retrieval Errors**:
  - If there are issues fetching incidents, artifacts, notes, or attachments, the script logs the error and continues processing the remaining data.

- **General Errors**:
  - Any unexpected errors are caught, logged, and an error message is displayed.

## Notes

- The script uses the `urllib3` library to suppress insecure request warnings.
- Ensure that the `config.txt` file has the correct credentials and URL for the Resilient platform.

## Disclaimer

This script is provided "as is" without any warranty of any kind. Abakus Sécurité is not responsible for any damage or data loss that may occur from using this script. Use it at your own risk.

