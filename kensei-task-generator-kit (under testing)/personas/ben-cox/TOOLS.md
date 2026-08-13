# Tools: Ben Cox

## Tool Usage

### General Agent Capabilities

- **Wide Research**: Use for material pricing (cherry, maple, oak, walnut at Hardwick Lumber and Burlington specialty suppliers), building code lookups, and the occasional medical question he will not bring to Dr. Whitfield, presented as clean comparisons with sources cited.
- **Documents**: Use to draft client estimates, project schedules, material orders, and the occasional letter Diane then handles through her own channels.
- **Memory Search** (`memory_search`): Always search before tasks involving people, dates, or past context.

### Connected Services

#### Workspace, Mail & Files

- **Gmail** (`gmail-api`): Personal mail on `ben.cox@finthesiss.ai` for client email; draft replies to the Hendersons in Stowe and the Craftsbury professor, drafts only, Ben sends.
- **Google Calendar** (`google-calendar-api`): The work schedule, client meetings, deliveries, and medical appointments; cross-check the forecast before any on-site block.
- **Google Drive** (`google-drive-api`): Estimates, project plans, the project tracking sheet, photos of finished work, and the running material order log.
- **Outlook** (`outlook-api`): Backup email only; the Gmail address is the primary channel.
- **Dropbox** (`dropbox-api`): Backup reference for job-site photos; Google Drive is primary.
- **Box** (`box-api`): Backup reference only; clients occasionally share files this way.
- **DocuSign** (`docusign-api`): Client contracts and the occasional vendor agreement; Diane co-signs anything that touches the business books.

#### Scheduling, Tasks, Notes & Forms

- **Notion** (`notion-api`): Available as an alternate planning space; the default is Google Sheets.
- **Obsidian** (`obsidian-api`): Available for shop notes if Ben ever wants a local notebook; not active.
- **Airtable** (`airtable-api`): Useful for the Greensboro barn restoration, with material counts, contractor handoffs, and salvage inventory in one view.
- **Asana** (`asana-api`): Alternate task board if Ben asks; default is Google Sheets.
- **Trello** (`trello-api`): Alternate board for a project punch-list if he wants one.
- **Monday** (`monday-api`): Alternate project tracker, not in daily use.
- **Linear** (`linear-api`): The shop punch-list (sharpening cycle, jointer setup, finish schedule); never used for client work.
- **Calendly** (`calendly-api`): Scheduling client consultations; the Hendersons already use it to finalize install dates.
- **Typeform** (`typeform-api`): Available for a simple client intake form; not active yet.
- **Google Classroom** (`google-classroom-api`): Reference for Diane's school librarian work; Ben does not use it.

#### Messaging & Calls

- **WhatsApp** (`whatsapp-api`): The occasional message with Keith or Marie when SMS is flaky; send only on explicit instruction.
- **Telegram** (`telegram-api`): Not active for Ben; reference only.
- **Discord** (`discord-api`): Not active for Ben; reference only.
- **Slack** (`slack-api`): Reference only; Keith uses it at his startup, Ben does not.
- **Microsoft Teams** (`microsoft-teams-api`): Reserved for the rare remote consultation with an out-of-state client.
- **Zoom** (`zoom-api`): Reserved for a virtual walkthrough of a finished piece before he ships it.
- **Twilio** (`twilio-api`): Transactional SMS confirmations (delivery alerts, dental reminders) routed to his iPhone 13.

#### Client Email & Outreach

- **SendGrid** (`sendgrid-api`): Batch email drafts such as year-end client thank-you notes; never sent in bulk without his sign-off.
- **Mailchimp** (`mailchimp-api`): Available if Ben ever sends a yearly client newsletter; he has not yet.
- **Mailgun** (`mailgun-api`): Alternate bulk-email option for that someday newsletter, dormant.
- **Klaviyo** (`klaviyo-api`): Reference only; no marketing list exists.
- **ActiveCampaign** (`activecampaign-api`): Reference only; no marketing automation in use.

#### Weather, Maps, Travel & Errands

- **OpenWeather** (`openweather-api`): The primary feed; pull Craftsbury, Stowe, Greensboro, and Hardwick forecasts whenever an outdoor task or drive is in play.
- **Google Maps** (`google-maps-api`): Navigation to client sites, supplier yards, and the trout streams, with drive-time estimates for the F-350.
- **Uber** (`uber-api`): Backup if the truck is down; Ben strongly prefers his own vehicle.
- **Airbnb** (`airbnb-api`): Reference for the occasional family trip Diane plans; Ben does not initiate travel.
- **Amadeus** (`amadeus-api`): Reference for flights; Ben rarely flies and Diane handles itineraries.
- **NASA** (`nasa-api`): The once-a-year aurora sighting or meteor shower question.
- **Yelp** (`yelp-api`): Reference for the rare new restaurant Diane wants to try; Ben sticks with his regulars.
- **DoorDash** (`doordash-api`): Reference only; Diane handles groceries and Ben prefers to drive to town.
- **Instacart** (`instacart-api`): Reference only; same reason.

#### Materials, Vendors & Shipping

- **Amazon Seller** (`amazon-seller-api`): Buyer-side price baseline for tools; Ben prefers Hardwick or Burlington in person but uses it for the obscure part.
- **Etsy** (`etsy-api`): Specialty hardware for a finished cabinet, or the occasional gift for Marie.
- **Pinterest** (`pinterest-api`): The inspiration boards clients send him and vintage tool research.
- **BigCommerce** (`bigcommerce-api`): Reference for small vendors during material research; never a direct purchase over $150 without confirmation.
- **WooCommerce** (`woocommerce-api`): Same, an alternate small-vendor storefront for materials.
- **FedEx** (`fedex-api`): Track inbound material shipments and the occasional outbound restoration component.
- **UPS** (`ups-api`): Track material and tool shipments to the farmhouse.
- **Shippo** (`shippo-api`): Reference for the rare outbound piece sent to an out-of-state client.
- **Zillow** (`zillow-api`): Neighborhood comparables when a client asks about the value impact of a built-in or kitchen renovation.
- **Ring** (`ring-api`): Not installed at the farmhouse; reference only.

#### Payments & Finance

- **Stripe** (`stripe-api`): Reference for parsing receipts on supplier orders; Diane handles invoicing in QuickBooks.
- **Square** (`square-api`): Reference for parsing receipts from the Craftsbury General Store and other local vendors.
- **PayPal** (`paypal-api`): Occasional online vendor payments under $150; anything larger needs Ben's confirmation.
- **QuickBooks** (`quickbooks-api`): Diane's business books on the laptop; reference only, never reach into the books on Ben's behalf.
- **Xero** (`xero-api`): Reference alternate to QuickBooks; not used.
- **Plaid** (`plaid-api`): Reference only; banking happens in person at Community National Bank.
- **Coinbase** (`coinbase-api`): Reference only; Ben does not trade.
- **Alpaca** (`alpaca-api`): Reference only; no investing through it.
- **Binance** (`binance-api`): Reference only; no crypto holdings.
- **Kraken** (`kraken-api`): Reference only; no crypto holdings.

#### Music, Reading, Downtime & Health

- **Spotify** (`spotify-api`): Classic rock (CCR, Stones, Zeppelin), bluegrass, and old country for the iPhone on a job site; the shop radio covers the rest.
- **YouTube** (`youtube-api`): Technique videos, vintage tool restoration walkthroughs, and the rare Red Sox highlight.
- **TMDB** (`tmdb-api`): Confirms what Ben and Diane queued on Netflix.
- **OpenLibrary** (`openlibrary-api`): Vermont history and WWII reading he picks up at the Craftsbury Public Library.
- **Reddit** (`reddit-api`): r/woodworking threads when he wants a second opinion on a finish or a glue-up; rare but useful.
- **Twitch** (`twitch-api`): Not part of Ben's flow; reference only.
- **Vimeo** (`vimeo-api`): Not part of Ben's flow; reference only.
- **Ticketmaster** (`ticketmaster-api`): Red Sox or local fair tickets if Ben asks.
- **Eventbrite** (`eventbrite-api`): Local fair and community event tickets when one comes up.
- **MyFitnessPal** (`myfitnesspal-api`): Available for the 15-pound weight-loss goal Dr. Whitfield set; surface only if Ben asks.
- **Strava** (`strava-api`): Not used by Ben; reference only.

#### Website, Design & Social (Keith maintains, Ben does not touch)

- **WordPress** (`wordpress-api`): The Cox Custom Woodwork website Keith maintains; Ben does not edit it directly.
- **Webflow** (`webflow-api`): Reference for the website build; Keith's domain.
- **Contentful** (`contentful-api`): Reference content backend for the site; Keith's domain.
- **Figma** (`figma-api`): Reference only; clients sometimes share design files this way.
- **Algolia** (`algolia-api`): Reference for site search Keith manages; Ben does not use it.
- **Instagram** (`instagram-api`): Not used by Ben; Marie occasionally posts a photo of one of his pieces.
- **Twitter** (`twitter-api`): Not used by Ben.
- **LinkedIn** (`linkedin-api`): Not used by Ben.

#### Site Analytics (passive, Keith reviews)

- **Google Analytics** (`google-analytics-api`): Website traffic Keith reviews; Ben does not look at it.
- **Mixpanel** (`mixpanel-api`): Reference only; product analytics Ben does not use.
- **Amplitude** (`amplitude-api`): Reference only; same.
- **PostHog** (`posthog-api`): Reference only; same.
- **Segment** (`segment-api`): Reference only; no event pipeline in Ben's world.

#### Engineering & Infrastructure (Keith's world, reference)

- **GitHub** (`github-api`): Reference for Keith's tinkering with the website; Ben does not touch code.
- **GitLab** (`gitlab-api`): Reference only; Keith's domain.
- **Jira** (`jira-api`): Reference only; not part of Ben's flow.
- **Confluence** (`confluence-api`): Reference only; not part of Ben's flow.
- **ServiceNow** (`servicenow-api`): Reference only; not part of Ben's flow.
- **PagerDuty** (`pagerduty-api`): Reference for Keith's tech context; Ben does not interact with it.
- **Datadog** (`datadog-api`): Reference only; Keith's world.
- **Sentry** (`sentry-api`): Reference only; Keith's world.
- **Cloudflare** (`cloudflare-api`): Reference only; protects the website Keith runs.
- **Kubernetes** (`kubernetes-api`): Reference only; Keith's world.
- **Okta** (`okta-api`): Reference for subcontractor onboarding if Ben ever formalizes hiring; current setup is informal.

#### CRM, Support & HR (reference)

- **HubSpot** (`hubspot-api`): Reference only; Ben handles client relationships in person and by phone.
- **Salesforce** (`salesforce-api`): Reference only; no CRM in use.
- **Intercom** (`intercom-api`): Reference only; no support product.
- **Zendesk** (`zendesk-api`): Reference only; no support desk.
- **Freshdesk** (`freshdesk-api`): Reference only; no ticket queue.
- **BambooHR** (`bamboohr-api`): Reference for subcontractor onboarding on a larger job; setup is informal.
- **Greenhouse** (`greenhouse-api`): Reference only; Ben is not hiring formally.
- **Gusto** (`gusto-api`): Reference only; no payroll beyond the occasional cash subcontractor.

#### Not Connected

- Live web search, web browsing, and deep internet research are not available. You work only from connected mock APIs and stored memory.
- Banking (Community National Bank) is handled in person; no app or API access. Reference balances from MEMORY.md, but never initiate transactions.
- QuickBooks is Diane's on the household laptop and out of scope; route accounting questions back to her.
- Health portals (Copley Hospital, Hardwick Dental) require manual login; appointments stay on the calendar, clinical details stay on the portal.
- Ben uses no social media accounts of his own; do not draft posts, check feeds, or propose creating an account.
