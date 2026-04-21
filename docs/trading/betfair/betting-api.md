# Betfair Betting API Reference

Source: [Betfair Developer Documentation](https://betfair-developer-docs.atlassian.net/wiki/spaces/1smk3cen4v3lu3yomq5qye0ni/pages/2687158/Betting+API)

## Endpoints

All API requests should be sent as **POST**.

### Global Exchange

| Interface | Endpoint | JSON-RPC Prefix | Example |
|-----------|----------|-----------------|---------|
| JSON-RPC | `https://api.betfair.com/exchange/betting/json-rpc/v1` | `SportsAPING/v1.0/` | `SportsAPING/v1.0/listMarketBook` |
| JSON REST | `https://api.betfair.com/exchange/betting/rest/v1.0/` | N/A | `listMarketBook/` |

### New Zealand Customers

| Interface | Endpoint | JSON-RPC Prefix | Example |
|-----------|----------|-----------------|---------|
| JSON-RPC | `https://api.betfair.com.au/exchange/betting/json-rpc/v1` | `SportsAPING/v1.0/` | `SportsAPING/v1.0/listMarketBook` |
| JSON REST | `https://api.betfair.com.au/exchange/betting/rest/v1.0/` | N/A | `listMarketBook/` |

> **Note:** If you have an Italian or Spanish Exchange account, see separate documentation for those exchanges.

---

## Operation Summary

### Event & Competition Operations

| Return Type | Operation | Description |
|-------------|-----------|-------------|
| `List<EventTypeResult>` | `listEventTypes(MarketFilter filter, String locale)` | Returns a list of Event Types (i.e. Sports) associated with the markets selected by the MarketFilter |
| `List<CompetitionResult>` | `listCompetitions(MarketFilter filter, String locale)` | Returns a list of Competitions (i.e., World Cup 2013) associated with the markets selected by the MarketFilter. **Note:** Horse racing & greyhounds are not associated with competitions, only Venues |
| `List<EventResult>` | `listEvents(MarketFilter filter, String locale)` | Returns a list of Events (i.e, Reading vs. Man United) associated with the markets selected by the MarketFilter |
| `List<TimeRangeResult>` | `listTimeRanges(MarketFilter filter, TimeGranularity granularity)` | Returns a list of time ranges in the granularity specified in the request (i.e. 3PM to 4PM, Aug 14th to Aug 15th) |

### Market Operations

| Return Type | Operation | Description |
|-------------|-----------|-------------|
| `List<MarketTypeResult>` | `listMarketTypes(MarketFilter filter, String locale)` | Returns a list of market types (i.e. MATCH_ODDS, NEXT_GOAL) associated with the markets selected by the MarketFilter |
| `List<CountryCodeResult>` | `listCountries(MarketFilter filter, String locale)` | Returns a list of Countries associated with the markets selected by the MarketFilter |
| `List<VenueResult>` | `listVenues(MarketFilter filter, String locale)` | Returns a list of Venues (i.e. Cheltenham, Ascot). **Note:** Only horse racing & greyhound markets are associated with a Venue |
| `List<MarketCatalogue>` | `listMarketCatalogue(MarketFilter filter, Set<MarketProjection> marketProjection, MarketSort sort, int maxResults, String locale)` | Returns a list of information about published (ACTIVE/SUSPENDED) markets that does not change (or changes very rarely) |
| `List<MarketBook>` | `listMarketBook(List<String> marketIds, PriceProjection priceProjection, OrderProjection orderProjection, MatchProjection matchProjection, String currencyCode, String locale, Date matchedSince, Set<BetId> betIds)` | Returns a list of dynamic data about markets. Dynamic data includes prices, the status of the market, the status of selections, the traded volume, and the status of any orders you have placed in the market |
| `List<MarketBook>` | `listRunnerBook(MarketId marketId, SelectionId selectionId, double handicap, PriceProjection priceProjection, OrderProjection orderProjection, MatchProjection matchProjection, boolean includeOverallPosition, boolean partitionMatchedByStrategyRef, Set<String> customerStrategyRefs, String currencyCode, String locale, Date matchedSince, Set<BetId> betIds)` | Returns a list of dynamic data about a market and a specified runner |
| `List<MarketProfitAndLoss>` | `listMarketProfitAndLoss(Set<MarketId> marketIds, boolean includeSettledBets, boolean includeBspBets, boolean netOfCommission)` | Retrieve profit and loss for a given list of OPEN markets. The values are calculated using matched bets and optionally settled bets |

### Order Operations

| Return Type | Operation | Description |
|-------------|-----------|-------------|
| `CurrentOrderSummaryReport` | `listCurrentOrders(Set<String> betIds, Set<String> marketIds, OrderProjection orderProjection, TimeRange placedDateRange, OrderBy orderBy, SortDir sortDir, int fromRecord, int recordCount)` | Returns a list of your current orders |
| `ClearedOrderSummaryReport` | `listClearedOrders(BetStatus betStatus, Set<EventTypeId> eventTypeIds, Set<EventId> eventIds, Set<MarketId> marketIds, Set<RunnerId> runnerIds, Set<BetId> betIds, Side side, TimeRange settledDateRange, GroupBy groupBy, boolean includeItemDescription, String locale, int fromRecord, int recordCount)` | Returns a list of settled bets based on the bet status, ordered by settled date |
| `PlaceExecutionReport` | `placeOrders(String marketId, List<PlaceInstruction> instructions, String customerRef, MarketVersion marketVersion, String customerStrategyRef, boolean async)` | Place new orders into market |
| `CancelExecutionReport` | `cancelOrders(String marketId, List<CancelInstruction> instructions, String customerRef)` | Cancel all bets OR cancel all bets on a market OR fully or partially cancel particular orders on a market |
| `ReplaceExecutionReport` | `replaceOrders(String marketId, List<ReplaceInstruction> instructions, String customerRef, MarketVersion marketVersion, boolean async)` | This operation is logically a bulk cancel followed by a bulk place. The cancel is completed first then the new orders are placed |
| `UpdateExecutionReport` | `updateOrders(String marketId, List<UpdateInstruction> instructions, String customerRef)` | Update non-exposure changing fields |

---

## Related Documentation

- [Betting Enums](./betting-enums.md)
- [Betting Exceptions](./betting-exceptions.md)
- [Betting Type Definitions](./betting-type-definitions.md)
