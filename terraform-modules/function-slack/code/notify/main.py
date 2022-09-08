#!/usr/bin/env python

from __future__ import print_function

import base64
import json
import os
import requests

from google.cloud import secretmanager


def get_webhook(slack_channel):

    environment = os.environ["ENVIRONMENT"]
    name = os.environ["NAME"]
    project_number = os.environ["PROJECT_NUMBER"]

    secrets = secretmanager.SecretManagerServiceClient()
    webhook = secrets.access_secret_version(
        f"projects/{project_number}/secrets/{name}-{slack_channel}-{environment}"
    ).payload.data.decode("utf-8")

    return webhook


def notify(event, context):

    slack_channel = os.environ["SLACK_CHANNEL"]
    slack_username = os.environ["SLACK_USERNAME"]
    slack_emoji = os.environ["SLACK_EMOJI"]
    slack_url = get_webhook(slack_channel)

    print(f"Function triggered by messageId {context.event_id} at {context.timestamp} to {context.resource['name']}")

    if "data" in event:
        pubsub_message = base64.b64decode(event["data"]).decode("utf-8")

        # print(pubsub_message)
        json_data = json.loads(pubsub_message)
        findings = json_data["Findings"]

        payload = {
            "channel": slack_channel,
            "username": slack_username,
            "icon_emoji": slack_emoji,
            "attachments": [],
            "text": json_data["Subject"],
        }

        slack_message = {
            "fallback": "A new message",
            "fields": [{"title": "Vulnerable domains"}],
        }

        for finding in findings:

            try:
                cname = finding["CNAME"]
                print(f"VULNERABLE: {finding['Domain']}  CNAME  {cname} in GCP Project {finding['Project']}")
                slack_message["fields"].append(
                    {
                        "value": finding["Domain"] + "  CNAME  " + cname + " in GCP Project " + finding["Project"],
                        "short": False,
                    }
                )

            except KeyError:
                print(f"VULNERABLE: {finding['Domain']} in GCP Project {finding['Project']}")
                slack_message["fields"].append(
                    {
                        "value": finding["Domain"] + " in GCP Project " + finding["Project"],
                        "short": False,
                    }
                )

        payload["attachments"].append(slack_message)
        response = requests.post(
            slack_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        if response.status_code != 200:
            ValueError(f"Request to Slack returned error {response.status_code}:\n{response.text}")
        else:
            print(f"Message sent to {slack_channel} Slack channel")
