"""
analyzer.py
Send ONE review to Jev (all 14 questions in one request)
and turn the answers into star ratings per topic.
"""

from dotenv import load_dotenv
from typesafe_sdk import TypeSafeClient
from questions import QUESTIONS, TOPICS

# Load TYPESAFE_API_KEY from the .env file, then create the Jev client
load_dotenv()
client = TypeSafeClient()

# Keep a topic's rating only if Jev is at least this sure the topic is discussed
MENTION_THRESHOLD = 0.5


def analyze_review(review_text):
    """Return a dict like {"Camera": 4.2, "Battery": 1.8}.
    Topics the review doesn't talk about are left out."""

    response = client.system_one(
        model="jev-latest",
        state=review_text,
        questions=QUESTIONS,
    )
    answers = response.answers

    ratings = {}
    for topic_name, topic_id in TOPICS.items():
        # Question 1: probability (0 to 1) that the topic is discussed
        mentioned = answers[topic_id + "_mentioned"].noul

        if mentioned >= MENTION_THRESHOLD:
            # Question 2: Jev gives a level from 0 to 4 (can be in between, e.g. 3.4)
            level = answers[topic_id + "_rating"].score
            stars = level + 1  # convert 0-4 into 1-5 stars
            ratings[topic_name] = round(stars, 1)

    return ratings
