# VeriFact User Feedback System

This document provides an overview of the VeriFact User Feedback System, which allows users to provide feedback on factchecking results. The system collects ratings for accuracy and helpfulness, along with optional comments.

## Features

- **User Feedback Collection**: Collect user ratings and comments on factchecking results
- **Feedback Analytics**: Track feedback metrics and trends over time
- **Admin Dashboard**: View feedback statistics and manage feedback data
- **API Endpoints**: Submit and retrieve feedback programmatically
- **Data Export**: Export feedback data for analysis

## Database Schema

The feedback system uses a dedicated `feedback` table in Supabase with the following structure:

| Column             | Type      | Description                                  |
| ------------------ | --------- | -------------------------------------------- |
| feedback_id        | UUID      | Primary key                                  |
| claim_id           | UUID      | Foreign key to factchecks                    |
| user_id            | VARCHAR   | Authenticated user ID (optional)             |
| session_id         | UUID      | Session ID for anonymous users               |
| accuracy_rating    | INTEGER   | Rating for factcheck accuracy (1-5 scale)    |
| helpfulness_rating | INTEGER   | Rating for factcheck helpfulness (1-5 scale) |
| comment            | TEXT      | Optional user comment                        |
| created_at         | TIMESTAMP | When the feedback was submitted              |
| metadata           | JSONB     | Additional metadata (browser info, etc.)     |

## Setup Instructions

### 1. Create the Feedback Table

Run the SQL script to create the feedback table in your Supabase project:

```bash
# Connect to your Supabase PostgreSQL database
psql -f scripts/create_feedback_table.sql your_connection_string
```

Alternatively, you can run the SQL script in the Supabase SQL Editor in the Dashboard.

### 2. Environment Variables

No additional environment variables are required for the feedback system.

## Usage

### Collecting Feedback in Chainlit UI

The feedback mechanism is automatically included in the factchecking results in the Chainlit UI. After receiving a factcheck result:

1. Users can click the "Rate this verdict" button on any verdict
2. A form will appear to rate accuracy (1-5) and helpfulness (1-5) and add an optional comment
3. After submission, a thank you message confirms the feedback was recorded

To disable the feedback form, users can toggle off "Show feedback form" in the chat settings.

### Admin Dashboard

Admin users can access the feedback dashboard to view statistics and recent feedback:

1. Complete a factcheck in the Chainlit UI
2. Click the "View Feedback Dashboard" button in the factcheck summary
3. Browse overall statistics, rating distributions, and recent comments
4. Export all feedback data as CSV for detailed analysis

Admin access is restricted to users with the admin username (configured with the `VERIFACT_ADMIN_USER` environment variable).

### API Endpoints

The feedback system includes the following API endpoints:

#### Submit Feedback

```
POST /api/v1/feedback
```

Request body:

```json
{
  "claim_id": "UUID_of_claim",
  "accuracy_rating": 5,
  "helpfulness_rating": 4,
  "comment": "Optional comment text"
}
```

#### Get Feedback Statistics

```
GET /api/v1/feedback/stats
```

Returns aggregated statistics across all feedback.

#### Get Feedback for a Claim

```
GET /api/v1/feedback/{claim_id}
```

Returns all feedback submissions for a specific claim.

#### Get Feedback Statistics for a Claim

```
GET /api/v1/feedback/stats/{claim_id}
```

Returns aggregated statistics for feedback on a specific claim.

## Database Functions

The system includes several SQL functions for retrieving feedback statistics:

- `get_feedback_stats`: Get total count and average ratings
- `get_accuracy_distribution`: Get distribution of accuracy ratings
- `get_helpfulness_distribution`: Get distribution of helpfulness ratings
- `get_recent_comments`: Get recent user comments

## Security and Privacy

The feedback system implements several security and privacy measures:

- **Rate Limiting**: Maximum 5 feedback submissions per hour per IP address
- **Data Validation**: Ensures valid ratings and prevents malicious inputs
- **Access Control**: Admin-only access to feedback dashboard and statistics
- **Row-Level Security**: Appropriate Supabase RLS policies to control data access

## Extending the System

To extend the feedback system:

1. Add new fields to the `feedback` table in Supabase
2. Update the Pydantic models in `src/models/feedback.py`
3. Modify the database functions in `src/utils/db.py`
4. Update the API endpoints in `src/api/feedback.py`
5. Update the Chainlit UI components in `app.py`

## Troubleshooting

If feedback submission fails:

1. Check that the feedback table was created correctly in Supabase
2. Verify that the user has the necessary permissions to submit feedback
3. Check the server logs for any error messages
4. Ensure the feedback object contains at least one rating or comment
