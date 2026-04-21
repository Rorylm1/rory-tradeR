# Betfair Sample Code & Client Libraries

Source: [Betfair Developer Documentation](https://betfair-developer-docs.atlassian.net/wiki/spaces/1smk3cen4v3lu3yomq5qye0ni/pages/2687537/Sample+Code)

## Overview

This page contains sample code developed by Betfair and the Developer Program community.

**All Betfair-developed sample code follows a typical workflow:**
1. Find the next UK Horse Racing Win market
2. Get prices for the market
3. Place a bet on the market
4. Handle the error returned by the API when the bet fails (below minimum stake)

> **Note:** Basic Betfair samples are not intended to show certain best practices for speed and throughput. Well-designed applications should:
> - Request gzip'd responses
> - Use HTTP connection keep-alives
> - See [Optimizing API Application Performance](./optimizing-performance.md) for further details

---

## Official Betfair Sample Code

| Language | Repository | Description |
|----------|------------|-------------|
| Java | [github.com/betfair/API-NG-sample-code/tree/master/java](https://github.com/betfair/API-NG-sample-code/tree/master/java) | Sample Code for Java |
| JavaScript | [github.com/betfair/API-NG-sample-code/tree/master/javascript](https://github.com/betfair/API-NG-sample-code/tree/master/javascript) | Sample Code for Node.js |
| Python | [github.com/betfair/API-NG-sample-code/tree/master/python](https://github.com/betfair/API-NG-sample-code/tree/master/python) | Sample Code for Python |
| PHP | [github.com/betfair/API-NG-sample-code/tree/master/php](https://github.com/betfair/API-NG-sample-code/tree/master/php) | Sample Code for PHP |
| Excel/VBA | [github.com/betfair/API-NG-sample-code/tree/master/vba](https://github.com/betfair/API-NG-sample-code/tree/master/vba) | Sample Code for Excel/VBA |
| C# | [github.com/betfair/API-NG-sample-code/tree/master/cSharp](https://github.com/betfair/API-NG-sample-code/tree/master/cSharp) | Sample Code for C# |
| Curl | [github.com/betfair/API-NG-sample-code/tree/master/curl](https://github.com/betfair/API-NG-sample-code/tree/master/curl) | Sample Curl Requests |
| Perl | [github.com/betfair/API-NG-sample-code/tree/master/perl](https://github.com/betfair/API-NG-sample-code/tree/master/perl) | Sample Code for Perl |

---

## Community Client Libraries

| Language | Repository | Description | Developer |
|----------|------------|-------------|-----------|
| C# | [github.com/joelpob/betfairng](https://github.com/joelpob/betfairng) | API-NG Client Library for C# | joelpob |
| Java | [github.com/joelpob/jbetfairng](https://github.com/joelpob/jbetfairng) | Client library for Java | joelpob |
| Delphi | [github.com/jamiei/Betfair-API-NG-Sample](https://github.com/jamiei/Betfair-API-NG-Sample) | Sample Code for Delphi | jamiei |
| Delphi | [github.com/betfair/API-NG-Delphi-Client](https://github.com/betfair/API-NG-Delphi-Client) | API-NG Client Library for Delphi | khughes |
| Clojure | [github.com/jamiei/betfair-aping-sample](https://github.com/jamiei/betfair-aping-sample) | Sample Code for Clojure | jamiei |
| JavaScript | [github.com/AlgoTrader/betfair](https://github.com/AlgoTrader/betfair) | API-NG Client Library for Node.js | AlgoTrader |
| Perl | [github.com/MyrddinWyllt/WWW-BetfairNG](https://github.com/MyrddinWyllt/WWW-BetfairNG) | Perl Library for API-NG | MerlinP |
| PHP | [github.com/danieledangeli/betfair-php](https://github.com/danieledangeli/betfair-php) | API-NG Client Library for PHP | daniele8805 |
| Ruby | [github.com/mikecmpbll/betfair](https://github.com/mikecmpbll/betfair) | Ruby wrapper for API-NG | mikecmpbll |
| **Python** | [github.com/betcode-org/betfair](https://github.com/betcode-org/betfair) | **Lightweight Python wrapper for Betfair API-NG (with streaming)** | LiamP |
| **Python** | [github.com/betcode-org/flumine](https://github.com/betcode-org/flumine) | **Betting Trading Framework** | LiamP |
| Scala | [github.com/city81/betfair-service-ng](https://github.com/city81/betfair-service-ng) | Scala sample code for API-NG | theswan1 |
| R | [github.com/phillc73/abettor](https://github.com/phillc73/abettor) | Sample code for R | phill_c |
| C++ | [github.com/captain-igloo/greentop](https://github.com/captain-igloo/greentop) | C++ Betfair API Client | plachner |
| C++ | [github.com/tosinalagbe/hedg](https://github.com/tosinalagbe/hedg) | High-frequency trading framework for Betfair | tosin |
| Rust | [docs.rs/botfair/0.3.0/botfair/](https://docs.rs/botfair/0.3.0/botfair/) | Rust bindings for the Betfair API | esotericnonsense |
| Excel/VBA | [github.com/betfair/API-NG-Excel-Toolkit](https://github.com/betfair/API-NG-Excel-Toolkit) | Excel Sample Spreadsheet Application | Robin Barrett |

---

## Stream API Sample Code

| Language | Repository | Description |
|----------|------------|-------------|
| C# | [github.com/betfair/stream-api-sample-code/tree/master/csharp](https://github.com/betfair/stream-api-sample-code/tree/master/csharp) | Sample application for Stream API |
| Java | [github.com/betfair/stream-api-sample-code/tree/master/java](https://github.com/betfair/stream-api-sample-code/tree/master/java) | Sample application for Stream API |
| Node.js | [github.com/betfair/stream-api-sample-code/tree/master/node.js](https://github.com/betfair/stream-api-sample-code/tree/master/node.js) | Sample application for Stream API |

---

## Historical Data

Code for processing the data provided by the Betfair Exchange historical data service available via [historicdata.betfair.com](https://historicdata.betfair.com)

| Language | Repository | Description | Developer |
|----------|------------|-------------|-----------|
| Web Application | [betfairhistoricdata.co.uk](https://www.betfairhistoricdata.co.uk/) | Web app for converting historical data files to CSV | LiamP |
| Python | [github.com/mberk/betfairviz](https://github.com/mberk/betfairviz) | Create visualisations of Betfair order books | mberk |
| Python | [github.com/betcode-org/betfair](https://github.com/betcode-org/betfair) | Parse/output historical data for back testing | LiamP |
| Excel/VBA | [github.com/betfair/historic-data-workbook](https://github.com/betfair/historic-data-workbook) | Excel workbook for BASIC historical data | Robin Barrett |

### Other Resources

- **Competition & Event Mapping Data** for all historical markets from 2018-2023 (mapping data prior to 2018 isn't available)

---

## Tutorials

| Language | Tutorial | Description | Developer |
|----------|----------|-------------|-----------|
| R | [Betfair API R Tutorial](https://betfair-datascientists.github.io/tutorials/apiRtutorial/) | Getting started with R | Betfair Australia |
| Python | [Historical data - Json to Csv](https://betfair-datascientists.github.io/tutorials/jsonToCsvRevisited/) | Converting historical data | Betfair Australia |
| Python | [Betfair API Python Tutorial](https://betfair-datascientists.github.io/tutorials/apiPythontutorial/) | Getting started with Python | Betfair Australia |
| Python | [Backtesting wagering models](https://betfair-datascientists.github.io/historicData/backtestingRatingsTutorial/) | Backtesting with JSON stream data | Tom Bishop |
| Python | [How to Automate I](https://betfair-datascientists.github.io/tutorials/How_to_Automate_1/) | Understanding Flumine | Betfair Australia |
| Python | [How to Automate II](https://betfair-datascientists.github.io/tutorials/How_to_Automate_2/) | Backing/laying favorites | Betfair Australia |
| Python | [How to Automate III](https://betfair-datascientists.github.io/tutorials/How_to_Automate_3/) | Betfair Data Scientist's Models | Betfair Australia |
| Python | [How to Automate IV](https://betfair-datascientists.github.io/tutorials/How_to_Automate_4/) | Automate your own Model | Betfair Australia |
| Python | [How to Automate V](https://betfair-datascientists.github.io/tutorials/How_to_Automate_5/) | Advanced automation | Betfair Australia |

---

## Recommended Python Libraries

For Python development, the recommended libraries are:

1. **[betfairlightweight](https://github.com/betcode-org/betfair)** - Lightweight Python wrapper for Betfair API-NG with streaming support
2. **[flumine](https://github.com/betcode-org/flumine)** - Betting Trading Framework built on betfairlightweight

---

## Related Documentation

- [Getting Started](./getting-started.md)
- [Exchange Stream API](./exchange-stream-api.md)
- [Betting API](./betting-api.md)
