# Betfair Navigation Data For Applications

Source: [Betfair Developer Documentation](https://betfair-developer-docs.atlassian.net/wiki/spaces/1smk3cen4v3lu3yomq5qye0ni/pages/2687802/Navigation+Data+For+Applications)

## Overview

This Navigation Data service allows the retrieval of the full Betfair market navigation menu from a compressed file.

---

## Endpoints

| Exchange | HTTP Method | Endpoint |
|----------|-------------|----------|
| UK | GET | `https://api.betfair.com/exchange/betting/rest/v1/en/navigation/menu.json` |
| Italy | GET | `https://api.betfair.it/exchange/betting/rest/v1/it/navigation/menu.json` |
| Spain | GET | `https://api.betfair.es/exchange/betting/rest/v1/es/navigation/menu.json` |

---

## Required Headers

| Header | Description |
|--------|-------------|
| `X-Application` | Your Application Key |
| `X-Authentication` | Your session token, obtained from the API login response |
| `Accept` | `application/json` |
| `Accept-Encoding` | `gzip,deflate` |

---

## Best Practice

The file data is cached. **New requests for the file once an hour** should be suitable for those looking to accurately recreate the Betfair navigation menu.

---

## Example Request

```http
GET https://api.betfair.com/exchange/betting/rest/v1/en/navigation/menu.json
Connection: keep-alive
X-Application: <AppKey>
X-Authentication: <SessionToken>
Accept: application/json
Accept-Encoding: gzip,deflate
```

---

## Supported Locales

| Language | Code |
|----------|------|
| English | `en` or `en_GB` |
| Spanish | `es` |
| Italian | `it` |
| German | `de` |
| Swedish | `sv` |
| Portuguese | `pt` |
| Russian | `ru` |
| Danish | `da` |

---

## Navigation Data File Structure

- A **ROOT** group node has one or many **EVENT_TYPE** nodes
- An **EVENT_TYPE** node has zero, one or many **GROUP** nodes
- An **EVENT_TYPE** node has zero, one or many **EVENT** nodes
- A Horse Racing **EVENT_TYPE** node has zero, one or many **RACE** nodes
- A **RACE** node has one or many **MARKET** nodes
- A **GROUP** node has zero, one or many **EVENT** nodes
- A **GROUP** node has zero, one or many **GROUP** nodes
- An **EVENT** node has zero, one or many **MARKET** nodes
- An **EVENT** node has zero, one or many **GROUP** nodes
- An **EVENT** node has zero, one or many **EVENT** nodes

---

## JSON Model Structure

### ROOT

```json
{
    "children": [
        { "EVENT_TYPE1": "..." },
        { "EVENT_TYPE2": "..." }
    ],
    "id": 0,
    "name": "ROOT",
    "type": "GROUP"
}
```

| Field | Description |
|-------|-------------|
| `id` | Always 0 |
| `name` | Always "ROOT" |
| `type` | Always "GROUP" |
| `children` | Array of EVENT_TYPE nodes |

### EVENT_TYPE

```json
{
    "children": [
        { "GROUP or EVENT or RACE": "..." }
    ],
    "id": "1",
    "name": "Soccer",
    "type": "EVENT_TYPE"
}
```

| Field | Description |
|-------|-------------|
| `id` | Betfair specific eventTypeId (e.g., "1" for Soccer, "7" for Horse Racing) |
| `name` | Event type name |
| `type` | Always "EVENT_TYPE" |
| `children` | Array of GROUP, EVENT, or RACE nodes (RACE only for Greyhounds/Horse Racing) |

### GROUP

```json
{
    "children": [
        { "GROUP or EVENT": "..." }
    ],
    "id": "74568202414",
    "name": "Womens Soccer",
    "type": "GROUP"
}
```

| Field | Description |
|-------|-------------|
| `id` | Not a Betfair specific id (different for every GROUP) |
| `name` | Group name |
| `type` | Always "GROUP" |
| `children` | Array of GROUP or EVENT nodes |

### EVENT

```json
{
    "children": [
        { "GROUP, MARKET or EVENT": "..." }
    ],
    "id": "27244118",
    "name": "South Korea U20 (W) v Mexico U20 (W)",
    "countryCode": "GB",
    "type": "EVENT"
}
```

| Field | Description |
|-------|-------------|
| `id` | Betfair specific eventId |
| `name` | Event name |
| `countryCode` | ISO country code |
| `type` | Always "EVENT" |
| `children` | Array of GROUP, MARKET, or EVENT nodes |

### RACE

```json
{
    "children": [
        { "MARKET": "..." }
    ],
    "id": "27247020.1115",
    "name": "1300m 3yo",
    "startTime": "2014-08-12T11:15:00.000Z",
    "type": "RACE",
    "venue": "Deauville",
    "raceNumber": "R1",
    "countryCode": "GB"
}
```

| Field | Description |
|-------|-------------|
| `id` | Betfair specific raceId |
| `name` | Race name |
| `startTime` | Race start time (ISO 8601) |
| `type` | Always "RACE" |
| `venue` | Race venue |
| `raceNumber` | US specific race number (e.g., "R1") |
| `countryCode` | ISO country code |
| `children` | Array of MARKET nodes |

### MARKET

```json
{
    "exchangeId": "1",
    "id": "1.114881860",
    "marketStartTime": "2014-08-14T00:00:00.000Z",
    "marketType": "WIN",
    "numberOfWinners": "2",
    "name": "Over/Under 6.5 Goals",
    "type": "MARKET"
}
```

| Field | Description |
|-------|-------------|
| `exchangeId` | Betfair specific exchangeId |
| `id` | Betfair specific marketId |
| `marketStartTime` | Market start time (ISO 8601) |
| `marketType` | Betfair specific market type (e.g., WIN, PLACE, FORECAST) |
| `numberOfWinners` | Number of winners for this market |
| `name` | Market name |
| `type` | Always "MARKET" |

---

## Related Documentation

- [Getting Started](./getting-started.md)
- [Betting API](./betting-api.md)
