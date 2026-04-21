# Betfair API - Getting Started

Source: [Betfair Developer Documentation](https://betfair-developer-docs.atlassian.net/wiki/spaces/1smk3cen4v3lu3yomq5qye0ni/pages/2687786/Getting+Started)

## Table of Contents

- [Login](#login)
- [Request Headers](#request-headers)
- [API Endpoints](#api-endpoints)
- [Betting API](#betting-api)
- [Account API](#account-api)
- [JSON](#json)
- [JSON-RPC](#json-rpc)
- [Example Requests](#example-requests)
- [Sample Code & Client Libraries](#sample-code-client-libraries--tutorials)

---

## Login

The Betfair API offers three login flows for developers, depending on the use case of your application:

1. **Non-Interactive login** - if you are building an application that will run autonomously, there is a separate login flow to follow to ensure your account remains secure.

2. **Interactive login** - if you are building an application that will be used interactively, then this is the flow for you. This flow has two variants:
   - **Interactive login - API method** - This flow makes use of a JSON API Endpoint and is the simplest way to get started if you are looking to create your own login form.
   - **Interactive login - Desktop Application** - This login flow makes use of Betfair's login pages and allows your app to gracefully handle all errors and re-directions in the same way as the Betfair website.

---

## Request Headers

All requests must include the following HTTP headers:

| Header | Value | Description |
|--------|-------|-------------|
| `X-Application` | Your Application Key | The Application Key assigned to you |
| `X-Authentication` | Your Session Token | Your sessionToken from login |
| `Accept` | `application/json` | Required content type |

> **Note:** The only exceptions to the above are some of the Account Operations (Vendor API) which require the `X-Authentication` HTTP header only.

---

## API Endpoints

You can make requests and place bets on UK & international markets by accessing the Global Exchange via the following endpoints.

**All API requests should be sent as POST.**

---

## Betting API

The current Betting API endpoints for the Global Exchange:

| Interface | Endpoint | JSON-RPC Prefix | Example |
|-----------|----------|-----------------|---------|
| JSON-RPC | `https://api.betfair.com/exchange/betting/json-rpc/v1` | `SportsAPING/v1.0/` | `SportsAPING/v1.0/listMarketBook` |
| JSON REST | `https://api.betfair.com/exchange/betting/rest/v1.0/` | N/A | `listMarketBook/` |

---

## Account API

The current Accounts API endpoints for the Global Exchange (UK Exchange wallet information):

| Interface | Endpoint | JSON-RPC Prefix | Example |
|-----------|----------|-----------------|---------|
| JSON-RPC | `https://api.betfair.com/exchange/account/json-rpc/v1` | `AccountAPING/v1.0/` | `AccountAPING/v1.0/getAccountFunds` |
| JSON REST | `https://api.betfair.com/exchange/account/rest/v1.0/` | N/A | `getAccountFunds/` |

---

## Spanish & Italian Exchange

Please see separate documentation for the Spanish & Italian Exchange.

---

## JSON

You can POST a request to the API at:

```
https://api.betfair.com/exchange/betting/rest/v1.0/<operation name>
```

So, to call the `listEventTypes` method, you would POST to:

```
https://api.betfair.com/exchange/betting/rest/v1.0/listEventTypes/
```

The POST data contains the request parameters. For `listEventTypes`, the only required parameter is a filter to select markets. You can pass an empty filter to select all markets, in which case `listEventTypes` returns the EventTypes associated with all available markets.

### JSON POST Data

```json
{
    "filter": {}
}
```

### Python Example JSON Request

```python
import requests
import json

endpoint = "https://api.betfair.com/exchange/betting/rest/v1.0/"

header = {
    'X-Application': 'APP_KEY_HERE',
    'X-Authentication': 'SESSION_TOKEN_HERE',
    'content-type': 'application/json'
}

json_req = '{"filter":{ }}'

url = endpoint + "listEventTypes/"
response = requests.post(url, data=json_req, headers=header)

print(json.dumps(json.loads(response.text), indent=3))
```

---

## JSON-RPC

You can POST a request to the API using JSON-RPC at:

```
https://api.betfair.com/exchange/betting/json-rpc/v1
```

The POST data should contain a valid JSON-RPC formatted request where:
- The `params` field contains the request parameters
- The `method` field contains the API method you are calling, specified like `SportsAPING/v1.0/<operation name>`

### Example JSON-RPC POST Data

For calling the `listCompetitions` operation and passing in a filter to find all markets with a corresponding event type id of 1 (i.e., all Football markets):

```json
{
    "params": {
        "filter": {
            "eventTypeIds": [1]
        }
    },
    "jsonrpc": "2.0",
    "method": "SportsAPING/v1.0/listCompetitions",
    "id": 1
}
```

### JSON-RPC Python Example

```python
import requests
import json

url = "https://api.betfair.com/exchange/betting/json-rpc/v1"

header = {
    'X-Application': 'APP_KEY_HERE',
    'X-Authentication': 'SESSION_TOKEN',
    'content-type': 'application/json'
}

jsonrpc_req = '{"jsonrpc": "2.0", "method": "SportsAPING/v1.0/listEventTypes", "params": {"filter":{ }}, "id": 1}'

response = requests.post(url, data=jsonrpc_req, headers=header)
print(json.dumps(json.loads(response.text), indent=3))
```

### EventTypeResult Response Example

```json
{
    "jsonrpc": "2.0",
    "result": [
        {
            "eventType": {
                "id": "1",
                "name": "Soccer"
            },
            "marketCount": 25388
        },
        {
            "eventType": {
                "id": "7",
                "name": "Horse Racing"
            },
            "marketCount": 398
        },
        {
            "eventType": {
                "id": "2",
                "name": "Tennis"
            },
            "marketCount": 402
        }
        // ... more event types
    ],
    "id": 1
}
```

---

## Example Requests

This section shows how you might call the Betting API to retrieve information. All examples are in JSON-RPC format.

### Request A List Of Available Event Types

Use the `listEventTypes` service to return eventTypes (e.g. Soccer, Horse Racing etc.) currently available on Betfair.

**Request:**
```json
{
    "jsonrpc": "2.0",
    "method": "SportsAPING/v1.0/listEventTypes",
    "params": {
        "filter": {}
    },
    "id": 1
}
```

### Request a List of Events for an Event Type

Use `listEvents` to retrieve a list of events (eventIds) for a specific event type. This example retrieves all Soccer events for a single day.

**Request:**
```json
{
    "jsonrpc": "2.0",
    "method": "SportsAPING/v1.0/listEvents",
    "params": {
        "filter": {
            "eventTypeIds": ["1"],
            "marketStartTime": {
                "from": "2014-03-13T00:00:00Z",
                "to": "2014-03-13T23:59:00Z"
            }
        }
    },
    "id": 1
}
```

### Request the Market Information for an Event

Use `listMarketCatalogue` to retrieve all the market information that belongs to an event (excluding price data).

**Request:**
```json
{
    "jsonrpc": "2.0",
    "method": "SportsAPING/v1.0/listMarketCatalogue",
    "params": {
        "filter": {
            "eventIds": ["27165685"]
        },
        "maxResults": "200",
        "marketProjection": [
            "COMPETITION",
            "EVENT",
            "EVENT_TYPE",
            "MARKET_START_TIME",
            "MARKET_DESCRIPTION",
            "RUNNER_DESCRIPTION",
            "RUNNER_METADATA"
        ]
    },
    "id": 1
}
```

### Horse Racing - Today's Win & Place Markets

Retrieve the available win/place horse racing markets for a specific day:

**Request:**
```json
{
    "jsonrpc": "2.0",
    "method": "SportsAPING/v1.0/listMarketCatalogue",
    "params": {
        "filter": {
            "eventTypeIds": ["7"],
            "marketTypeCodes": ["WIN", "PLACE"],
            "marketStartTime": {
                "from": "2014-03-13T00:00:00Z",
                "to": "2014-03-13T23:59:00Z"
            }
        },
        "sort": "FIRST_TO_START",
        "maxResults": "200",
        "marketProjection": [
            "COMPETITION",
            "EVENT",
            "EVENT_TYPE",
            "MARKET_START_TIME",
            "MARKET_DESCRIPTION",
            "RUNNER_DESCRIPTION",
            "RUNNER_METADATA"
        ]
    },
    "id": 1
}
```

### Request a List of Football Competitions

**Request:**
```json
{
    "jsonrpc": "2.0",
    "method": "SportsAPING/v1.0/listCompetitions",
    "params": {
        "filter": {
            "eventTypeIds": ["1"]
        }
    },
    "id": 1
}
```

The filter selects all markets that have an eventTypeId of 1 (Football), then returns a list of Competitions with their Ids and market counts.

### Request Market Prices

Once you have identified the market (marketId) using `listMarketCatalogue`, you can request prices using `listMarketBook`.

**Request (best prices and trading volume including virtual bets):**
```json
{
    "jsonrpc": "2.0",
    "method": "SportsAPING/v1.0/listMarketBook",
    "params": {
        "marketIds": ["1.109850906"],
        "priceProjection": {
            "priceData": ["EX_BEST_OFFERS", "EX_TRADED"],
            "virtualise": "true"
        }
    },
    "id": 1
}
```

---

## Placing Bets

### Placing a Normal Bet

To place a bet you require the `marketId` and `selectionId` parameters from the `listMarketCatalogue` API call.

**Request (back bet at odds of 3.0 for stake of £2.0):**
```json
{
    "jsonrpc": "2.0",
    "method": "SportsAPING/v1.0/placeOrders",
    "params": {
        "marketId": "1.109850906",
        "instructions": [
            {
                "selectionId": "6082482",
                "handicap": "0",
                "side": "BACK",
                "orderType": "LIMIT",
                "limitOrder": {
                    "size": "2",
                    "price": "3",
                    "persistenceType": "LAPSE"
                }
            }
        ]
    },
    "id": 1
}
```

**Response (success):**
```json
{
    "jsonrpc": "2.0",
    "result": {
        "status": "SUCCESS",
        "marketId": "1.109850906",
        "instructionReports": [
            {
                "status": "SUCCESS",
                "instruction": {
                    "selectionId": 6082482,
                    "handicap": 0,
                    "limitOrder": {
                        "size": 2,
                        "price": 3,
                        "persistenceType": "LAPSE"
                    },
                    "orderType": "LIMIT",
                    "side": "BACK"
                },
                "betId": "30580539628",
                "placedDate": "2014-03-12T14:19:41.000Z",
                "averagePriceMatched": 0,
                "sizeMatched": 0
            }
        ]
    },
    "id": 1
}
```

### Placing a Keep Bet

A Keep bet remains unmatched until matched/cancelled.

**Request:**
```json
{
    "jsonrpc": "2.0",
    "method": "SportsAPING/v1.0/placeOrders",
    "params": {
        "marketId": "1.109850906",
        "instructions": [
            {
                "selectionId": "6082482",
                "handicap": "0",
                "side": "BACK",
                "orderType": "LIMIT",
                "limitOrder": {
                    "size": "2",
                    "price": "1000",
                    "persistenceType": "PERSIST",
                    "timeInForce": "GOOD_TILL_CANCELLED"
                }
            }
        ]
    },
    "id": 1
}
```

### Placing a Betfair SP Bet - MARKET_ON_CLOSE

**Request (SP back bet for stake of £2.00):**
```json
{
    "jsonrpc": "2.0",
    "method": "SportsAPING/v1.0/placeOrders",
    "params": {
        "marketId": "1.113231103",
        "instructions": [
            {
                "selectionId": "7389516",
                "handicap": "0",
                "side": "BACK",
                "orderType": "MARKET_ON_CLOSE",
                "marketOnCloseOrder": {
                    "liability": "2"
                }
            }
        ]
    },
    "id": 1
}
```

### Placing a Betfair SP Bet - LIMIT_ON_CLOSE

Refer to Additional Information for Min BSP liability.

---

## Retrieving Bet Information

### Retrieving Details of Bets Placed on a Market

Use `listCurrentOrders` to retrieve bets placed on a specific market.

**Request:**
```json
{
    "jsonrpc": "2.0",
    "method": "SportsAPING/v1.0/listCurrentOrders",
    "params": {
        "marketIds": ["1.109850906"]
    },
    "id": 1
}
```

### Retrieving the Result of a Settled Market

Request `listMarketBook` **after** the market has been settled. The response will indicate whether the selection was settled as a 'WINNER' or 'LOSER' in the runners 'status' field.

> **Note:** Settled market information is available for 90 days after settlement.

### Retrieving Details of Settled Bets (including P&L & Commission)

Use `listClearedOrders` with a specific `settledDateRange` and `groupBy MARKET` to group results at marketId level.

**Request:**
```json
{
    "jsonrpc": "2.0",
    "method": "SportsAPING/v1.0/listClearedOrders",
    "params": {
        "betStatus": "SETTLED",
        "settledDateRange": {
            "from": "2014-03-01T00:00:00Z",
            "to": "2014-03-12T23:59:00Z"
        },
        "groupBy": "MARKET"
    },
    "id": 1
}
```

---

## Sample Code, Client Libraries & Tutorials

As well as sample code developed by Betfair, this page allows you to find sample code or documentation prepared by members of the Developer Program community.

### Betfair-developed Sample Workflow

1. Authenticate using one of the login methods
2. Retrieve available event types
3. Retrieve events for a specific event type
4. Retrieve market catalogue
5. Retrieve market prices
6. Place orders

> **Note:** Basic Betfair samples are not intended to show certain best practices for speed and throughput. Well-designed applications should:
> - Request gzip'd responses
> - Use HTTP connection keep-alives
> - See "Optimizing API Application Performance" for further details

### Available Sample Code

- Client Libraries & Sample Applications
- Stream API code samples
- Historical Data processing code (via https://historicdata.betfair.com)
- Tutorials

---

## Related Documentation

- [Application Keys](../application-keys.md)
- [Login & Session Management](../login-session-management.md)
- [Best Practice](../best-practice.md)
- [Market Data Request Limits](../market-data-limits.md)
- [Reference Guide](../reference-guide.md)
- [Exchange Stream API](../exchange-stream-api.md)
