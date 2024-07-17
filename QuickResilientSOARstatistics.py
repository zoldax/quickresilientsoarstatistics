#!/usr/bin/env python3.9
# -*- coding: utf-8 -*-

"""
File : QuickResilientSOARstatistics.py
Copyright (c) 2024 Abakus Sécurité
Version tested : V43 of IBM SOAR (directly on a dev platform)
Author : Abakus Sécurité / Pascal Weber

Description : This script retrieves artifact, note, attachment, and incident data from a Resilient SOAR platform and prints the count of artifacts, notes, attachments, and incidents. The results are printed to the console and saved to a file named results.txt. The script includes a progress bar to track the completion of the export.

Input : config.txt
The script requires a configuration file with the following parameters:
- org_name: the name of the Resilient organization
- base_url: the URL of the Resilient SOAR platform
- api_key_id: the API key ID for accessing the Resilient API
- api_key_secret: the API key secret for accessing the Resilient API

Output : QuickResilientSOARstatistics.log
Error handling, by default DEBUG

Output : Console and results.txt file with the count of incidents, artifacts, notes, and attachments including the total size of attachments.
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
from threading import Thread, Lock
from queue import Queue

# Disable insecure request warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Set up logging
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
logging.basicConfig(filename='QuickResilientSOARstatistics.log', level=logging.DEBUG)
logging.info('Starting script at %s', now)

lock = Lock()

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
            logging.error("Error fetching incidents: %s", e)
            sys.exit("Error fetching incidents: {}".format(e))
    return incidents

def count_artifacts(res_client, incident_id):
    """Count the number of artifacts in an incident."""
    try:
        artifacts = res_client.get("/incidents/{}/artifacts".format(incident_id))
        return len(artifacts)
    except Exception as e:
        logging.error("Error counting artifacts for incident %s: %s", incident_id, e)
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
        logging.error("Error counting notes for incident %s: %s", incident_id, e)
        return 0

def count_attachments(res_client, incident_id):
    """Count the number and total size of attachments in an incident."""
    try:
        attachments = res_client.get("/incidents/{}/attachments".format(incident_id))
        total_size = sum(attachment["size"] for attachment in attachments)
        return len(attachments), total_size
    except Exception as e:
        logging.error("Error counting attachments for incident %s: %s", incident_id, e)
        return 0, 0

def process_incident(res_client, incident, results, progress_queue):
    """Process an incident and update results and progress queue."""
    incident_id = incident.get("id")
    artifact_count = count_artifacts(res_client, incident_id)
    note_count = count_notes(res_client, incident_id)
    attachment_count, total_size = count_attachments(res_client, incident_id)
    status = incident.get("plan_status", "Unknown")

    with lock:
        results['incident_count'] += 1
        results['artifact_count'] += artifact_count
        results['note_count'] += note_count
        results['attachment_count'] += attachment_count
        results['total_attachment_size'] += total_size
        results['status_counts'][status] = results['status_counts'].get(status, 0) + 1
        if status == 'C':
            results['closed_incident_count'] += 1
        progress_queue.put(1)

def worker(res_client, incidents, results, progress_queue):
    """Worker thread to process incidents from the queue."""
    while not incidents.empty():
        incident = incidents.get()
        process_incident(res_client, incident, results, progress_queue)
        incidents.task_done()

def print_progress(progress_queue, total):
    """Print a progress bar to the console."""
    progress = 0
    while progress < total:
        progress += progress_queue.get()
        percent = int(progress / total * 100)
        bars = '#' * int(progress / total * 20)
        spaces = ' ' * (20 - len(bars))
        sys.stdout.write('\r[{0}] {1}%'.format(bars + spaces, percent))
        sys.stdout.flush()
        progress_queue.task_done()

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
            'closed_incident_count': 0,
            'artifact_count': 0,
            'note_count': 0,
            'attachment_count': 0,
            'total_attachment_size': 0,
            'status_counts': {}
        }

        total_incidents = len(incidents)
        start_time = time.time()
        progress_queue = Queue()

        with codecs.open('results.txt', 'w', encoding='utf-8') as output_file:
            # Print header
            current_date = datetime.datetime.now().strftime("%d/%m/%Y")
            header = 'Quick SOAR Statistics by Abakus Sécurité\n'
            header += 'Date: {}\n'.format(current_date)
            header += '--------------------------------------'
            print_and_write(output_file, header)

            # Queue incidents for processing
            incidents_queue = Queue()
            for incident in incidents:
                incidents_queue.put(incident)

            # Start worker threads
            for _ in range(args.workers):
                worker_thread = Thread(target=worker, args=(res_client, incidents_queue, results, progress_queue))
                worker_thread.setDaemon(True)
                worker_thread.start()

            # Start progress bar thread
            progress_thread = Thread(target=print_progress, args=(progress_queue, total_incidents))
            progress_thread.setDaemon(True)
            progress_thread.start()

            incidents_queue.join()
            progress_queue.join()

            end_time = time.time()
            elapsed_time = end_time - start_time

            # Convert elapsed time to a human-readable format
            minutes, seconds = divmod(elapsed_time, 60)
            hours, minutes = divmod(minutes, 60)

            # Print results
            results_message = '\nTotal number of incidents: {}\n'.format(results['incident_count'])
            results_message += 'Total number of closed incidents: {}\n'.format(results['closed_incident_count'])
            for status, count in results['status_counts'].items():
                results_message += 'Total number of incidents with status {}: {}\n'.format(status, count)
            results_message += 'Total number of artifacts: {}\n'.format(results['artifact_count'])
            results_message += 'Total number of notes: {}\n'.format(results['note_count'])
            results_message += 'Total number of attachments: {}\n'.format(results['attachment_count'])
            results_message += 'Total size of attachments: {:.2f} MB\n'.format(results['total_attachment_size'] / (1024 * 1024))
            results_message += 'Elapsed time: {}h {}m {}s'.format(int(hours), int(minutes), int(seconds))

            print_and_write(output_file, results_message)

    except Exception as e:
        logging.error("An unexpected error occurred: %s", e)
        print('An unexpected error occurred. Please check the log file for more details.')

if __name__ == "__main__":
    main()

