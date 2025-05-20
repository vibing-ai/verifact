# VeriFact API Documentation

This document provides detailed documentation for the VeriFact API endpoints.

## Model Provider

VeriFact uses OpenRouter to access various AI models through a unified API. All API requests are processed using models configured in the environment settings.

### OpenRouter Integration

- Requests are processed using free tier models from OpenRouter
- Each agent type uses a specialized model optimized for its task
- API response times may vary based on model queue times
- Rate limits apply based on OpenRouter's free tier restrictions

### Free Tier Considerations

- Limited requests per minute/hour may apply
- Fallback mechanisms are in place if a model is unavailable
- Processing time may be longer during high-demand periods

## OpenAPI/Swagger Documentation

VeriFact now provides interactive API documentation using OpenAPI/Swagger. You can access it at:

```
http://localhost:8000/api/docs
```

For ReDoc version (more readable):

```
http://localhost:8000/api/redoc
```

The OpenAPI documentation allows you to:

- Browse all available endpoints
- See request and response schemas
- Try out API calls directly from the browser
- Download the OpenAPI specification in JSON format at `/api/openapi.json`

When the API is deployed to production, these endpoints will be available at the base URL of the deployment.

## Base URL

```
https://api.verifact.example.com/v1
```

For local development:

```
http://localhost:8000/v1
```

## Authentication

The API uses API key authentication. Include your API key in the header of all requests:

```
Authorization: Bearer YOUR_API_KEY
```

## Endpoints

### Factcheck

#### POST /factcheck

Submits text for factchecking and returns detected claims with verdicts.

**Request**

```http
POST /factcheck
Content-Type: application/json
Authorization: Bearer YOUR_API_KEY

{
  "text": "The Earth is approximately 4.54 billion years old. Mount Everest is the highest mountain on Earth.",
  "options": {
    "min_check_worthiness": 0.7,
    "domains": ["science", "geography"],
    "max_claims": 5,
    "explanation_detail": "detailed"
  }
}
```

**Parameters**

| Name                         | Type     | Required | Description                                                                        |
| ---------------------------- | -------- | -------- | ---------------------------------------------------------------------------------- |
| text                         | string   | Yes      | The text containing claims to be fact-checked                                      |
| options.min_check_worthiness | float    | No       | Minimum threshold (0-1) for claim check-worthiness. Default: 0.7                   |
| options.domains              | string[] | No       | Specific domains to focus on (e.g., "politics", "science")                         |
| options.max_claims           | integer  | No       | Maximum number of claims to process. Default: 5                                    |
| options.explanation_detail   | string   | No       | Level of explanation detail ("brief", "standard", "detailed"). Default: "standard" |

**Response**

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "claims": [
    {
      "text": "The Earth is approximately 4.54 billion years old.",
      "verdict": "True",
      "confidence": 0.95,
      "explanation": "Scientific evidence from radiometric dating of meteorites and Earth's oldest minerals confirms the Earth is 4.54 billion years old with an error margin of about 1%.",
      "sources": [
        {
          "url": "https://example.com/earth-age",
          "credibility": 0.95,
          "quote": "Scientists have determined that the Earth is 4.54 billion years old with an error range of less than 1 percent."
        }
      ]
    },
    {
      "text": "Mount Everest is the highest mountain on Earth.",
      "verdict": "True",
      "confidence": 0.99,
      "explanation": "Mount Everest is indeed the highest mountain on Earth when measured from sea level, with a height of 8,848.86 meters (29,031.7 feet).",
      "sources": [
        {
          "url": "https://example.com/mount-everest",
          "credibility": 0.98,
          "quote": "Mount Everest, at 8,848.86 meters (29,031.7 feet), is the Earth's highest mountain above sea level."
        }
      ]
    }
  ],
  "metadata": {
    "processing_time": "2.3s",
    "model_version": "1.0.4",
    "claims_detected": 2,
    "claims_processed": 2
  }
}
```

**Status Codes**

| Status Code | Description                                        |
| ----------- | -------------------------------------------------- |
| 200         | Success                                            |
| 400         | Bad Request - Invalid input parameters             |
| 401         | Unauthorized - Invalid or missing API key          |
| 422         | Unprocessable Entity - Text could not be processed |
| 429         | Too Many Requests - Rate limit exceeded            |
| 500         | Internal Server Error                              |

### Claims

#### GET /claims

Retrieves previously processed claims.

**Request**

```http
GET /claims?limit=10&offset=0
Authorization: Bearer YOUR_API_KEY
```

**Parameters**

| Name    | Type    | Required | Description                                                   |
| ------- | ------- | -------- | ------------------------------------------------------------- |
| limit   | integer | No       | Maximum number of claims to return. Default: 10               |
| offset  | integer | No       | Number of claims to skip. Default: 0                          |
| verdict | string  | No       | Filter by verdict (true, false, partially_true, unverifiable) |

**Response**

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "claims": [
    {
      "id": "claim123",
      "text": "The Earth is approximately 4.54 billion years old.",
      "verdict": "True",
      "processed_at": "2023-05-15T14:30:45Z"
    },
    {
      "id": "claim124",
      "text": "Mount Everest is the highest mountain on Earth.",
      "verdict": "True",
      "processed_at": "2023-05-15T14:30:46Z"
    }
  ],
  "pagination": {
    "total": 24,
    "limit": 10,
    "offset": 0,
    "next": "/v1/claims?limit=10&offset=10"
  }
}
```

#### GET /claims/{claim_id}

Retrieves detailed information about a specific claim.

**Request**

```http
GET /claims/claim123
Authorization: Bearer YOUR_API_KEY
```

**Response**

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "claim123",
  "text": "The Earth is approximately 4.54 billion years old.",
  "original_context": "The Earth is approximately 4.54 billion years old. Mount Everest is the highest mountain on Earth.",
  "verdict": "True",
  "confidence": 0.95,
  "explanation": "Scientific evidence from radiometric dating of meteorites and Earth's oldest minerals confirms the Earth is 4.54 billion years old with an error margin of about 1%.",
  "sources": [
    {
      "url": "https://example.com/earth-age",
      "credibility": 0.95,
      "quote": "Scientists have determined that the Earth is 4.54 billion years old with an error range of less than 1 percent."
    }
  ],
  "processed_at": "2023-05-15T14:30:45Z"
}
```

## Error Responses

All errors follow a standard format:

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": {
    "code": "invalid_request",
    "message": "The request was invalid",
    "details": "The 'text' field must not be empty"
  }
}
```

## Rate Limiting

The API has the following rate limits:

- 60 requests per minute
- 1000 requests per day

Rate limit information is included in the response headers:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1589555400
```

## Webhook Notifications

For long-running factchecks, you can receive notifications when processing is complete by registering a webhook:

#### POST /webhooks

**Request**

```http
POST /webhooks
Content-Type: application/json
Authorization: Bearer YOUR_API_KEY

{
  "url": "https://your-server.com/webhook-receiver",
  "events": ["factcheck.completed", "factcheck.failed"]
}
```

**Response**

```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "id": "webhook123",
  "url": "https://your-server.com/webhook-receiver",
  "events": ["factcheck.completed", "factcheck.failed"],
  "created_at": "2023-05-15T14:35:42Z"
}
```

## OpenAPI Specification

A complete OpenAPI specification file is available at `/openapi.json`.

## Health Check Endpoint

VeriFact provides a health check endpoint for monitoring and operational status.

### GET /health

Returns the health status of the application and its dependencies.

**Parameters**

| Name | Type    | Required | Description                                  |
| ---- | ------- | -------- | -------------------------------------------- |
| full | boolean | No       | If true, includes detailed dependency checks |

**Response**

```json
{
  "status": "ok", // "ok", "degraded", or "error"
  "version": {
    // Version information
    "version": "1.0.0",
    "build_date": "2023-06-15",
    "git_hash": "a1b2c3d",
    "git_branch": "main"
  },
  "timestamp": 1621234567, // Current timestamp
  "uptime": 3600, // Seconds since system boot
  "request_time_ms": 15, // Time to process this request
  "dependencies": [
    // Only included if full=true
    {
      "name": "database",
      "type": "postgres",
      "status": "ok",
      "latency_ms": 5,
      "details": {
        "size": 5,
        "free_connections": 3,
        "used_connections": 2,
        "max_size": 10
      }
    },
    {
      "name": "redis",
      "type": "redis",
      "status": "ok",
      "latency_ms": 2,
      "details": {
        "version": "7.0.5",
        "used_memory_mb": 45.2,
        "clients_connected": 3
      }
    },
    {
      "name": "openrouter",
      "type": "api",
      "status": "ok",
      "latency_ms": 85,
      "details": {
        "status_code": 200
      }
    }
  ],
  "system": {
    // Only included if full=true
    "os": "Linux",
    "python_version": "3.10.4",
    "cpu_count": 4,
    "memory_total_mb": 8192,
    "memory_available_mb": 4096,
    "disk_free_mb": 20480
  }
}
```

**Use Cases**

- Kubernetes/container liveness and readiness probes
- Monitoring and alerting systems
- Load balancer health checks
- Debugging and operational visibility
