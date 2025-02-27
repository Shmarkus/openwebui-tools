#!/usr/bin/env python3
import argparse
import asyncio

from google_tools import Tools


async def mock_callback(data):
    print(f"Mock callback received data: {data}")


async def main():
    parser = argparse.ArgumentParser(description="Google Tools CLI")
    parser.add_argument('--get_calendar_events', action='store_true', help='List all calendar events with default values')
    args = parser.parse_args()

    tools = Tools()

    if args.get_calendar_events:
        print(await tools.get_user_events(__event_emitter__=mock_callback))
    else:
        while True:
            print("\nChoose an action:")
            print("1. Get User Emails")
            print("2. Get Email Content")
            print("3. Create Draft Message")
            print("4. Get Upcoming Events")
            print("5. Exit")

            choice = input("Enter your choice: ")

            if choice == "1":
                count = int(input("Enter the number of emails to fetch (-1 for default): "))
                label_id = input("Enter the label ID (INBOX, UNREAD, etc., leave empty for INBOX): ").strip() or "INBOX"
                print(await tools.get_user_emails(count=count, label_id=label_id, __event_emitter__=mock_callback))
            elif choice == "2":
                message_id = input("Enter the message ID: ")
                print(await tools.get_email_content(message_id=message_id, __event_emitter__=mock_callback))
            elif choice == "3":
                to = input("Enter recipient email address: ")
                subject = input("Enter subject: ")
                body = input("Enter body content: ")
                print(await tools.gmail_create_draft(to=to, subject=subject, body=body, __event_emitter__=mock_callback))
            elif choice == "4":
                count = int(input("Enter the number of events to fetch (leave empty for 10 entries): ")) or "-1"
                print(await tools.get_user_events(count=count, __event_emitter__=mock_callback))
            elif choice == "5":
                break
            else:
                print("Invalid choice. Please try again.")


if __name__ == "__main__":
    asyncio.run(main())