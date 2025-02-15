# Google Tools for Open WebUI

This tool provides functionalities to interact with Google Calendar and Gmail using the Google API within the [Open WebUI](https://github.com/open-webui/open-webui) platform.

The tool allows you to:
 - 📅 Fetch upcoming events from your calendar
 - 📧 Retrieve emails from your inbox.

## Table of Contents
- [Get Started](#get-started)
- [Configuration](#configuration)
- [Usage](#usage)
- [License](#license)

## Get Started

1. Follow the steps on the [Google API Python Quickstart](https://developers.google.com/gmail/api/quickstart/python) to obtain your credentials file.
2. Copy the contents of `google_tools.py` into your Open WebUI tools page (Workspace > Tools).
   3. Alternatively, you can open the [hosted tool page on OpenWebUI](https://openwebui.com/t/shmarkus/google_tools/) and press "Get"

## Configuration

The following configuration values can be set under the `Valve` class:

- **`path_to_credentials`**: The absolute path to the `credentials.json` file. *Required!*
- **`default_calendar_entries`** (optional): The default number of calendar entries to fetch (default: 10).
- **`default_email_entries`** (optional): The default number of email entries to fetch (default: 10).

### special notes for Docker

- the oath authorization can't be done when using Open WebUI docker container. Do the authorization by running the test.py locally and copy the created `token.json` to the container directory `/app/backend`
- note! by default this directory is in the docker volume and will be destroyed in every restart. 

## Usage

- Enable the "Google Tools" tool for your model.
- Ask about upcoming events using the command `What are the upcoming events?`.
  - For the events, the start time, summary and creator email are fetched
- Ask about noteworthy or actionable emails with the command `Are there any noteworthy or actionable emails?`.
  - For the emails, the sender, subject, date and snippet are fetched together with a flag whether the email is unread.
- Ask for email content `Get the content of email <email ID>`. Email ID can be found in the email list.
- Ask to create a reply to an email or just create a new email draft with the command `Create a reply to email` or `Create a new email draft`.
- Ask the model to create a draft email with the command `Create an email draft with a party invitation`.
**Note:** When running the query for the first time, you'll be prompted to authenticate and authorize the application to access your Google account through a Google OAuth dialog.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.