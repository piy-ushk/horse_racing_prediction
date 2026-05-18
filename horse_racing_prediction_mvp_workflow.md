
# Horse Racing Prediction Automation System

## Simple MVP Workflow Document

### 1. Project Overview

This document describes a simple MVP workflow for an automated horse racing prediction system.

The system is designed for a small-budget, 15-day implementation. It focuses only on the core automation required to fetch racing odds once per day, generate simple prediction marks, publish the results to WordPress, and allow users to access the pages through special LINE links.

The goal is to create a stable and practical automated workflow with minimal manual operation.

---

## 2. Existing Infrastructure

The client has already prepared the main infrastructure required for the MVP.

| Area | Existing Infrastructure |
| --- | --- |
| Data Sources | JRA-VAN Data Lab (JV-Link), UmaConn |
| Processing Server | ConoHa VPS, Windows Server |
| Publishing Server | ConoHa WING, Linux + WordPress |
| User Access | LINE Rich Menu links |

No additional infrastructure layer is required for the MVP.

---

## 3. MVP Scope

The system will automatically:

1. Fetch horse racing odds once daily
2. Generate prediction marks automatically
3. Save the generated predictions permanently
4. Send prediction data to WordPress
5. Create or update race prediction pages
6. Restrict page access using a special URL parameter

This MVP uses a simple rule-based prediction process and keeps the technical scope limited.

---

## 4. Important Daily Odds Rule

The system must not update odds continuously.

Final specification:

- Odds are fetched only once per day
- Example execution time: 09:30 AM
- At 09:30 AM, the system fetches all target races
- Predictions are generated immediately after fetching odds
- Generated predictions are saved permanently
- Predictions remain fixed for that day
- If odds change later, displayed predictions do not change

This keeps the system simple, stable, and easy to explain to users.

---

## 5. Main Workflow

```text
09:30 AM Scheduled Task
        ↓
Windows VPS Starts Python Script
        ↓
Fetch Odds from JV-Link & UmaConn
        ↓
Sort Horses by Lowest Odds
        ↓
Generate Prediction Marks
(◎ ○ ▲ △)
        ↓
Save Data in SQLite Database
        ↓
Send Data to WordPress via REST API
        ↓
WordPress Creates/Updates Race Pages
        ↓
Users Access Pages via LINE Links
```

---

## 6. Daily Processing Explanation

### Step 1: Scheduled Start

Windows Task Scheduler runs the Python script automatically at the scheduled time, such as 09:30 AM.

No staff member needs to manually start the process during normal operation.

### Step 2: Odds Fetching

The Python script fetches race and odds data from:

- JRA-VAN Data Lab using JV-Link
- UmaConn

Only the odds available at the scheduled execution time are used.

### Step 3: Prediction Generation

The system sorts horses automatically based on odds.

Lower odds mean a higher prediction rank.

Example:

| Rank | Prediction Mark |
| --- | --- |
| 1 | ◎ |
| 2 | ○ |
| 3 | ▲ |
| 4 | △ |

This is a simple rule-based prediction workflow based only on the odds ranking.

### Step 4: Save Final Predictions

After prediction marks are generated, the results are saved in a SQLite database.

The saved data becomes the fixed prediction result for that day. Even if odds change later, the displayed race prediction page continues to show the saved results.

### Step 5: Publish to WordPress

The Python script sends prediction data to WordPress through the WordPress REST API.

WordPress then creates or updates race prediction pages using the fixed prediction data.

### Step 6: User Access from LINE

Users access the prediction pages from LINE Rich Menu links.

Each LINE link includes a special access parameter.

Example:

```text
https://site.com/race1?auth=line_only
```

---

## 7. Access Restriction Workflow

Prediction pages should only be viewable when the URL contains:

```text
?auth=line_only
```

If the parameter is included, the user can view the page.

If the parameter is missing or incorrect, WordPress should block access or redirect the user.

Simple workflow:

```text
User Opens Race Page
        ↓
WordPress Checks URL Parameter
        ↓
Is auth=line_only Present?
        ↓
Yes → Show Prediction Page
No  → Redirect or Block Access
```

This is a simple MVP-level restriction suitable for LINE-only traffic.

---

## 8. SEO Requirements

Prediction pages should not appear in Google or other search engines.

Recommended MVP handling:

- Add `noindex` to race prediction pages
- Prevent search engines from indexing prediction content
- Avoid including prediction pages in public sitemaps

This keeps the pages intended for LINE users only.

---

## 9. Logging Workflow

The Python script should create simple operation logs each time it runs.

Example log output:

```text
[09:30] Odds fetched successfully
[09:31] WordPress updated successfully
[09:32] Prediction generation completed
```

Logs help confirm that the weekend operation completed normally. They also make it easier to debug issues such as missing odds, failed WordPress updates, or connection problems.

For the MVP, a simple daily text log file is enough.

---

## 10. Simple MVP Tech Stack

| Component | Technology |
| --- | --- |
| Backend | Python |
| Scheduler | Windows Task Scheduler |
| Database | SQLite |
| Website | WordPress |
| API | WordPress REST API |
| Security | URL parameter validation |

This stack is simple, practical, and suitable for the prepared infrastructure.

---

## 11. Development Phases

### Phase 1: Environment Setup

- Prepare Python on the Windows VPS
- Create project folder structure
- Prepare SQLite database file
- Confirm WordPress REST API access
- Configure basic logging

### Phase 2: Odds Fetching Integration

- Connect Python script to JV-Link
- Connect or import data from UmaConn
- Fetch daily race and odds data
- Validate fetched data format
- Store raw fetched data for checking

### Phase 3: Prediction Generation Logic

- Sort horses by lowest odds
- Assign prediction marks automatically
- Save final prediction results in SQLite
- Ensure predictions do not change after generation

### Phase 4: WordPress Integration

- Send prediction data to WordPress through REST API
- Create or update race prediction pages
- Add URL parameter validation
- Add `noindex` handling for prediction pages

### Phase 5: Testing and Deployment

- Test scheduled execution at the expected time
- Confirm all race pages are created or updated
- Confirm predictions remain fixed after generation
- Test LINE Rich Menu links
- Test blocked access when the URL parameter is missing
- Review logs after weekend operation

---

## 12. 15-Day MVP Implementation Plan

| Period | Main Work |
| --- | --- |
| Days 1-2 | Environment setup and WordPress API confirmation |
| Days 3-6 | Odds fetching integration |
| Days 7-9 | Prediction generation and SQLite saving |
| Days 10-12 | WordPress page creation and access restriction |
| Days 13-14 | End-to-end testing and fixes |
| Day 15 | Deployment check and handover |

The schedule assumes the infrastructure, data source access, and WordPress environment are already available.

---

## 13. Final MVP Notes

This workflow is intentionally simple.

The MVP avoids complex architecture and focuses on the minimum system needed to operate reliably:

- One scheduled daily run
- One fixed prediction result per race
- One lightweight SQLite database
- One WordPress publishing flow
- Simple LINE-only URL access
- Simple logs for operation checking

This approach keeps development cost low, reduces technical risk, and makes the system easier to maintain.

Future expansion can be added later, such as improved prediction rules, admin screens, better access control, analytics, or more advanced data processing.
