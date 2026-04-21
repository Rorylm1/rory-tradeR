# Betfair Accounts API Reference

Source: [Betfair Developer Documentation](https://betfair-developer-docs.atlassian.net/wiki/spaces/1smk3cen4v3lu3yomq5qye0ni/pages/2687725/Accounts+API)

## Endpoints

All API requests should be sent as **POST**.

### Global Exchange

| Interface | Endpoint | JSON-RPC Prefix | Example |
|-----------|----------|-----------------|---------|
| JSON-RPC | `https://api.betfair.com/exchange/account/json-rpc/v1` | `AccountAPING/v1.0/` | `AccountAPING/v1.0/getAccountFunds` |
| JSON REST | `https://api.betfair.com/exchange/account/rest/v1.0/` | N/A | `getAccountFunds/` |

### New Zealand Customers

| Interface | Endpoint | JSON-RPC Prefix | Example |
|-----------|----------|-----------------|---------|
| JSON-RPC | `https://api.betfair.com.au/exchange/account/json-rpc/v1` | `AccountAPING/v1.0/` | `AccountAPING/v1.0/getAccountFunds` |
| JSON REST | `https://api.betfair.com.au/exchange/account/rest/v1.0/` | N/A | `getAccountFunds/` |

> **Note:** If you have an Italian or Spanish Exchange account, see separate documentation for those exchanges.

---

## Required Headers

Although the majority of API-NG calls require both the `X-Authentication` (sessionToken) and `X-Application` (Application Key) in the request header, this isn't applicable for some API Account Operations that are available to Software Vendors Only.

---

## Operation Summary

### Application Key Operations

| Return Type | Operation | Description | Vendor Only | X-Auth | X-App |
|-------------|-----------|-------------|-------------|--------|-------|
| `DeveloperApp` | `createDeveloperAppKeys(String appName)` | Create 2 Application Keys for given user; one 'Delayed' and the other 'Live'. You must apply to have your 'Live' App Key activated | | ✓ | |
| `List<DeveloperApp>` | `getDeveloperAppKeys()` | Get all application keys owned by the given developer/vendor | | ✓ | |

### Account Information Operations

| Return Type | Operation | Description | Vendor Only | X-Auth | X-App |
|-------------|-----------|-------------|-------------|--------|-------|
| `AccountFundsResponse` | `getAccountFunds()` | Get available to bet amount | | ✓ | ✓ |
| `AccountDetailsResponse` | `getAccountDetails()` | Returns the details relating your account, including your discount rate and Betfair point balance | | ✓ | ✓ |
| `AccountStatementReport` | `getAccountStatement(String locale, int fromRecord, int recordCount, TimeRange itemDateRange, IncludeItem includeItem, Wallet wallet)` | Get account statement - provides full audit trail of money moving to and from your account. **Not available via the Vendor Web API** | | ✓ | ✓ |
| `List<CurrencyRate>` | `listCurrencyRates(String fromCurrency)` | Returns a list of currency rates based on given currency | | | |

### Vendor Operations (Software Vendors Only)

| Return Type | Operation | Description | Vendor Only | X-Auth | X-App |
|-------------|-----------|-------------|-------------|--------|-------|
| `String` | `getVendorClientId()` | Returns the vendor client id for customer account which is a unique identifier for that customer | | ✓ | |
| `String` | `getApplicationSubscriptionToken(int subscriptionLength)` | Used to create new subscription tokens for an application. Returns the newly generated subscription token which can be provided to the end user | ✓ | ✓ | ✓ |
| `Status` | `activateApplicationSubscription(String subscriptionToken)` | Activates the customers subscription token for an application | | ✓ | |
| `Status` | `cancelApplicationSubscription(String subscriptionToken)` | Cancel the subscription token. The customers subscription will no longer be active once cancelled | ✓ | ✓ | ✓ |
| `String` | `updateApplicationSubscription(String vendorClientId, int subscriptionLength)` | Update an application subscription with a new expiry date | ✓ | ✓ | ✓ |
| `List<ApplicationSubscription>` | `listApplicationSubscriptionTokens(SubscriptionStatus subscriptionStatus)` | Returns a list of subscription tokens for an application based on the subscription status passed in the request | ✓ | ✓ | ✓ |
| `List<AccountSubscription>` | `listAccountSubscriptionTokens()` | List of subscription tokens associated with the account | ✓ | ✓ | ✓ |
| `List<SubscriptionHistory>` | `getApplicationSubscriptionHistory(String vendorClientId)` | Returns a list of subscriptions tokens that have been associated with the customers account | ✓ | ✓ | ✓ (or body) |

### Web App & Vendor Details Operations

| Return Type | Operation | Description | Vendor Only | X-Auth | X-App |
|-------------|-----------|-------------|-------------|--------|-------|
| `VendorAccessTokenInfo` | `token(String client_id, GrantType grant_type, String code, String client_secret, String refresh_token)` | Generate web vendor session based on a standard session identifiable by auth code, vendor secret and app key | ✓ | ✓ | ✓ |
| `VendorDetails` | `getVendorDetails(String vendorId)` | Return details about a vendor from its identifier. Response includes Vendor Name and URL | | | |
| `Status` | `revokeAccessToWebApp(long vendorId)` | Remove the link between an account and a vendor web app. This will remove the refreshToken for this user-vendor pair subscription | | | |
| `List<VendorDetails>` | `listAuthorizedWebApps()` | Retrieve all vendors applications currently subscribed to by the user making the request | | | |
| `boolean` | `isAccountSubscribedToWebApp(String vendorId)` | Return whether an account has authorised a web app | | | |
| `List<AffiliateRelation>` | `getAffiliateRelation(List<String> vendorClientIds)` | Return relation between a list of users and an affiliate | ✓ | ✓ | ✓ |

---

## Related Documentation

- [Accounts Exceptions](./accounts-exceptions.md)
- [Accounts Enums](./accounts-enums.md)
- [Accounts TypeDefinitions](./accounts-type-definitions.md)
