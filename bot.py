import google.generativeai as genai
import re

from dateparser.search import search_dates

from telegram.ext import (
    Application,
    MessageHandler,
    filters
)

from google_auth_oauthlib.flow import (
    InstalledAppFlow
)

from googleapiclient.discovery import build


# =====================================
# CONFIG
# =====================================

BOT_TOKEN = "*******"

GEMINI_API_KEY = "*******"

SCOPES = [
    "https://www.googleapis.com/auth/calendar"
]


# =====================================
# GEMINI AI SETUP
# =====================================

genai.configure(
    api_key=GEMINI_API_KEY
)

model = genai.GenerativeModel(
    "gemini-2.0-flash"
)


# =====================================
# GOOGLE AUTH
# =====================================

def google_auth():

    flow = InstalledAppFlow.from_client_secrets_file(
        "credentials.json",
        SCOPES
    )

    creds = flow.run_local_server(
        port=0
    )

    service = build(
        "calendar",
        "v3",
        credentials=creds
    )

    return service


calendar_service = google_auth()


# =====================================
# BANGLA TIME CONVERTER
# =====================================

import re

def convert_bangla_time(text):

    replacements = {

        "আগামীকাল": "tomorrow",
        "কাল": "tomorrow",
        "পরশু": "in 2 days",

        "বিকাল": "PM",
        "রাত": "PM",
        "সকাল": "AM",

        "টায়": "",
        "টার": "",

        "মধ্যে": "",
        "এর মধ্যে": "",

        "১": "1",
        "২": "2",
        "৩": "3",
        "৪": "4",
        "৫": "5",
        "৬": "6",
        "৭": "7",
        "৮": "8",
        "৯": "9",
        "০": "0",
    }

    for bn, en in replacements.items():

        text = text.replace(
            bn,
            en
        )

    # FIX PM/AM ORDER
    text = re.sub(
        r'PM\s*(\d+)',
        r'\1 PM',
        text
    )

    text = re.sub(
        r'AM\s*(\d+)',
        r'\1 AM',
        text
    )

    return text

# =====================================
# CREATE GOOGLE CALENDAR EVENT
# =====================================

def create_event(
    title,
    event_time
):

    event = {

        "summary": title,

        "start": {
            "dateTime": event_time.isoformat(),
            "timeZone": "Asia/Dhaka",
        },

        "end": {
            "dateTime": (
                event_time.isoformat()
            ),
            "timeZone": "Asia/Dhaka",
        },

        "reminders": {

            "useDefault": False,

            "overrides": [

                {
                    "method": "popup",
                    "minutes": 2880
                },

                {
                    "method": "popup",
                    "minutes": 60
                }

            ],
        },
    }

    calendar_service.events().insert(
        calendarId="primary",
        body=event
    ).execute()

    print("✅ Event Added Successfully!")


# =====================================
# TELEGRAM MESSAGE HANDLER
# =====================================

async def handle_message(
    update,
    context
):

    text = update.message.text

    print("\n====================")
    print("NEW MESSAGE:")
    print(text)
    print("====================\n")

    parsed = None

    # =====================================
    # TRY GEMINI AI
    # =====================================

    try:

        prompt = f"""
        Extract only the deadline date and time
        from this message.

        Message:
        {text}

        Return short output only.

        Example outputs:
        tomorrow 5 PM
        Friday 8 PM
        in 2 days 10 AM
        """

        response = model.generate_content(
            prompt
        )

        ai_text = response.text.strip()

        print("AI OUTPUT:")
        print(ai_text)

        parsed = search_dates(
            ai_text
        )

    except Exception as e:

        print("GEMINI ERROR:")
        print(e)

        # =====================================
        # FALLBACK PARSER
        # =====================================

        converted_text = convert_bangla_time(
            text
        )

        print("CONVERTED TEXT:")
        print(converted_text)

        parsed = search_dates(
    converted_text,
    settings={
        "PREFER_DATES_FROM": "future"
    }
)

    # =====================================
    # FINAL RESULT
    # =====================================

    print("PARSED:")
    print(parsed)

    if parsed:

        detected_text, detected_date = parsed[0]

        create_event(
            title=text,
            event_time=detected_date
        )

        await update.message.reply_text(
            "✅ Deadline added to Google Calendar!"
        )

    else:

        await update.message.reply_text(
            "❌ Could not detect any deadline."
        )


# =====================================
# START TELEGRAM BOT
# =====================================

app = Application.builder().token(
    BOT_TOKEN
).build()

app.add_handler(
    MessageHandler(
        filters.TEXT,
        handle_message
    )
)

print("\n🚀 AI Deadline Bot Running...\n")

app.run_polling()