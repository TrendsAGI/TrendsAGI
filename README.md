# TrendsAGI Official Python Client

[![PyPI Version](https://img.shields.io/pypi/v/trendsagi.svg)](https://pypi.org/project/trendsagi/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Versions](https://img.shields.io/pypi/pyversions/trendsagi.svg)](https://pypi.org/project/trendsagi/)

The official Python client for the [TrendsAGI API](https://trendsagi.com), providing a simple and convenient way to access real-time trend data, AI-powered insights, and the full intelligence suite.

This library is fully typed with Pydantic models for all API responses, giving you excellent editor support (like autocompletion and type checking) and data validation out of the box.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Getting Started](#getting-started)
  - [Authentication](#authentication)
  - [Quickstart Example](#quickstart-example)
- [Usage Examples](#usage-examples)
  - [Get AI-Powered Insights for a Trend](#get-ai-powered-insights-for-a-trend)
  - [Perform a Deep Analysis on a Topic](#perform-a-deep-analysis-on-a-topic)
  - [Track an X (Twitter) User](#track-an-x-twitter-user)
  - [Monitor for Crisis Events](#monitor-for-crisis-events)
- [Handling Errors and Exceptions](#handling-errors-and-exceptions)
- [Full API Documentation](#full-api-documentation)
- [Contributing](#contributing)
- [License](#license)

## Features

- Access real-time and historical trend data
- Leverage powerful AI-driven insights, sentiment analysis, and content briefs for any trend
- Perform deep, causal analysis on any topic or query
- Utilize the Intelligence Suite for actionable recommendations, crisis monitoring, and market tracking
- Manage topic interests, alerts, and data export configurations
- Simple, intuitive methods mirroring the API structure
- Robust error handling with custom exceptions
- Data validation and rich type-hinting powered by Pydantic

## Installation

Install the library directly from PyPI:

```bash
pip install trendsagi
```

## Getting Started

### Authentication

First, you'll need a TrendsAGI account and an API key. You can sign up and generate a key from your dashboard.

We strongly recommend storing your API key as an environment variable to avoid committing it to version control.

```bash
export TRENDSAGI_API_KEY="your_api_key_here"
```

### Quickstart Example

This example demonstrates how to initialize the client and fetch the latest trending topics.

```python
import os
import trendsagi
from trendsagi import exceptions

# It's recommended to load your API key from an environment variable
API_KEY = os.environ.get("TRENDSAGI_API_KEY")

if not API_KEY:
    raise ValueError("Please set the TRENDSAGI_API_KEY environment variable.")

# Initialize the client
client = trendsagi.TrendsAGIClient(api_key=API_KEY)

try:
    # Get the top 5 trending topics from the last 24 hours
    print("Fetching top 5 trending topics...")
    response = client.get_trends(limit=5, period='24h')

    print(f"\nFound {response.meta.total} total trends. Displaying the top {len(response.trends)}:")
    for trend in response.trends:
        print(f"- ID: {trend.id}, Name: '{trend.name}', Volume: {trend.volume}")

except exceptions.AuthenticationError:
    print("Authentication failed. Please check your API key.")
except exceptions.APIError as e:
    print(f"An API error occurred: Status {e.status_code}, Details: {e.error_detail}")
except exceptions.TrendsAGIError as e:
    print(f"A client-side error occurred: {e}")
```

## Usage Examples

### Get AI-Powered Insights for a Trend

Retrieve AI-generated insights for a specific trend, such as key themes, target audiences, and content ideas.

```python
# Assuming 'client' is an initialized TrendsAGIClient
# and you have a trend_id from a call to get_trends()
TREND_ID = 12345 

try:
    print(f"\nGetting AI insights for trend ID {TREND_ID}...")
    ai_insight = client.get_ai_insights(trend_id=TREND_ID)
    
    if ai_insight:
        print(f"  Sentiment: {ai_insight.sentiment_category}")
        print("  Key Themes:")
        for theme in ai_insight.key_themes[:3]:  # show first 3
            print(f"    - {theme}")
        print("  Suggested Content Angle:")
        print(f"    - {ai_insight.content_brief.key_angles_for_content[0]}")
        
except exceptions.NotFoundError:
    print(f"Trend with ID {TREND_ID} not found.")
except exceptions.APIError as e:
    print(f"An API error occurred: {e}")
```

### Perform a Deep Analysis on a Topic

```python
# Assuming 'client' is an initialized TrendsAGIClient
try:
    print("\nPerforming deep analysis on 'artificial intelligence'...")
    analysis = client.perform_deep_analysis(
        query="artificial intelligence",
        analysis_type="comprehensive"
    )
    
    print(f"Analysis completed. Key findings:")
    print(f"- Market sentiment: {analysis.market_sentiment}")
    print(f"- Growth trajectory: {analysis.growth_projection}")
    print(f"- Key influencers: {', '.join(analysis.top_influencers[:3])}")
    
except exceptions.APIError as e:
    print(f"An API error occurred: {e}")
```

### Track an X (Twitter) User

Add a user to your tracked market entities in the Intelligence Suite.

```python
# Assuming 'client' is an initialized TrendsAGIClient
try:
    print("\nAdding a new X user to track...")
    new_entity = client.create_tracked_x_user(
        handle="OpenAI",
        name="OpenAI",
        notes="Key player in the AI industry."
    )
    print(f"Successfully started tracking '{new_entity.name}' (ID: {new_entity.id})")

except exceptions.ConflictError:
    print("This user is already being tracked.")
except exceptions.APIError as e:
    print(f"An API error occurred: {e}")
```

### Monitor for Crisis Events

Retrieve any active crisis events detected by the system.

```python
# Assuming 'client' is an initialized TrendsAGIClient
try:
    print("\nChecking for active crisis events...")
    crisis_response = client.get_crisis_events(status='active', limit=5)

    if not crisis_response.events:
        print("No active crisis events found.")
    else:
        for event in crisis_response.events:
            print(f"- [SEVERITY: {event.severity}] {event.title}")
            print(f"  Summary: {event.summary}\n")

except exceptions.APIError as e:
    print(f"An API error occurred: {e}")
```

## Handling Errors and Exceptions

The library raises specific exceptions for different types of errors, all inheriting from `trendsagi.exceptions.TrendsAGIError`. This allows for granular error handling.

- **`TrendsAGIError`**: The base exception for all library-specific errors
- **`AuthenticationError`**: Raised on 401 errors for an invalid or missing API key
- **`APIError`**: The base class for all non-2xx API responses
- **`NotFoundError`**: Raised on 404 errors when a resource is not found
- **`ConflictError`**: Raised on 409 errors, e.g., when trying to create a resource that already exists
- **`RateLimitError`**: Raised on 429 errors when you have exceeded your API rate limit

Example error handling:

```python
try:
    response = client.get_trends()
except exceptions.AuthenticationError:
    print("Invalid API key. Please check your credentials.")
except exceptions.RateLimitError as e:
    print(f"Rate limit exceeded. Retry after: {e.retry_after} seconds")
except exceptions.NotFoundError:
    print("The requested resource was not found.")
except exceptions.APIError as e:
    print(f"API error: {e.status_code} - {e.error_detail}")
except exceptions.TrendsAGIError as e:
    print(f"Client error: {e}")
```

## Advanced Usage

### Working with Pagination

```python
# Get all trends with pagination
all_trends = []
page = 1
while True:
    response = client.get_trends(page=page, limit=100)
    all_trends.extend(response.trends)
    
    if page >= response.meta.total_pages:
        break
    page += 1

print(f"Retrieved {len(all_trends)} total trends")
```

### Setting Up Alerts

```python
# Create a new trend alert
alert = client.create_alert(
    name="AI Technology Alert",
    keywords=["artificial intelligence", "machine learning", "AI"],
    threshold_volume=1000,
    notification_method="email"
)
print(f"Created alert: {alert.name} (ID: {alert.id})")
```

### Export Data

```python
# Export trend data to CSV
export_job = client.export_trends(
    format="csv",
    date_range="last_7_days",
    filters={"category": "technology"}
)
print(f"Export job started: {export_job.job_id}")

# Check export status
status = client.get_export_status(export_job.job_id)
if status.is_complete:
    print(f"Export ready for download: {status.download_url}")
```

## Full API Documentation

This library is a client for the TrendsAGI REST API. For complete details on all available API endpoints, parameters, data models, rate limits, and best practices, please refer to our official [API Documentation](https://trendsagi.com/api-docs).

## Contributing

Contributions are welcome! If you find a bug or have a feature request, please open an issue on our GitHub Issues page. If you'd like to contribute code, please fork the repository and open a pull request.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone the repository
git clone https://github.com/trendsagi/TrendsAGI.git
cd TrendsAGI

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
flake8 trendsagi/
mypy trendsagi/
```

## Support


- **API Reference**: [https://trendsagi.com/api-docs](https://trendsagi.com/api-docs)
- **Support Email**: contact@trendsagi.com
- **GitHub Issues**: [https://github.com/TrendsAGI/TrendsAGI/issues](https://github.com/TrendsAGI/TrendsAGI/issues)


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built with ❤️ by the TrendsAGI Team**