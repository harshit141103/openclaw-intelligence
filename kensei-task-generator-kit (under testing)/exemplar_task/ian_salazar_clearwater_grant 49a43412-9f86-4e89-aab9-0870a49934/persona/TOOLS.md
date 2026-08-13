# Tools: Ian Salazar

## Tool Usage

### General Agent Capabilities

- **Documents**: Draft grant narratives, county briefing notes, bilingual community surveys, Etsy product descriptions, and the occasional dormant-blog post about Las Cruces urbanism. Match the register of the audience.
- **Memory Search** (`memory_search`): Always search before tasks involving people, dates, or past context.

### Connected Services

#### Fieldwork, Mapping & Weather
- **Google Maps** (`google-maps-api`): Route planning to sample sites and pronghorn survey routes, plus drive-time estimates from Las Cruces to El Paso.
- **OpenWeather** (`openweather-api`): Forecast checks for fieldwork windows. Surface monsoon-rain probability for any morning Ian is sampling.
- **NASA** (`nasa-api`): Landsat and MODIS imagery for watershed monitoring. Pull cloud-cover masks before Ian commits to a satellite-dependent comparison.

#### Audio & Listening
- **Spotify** (`spotify-api`): Chicano alternative, cumbia, and ambient instrumentals for long leatherwork evenings.

#### Calendar, Notes & Files
- **Google Calendar** (`google-calendar-api`): Fieldwork schedule, county meetings, leatherwork deadlines, Sunday visits with Abuela Rosa, and Marco reality-TV nights.
- **Gmail** (`gmail-api`): Primary email at `ian.salazar@voissync.ai`. Triage county and grant correspondence before personal.
- **Google Drive** (`google-drive-api`): Grant drafts, watershed data spreadsheets, sampling SOPs, and leatherwork inventory logs.
- **Notion** (`notion-api`): Long-form study notes for grant methodology and Chicano-speculative-fiction reading log.
- **Obsidian** (`obsidian-api`): Personal field journal with location-tagged observations from Doña Ana County sites.
- **Airtable** (`airtable-api`): 12-site water-quality sample tracker. One row per sample with chain-of-custody status.
- **Dropbox** (`dropbox-api`): Backup of large NetCDF and GeoTIFF files that exceed Drive quotas.
- **Box** (`box-api`): Read-only access to Dr. Brennan's shared Ridgemont State University research folder.

#### Council, Federal & Grant Coordination
- **DocuSign** (`docusign-api`): Grant signature pages, memoranda of understanding with community partners. Draft only.
- **Calendly** (`calendly-api`): Booking link for community-survey follow-up interviews across Doña Ana County (Mesilla, Las Cruces, Hatch, Anthony).
- **Typeform** (`typeform-api`): Bilingual community surveys (English, Spanish) for the Doña Ana County environmental-equity study.
- **ServiceNow** (`servicenow-api`): County IT ticketing for field-laptop and Garmin GPS issues. Submit, do not resolve.
- **HubSpot** (`hubspot-api`): Donor and community-partner contact rolodex for the leatherwork side, kept separate from county work.
- **Salesforce** (`salesforce-api`): Read-only into the Clearwater Environmental Trust grantee portal.
- **Google Classroom** (`google-classroom-api`): Read-only access to a Ridgemont State alum-mentoring cohort.
- **BambooHR** (`bamboohr-api`): Doña Ana County HR portal. Read-only to confirm payroll dates and PTO balance.

#### Storefront, Payments & Logistics (Salazar Leathercraft)
- **Etsy** (`etsy-api`): Salazar Leathercraft shop. New orders, message replies, listing tweaks.
- **Stripe** (`stripe-api`): Custom-commission invoicing outside Etsy, sent to clients in Albuquerque and El Paso.
- **PayPal** (`paypal-api`): Backup payment method for buyers who avoid Stripe.
- **Square** (`square-api`): Point-of-sale for in-person fiesta sales (Dia de los Muertos Mercado, Renaissance ArtsFaire).
- **Plaid** (`plaid-api`): Read-only link from Rio Grande Credit Union for monthly budget reconciliation.
- **QuickBooks** (`quickbooks-api`): Leatherwork bookkeeping. Quarterly reconciliation, no auto-categorization without his review.
- **Xero** (`xero-api`): Not used for personal books. Watching it in case Marco asks Ian about it for his clinic.
- **Shippo** (`shippo-api`): Etsy order labels. Domestic media-mail and First Class.
- **FedEx** (`fedex-api`): Larger commission shipments, journal covers in custom boxes.
- **UPS** (`ups-api`): Pickup scheduling for batched fiesta-restock returns.
- **Mailgun** (`mailgun-api`): Transactional order confirmations from the Etsy shop.
- **SendGrid** (`sendgrid-api`): Backup transactional email if Mailgun fails.
- **Google Analytics** (`google-analytics-api`): Salazar Leathercraft landing-page traffic only.

#### Customer Support & Comms
- **Zendesk** (`zendesk-api`): Etsy customer service messages funneled here for tracking. Reply within 24 hours.
- **Zoom** (`zoom-api`): EPA Region 6 coordination calls, monthly Dr. Brennan check-ins, county commissioner briefings.
- **Microsoft Teams** (`microsoft-teams-api`): Cross-county collaboration with neighboring jurisdictions.
- **Outlook** (`outlook-api`): Read-only mirror of certain county distribution lists that still default to Outlook.
- **Slack** (`slack-api`): Doña Ana County Environmental Services internal channel and the Ridgemont State University alumni research circle.
- **Discord** (`discord-api`): A small Chicano speculative fiction reading group Ian lurks in.
- **Telegram** (`telegram-api`): Diego's preferred channel for long-form messages across the border to El Paso.
- **WhatsApp** (`whatsapp-api`): Carmen, Abuela Rosa (relayed), Marco, Sofia. Spanish and English both belong here.

#### Project, Code & Engineering Edges
- **Linear** (`linear-api`): Personal project tracker for grant milestones and leather commissions. One workspace, two projects.
- **Jira** (`jira-api`): County IT uses Jira for field-equipment requests. Read-only.
- **Trello** (`trello-api`): Personal Kanban for fieldwork prep checklists.
- **Asana** (`asana-api`): Dr. Brennan's shared grant planning board. Edit access on Ian's assigned tasks only.
- **Monday** (`monday-api`): Read-only view of Sofia's NM Game and Fish habitat-survey board.
- **Confluence** (`confluence-api`): Ridgemont State research notes from his BS thesis, archived.
- **GitHub** (`github-api`): Repository `iansalazar/dona-ana-water-quality` for R scripts that wrangle the monthly sample data, shared with Dr. Brennan. Keep commits plain English.
- **GitLab** (`gitlab-api`): Read-only mirror of county GIS scripts.
- **Sentry** (`sentry-api`): Error tracking for the small Etsy listing helper Ian wrote in Python.
- **Okta** (`okta-api`): County SSO. Read account status, do not modify.
- **Cloudflare** (`cloudflare-api`): DNS for the Salazar Leathercraft small landing page.
- **Webflow** (`webflow-api`): Salazar Leathercraft landing page, occasional copy edits only.
- **WordPress** (`wordpress-api`): Dormant blog on Las Cruces urbanism Ian keeps meaning to revive.
- **Algolia** (`algolia-api`): Search on the Etsy listings helper. Index leather products by tag and weight.
- **Figma** (`figma-api`): Logo iterations for Salazar Leathercraft and seasonal flyer drafts for fiesta booths.

#### Social, Media & Public Voice
- **Instagram** (`instagram-api`): Wildlife photography and leatherwork posts. Small and engaged audience.
- **Pinterest** (`pinterest-api`): Reference boards for tooling patterns, Mission floral motifs, and Chicano craft tradition.
- **YouTube** (`youtube-api`): Watch-only. Leatherwork tutorial videos and Latin American astronomy talks.
- **Twitter** (`twitter-api`): Lurking account. Follows urban-planning and environmental-science accounts. Do not post.
- **Reddit** (`reddit-api`): r/Leathercraft and r/EnvironmentalScience for reference and the occasional thoughtful reply.
- **LinkedIn** (`linkedin-api`): Quarterly professional updates, county-position visibility for grant-relevant networking.
- **Vimeo** (`vimeo-api`): Hosts two short field videos for grant supplementary materials.
- **TMDB** (`tmdb-api`): Movie metadata for the nature documentaries Ian watches alone on Netflix.
- **OpenLibrary** (`openlibrary-api`): Borrowed-book and reading-list tracking, including Bacigalupi and Luis Alberto Urrea.

#### Health, Fitness & Outdoor
- **MyFitnessPal** (`myfitnesspal-api`): Hiking and walking logs with Scout. Consistency patterns only, no calorie obsession.
- **Strava** (`strava-api`): Occasional runs in cooler months along Las Cruces neighborhood streets. Match the route to the morning forecast before heading out.

#### Real Estate, Travel & Local Services
- **Zillow** (`zillow-api`): Watching small properties near Old Mesilla in case the rental market shifts.
- **Airbnb** (`airbnb-api`): Future Oaxaca trip planning with his mother.
- **Uber** (`uber-api`): Airport runs to El Paso International when his Subaru is in for service.
- **DoorDash** (`doordash-api`): Rare. Used only when fieldwork days run past 7 PM and the kitchen is empty.
- **Instacart** (`instacart-api`): Local mercado is closer than the Costco run for weekly basics; Instacart used about monthly.
- **Yelp** (`yelp-api`): Family-restaurant recommendations when Diego visits from El Paso.
- **Eventbrite** (`eventbrite-api`): Local fiesta-circuit registration (Día de los Muertos Mercado, Renaissance ArtsFaire) and occasional environmental-science satellite events (NM Water Conference, AGU Fall Meeting regional).
- **Ticketmaster** (`ticketmaster-api`): Concert lookups for Las Cafeteras or Ozomatli tours that might swing through New Mexico.
- **Amadeus** (`amadeus-api`): Airfare watching for the Oaxaca trip and conference travel.
- **Ring** (`ring-api`): No doorbell installed; account held to share with Carmen if she ever asks for help setting one up.

#### Not Connected

- **ActiveCampaign** (`activecampaign-api`): Unused. No marketing-email lists.
- **Alpaca** (`alpaca-api`): Unused. Ian does not trade.
- **Amazon Seller** (`amazon-seller-api`): Unused as a seller. Ian's Etsy shop is his only storefront; Amazon access is buyer-side only and not connected here.
- **Amplitude** (`amplitude-api`): Unused. No product-analytics surface in Ian's work.
- **BigCommerce** (`bigcommerce-api`): Unused. No standalone storefront beyond Etsy.
- **Binance** (`binance-api`): Unused. Ian does not trade.
- **Coinbase** (`coinbase-api`): Unused. Ian does not trade crypto.
- **Contentful** (`contentful-api`): Unused. No headless CMS in Ian's stack.
- **Datadog** (`datadog-api`): Unused. Out of scope for Ian's single-person operation.
- **Freshdesk** (`freshdesk-api`): Unused. Ian's Etsy shop is small enough that Zendesk covers it.
- **Greenhouse** (`greenhouse-api`): Unused. Ian has no employees.
- **Gusto** (`gusto-api`): Unused. Ian has no employees.
- **Intercom** (`intercom-api`): Unused. No live-chat surface needed for Salazar Leathercraft.
- **Klaviyo** (`klaviyo-api`): Unused. Salazar Leathercraft uses transactional only (Mailgun / SendGrid).
- **Kraken** (`kraken-api`): Unused. Ian does not trade.
- **Kubernetes** (`kubernetes-api`): Unused. Out of scope for a county environmental scientist.
- **Mailchimp** (`mailchimp-api`): Unused. No newsletter list for the leather shop yet.
- **Mixpanel** (`mixpanel-api`): Unused. No product-analytics surface in Ian's work.
- **PagerDuty** (`pagerduty-api`): Unused. Ian is not on call.
- **PostHog** (`posthog-api`): Unused. No product-analytics surface in Ian's work.
- **Segment** (`segment-api`): Unused. No analytics plumbing in Ian's work.
- **Twilio** (`twilio-api`): Unused. Ian's 2FA codes arrive via iPhone carrier SMS; he is not a Twilio account holder.
- **Twitch** (`twitch-api`): Unused. Diego streams gaming occasionally; Ian only drops in as a guest.
- **WooCommerce** (`woocommerce-api`): Unused. No standalone storefront beyond Etsy.
- Live web search, web browsing, and deep internet research are not available. The agent works only from connected mock APIs and stored memory.
- Doña Ana County internal GIS layers, county financial systems, and EPA Region 6 pre-decisional document repositories are not connected.
- Carmen Salazar's personal accounts, Abuela Rosa's home phone records, Marco's clinic systems, Sofia's NM Game and Fish internal databases, and Diego's hospital records are off limits.
- Ian's prior university email accounts and Ridgemont State University internal systems are not connected.
- **Twilio**: Ian is not a Twilio account holder; 2FA codes arrive via iPhone carrier SMS.
- **Coinbase, Alpaca, Binance, Kraken**: no crypto or brokerage activity. Ian does not trade.
- **Kubernetes**: Dr. Brennan's Ridgemont research-computing cluster is institution-side; Ian does not hold direct access.
- **Datadog, PagerDuty, Sentry-equivalent ops platforms beyond the single Etsy-helper Sentry project, Mixpanel, Amplitude, PostHog, Segment**: no analytics or on-call workflows for Ian's single-person operations.
- **Intercom, Freshdesk, Contentful**: no enterprise support or CMS workflows beyond Zendesk and WordPress.
- **Klaviyo, Mailchimp, ActiveCampaign**: no marketing-email lists; Salazar Leathercraft uses Mailgun and SendGrid transactional only.
- **BigCommerce, WooCommerce**: no standalone storefront beyond Etsy.
- **Greenhouse, Gusto**: no hiring or payroll workflows; Ian has no employees.
- **Twitch**: no streaming account; Diego streams gaming occasionally but Ian only drops in as a guest.
- **TikTok, Bluesky**, and any social network not listed above are not available.
