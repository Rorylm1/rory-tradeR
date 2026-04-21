# Betfair Exchange Stream API

Source: [Betfair Developer Documentation](https://betfair-developer-docs.atlassian.net/wiki/spaces/1smk3cen4v3lu3yomq5qye0ni/pages/2687396/Exchange+Stream+API)

## Overview

The Exchange Streaming API provides low latency access to Betfair Exchange market data allowing you to subscribe to and efficiently track changes to market, price, and order data.

- **Protocol:** SSL sockets with CRLF JSON protocol
- **Schema:** Available in Swagger format
- **Sample Code:** [GitHub - betfair/stream-api-sample-code](https://github.com/betfair/stream-api-sample-code)

---

## Connection

### Protocol

Every message is in JSON and terminated with a line feed (CRLF):

```
{json message}\r\n
```

### TCP / SSL Connection

| Environment | Endpoint |
|-------------|----------|
| External (SSL) | `stream-api.betfair.com:443` |
| Integration (Beta) | `stream-api-integration.betfair.com` |

> **Important:** Once you have established a connection, you should send a message within 15 seconds to avoid receiving a TIMEOUT error.

---

## Basic Message Protocol

### RequestMessage

Base class for requests from the client. The discriminator is `op=<message type>`.

| Operation | Message Type | Description |
|-----------|--------------|-------------|
| `op=authentication` | AuthenticationMessage | Authenticates your connection |
| `op=marketSubscription` | MarketSubscriptionMessage | Subscribes to market changes |
| `op=orderSubscription` | OrderSubscriptionMessage | Subscribes to order changes |
| `op=heartbeat` | HeartbeatMessage | Keep firewall open or test connectivity |

> **Important:**
> - Set `op=<message type>` - otherwise, we can't decode the request
> - Set `id=<unique sequence>` - this links requests with responses

### ResponseMessage

Base class for responses back to the client.

| Operation | Message Type | Description |
|-----------|--------------|-------------|
| `op=connection` | ConnectionMessage | Sent on connection |
| `op=status` | StatusMessage | Returned in response to every RequestMessage |
| `op=mcm` | MarketChangeMessage | Initial image and updates to markets subscribed |
| `op=ocm` | OrderChangeMessage | Initial image and updates to orders subscribed |

---

## Status / StatusMessage

Every request receives a status response with a matching `id`.

### Key Fields

| Field | Description |
|-------|-------------|
| `statusCode` | `SUCCESS` or `FAILURE` |
| `connectionClosed` | Boolean, true if connection was closed |
| `errorCode` | Type of error (see below) |
| `errorMessage` | Additional message in case of failure |
| `connectionsAvailable` | Number of additional connections you can open |

### Error Codes

| Category | ErrorCode | Description |
|----------|-----------|-------------|
| Protocol | `INVALID_INPUT` | Could not deserialize the message |
| Protocol | `TIMEOUT` | Client times out (too slow sending data) |
| Auth | `NO_APP_KEY` | Application key not found |
| Auth | `INVALID_APP_KEY` | Invalid application key |
| Auth | `NO_SESSION` | Session token not found |
| Auth | `INVALID_SESSION_INFORMATION` | Invalid session token |
| Auth | `NOT_AUTHORIZED` | Client not authorized |
| Auth | `MAX_CONNECTION_LIMIT_EXCEEDED` | Too many connections |
| Auth | `TOO_MANY_REQUESTS` | Too many requests in short time |
| Subscription | `SUBSCRIPTION_LIMIT_EXCEEDED` | Subscribed to more than 200 markets (default limit) |
| Subscription | `INVALID_CLOCK` | Invalid clock on re-subscription |
| General | `UNEXPECTED_ERROR` | Internal error (often client connectivity issues) |
| General | `CONNECTION_FAILED` | Connection terminated |

---

## Authentication / AuthenticationMessage

First message that the client must send after connecting.

```json
{
  "op": "authentication",
  "appKey": "YOUR_APP_KEY",
  "session": "YOUR_SESSION_TOKEN"
}
```

---

## Connection / ConnectionMessage

Received when successfully opening a connection.

```json
{
  "op": "connection",
  "connectionId": "002-230915140112-174"
}
```

> **Important:** The `connectionId` must be logged and supplied on any support queries.

---

## Subscription / SubscriptionMessage

### Key Fields

| Field | Description |
|-------|-------------|
| `segmentationEnabled` | Break up large messages, improves performance |
| `conflateMs` | Forced conflation rate in milliseconds (180000 for delayed keys) |
| `heartbeatMs` | Minimum interval to receive a message (500-5000ms) |
| `initialClk` / `clk` | Sequence tokens for faster recovery on reconnection |

---

## Market Subscription Message

### MarketFilter

| Filter | Type | Description |
|--------|------|-------------|
| `marketIds` | Set<String> | Specific market IDs (if empty, subscribe to all) |
| `bspMarket` | Boolean | Restrict to BSP markets only |
| `bettingTypes` | Set<BettingType> | ODDS, ASIAN_HANDICAP_SINGLES, etc. |
| `eventTypeIds` | Set<String> | Event type IDs (e.g., "1" for Football, "7" for Horse Racing) |
| `eventIds` | Set<String> | Specific event IDs |
| `turnInPlayEnabled` | Boolean | Markets that will turn in-play |
| `marketTypes` | Set<String> | Market types (MATCH_ODDS, HALF_TIME_SCORE, etc.) |
| `venues` | Set<String> | Venues (Horse Racing only) |
| `countryCodes` | Set<String> | ISO country codes (default: 'GB') |
| `raceTypes` | Set<String> | Race types: Harness, Flat, Hurdle, Chase, Bumper, NH Flat, Steeple |

### MarketDataFilter

| Filter | Fields | Description |
|--------|--------|-------------|
| `EX_BEST_OFFERS_DISP` | bdatb, bdatl | Best prices including Virtual Bets |
| `EX_BEST_OFFERS` | batb, batl | Best prices not including Virtual Bets |
| `EX_ALL_OFFERS` | atb, atl | Full available to BACK/LAY ladder |
| `EX_TRADED` | trd | Full traded ladder |
| `EX_TRADED_VOL` | tv | Market and runner level traded volume |
| `EX_LTP` | ltp | Last Price Matched |
| `EX_MARKET_DEF` | marketDefinition | Market definition |
| `SP_TRADED` | spb, spl | Starting price ladder |
| `SP_PROJECTED` | spn, spf | Starting price projection prices |

### Example Subscription

```json
{
  "op": "marketSubscription",
  "id": 2,
  "marketFilter": {
    "marketIds": ["1.120684740"],
    "eventTypeIds": ["1"],
    "turnInPlayEnabled": true,
    "marketTypes": ["MATCH_ODDS"],
    "countryCodes": ["ES"]
  },
  "marketDataFilter": {
    "ladderLevels": 2,
    "fields": ["EX_MARKET_DEF", "EX_BEST_OFFERS"]
  }
}
```

---

## Market Change Message (MCM)

### ChangeType

| Type | Description |
|------|-------------|
| `SUB_IMAGE` | Initial image from subscription (replace local cache) |
| `RESUB_DELTA` | Patch from resubscribe |
| `HEARTBEAT` | Empty message if no data within heartbeatMs |
| `null` | Update message |

### SegmentType

| Type | Description |
|------|-------------|
| `SEG_START` | Start of segmented message |
| `SEG` | Middle part |
| `SEG_END` | Last part |
| `null` | Non-segmented message |

### Key Fields

| Field | Description |
|-------|-------------|
| `tv` | Total amount matched across the market (truncated at 2dp) |
| `marketDefinition` | Sent in full if changed |
| `rc` | RunnerChange - runner details/prices |
| `con` | Conflated = true if multiple changes combined |

### Runner Change Values

| Field | Description |
|-------|-------------|
| `tv` | Traded Volume on this runner |
| `ltp` | Last Traded Price |
| `spn` | Starting Price Near |
| `spf` | Starting Price Far |
| `batb` / `batl` | Best Available To Back / Lay (non-virtual) |
| `bdatb` / `bdatl` | Best Display Available To Back / Lay (virtual) |
| `atb` / `atl` | Full depth Available To Back / Lay |
| `spb` / `spl` | Starting Price Available To Back / Lay |
| `trd` | Traded |

### Price Cache Rules

- `img=true`: Replace item in cache
- Level-based ladders: `[level, price, size]` - size=0 means remove
- Price-based ladders: `[price, size]` - size=0 means remove

---

## MarketDefinition Fields

| Field | Type | Description |
|-------|------|-------------|
| `Id` | string | Market ID |
| `Venue` | string | Venue (horse racing/greyhounds only) |
| `raceType` | string | Harness, Flat, Hurdle, Chase, etc. |
| `settledTime` | date-time | Market settled time |
| `timeZone` | string | Event timezone |
| `eachWayDivisor` | double | For EACH_WAY markets |
| `bspMarket` | boolean | Supports Betfair SP betting |
| `turnInPlayEnabled` | boolean | Will turn in-play |
| `persistenceEnabled` | boolean | Supports 'Keep' bets |
| `marketBaseRate` | double | Commission rate |
| `eventId` | string | Event ID |
| `eventTypeId` | string | Event type ID |
| `numberOfWinners` | integer | Winners on market |
| `countryCode` | string | ISO 3166-2 country code |
| `bettingType` | string | ODDS, ASIAN_HANDICAP_DOUBLE_LINE, etc. |
| `marketType` | string | Market base type |
| `marketTime` | string | Market start time |
| `inPlay` | boolean | Currently in play |
| `crossMatching` | boolean | Cross-matching enabled |
| `runnersVoidable` | boolean | Runners can be voided |
| `numberOfActiveRunners` | integer | Active selection count |
| `betDelay` | integer | Order hold time in seconds |
| `status` | string | OPEN, SUSPENDED, CLOSED, etc. |
| `suspendReason` | string | Soccer only: Goal, Penalty, Red Card, etc. |

---

## Order Subscription Message

Subscribes to order changes for your account.

```json
{
  "op": "orderSubscription",
  "id": 3
}
```

---

## Re-connection / Re-subscription

Use `initialClk` and `clk` tokens for faster recovery:
- Store these tokens when received
- Supply them on re-subscription with identical criteria
- Receive delta instead of full initial image

---

## Performance Considerations

- Use coarse grain subscriptions (subscribe to a super-set) rather than fine grain
- Correctly configure field filters to reduce initial image size and change rate
- Enable `segmentationEnabled=true` for better performance
- Set appropriate `heartbeatMs` for connection verification
- Set appropriate `conflateMs` for your use case

---

## Sample Code

Available at: https://github.com/betfair/stream-api-sample-code

- **C#** console application
- **Java** console application
- **Node.js** console application

### Swagger Code Generation

1. Download [swagger-codegen-cli-2.2.1.jar](https://oss.sonatype.org/content/repositories/releases/io/swagger/swagger-codegen-cli/2.2.1/swagger-codegen-cli-2.2.1.jar)
2. Download [ESASwaggerSchema.json](https://github.com/betfair/stream-api-sample-code/blob/master/ESASwaggerSchema.json)
3. Generate code:

```bash
java -jar swagger-codegen-cli-2.2.1.jar generate -i ESASwaggerSchema.json -l <LANGUAGE> -o <OUTPUT_DIRECTORY>
```

---

## Related Documentation

- [Getting Started](./getting-started.md)
- [Betting API](./betting-api.md)
- [Sample Code](./sample-code.md)
