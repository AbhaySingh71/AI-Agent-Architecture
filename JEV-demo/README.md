# Smartphone Review Analyzer

Turns free-text smartphone reviews into Flipkart-style per-topic star ratings using **Jev** (via the TypeSafe SDK).

For every review, Jev is asked 14 questions — two per topic:

- **`<topic>_mentioned`** (`Noul`) — probability (0–1) that the review discusses the topic
- **`<topic>_rating`** (`Score`) — reviewer satisfaction on a 5-level scale (0–4, mapped to 1–5 stars)

A topic's rating is kept only when the mention probability is at least `0.5`. Ratings are then averaged across all reviews.

**Topics:** Camera, Battery, Display, Design, Performance, Build Quality, Value for Money

## Project structure

| File | Purpose |
|---|---|
| `main.py` | Reads the CSV, analyzes each review, prints the summary |
| `analyzer.py` | Sends one review to Jev and converts answers into star ratings |
| `questions.py` | Topic list and the 14 Jev questions |
| `aggregation.py` | Averages per-review ratings into one score per topic |
| `synthetic_phone_reviews.csv` | 50 synthetic sample reviews |

## Setup

```bash
pip install python-dotenv typesafe-sdk
```

Create a `.env` file in the project root:

```
TYPESAFE_API_KEY=your_api_key_here
```

## Usage

```bash
python main.py
```

Example output:

```
R001 {'Camera': 4.6, 'Battery': 4.2, 'Performance': 4.3, 'Value for Money': 4.5}
R002 {'Battery': 1.8}
...

3.4 ★  based on 50 ratings
----------------------------------------
Camera           3.8 ★  (21 reviews)
Battery          2.9 ★  (24 reviews)
...
```

## Input format

The CSV must have these columns:

| Column | Description |
|---|---|
| `review_id` | Unique review ID |
| `phone_model` | Phone name |
| `overall_rating` | Integer 1–5 star rating given by the reviewer |
| `review_text` | The review body |
| `is_synthetic` | Whether the review was generated |
