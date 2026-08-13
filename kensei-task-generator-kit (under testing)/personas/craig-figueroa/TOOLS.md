# Tools: Craig Figueroa

## Tool Usage

### Connected Services

#### Email, Calendar & Contacts

- **Gmail** (`gmail-api`): Read and triage craig.figueroa@Finthesiss.ai, draft replies to farmers, APHA, Douglas Mackay, Jean MacKenzie, and suppliers without auto-sending.
- **Google Calendar** (`google-calendar-api`): Manage farm visit blocks, TB testing windows, APHA appointments, family check-ins, and protected Friday and Sunday windows in UK time.
- **Google Contacts** (`google-contacts-api`): Keeps farmer, supplier, family, and APHA contact records current and synced so call-out numbers are never stale.
- **Outlook** (`outlook-api`): Handles the Microsoft-side calendar invites for APHA regional meetings and correspondence from Rhona Matheson's office, kept in sync with Google Calendar so nothing regulatory sits unread.

#### Files, Notes & Documents

- **Google Drive** (`google-drive-api`): Store clinical record exports, APHA filings, invoicing sheets, drug dispensing logs, supplier quotes, and conference notes.
- **Dropbox** (`dropbox-api`): Shares case photo and ultrasound image folders with Jean MacKenzie for second opinions and holds the Series III restoration photo archive.
- **Box** (`box-api`): Exchanges TB testing paperwork and disease surveillance documents with APHA contacts who send secure Box links.
- **Notion** (`notion-api`): Runs the practice knowledge base of farm profiles, herd histories, withdrawal-period notes, and supplier terms, updated after each visit.
- **Obsidian** (`obsidian-api`): Keeps his personal vault of Munro logs, Series III restoration notes, and reading notes, linked so parts leads and route ideas resurface when needed.
- **Confluence** (`confluence-api`): Holds the practice digitisation runbook and migration checklists shared with the clinical-platform vendor ahead of the December cutover.
- **Airtable** (`airtable-api`): Tracks the autumn TB testing round across 28 herds with test dates, results, retest flags, and APHA reporting status per farm.
- **DocuSign** (`docusign-api`): Signs and routes locum agreements with Graeme Sutherland, supplier contracts, and the APHA forms that accept electronic signature.

#### Banking, Payments & Trading

- **Plaid** (`plaid-api`): Feeds Bank of Scotland personal and business transactions into the monthly financial review and the thirty-percent tax set-aside check.
- **Stripe** (`stripe-api`): Takes card payment on emailed practice invoices through pay-by-link, cutting the lag on farm accounts.
- **Square** (`square-api`): Runs the card reader in the Defender so farmers can settle on the spot at the end of a visit.
- **PayPal** (`paypal-api`): Pays private sellers and forum traders for period-correct Series III parts where cards are not an option.
- **QuickBooks** (`quickbooks-api`): Syncs categorised practice income and expenses to the books Douglas Mackay keeps at Mackay & Co. ahead of each quarterly check-in.
- **Xero** (`xero-api`): Raises and tracks practice invoices and quotes, including Graeme Sutherland's locum cover paid as contractor invoices, flagging farm accounts that drift past thirty days.
- **Gusto** (`gusto-api`): Holds a sandbox account from evaluating payroll tools for the practice; Gusto serves US employers only, so it is reference-and-comparison use, never live UK payments.
- **Coinbase** (`coinbase-api`): Holds the small experimental position Craig opened after a congress talk on alternative assets, checked at the monthly review.
- **Binance** (`binance-api`): Supplies cross-exchange price data so the monthly check on that small position takes one glance, not a rabbit hole.
- **Kraken** (`kraken-api`): Covers the GBP pairs and staking yield on the experimental holding, reported in pounds at the monthly review.
- **Alpaca** (`alpaca-api`): Paper-trades US stock ideas so Craig can stress-test a thought before raising it with Douglas Mackay.

#### Travel, Navigation & Logistics

- **Google Maps** (`google-maps-api`): Plan farm routes across Wester Ross, Lochalsh, and Sutherland, including single-track sections and seasonal access changes.
- **OpenWeather** (`openweather-api`): Check Strathcarron and farm-area forecasts for call-out planning, hill walks, and Loch Carron swims.
- **FedEx** (`fedex-api`): Tracks specialist instrument and equipment shipments inbound to the dispensary and flags delays that hit the visit schedule.
- **UPS** (`ups-api`): Tracks inbound supplier shipments, including refrigerated drug deliveries, so cold-chain stock is met at the door.
- **Shippo** (`shippo-api`): Generates return labels for drug recalls, warranty returns on practice equipment, and the occasional sold Series III spare.
- **DoorDash** (`doordash-api`): Legacy US-only account kept from a stateside veterinary study trip; it covers hotel dinners only when travel takes him across the Atlantic, never anything local.
- **Instacart** (`instacart-api`): Legacy US-only account from the same stateside trip, used to pre-order groceries to the rental on American travel; the Inverness shop stays a hand-built list.
- **Uber** (`uber-api`): Covers rides during congress trips and nights out in Edinburgh or Glasgow when the Defender stays parked.
- **Airbnb** (`airbnb-api`): Searches and shortlists Tromsø lodging for the Norway nostalgia trip he is planning with Fiona.
- **Amadeus** (`amadeus-api`): Searches Inverness to Tromsø flight routings for the Norway trip and rail-plus-hotel options for Harrogate.

#### Communication

- **Slack** (`slack-api`): Runs a shared channel with Graeme Sutherland for locum handovers and live case threads during cover weeks.
- **Microsoft Teams** (`microsoft-teams-api`): Joins the APHA regional briefings and Inverness veterinary CPD sessions that run on Teams.
- **Discord** (`discord-api`): Follows the Land Rover Series III restoration server, watching the parts-wanted channel for period-correct trim.
- **Telegram** (`telegram-api`): Follows the Highland road-conditions and mountain-weather channels that update faster than anything else in winter.
- **WhatsApp** (`whatsapp-api`): Drafts messages to the family group with Fiona, Alejandro, Elena, Isabel, and Callum, plus a few farmer friends. Send only on explicit confirmation.
- **Twilio** (`twilio-api`): Sends next-day farm-visit reminder texts in batches Craig approves, trimming missed appointments on long-drive days.
- **SendGrid** (`sendgrid-api`): Delivers booking confirmations and TB-testing date notices from the practice system to farmers' inboxes.
- **Mailgun** (`mailgun-api`): Carries the dispensing-refill reminder mail stream, kept on its own service so deliverability stays clean.
- **Zoom** (`zoom-api`): Runs the monthly case call with Jean MacKenzie, congress catch-ups, and the quarterly reviews with Douglas Mackay.

#### Productivity & Project Management

- **Asana** (`asana-api`): Tracks the practice modernisation project against the December full-migration target, task by task.
- **Trello** (`trello-api`): Boards the autumn TB round, moving each of the 28 herds from scheduled to tested to reported.
- **Monday** (`monday-api`): Tracks the Autumn Herd Health Round across the three complex-history farms at Achnasheen, Applecross, and near Torridon.
- **Linear** (`linear-api`): Files and follows the bugs he hits in the clinical-records pilot so vendor fixes land before the December cutover.
- **Jira** (`jira-api`): Tracks his open support tickets with the practice-platform vendor, including the offline-sync issues from remote farms.
- **Calendly** (`calendly-api`): Offers farmers a booking link for non-urgent visits, padded with drive time and synced against the farm-visit blocks.
- **Typeform** (`typeform-api`): Collects pre-visit herd history forms from farmers ahead of TB testing days so paperwork starts before the crush gate opens.

#### Clients, Marketing & Support

- **HubSpot** (`hubspot-api`): Keeps contact records for the forty-five farm clients with herd notes, visit history, and follow-up reminders.
- **Salesforce** (`salesforce-api`): Tracks supplier and drug-rep relationships separately from farm clients, with contract dates and pricing history.
- **Mailchimp** (`mailchimp-api`): Sends the seasonal practice update to farmers covering disease alerts, TB round scheduling, and lambing prep.
- **Klaviyo** (`klaviyo-api`): Runs automated reminder flows for routine bookings such as vaccination boosters, condition scoring, and fertility rechecks, segmented by herd.
- **ActiveCampaign** (`activecampaign-api`): Runs the lambing-season prep email sequence for hill-flock clients through late winter.
- **Intercom** (`intercom-api`): Powers the chat widget on the practice page where farmers drop non-urgent questions Crook triages into the queue.
- **Zendesk** (`zendesk-api`): Tickets non-urgent farmer requests like recheck bookings, paperwork copies, and certificate requests so nothing gets lost on the road.
- **Freshdesk** (`freshdesk-api`): Tracks open supplier issues such as short deliveries, cold-chain breaches, and invoice disputes as tickets until closed.

#### Social, Press & Media

- **Instagram** (`instagram-api`): Posts occasional Highland life shots from farm rounds to the practice account that doubles as the area's informal vet noticeboard.
- **Twitter** (`twitter-api`): Follows APHA, Defra, and disease-surveillance accounts for bluetongue and TB policy updates that affect the round.
- **Pinterest** (`pinterest-api`): Builds boards for Fiona's conservatory reading nook, the kitchen garden layout, and crofthouse renovation ideas.
- **Reddit** (`reddit-api`): Reads the Land Rover restoration and rural-vet threads for parts leads and kit recommendations.
- **LinkedIn** (`linkedin-api`): Keeps his professional profile current and tracks congress speakers and locum-network contacts ahead of Harrogate.
- **YouTube** (`youtube-api`): Pulls veterinary technique videos and Land Rover restoration references for evening workshop sessions in the outbuilding.
- **Twitch** (`twitch-api`): Follows a couple of slow workshop channels restoring vintage Land Rovers, mined for Series III technique.
- **Vimeo** (`vimeo-api`): Streams congress session recordings and CPD video modules, including the bovine ultrasonography previews.
- **Figma** (`figma-api`): Holds the paddock-fencing layout, dispensary shelving plans, and practice-page mockups Craig sketches with Crook before ordering materials.
- **NASA** (`nasa-api`): Pulls aurora and space-weather forecasts for clear Strathcarron nights when the northern lights are worth stepping outside for.
- **TMDB** (`tmdb-api`): Picks films for slow Wednesday evenings in with Fiona on the shared streaming service, biased toward adaptations of books he has read.
- **Spotify** (`spotify-api`): Active for long drives (Rodrigo y Gabriela, Vicente Amigo, Fleet Foxes, Dire Straits) and BBC Radio 3 classical at home.

#### Storefront & E-commerce

- **BigCommerce** (`bigcommerce-api`): Runs the small online shop for over-the-counter animal-health lines farmers pre-order and collect at the dispensary.
- **WooCommerce** (`woocommerce-api`): Maintains the order page for Isabel's Plockton tearoom hampers, which Craig keeps patched as the family's tech hand.
- **Etsy** (`etsy-api`): Sources handmade gifts for Fiona and tracks sellers who turn out period-correct Series III trim and brass fittings.
- **Amazon Seller** (`amazon-seller-api`): Lists duplicate Series III spares he has accumulated, turning surplus parts into restoration budget.
- **Webflow** (`webflow-api`): Hosts the one-page practice site with emergency contact details, dispensary hours, and seasonal notices.
- **WordPress** (`wordpress-api`): Runs the practice blog where seasonal husbandry notes and TB round updates get posted for farmers.
- **Contentful** (`contentful-api`): Serves the reusable client advice sheets on withdrawal periods, lambing prep, and biosecurity to the practice page from one structured source.

#### Operations & Platform

- **BambooHR** (`bamboohr-api`): Files Graeme Sutherland's locum agreements, insurance certificates, and cover dates in one place.
- **Greenhouse** (`greenhouse-api`): Tracks the shortlist of locum candidates for spring lambing cover as Graeme builds toward his own practice.
- **Okta** (`okta-api`): Handles single sign-on across the new cloud practice stack so one login covers records, dispensing logs, and the booking tools.
- **ServiceNow** (`servicenow-api`): Logs and tracks service requests with the equipment contractor for the Defender's refrigerated drug storage and surgical kit.
- **GitHub** (`github-api`): Watches the open-source offline-sync tool underpinning the records migration, tracking releases and known issues.
- **GitLab** (`gitlab-api`): Follows the practice-platform vendor's public issue tracker and changelog for fixes that affect the December migration.
- **Datadog** (`datadog-api`): Monitors uptime of the cloud clinical-records pilot so sync failures surface before Craig is out of signal range.
- **Sentry** (`sentry-api`): Captures crash and error reports from the offline-first records app during the pilot, forwarded to the vendor with context.
- **PagerDuty** (`pagerduty-api`): Escalates missed emergency-line calls into alerts so a farmer's call-out never sits silent while Craig is in a dead zone.
- **Cloudflare** (`cloudflare-api`): Manages DNS and edge security for the practice site and keeps the booking page up when the village connection wobbles.
- **Kubernetes** (`kubernetes-api`): Keeps the small self-hosted sync stack for the records pilot healthy, restarting workloads when the overnight backup job hangs.
- **Google Analytics** (`google-analytics-api`): Shows which practice-page notices farmers actually read, shaping what goes in the seasonal update.
- **Mixpanel** (`mixpanel-api`): Tracks which advice sheets and booking flows farmers use most, feeding what gets written next.
- **Amplitude** (`amplitude-api`): Measures engagement on the reminder flows so Crook can tell which nudges actually move bookings.
- **PostHog** (`posthog-api`): Runs self-hosted analytics and feature flags on the records pilot, rolling new modules out farm by farm.
- **Segment** (`segment-api`): Pipes booking, page, and reminder events into one stream so the practice numbers reconcile in a single view.
- **Algolia** (`algolia-api`): Powers instant search across the digitised clinical notes and drug formulary so withdrawal periods come back in seconds.

#### Lifestyle, Health & Home

- **Ticketmaster** (`ticketmaster-api`): Watches Inverness and Glasgow listings for Rodrigo y Gabriela dates and the shows Fiona flags, booking when the rota allows.
- **Eventbrite** (`eventbrite-api`): Registers for veterinary congresses and local agricultural shows, including the Lochcarron Agricultural Show in November.
- **Yelp** (`yelp-api`): Picks restaurants for Inverness supply-run lunches and scouts Harrogate options for congress week.
- **Strava** (`strava-api`): Logs his twice-weekly estate-road runs and Munro days, with the summit count ticking up from 87.
- **MyFitnessPal** (`myfitnesspal-api`): Tracks protein and energy intake through lambing season when meals get skipped, at Fiona's insistence.
- **Google Classroom** (`google-classroom-api`): Hosts the bovine reproductive ultrasonography course modules he is working through ahead of Harrogate.
- **OpenLibrary** (`openlibrary-api`): Tracks down nature writing, Garcia Marquez translations, and the James Herriot editions for the slow re-read pile.
- **Ring** (`ring-api`): Watches the dispensary outbuilding camera and flags after-dark motion near the controlled-drug store.

#### Not Connected

- Web search, browsing, and live internet research are not available through this assistant. Treat any task that requires fresh web data as out of scope.
- The practice's vet-specific clinical records platform is managed in its own app and is not connected here.
- The APHA reporting portal is web-login only and not connected here.
- Self-assessment tax through HMRC runs via Douglas Mackay at Mackay & Co. and is not connected here.
- OS Maps Premium and Met Office for offline route planning live on the phone directly.
