import os
import base64
import logging
import html
import json

from email.message import EmailMessage

from datetime import datetime
from pydantic import BaseModel, Field
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = [
    # See and download any calendar you can access using your Calendar.
    "https://www.googleapis.com/auth/calendar.readonly",
    # See, create, change, and delete events on Google calendars you own.
    "https://www.googleapis.com/auth/calendar.events.owned",
    # Read all resources and their metadata—no write operations.
    "https://www.googleapis.com/auth/gmail.readonly",
    # Create, read, update, and delete drafts. Send messages and drafts.
    "https://www.googleapis.com/auth/gmail.compose"
]

MAIN_FORMAT = """
<interpreter_output>
    <description>
        {description}
    </description>
    <output>
        {output}
    </output>
</interpreter_output>
"""
MAIL_FORMAT = """
<email>
    <message_id>{id}</message_id>
    <date>{date}</date>
    <from>{sender}</from>
    <subject>{subject}</subject>
    <snippet>{snippet}</snippet>
    <unread>{unread}</unread>
    <email_body>{email_body}</email_body>
</email>
"""
CALENDAR_FORMAT = """
<event>
    <start>{start}</start>
    <summary>{summary}</summary>
    <calendar>{calendar}</calendar>
</event>
"""

"""
title: Google Tools
author: Markus Karileet
author_url: https://website.com
git_url: https://github.com/Shmarkus/openwebui-tools.git
description: This tool provides functionalities to interact with Google Calendar and Gmail using the Google API. It allows you to fetch upcoming events from your calendar and retrieve emails from your inbox, create draft messages, and more.
required_open_webui_version: 0.5.7
requirements: google-api-python-client, google-auth-httplib2, google-auth-oauthlib, requests, email
version: 0.0.2
licence: MIT
"""

def setup_logger():
    name = "GoogleTools"
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.set_name(name)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger


logger = setup_logger()


class Tools:
    def __init__(self):
        """Initialize the Tool."""
        self.valves = self.Valves()
        self.citation = True

    class Valves(BaseModel):
        default_calendar_entries: int = Field(
                default=10, description="The default number of calendar entries to fetch"
        )
        default_email_entries: int = Field(
            default=10, description="The default number of email entries to fetch"
        )
        path_to_credentials: str = Field(
            default="credentials.json", description="The absolute path to the credentials file"
        )
        pass

    def get_user_emails(self, count: int = -1, label_id: str = "INBOX") -> str:
        """
        Retrieves and displays the latest emails from the user's Gmail inbox. Always return message ID to the user so
        that the message content can be later accessed separately.

        This function fetches the specified number of emails (default is 10 if not provided)
        and returns them in the following XML format:
        <interpreter_output>
            <description>The requested {number_of_emails} emails from the user's inbox that have the label {labelId}. Today is {current_time}</description>
            <output>
                <emails>
                    <email>
                        <message_id>{id}</message_id>
                        <date>{date}</date>
                        <from>{sender}</from>
                        <subject>{subject}</subject>
                        <snippet>{snippet}</snippet>
                        <unread>{unread}</unread>
                        <email_body>{email_body}</email_body>
                    </email>
                </email>
            </output>
        </interpreter_output>

        :param count: The number of emails to fetch.
            If set to -1 (default), it uses the default value configured in the tool
            settings.
        :param label_id: The label of the emails to fetch, Can be one of UNREAD, INBOX (this is the default), STARRED,
            IMPORTANT, SENT.

        :return: An XML-formatted string containing the email details or an error message.
        """
        if count == -1:
            count = self.valves.default_email_entries
        creds = self.get_google_creds()
        description = f"The requested  {count} emails from the user's inbox that have the label {label_id}. Today is {get_current_time()}"
        logger.debug(description)
        try:
            service = build("gmail", "v1", credentials=creds)
            results = service.users().messages().list(
                userId="me",
                maxResults=count,
                includeSpamTrash=False,
                labelIds=[label_id]
            ).execute()
            messages = results.get("messages", [])
            out = ""
            if not messages:
                out = "No messages found."
            else:
                for msg in messages:
                    mail = service.users().messages().get(userId="me", id=msg["id"]).execute()
                    email_body = parse_email_body(mail["payload"])

                    out += MAIL_FORMAT.format(
                        date=get_header_value(mail["payload"]["headers"], "Date"),
                        sender=get_header_value(mail["payload"]["headers"], "From"),
                        subject=get_header_value(mail["payload"]["headers"], "Subject"),
                        snippet=mail["snippet"],
                        unread="UNREAD" in mail["labelIds"],
                        id=msg["id"],
                        email_body=email_body
                    )

        except HttpError as error:
            out = f"An error occurred: {error}"

        result = MAIN_FORMAT.format(description=description, output=f"<emails>{out}</emails>")
        logger.debug(result)
        return result

    def get_email_content(self, message_id: str) -> str:
        """
        Retrieves and returns the full body content of an email from the user's inbox for the user to READ in the
        following XML format:
        <interpreter_output>
            <description>Contents of the email message for message_id: {message_id}</description>
            <output><![CDATA[{output}]]></output>
        </interpreter_output>

        Where the description is the description of the action and in the output tag, there is the full body content
        of the email.

        :param message_id: The unique message ID of the email to fetch from the inbox (eg. 194d1f624c165d4b)

        :return: An XML-formatted string containing the email body content or an error message.

        :raises HttpError: If there's a problem fetching the email or its body content,
            such as network errors, rate limits exceeded, or invalid credentials.
        """
        creds = self.get_google_creds()
        description = f"Contents of the email message for message_id: {message_id}. Today is {get_current_time()}"
        logger.debug(description)
        try:
            service = build("gmail", "v1", credentials=creds)
            mail = service.users().messages().get(userId="me", id=message_id).execute()
            email_body = parse_email_body(mail["payload"])

        except HttpError as error:
            email_body = f"An error occurred: {error}"

        result = MAIN_FORMAT.format(description=description, output=f"<![CDATA[{email_body}]]>")
        logger.debug(result)
        return result

    def gmail_create_draft(self, to: str, subject: str, body: str) -> str:
        """
        Creates a new draft message in the user's Gmail account using the provided recipient,
        subject, and body content.

        This function uses the Google API to authenticate and create a new draft message.
        The draft message is not sent immediately; it remains as a draft in the user's
        Gmail account until manually sent or deleted. The method returns a confirmation message
        indicating that the draft was created successfully, or an error message if there's a problem.

        :param to: The email address of the recipient.
        :param subject: The subject line for the email.
        :param body: The main content or body of the email message.

        :return: A confirmation message indicating that the draft was created successfully,
                or an error message if there's a problem creating the draft.
        """
        logger.debug("Creating draft message...")
        creds = self.get_google_creds()
        try:
            service = build("gmail", "v1", credentials=creds)
            message = EmailMessage()
            message.set_content(body)

            message["To"] = to
            # message["From"] = ""
            message["Subject"] = subject

            # encoded message
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            create_message = {"message": {"raw": encoded_message}}
            # pylint: disable=E1101
            draft = (
                service.users()
                .drafts()
                .create(userId="me", body=create_message)
                .execute()
            )

            out = "Draft message created!"

        except HttpError as error:
            out = f"An error occurred: {error}"

        logger.debug(out)
        return out

    def get_user_events(self, count: int = -1) -> str:
        """
        Retrieves and displays upcoming events from the user's Google Calendar.

        This function fetches the specified number of upcoming events (default is 10 if not provided)
        and returns an XML-formatted string with the event details in the following format:
        <interpreter_output>
            <description>The requested {number_of_events} upcoming events from the user's calendar. Today is {current_time}</description>
            <output>
                <events>
                    <event>
                        <start>{start}</start>
                        <summary>{summary}</summary>
                        <calendar>{calendar}</calendar>
                    </event>
                </events>
            </output>

        The method retrieves all user calendar IDs first, then fetches events from each calendar.
        Events are sorted by their start time before being returned.

        :param count: The number of upcoming events to fetch from the calendar.
            If set to -1 (default), it uses the default value configured in the tool settings.

        :return: Upcoming events as a formatted string, or an error message if fetching fails.
        """
        if count == -1:
            count = self.valves.default_calendar_entries
        creds = self.get_google_creds()
        description = f"The requested {count} upcoming events from the user's calendar. Today is {get_current_time()}"
        logger.debug(description)

        try:
            service = build("calendar", "v3", credentials=creds)
            from_time = get_current_time()
            out = ""
            calendar_ids = get_calendar_ids(service)
            event_list = []
            for calendar_id in calendar_ids:
                events = get_cal_evts(service, calendar_id, count, from_time)
                event_list += events
            event_list.sort(key=lambda x: x["start"])
            for i in range(count):
                out += CALENDAR_FORMAT.format(start=event_list[i]["start"], summary=event_list[i]["summary"], calendar=event_list[i]["calendar"])

        except HttpError as error:
            out = f"Error fetching calendar data: {str(error)}"

        results = MAIN_FORMAT.format(description=description, output=f"<events>{out}</events>")
        logger.debug(results)
        return results

    def get_google_creds(self):
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.

        # If necessary, uncomment the following line to remove generated token.json on re-authenticate
        # os.remove("token.json")
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
            # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.valves.path_to_credentials, SCOPES
                )
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open("token.json", "w") as token:
                token.write(creds.to_json())
        return creds


def get_calendar_ids(service) -> list:
    out = []
    calendars = (service.calendarList().list().execute())
    cals = calendars.get("items", [])
    for cal in cals:
        out.append(cal["id"])
    logger.debug(f"Got following calendars {out}")

    return out


def get_current_time():
    return datetime.utcnow().isoformat() + "Z"


def get_cal_evts(service, calendarId, number_of_events, from_time) -> list:
    out = []
    events_result = (
        service.events()
        .list(
            calendarId=calendarId,
            timeMin=from_time,
            maxResults=number_of_events,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])
    for event in events:
        # print event as JSON
        # print(json.dumps(event, indent=4))
        if event["organizer"].get("displayName") == None:
            calendar = "mine"
        else:
            if "veikon" in event["organizer"]["displayName"].lower():
                continue
                calendar = "Veikko"
            else:
                if "kristan" in event["organizer"]["displayName"].lower():
                    continue
                    calendar = "Krista"
                else:
                    calendar = "Good to know events"

        out.append({
            "start": event["start"].get("dateTime", event["start"].get("date")),
            "summary": event["summary"],
            #"creator": event["creator"]["email"], # I don't actually need this
            "calendar": calendar # This tells me whose calendar it is
        })

    return out


def get_header_value(payload: list, name: str) -> str:
    field = next((field for field in payload if field["name"] == name), None)
    return field["value"] if field else ""


def parse_email_body(payload: dict) -> str:
    try:
        if payload["mimeType"] == "multipart/alternative" or payload["mimeType"] == "multipart/mixed":
            for part in payload["parts"]:
                if part["mimeType"] == "text/html" or part["mimeType"] == "text/plain":
                    return decode_mail_body(part["body"]["data"])

        return decode_mail_body(payload["body"]["data"])
    except ValueError as err:
        return f"Error decoding email body: {err}"
    except KeyError as err:
        return f"Error parsing email body: {err}"
    except Exception as err:
        return f"Error: {err}"


def decode_mail_body(data: str) -> str:
    return html.escape(base64.b64decode(data).decode("utf-8", errors='replace'))
