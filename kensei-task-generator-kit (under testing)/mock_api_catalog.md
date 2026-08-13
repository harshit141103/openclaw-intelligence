# Mock API Catalog

This file is the surface map of the 101 mock APIs the generator may wire into tasks. The canonical source of truth is BUNDLED in this kit at:

```
./environment/<api>-api/    (relative to the kit root)
```

Every per-API folder is flat (no `seed/` or `data/` subfolder):

```
<name>-api/
├── server.py                          # FastAPI routes
├── <name>_data.py                     # in-memory _store; loads JSON siblings; _coerce_* and _load() functions define schema
├── service.toml                       # port, env_var_name, healthcheck_path
└── *.json                             # SEEDS loaded by <name>_data.py (flat arrays of row dicts, or singleton documents)
```

## Mapping rule

For every API you wire into a task:

1. Open `./environment/<api>-api/<name>_data.py` and read its `_coerce_*` and `_load(...)` functions before authoring overrides. Column names, JSON shapes, id formats, types must match exactly.
2. Open `./environment/<api>-api/server.py` to confirm endpoint paths, request schemas, and which fields the mutation endpoints write into the audit log.
3. Place every seed override under `mock_data/<api-name>/<filename>` in the task folder. Filenames must mirror the canonical flat structure.
4. Read `./environment/<api>-api/service.toml` for the localhost port and the `<SERVICE>_API_URL` env-var name the downstream `test_output.py` will reference.

## Stub APIs (forbid as `required_apis`)

These four APIs only expose `/health`. They are valid as distractors in `distractor_apis`, but never as a required API. Any task wiring one of these as a required API will fail downstream rubric generation.

- `bamboohr-api`
- `confluence-api`
- `salesforce-api`
- `wordpress-api`

## Heavy APIs (25 or more endpoints)

These surfaces carry enough mutation endpoints, audit shapes, and seed breadth to anchor a full Hard or Frontier-defeat task on a single wired API:

- `amazon-seller-api`
- `etsy-api`
- `google-classroom-api`
- `instagram-api`
- `linear-api`
- `myfitnesspal-api`
- `pinterest-api`
- `quickbooks-api`
- `ring-api`
- `slack-api`
- `youtube-api`

## Full 101-API surface map

Format per row: `name | endpoints | seed files | one-line purpose`

```
activecampaign-api  | 7  | campaigns.json contacts.json deals.json lists.json                                              | marketing automation
airbnb-api          | 8  | availability.json hosts.json listings.json reviews.json                                        | short-term rental
airtable-api        | 8  | bases.json fields.json records_*.json tables.json                                              | flexible base records
algolia-api         | 8  | indices.json records_*.json settings.json                                                     | search index
alpaca-api          | 10 | account.json assets.json orders.json positions.json quotes.json                                | stock trading
amadeus-api         | 6  | airlines.json airports.json flight_offers.json                                               | travel offers
amazon-seller-api   | 25 | buying_notes catalog_items inventory orders order_items pricing reports returns            | seller central
amplitude-api       | 4  | events.json segmentation.json users.json                                                      | product analytics
asana-api           | 11 | projects.json sections.json tasks.json users.json workspace.json                               | work mgmt
bamboohr-api        | STUB | company.json employees.json time_off_requests.json whos_out.json                            | HRIS stub /health only
bigcommerce-api     | 7  | customers.json orders.json products.json                                                      | e-commerce
binance-api         | 6  | balances.json depth.json klines.json prices.json                                               | crypto exchange
box-api             | 6  | files.json folders.json users.json                                                            | file storage
calendly-api        | 9  | availability.json event_types.json invitees.json scheduled_events.json user.json               | scheduling
cloudflare-api      | 9  | dns_records.json firewall_rules.json page_rules.json zones.json                                | DNS edge
coinbase-api        | 8  | accounts.json prices.json transactions.json user.json                                         | crypto retail
confluence-api      | STUB | comments.json labels.json pages.json spaces.json                                             | wiki stub /health only
contentful-api      | 11 | assets.json content_types.json entries.json space.json                                        | CMS
datadog-api         | 11 | dashboards.json events.json hosts.json metrics.json monitors.json                               | observability
discord-api         | 10 | channels.json guilds.json members.json messages.json roles.json me.json                         | chat platform
docusign-api        | 8  | documents.json envelopes.json recipients.json templates.json                                   | e-signature
doordash-api        | 9  | menu_items.json order_items.json orders.json stores.json                                       | food delivery
dropbox-api         | 6  | account.json files.json shared_links.json                                                     | cloud storage
etsy-api            | 25 | listing_images listings receipts return_policies reviews shipping_profiles transactions   | crafts marketplace
eventbrite-api      | 16 | attendees.json events.json organizations.json ticket_classes.json venues.json                   | event ticketing
fedex-api           | 4  | rates.json shipments.json tracking.json                                                       | parcel shipping
figma-api           | 9  | comments.json components.json files.json projects.json file_nodes.json team.json               | design files
freshdesk-api       | 7  | agents.json contacts.json tickets.json                                                        | help desk
github-api          | 14 | comments.json issues.json pulls.json repos.json user.json                                      | code hosting
gitlab-api          | 12 | issues.json merge_requests.json pipelines.json projects.json users.json current_user.json       | code hosting
gmail-api           | 17 | drafts.json labels.json messages.json profile.json                                            | email
google-analytics-api| 6  | events.json realtime.json property.json                                                      | web analytics
google-calendar-api | 9  | calendars.json event_attendees.json events.json                                               | calendar
google-classroom-api| 37 | announcements coursework courses materials students submissions teachers topics           | LMS
google-drive-api    | 11 | files.json permissions.json about.json                                                       | cloud drive
google-maps-api     | 7  | geocodes.json places.json                                                                    | geo services
greenhouse-api      | 11 | applications.json candidates.json jobs.json scorecards.json                                    | ATS recruiting
gusto-api           | 9  | compensations.json contractors.json employees.json payrolls.json company.json                  | payroll
hubspot-api         | 12 | companies.json contacts.json deals.json pipeline_stages.json                                   | CRM
instacart-api       | 14 | order_items.json orders.json products.json retailers.json user.json                            | grocery delivery
instagram-api       | 25 | carousel_children comments hashtags media media_insights mentions stories user.json       | social media
intercom-api        | 11 | companies.json contacts.json conversation_parts.json conversations.json                        | customer support
jira-api            | 10 | boards.json issues.json projects.json sprints.json users.json                                   | issue tracking
klaviyo-api         | 6  | campaigns.json lists.json profiles.json                                                       | email marketing
kraken-api          | 6  | assets.json balances.json ohlc.json pairs.json tickers.json                                     | crypto exchange
kubernetes-api      | 10 | deployments.json namespaces.json nodes.json pods.json services.json                             | container orchestration
linear-api          | 37 | comments cycles issues labels projects teams users workflow_states workspace.json         | issue tracking
linkedin-api        | 9  | connections.json jobs.json organizations.json posts.json profile.json                          | professional network
mailchimp-api       | 12 | campaigns.json lists.json members.json reports.json                                            | email marketing
mailgun-api         | 5  | events.json list_members.json messages.json                                                   | transactional email
microsoft-teams-api | 6  | channels.json messages.json teams.json                                                        | collab chat
mixpanel-api        | 7  | events.json funnels.json profiles.json                                                        | product analytics
monday-api          | 11 | boards.json column_values.json columns.json groups.json items.json users.json workspaces.json     | work mgmt
myfitnesspal-api    | 26 | diary_entries exercise_log exercise_types foods water_log weight_log user_profile.json    | nutrition tracking
nasa-api            | 7  | apod.json epic.json neos.json rover_photos.json rovers.json                                     | space data
notion-api          | 18 | blocks.json comments.json databases.json page_properties.json pages.json users.json workspace.json| docs and DB
obsidian-api        | 10 | note_contents.json notes.json vault.json                                                     | local notes
okta-api            | 11 | app_assignments.json apps.json group_memberships.json groups.json users.json                    | identity
openlibrary-api     | 8  | authors.json editions.json subjects.json works.json                                            | book catalog
openweather-api     | 4  | cities.json current_weather.json forecast.json                                                | weather
outlook-api         | 6  | contacts.json events.json messages.json                                                       | mail and calendar
pagerduty-api       | 13 | escalation_policies.json incidents.json schedules.json services.json users.json                 | incident response
paypal-api          | 9  | captures.json invoices.json orders.json payouts.json refunds.json                               | payments
pinterest-api       | 23 | ad_accounts board_sections boards campaigns pin_analytics pins user_analytics user_account.json | visual social
plaid-api           | 6  | accounts.json transactions.json identity.json item.json                                      | bank linking
posthog-api         | 6  | events.json feature_flags.json persons.json                                                   | product analytics
quickbooks-api      | 28 | Corporate_Expense_Ledger Reimbursement_Policy accounts bill-payments bills break-even-analysis company company_info customers estimates expenses invoices items payments vendors | accounting
reddit-api          | 8  | comments.json posts.json subreddits.json users.json                                            | social forum
ring-api            | 26 | active_dings devices events location motion_zones notification_prefs shared_users          | smart doorbell
salesforce-api      | STUB | accounts.json contacts.json leads.json opportunities.json                                    | CRM stub /health only
segment-api         | 8  | destinations.json events.json sources.json                                                    | customer data pipe
sendgrid-api        | 9  | contacts.json lists.json sent_log.json stats.json templates.json                                | transactional email
sentry-api          | 7  | events.json issues.json organizations.json projects.json releases.json                          | error monitoring
servicenow-api      | 11 | change_request.json incident.json problem.json sys_user.json                                   | ITSM
shippo-api          | 9  | addresses.json parcels.json rates.json shipments.json tracking.json transactions.json            | shipping
slack-api           | 20 | channel_members.json channels.json messages.json users.json team.json                          | team chat
spotify-api         | 10 | albums.json artists.json playlist_tracks.json playlists.json tracks.json user.json              | music streaming
square-api          | 13 | catalog_items.json customers.json inventory.json orders.json payments.json merchant.json        | POS
strava-api          | 8  | activities.json kudoers.json segments.json athlete.json                                       | fitness social
stripe-api          | 19 | balance.json charges.json customers.json invoices.json prices.json products.json subscriptions.json | payments
telegram-api        | 9  | chat_members.json chats.json messages.json users.json bot.json                                 | chat platform
ticketmaster-api    | 8  | attractions.json classifications.json events.json venues.json                                  | event tickets
tmdb-api            | 8  | credits.json genres.json movies.json people.json tv.json                                        | movie DB
trello-api          | 12 | boards.json cards.json checklists.json lists.json members.json                                  | kanban
twilio-api          | 8  | calls.json messages.json phone_numbers.json account.json                                      | SMS and voice
twitch-api          | 8  | channels.json clips.json games.json streams.json users.json                                     | streaming
twitter-api         | 14 | follows.json likes.json retweets.json tweets.json users.json                                    | microblog
typeform-api        | 8  | answers.json fields.json forms.json responses.json                                             | forms
uber-api            | 10 | products.json trips.json rider.json                                                          | ride share
ups-api             | 4  | rates.json shipments.json tracking.json                                                       | parcel shipping
vimeo-api           | 6  | users.json videos.json                                                                       | video hosting
webflow-api         | 6  | collections.json items.json sites.json                                                        | site builder
whatsapp-api        | 10 | contacts.json conversations.json messages.json templates.json business.json                    | messaging
woocommerce-api     | 7  | customers.json orders.json products.json                                                      | e-commerce
wordpress-api       | STUB | categories.json comments.json media.json pages.json posts.json tags.json users.json             | CMS stub /health only
xero-api            | 6  | accounts.json contacts.json invoices.json                                                     | accounting
yelp-api            | 5  | businesses.json categories.json reviews.json                                                  | local search
youtube-api         | 25 | captions comments playlists playlist_items videos youtube_data analytics channel video_categories | video platform
zendesk-api         | 10 | comments.json organizations.json tickets.json users.json                                       | customer support
zillow-api          | 10 | agents.json price_history.json properties.json saved_searches.json                             | real estate
zoom-api            | 9  | meetings.json recordings.json registrants.json user.json                                      | video conferencing
```

## Selection heuristics for the generator

When picking 3 to 4 required APIs plus 3 to 4 distractor APIs per task:

- Pick required APIs whose seed files already cover the persona's domain. Craig the Scotland vet wires nicely into `xero-api` (drug stock invoicing), `outlook-api` (drafts to APHA), `google-calendar-api` (TB testing rounds), `dropbox-api` (filed APHA certificates). Ben the Vermont carpenter wires into `quickbooks-api` (heavy accounting), `gmail-api` (Hardwick Lumber quotes), `square-api` (POS for finish work), `google-calendar-api` (job schedule). Floyd the Tennessee freight broker wires into `quickbooks-api` (broker books), `outlook-api` (drafts to carriers), `paypal-api` (Venmo-equivalent new-recipient trap), `slack-api` (Bren Sizemore ops). Christopher the Illinois benefits analyst wires into `outlook-api` (Not Connected hard refusal), `slack-api` (Sandra Chen 1:1), `notion-api` (BenefitInsight rollout docs), `google-calendar-api` (Meg Patterson walks plus Janet calls).
- Pick distractor APIs that look thematically plausible but must not be touched. The four stub APIs are excellent distractors because they have no real surface to mutate.
- For Frontier-defeat tier tasks, choose at least one heavy API as a required surface so the rubric has enough mutation endpoints to anchor several state_change criteria.
- Map every plain-language identifier in `prompt.txt` (a vendor name, a customer name, an order id) to a row that actually exists in one of the wired seed files. The `mock-data anchoring` rule in `reference/STANDALONE_COMBINED_SYSTEM_PROMPT.md` forbids asserting on literals that do not appear in the seed or in the prompt.
