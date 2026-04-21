# Betfair Login & Session Management

Source: [Betfair Developer Documentation](https://betfair-developer-docs.atlassian.net/wiki/spaces/1smk3cen4v3lu3yomq5qye0ni/pages/2687869/Login+Session+Management)

## Overview

The Betfair API offers three login flows for developers, depending on the use case for your application.

**All API requests should be sent as POST.**

---

## Login Methods

### 1. Non-Interactive Login (Bot Login)

If you are building an application that will run autonomously, there is a separate login flow to follow to ensure your account remains secure.

- **Use Case:** Applications running autonomously (e.g., bots, scheduled tasks)
- **Method:** Non-interactive endpoint with SSL certificate
- **Pros:** Secure for automation. Recommended for bots
- **Cons:** Requires certificate setup

### 2. Interactive Login - API Endpoint

This flow makes use of a JSON API endpoint and is the simplest way to get started if you are looking to create your own login form.

- **Use Case:** Applications needing simple integration with minimal development time
- **Method:** API login endpoint (username + password, or username + password + 2FA if enabled)
- **Pros:** Easiest to implement. Good for most apps
- **Cons:** Less flexible for handling edge cases compared to the embedded login page

### 3. Interactive Login - Desktop Application

This login flow makes use of Betfair's login pages and allows your app to gracefully handle all errors and redirections in the same way as the Betfair website.

- **Use Case:** Applications used interactively by a wide range of users
- **Method:** Embedded Betfair login pages
- **Pros:** Handles workflows like T&Cs updates and jurisdiction checks. More flexible for 3rd party apps
- **Cons:** Requires embedding Betfair's login page. More development effort

---

## Login Method Summary

| Login Type | Use Case | Recommendation |
|------------|----------|----------------|
| Non-Interactive | Bots, scheduled tasks, autonomous apps | Use if your app runs without user interaction |
| Interactive - API | Quick setup, simple integration | Use if you want quick setup and don't need T&Cs or jurisdiction workflows |
| Interactive - Desktop | Multi-user apps, need to handle extra workflows | Use if your app is for many users and must handle extra workflows securely |

---

## Login Request Limits

- **Successful login requests:** Limited to **100 requests per minute**
- **Breach penalty:** Account prevented from creating new login sessions for **20 minutes**
- **Error returned:** `TEMPORARY_BAN_TOO_MANY_REQUESTS`
- **Note:** All existing sessions remain valid during a ban

---

## Session Expiry Times

| Exchange | Session Timeout |
|----------|-----------------|
| International (.com) - UK & Ireland | 24 hours |
| International (.com) - Other countries | 12 hours |
| Italian Exchange | 20 minutes |
| Spanish Exchange | 20 minutes |

> **Note:** Session times aren't determined or extended based on API activity. You can configure the timeout via My Account > Logout Preferences if required.

---

## Keep Alive

Use Keep-Alive to extend the session timeout period. You should request Keep Alive within the session timeout period to prevent session expiry.

### Endpoints

| Jurisdiction | Endpoint |
|--------------|----------|
| Global | `https://identitysso.betfair.com/api/keepAlive` |
| Australia & New Zealand | `https://identitysso.betfair.au/api/keepAlive` |
| Italy | `https://identitysso.betfair.it/api/keepAlive` |
| Spain | `https://identitysso.betfair.es/api/keepAlive` |
| Romania | `https://identitysso.betfair.ro/api/keepAlive` |

### Headers

| Name | Required | Description | Sample |
|------|----------|-------------|--------|
| `Accept` | Yes | Signals response should be JSON | `application/json` |
| `X-Authentication` | Yes | Session token to keep alive | Session Token |
| `X-Application` | No | Application Key | App Key |

### Request Example

```bash
curl -k -i \
  -H "Accept: application/json" \
  -H "X-Application: AppKey" \
  -H "X-Authentication: <token>" \
  https://identitysso.betfair.com/api/keepAlive
```

### Response Structure

```json
{
  "token": "<token_passed_as_header>",
  "product": "product_passed_as_header",
  "status": "<status>",
  "error": "<error>"
}
```

### Status Values

| Status | Description |
|--------|-------------|
| `SUCCESS` | Session extended successfully |
| `FAIL` | Operation failed |

### Error Values

| Error | Description |
|-------|-------------|
| `INPUT_VALIDATION_ERROR` | Invalid input |
| `INTERNAL_ERROR` | Server error |
| `NO_SESSION` | Session not found or expired |

---

## Logout

Use Logout to terminate your existing session.

### Endpoint

```
https://identitysso.betfair.com/api/logout
```

### Headers

| Name | Required | Description | Sample |
|------|----------|-------------|--------|
| `Accept` | Yes | Signals response should be JSON | `application/json` |
| `X-Authentication` | Yes | Session token created at login | Session Token |
| `X-Application` | No | Application Key | App Key |

### Request Example

```bash
curl -k -i \
  -H "Accept: application/json" \
  -H "X-Application: AppKey" \
  -H "X-Authentication: <token>" \
  https://identitysso.betfair.com/api/logout
```

### Response Structure

```json
{
  "token": "<token_passed_as_header>",
  "product": "product_passed_as_header",
  "status": "<status>",
  "error": "<error>"
}
```

---

## Related Documentation

- [Non-Interactive (Bot) Login](./non-interactive-login.md)
- [Interactive Login - API Endpoint](./interactive-login-api.md)
- [Interactive Login - Desktop Application](./interactive-login-desktop.md)
- [Getting Started](./getting-started.md)
