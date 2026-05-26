import json
import csv
import os
from datetime import datetime


def process_report(json_file_path, csv_file_path, scan_id):
    # attempts to open the json file specified
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            json_data = f.read()

        data = json.loads(json_data)

        # gets the timestamp from generated in the json file
        try:
            # if it finds a time at generated as a string and turns it into a datetime
            generated_time_str = data.get('@generated', 'unknown_time')
            generated_time = datetime.strptime(generated_time_str, "%a, %d %b %Y %H:%M:%S")
            # reconverts it back to a timestamp that is in the proper format for use later
            timestamp = generated_time.strftime("%Y-%m-%d_%H-%M-%S")
        except ValueError:
            timestamp = "unknown_timestamp"

        # gets the scanned site for the json and checks the host
        if data.get('site'):
            scanned_site = data['site'][0]
            host = scanned_site.get('@host', 'unknown_host')
        else:
            host = "unknown_host"

        # uses the host name and the time extracted from the scan to generate the file names of the reports
        vulnerabilities_file_name = os.path.join(csv_file_path, f"{host}_{timestamp}_vulnerabilities.csv")
        summary_file_name = os.path.join(csv_file_path, f"{host}_{timestamp}_summary.csv")

        # intializes the variables for parsing of vulnerability data
        vulnerability_counts = {}
        vulnerability_data = []
        high_count = 0
        medium_count = 0
        low_count = 0
        info_count = 0

        # Track unique URLs for reporting
        unique_urls = set()

        if data.get('site'):
            for site in data['site']:
                if site.get('alerts'):
                    for alert in site['alerts']:
                        vulnerability = alert.get('alert', 'N/A')
                        severity = alert.get('riskdesc', 'N/A')
                        instances = alert.get('instances', [])
                        description = alert.get('desc', 'N/A')
                        solution = alert.get('solution', 'N/A')

                        # checks what type of vulnerability is used startswith due to categorizations within each threat level
                        if severity.lower().startswith("high"):
                            high_count += len(instances)
                        if severity.lower().startswith("medium"):
                            medium_count += len(instances)
                        if severity.lower().startswith("low"):
                            low_count += len(instances)
                        if severity.lower().startswith("info"):
                            info_count += len(instances)

                        # Process each instance of this vulnerability type
                        for instance in instances:
                            url = instance.get('uri', 'N/A')
                            unique_urls.add(url)

                            # Use only the vulnerability name as the key
                            if vulnerability not in vulnerability_counts:
                                vulnerability_counts[vulnerability] = {
                                    'vulnerability_name': vulnerability,
                                    'severity': severity,
                                    'description': description,
                                    'solution': solution,
                                    'count': 0,
                                    'affected_urls': set(),
                                    'instance_url': ''  # Will store first URL for backwards compatibility
                                }

                            vulnerability_counts[vulnerability]['count'] += 1
                            vulnerability_counts[vulnerability]['affected_urls'].add(url)

                            # Store first URL for backwards compatibility with existing code
                            if not vulnerability_counts[vulnerability]['instance_url']:
                                vulnerability_counts[vulnerability]['instance_url'] = url

                            # Keep storing individual vulnerability-URL pairs for the CSV
                            vulnerability_data.append([vulnerability, url])

        # creates a vulnerabilites file for every issue that is found
        with open(vulnerabilities_file_name, "w", newline="", encoding="utf-8") as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(["Vulnerability", "URL"])
            csv_writer.writerows(vulnerability_data)

        # creates a two line sumamry file for  the main details of each report
        with open(summary_file_name, "w", newline="", encoding="utf-8") as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(
                ["Program", "Version", "Generated", "Site", "Host", "Port", "SSL", "High", "Medium", "Low", "Info"])
            # creates row with all of the basic information about the report, if missing information defaults to not N/A
            csv_writer.writerow([
                data.get('@programName', 'N/A'),
                data.get('@version', 'N/A'),
                generated_time_str,
                scanned_site.get('@name', 'N/A'),
                host,
                scanned_site.get('@port', 'N/A'),
                scanned_site.get('@ssl', 'N/A'),
                high_count,
                medium_count,
                low_count,
                info_count,
            ])

        print(f"Vulnerability data exported to {vulnerabilities_file_name}")
        print(f"Summary data exported to {summary_file_name}")

    # error checking for most common errors that could occur when creating the report
    except json.decoder.JSONDecodeError as e:
        print(f"Error decoding JSON in {json_file_path}: {e}")
    except FileNotFoundError:
        print(f"File not found: {json_file_path}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    values = [high_count, medium_count, low_count, info_count, host]

    # Convert the dictionary to a format compatible with the existing database structure
    # This preserves backward compatibility with the rest of the application
    final_vulnerability_counts = {}
    for vuln_name, details in vulnerability_counts.items():
        final_vulnerability_counts[vuln_name] = {
            'vulnerability_name': vuln_name,
            'severity': details['severity'],
            'description': details['description'],
            'solution': details['solution'],
            'count': details['count'],
            'instance_url': details['instance_url']
        }

    return values, final_vulnerability_counts, list(unique_urls)