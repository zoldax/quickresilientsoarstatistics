#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File : QuickResilientSOARstatistics.py
Version tested : V43 of IBM SOAR (directly on a dev platform)
Author : Abakus Sécurité / Pascal Weber
Version : 1.0.4
Description : This script retrieves artifact, note, attachment, and incident data from a Resilient SOAR platform and prints the count of artifacts, notes, attachments, and incidents. The results are printed to the console and saved to a file named results.txt. The script includes a progress bar to track the completion of the export.

Change header for Python 2.7 on resilient platform
#!/usr/bin/env python
# -*- coding: utf-8 -*-

Input : config.txt
The script requires a configuration file with the following parameters:
- org_name: the name of the Resilient organization
- base_url: the URL of the Resilient SOAR platform
- api_key_id: the API key ID for accessing the Resilient API
- api_key_secret: the API key secret for accessing the Resilient API

Output : QuickResilientSOARstatistics.log
Error handling, by default DEBUG

Output : Console and results.txt file with the count of incidents, artifacts, notes, and attachments including the total size of attachments.

 Copyright 2024 Pascal Weber (zoldax) / Abakus Sécurité

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

"""

from __future__ import print_function, division
import codecs
import logging
import urllib3
import resilient
import datetime
import time
import sys
import argparse
import threading

if sys.version_info[0] < 3:
    from Queue import Queue
else:
    from queue import Queue

# Disable insecure request warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Set up logging
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
logging.basicConfig(filename='QuickResilientSOARstatistics.log', level=logging.DEBUG)
logging.info(u'Starting script at %s', now)

lock = threading.Lock()

def load_config(filename='config.txt'):
    """Load configuration from file."""
    try:
        with codecs.open(filename, 'r', encoding='utf-8') as f:
            return dict(line.strip().split('=') for line in f)
    except IOError as e:
        logging.error(u"Error reading config file: %s", e)
        sys.exit(u"Error reading config file: {}".format(e))
    except ValueError as e:
        logging.error(u"Error parsing config file: %s", e)
        sys.exit(u"Error parsing config file: {}".format(e))

def connect_to_resilient(config):
    """Connect to the Resilient platform using the API key and URL."""
    try:
        res_client = resilient.SimpleClient(org_name=config['org_name'], base_url=config['base_url'], verify=False)
        res_client.set_api_key(api_key_id=config['api_key_id'], api_key_secret=config['api_key_secret'])
        return res_client
    except Exception as e:
        logging.error(u"Error connecting to Resilient platform: %s", e)
        sys.exit(u"Error connecting to Resilient platform: {}".format(e))

def fetch_all_incidents(res_client):
    """Fetch all incidents from the Resilient platform handling pagination."""
    incidents = []
    start = 0
    page_size = 1000  # Adjust page size if necessary
    while True:
        try:
            payload = {
                "start": start,
                "length": page_size
            }
            response = res_client.post("/incidents/query_paged?return_level=full", payload=payload)
            data = response.get("data", [])
            incidents.extend(data)
            if len(data) < page_size:
                break
            start += page_size
        except Exception as e:
            logging.error(u"Error fetching incidents: %s", e)
            sys.exit(u"Error fetching incidents: {}".format(e))
    return incidents

def count_artifacts(res_client, incident_id):
    """Count the number of artifacts in an incident."""
    try:
        artifacts = res_client.get("/incidents/{}/artifacts".format(incident_id))
        return len(artifacts)
    except Exception as e:
        logging.error(u"Error counting artifacts for incident %s: %s", incident_id, e)
        return 0

def count_notes(res_client, incident_id):
    """Count the number of notes in an incident and its tasks."""
    try:
        note_count = 0
        comments_incident = res_client.get("/incidents/{}/comments".format(incident_id))
        note_count += len(comments_incident)

        tasks = res_client.get("/incidents/{}/tasks".format(incident_id))
        for task in tasks:
            task_id = task.get("id")
            comments_task = res_client.get("/tasks/{}/comments".format(task_id))
            note_count += len(comments_task)

        return note_count
    except Exception as e:
        logging.error(u"Error counting notes for incident %s: %s", incident_id, e)
        return 0

def count_attachments(res_client, incident_id):
    """Count the number and total size of attachments in an incident."""
    try:
        attachments = res_client.get("/incidents/{}/attachments".format(incident_id))
        total_size = sum(attachment["size"] for attachment in attachments)
        return len(attachments), total_size
    except Exception as e:
        logging.error(u"Error counting attachments for incident %s: %s", incident_id, e)
        return 0, 0

def process_incident(res_client, incident, results):
    """Process an incident and update results."""
    incident_id = incident.get("id")
    plan_status = incident.get("plan_status")
    inc_training = incident.get("inc_training", False)

    artifact_count = count_artifacts(res_client, incident_id)
    note_count = count_notes(res_client, incident_id)
    attachment_count, total_size = count_attachments(res_client, incident_id)

    with lock:
        results['incident_count'] += 1
        results['artifact_count'] += artifact_count
        results['note_count'] += note_count
        results['attachment_count'] += attachment_count
        results['total_attachment_size'] += total_size
        results['status_counts'][plan_status] = results['status_counts'].get(plan_status, 0) + 1
        if inc_training:
            results['training_incidents'] += 1

def worker(res_client, incidents_queue, results, total_incidents):
    """Worker thread to process incidents."""
    while True:
        incident = incidents_queue.get()
        if incident is None:
            break
        process_incident(res_client, incident, results)
        incidents_queue.task_done()
        with lock:
            print_progress(total_incidents - incidents_queue.qsize(), total_incidents)

def print_progress(current, total):
    """Print a progress bar to the console."""
    progress = current / float(total)
    percent = int(progress * 100)
    bars = '#' * int(progress * 20)
    spaces = ' ' * (20 - len(bars))
    sys.stdout.write(u'\r[{0}] {1}%'.format(bars + spaces, percent))
    sys.stdout.flush()

def print_and_write(output_file, message):
    """Print a message to the console and write it to a file."""
    print(message)
    output_file.write(message + '\n')

def main():
    """Main function to retrieve and print Resilient SOAR statistics."""
    parser = argparse.ArgumentParser(description='Retrieve and print Resilient SOAR statistics.')
    parser.add_argument('--workers', type=int, default=4, help='Number of worker threads for concurrent processing')
    args = parser.parse_args()

    try:
        # Load configuration and connect to Resilient platform
        config = load_config()
        res_client = connect_to_resilient(config)
        incidents = fetch_all_incidents(res_client)

        # Initialize counts
        results = {
            'incident_count': 0,
            'artifact_count': 0,
            'note_count': 0,
            'attachment_count': 0,
            'total_attachment_size': 0,
            'status_counts': {},
            'training_incidents': 0
        }

        total_incidents = len(incidents)
        start_time = time.time()

        with codecs.open('results.txt', 'w', encoding='utf-8') as output_file:
            # Print header
            current_date = datetime.datetime.now().strftime("%d/%m/%Y")
            header = u'Quick SOAR Statistics by Abakus Sécurité\n'
            header += u'Date: {}\n'.format(current_date)
            header += u'--------------------------------------'
            print_and_write(output_file, header)

            # Queue incidents for processing
            incidents_queue = Queue()
            for incident in incidents:
                incidents_queue.put(incident)

            # Start worker threads
            threads = []
            for _ in range(args.workers):
                t = threading.Thread(target=worker, args=(res_client, incidents_queue, results, total_incidents))
                t.start()
                threads.append(t)

            # Block until all tasks are done
            incidents_queue.join()

            # Stop workers
            for _ in range(args.workers):
                incidents_queue.put(None)
            for t in threads:
                t.join()

            end_time = time.time()
            elapsed_time = end_time - start_time

            # Convert elapsed time to a human-readable format
            minutes, seconds = divmod(elapsed_time, 60)
            hours, minutes = divmod(minutes, 60)

            # Print results
            status_meanings = {
                'A': 'Active',
                'C': 'Closed',
                'D': 'Deleted',
                'P': 'Pending'
            }
            results_message = u'\nTotal number of incidents: {}\n'.format(results['incident_count'])
            results_message += u'Total number of artifacts: {}\n'.format(results['artifact_count'])
            results_message += u'Total number of notes: {}\n'.format(results['note_count'])
            results_message += u'Total number of attachments: {}\n'.format(results['attachment_count'])
            results_message += u'Total size of attachments: {:.2f} MB\n'.format(results['total_attachment_size'] / (1024 * 1024))
            results_message += u'Total training incidents: {}\n'.format(results['training_incidents'])
            for status, count in results['status_counts'].items():
                meaning = status_meanings.get(status, 'Unknown')
                results_message += u'Total incidents with status {}: {} ({})\n'.format(status, count, meaning)
            results_message += u'Elapsed time: {}h {}m {}s'.format(int(hours), int(minutes), int(seconds))

            print_and_write(output_file, results_message)

    except Exception as e:
        logging.error(u"An unexpected error occurred: %s", e)
        print(u'An unexpected error occurred. Please check the log file for more details.')

if __name__ == "__main__":
    main()

