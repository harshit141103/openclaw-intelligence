# Vendor Guidelines: OpenClaw **RL/Eval Multimodal** Data Collection

**Change Log:**  
**May 9, 2026**

- No need to do non\_multimodal passK as we realize the agent will refuse to answer the question without access to visual artifacts.

**May 5, 2026**

- Updated the taxonomy with some examples.

## Overview

This addendum defines the multimodal-specific overlay on top of the existing OpenClaw RL data collection format. Vendors should continue using the same task packaging, environment, rubric, pytest, and pass@k requirements from the main guide. The additions below specify what makes a task meaningfully multimodal, guidelines/issues to avoid, requirements for additional metadata.

## What qualifies as a multimodal task?

*A task should be counted as multimodal only if the visual, audio, or media evidence is necessary to complete at least one core requirement. Attaching an image to a task that can be solved from text alone does not count. Strong MM tasks require the agent to inspect, compare, extract from, or generate visual/media artifacts as part of the task outcome.*

Preferred patterns include visual-text reconciliation, OCR over messy real-world documents, visual search and product matching, time-series image/video change detection, document or receipt extraction, media quality/compliance review, and visual artifact creation where the output itself must be inspected.

U \-\> user uploaded media, T-\> tool/api returns media, O \-\> agent produces an artifact  
PS the [Taxonomy](#bookmark=kix.s3kjx7uolwya) below

| L1 | L2 | Task (gist) | Modality / Volume | Required capability | Verdict | Reasoning |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| Small Business & Personal Docs | Document Generation from Visual Input | I was on holiday last week. Reschedule the meetings I missed; cancel anything that conflicts with my flight back. | none | tool / text reasoning | ✗ | All inputs are calendar entries (text/JSON). No media to analyze or produce. |
| Small Business & Personal Docs | Document Generation from Visual Input | Screenshot of my budget spreadsheet attached. Plan a 7-day Tokyo trip within budget and book the flights. | U / 1 (decorative) | text extraction | ✗ | If the user pasted the spreadsheet directly the task is unchanged. Image is decorative; necessity test fails. |
| Creative & Media | Social Media Content Audit | Photo of last night's restaurant menu. Write a Yelp review based on what I had ,  filet mignon, pasta carbonara, tiramisu ,  and emphasize the ambience. | U / 1 (decorative) | text generation | ✗ | User already named the dishes; menu image carries no required information. |
| Commerce & Product | Visual Shopping / Comparison | I saw this lamp at my friend's house. Search for this exact lamp or the closest match in brushed brass and similar height. Check FB Marketplace, Amazon, and Craigslist; if you find the exact one on Marketplace, message the seller and ask if they'd take $50 for it. | U \+ T / 1 user, many tool | fine-grained visual matching (finish, proportions, era) | ✓ | No text label/title to search by ,  only path is visual matching across product listing images. |
| Property & Space | Interior Design / Renovation | 3 months of weekly kitchen-reno progress photos \+ approved design mockups. Estimate actual completion percentage; flag anything that looks wrong or different from the approved design. | U \+ U(ref) / time-series \~12 sets | cross-temporal change detection \+ mockup-vs-actual comparison | ✓ | Visual comparison across time and against reference designs. |
| Property & Space | Real Estate Listing Review | 15 inherited Zillow listings \+ recent seller-supplied photos. Flag listings where the photos are misleading or are missing required types (kitchen, bathrooms, exterior). | U \+ T / 15 listings × multi-photo | cross-source visual matching \+ completeness check | ✓ | Both sides are images; mismatch detection is purely visual. |
| Health & Wellness | Skin / Symptom Triage | Photos of my arm rash every few days for 2 weeks. Look at the progression, compare against common dermatological conditions, and write a clear summary for my doctor appointment with the photo timeline. | U / time-series 5-10 | medical perception \+ change detection over time | ✓ | Core task is describing visual change over time. |
| Visual Learning | Homework / Problem Solving | Worksheet pages photographed ,  printed problems, my kid's handwritten attempts, and diagrams (geometry, free-body, circuits). Solve, check her work, save solutions.md. | U / \~10 pages | handwriting OCR \+ diagram interpretation | ✓ | OCR \+ diagram parsing is the core challenge. |
| Creative & Media | Design / Portfolio Review | 8 logo concepts I sent a client \+ their vague feedback ("make it pop more", "the third one feels off"). Analyze each against the brief; translate the feedback into specific design changes. | U / 8 | design evaluation \+ interpretive reasoning over subjective feedback | ✓ | Concept evaluation against a brand brief requires visual aesthetic judgment. |
| Visual Learning | Textbook / Lecture Comprehension | 2-hour Org Chem lecture video. Generate timestamped notes with slide content, then build a quiz and flashcard deck for the exam. | U \+ O / 1 long video | speech-to-text \+ slide OCR \+ scene segmentation \+ flashcard layout | ✓ | Audio \+ visual \+ output-MM (flashcard deck) ,  main doc has no video tasks. |
| Operations & QA | Security Camera Review | Door cam \+ baby monitor running 24/7. Alert me on WhatsApp when an unknown person appears after 10pm OR the baby cries (not normal movement). Ignore cats and delivery drivers. | T / continuous streams | real-time video classification \+ face matching \+ audio classification | ✓ | Streaming MM with identity matching ,  main doc has no real-time examples. |
| Property & Space | Real Estate Listing Review | 100-page apartment lease (PDF) \+ 30-min property walkthrough video I recorded. Flag any mismatches between what's promised in the lease and what I saw. | U \+ U / long PDF \+ long video | cross-modal text ↔ video grounding over long context | ✓ | Cross-modal reasoning over long context ,  neither modality alone is sufficient. |
| Operations & QA | UI / UX Screenshot Audit | 30-page web-form screenshots for a permit application \+ my profile data. Fill it out and submit. | U \+ O / many pages | pixel-coordinate grounding \+ field extraction | ✓ | Form filling needs spatial grounding to map field labels → input positions. |

Other requirements

- **Real world**: Tasks should match real-world use-cases and not look contrived or made up. Real user data is messy ,  IMG\_0427.HEIC, duplicates, missing timestamps, blurry phone shots, scanned-skewed PDFs, mixed orientations. Tasks where input\_files/ is a curated set of perfectly-cropped JPGs are contrived.  
- **Diversity**: Add diversity so we can cover more broad use-cases. For example, all personal examples should not just focus on reading inbox or relying on them or start with “I was on holiday….” or “plan me a trip”.  
- **Cross-modal reasoning**: Cross-modal reconciliation as a first-class task type. ≥ 50% of tasks should require fusing ≥ 2 modalities ,  e.g., 100-page PDF lease ↔ 30-min walkthrough video, or meal photos ↔ MyFitnessPal targets. Single-modality MM is allowed but doesn't exercise the main capability of the eval. Similar to previous data collection we encourage the samples using multiple skills/apps.  
  - File-format and volume realism. Mix HEIC / JPG / PNG / WEBP ,  not all PNG. Mix phone-portrait / scanned-skewed / screenshots ,  not all 1024×1024 squares.  
- **Cross-artifact generation and consistency**: On tasks requiring multimodal artifact generation try to generate multiple artifacts and also have rubrics cross-check them   
- Make sure to also add depth. For example, a task requiring reading images \-\> producing report is a single depth while a task requiring images \-\> identifying issues \-\> cross reference against reference \-\> producing report could be more depth.  
- Rubrics should not only check for artifacts but also have some checks on actual content and values

Other common issues

- Outcome-oriented rubrics over process-oriented. Grade what the agent produced, not what tool / CLI it called.  
- Pass@k discipline. Target is ≈40% pass@8 across 2 SOTA models. If pass@k \= 0% on any rubric, attach a human justification ,  at that point the rubric is more likely wrong than the model.  
- Rubrics check values, not just artifact presence. Recurring rejection pattern: "Checking for a single incorrect value instead of validating the correct deterministic outcome." Each artifact needs ≥ 1 value-level rubric (a number, a string, a date, a range ,  not just "file exists").  
- No answer-leak in prompt or input\_files. Common MM trap: prompt asks the agent to transcribe a lecture, but input\_files/ contains a notes.txt summarizing it. Vendors paste reference material to help reviewers; agent shortcuts; eval signal collapses.

## MM annotator checklist

Use this checklist as the quick acceptance gate for multimodal tasks. The main OpenClaw collection guide still defines the task package, environment, rubric, pytest, and pass@k requirements. This checklist only covers the MM-specific pieces annotators should verify before submission.

- [ ] **The media is necessary.** At least one core requirement cannot be completed without inspecting the image, screenshot, PDF scan, video, audio, or generated visual artifact.  
- [ ] **The MM dependency is explicit.** The task has tags noting the input such as upload\_image, api\_image, pdf, screenshot, video, audio.   
- [ ] **The assets look realistic.** Include plausible user-file messiness when appropriate: blurry photos, mixed orientations, duplicates, screenshots, scans, HEIC/JPG/PNG/PDF formats, missing or misleading filenames, and imperfect lighting.  
- [ ] **The task is still solvable and gradable.** Messiness should create realistic difficulty, not make the key visual evidence unrecoverable.  
- [ ] **There is no answer leak.** Asset manifests, filenames, notes, reference files, and helper docs must not reveal the answer the agent is supposed to infer from media.  
- [ ] **At least one grader checks media content.** The rubric or pytest should verify a value, match, mismatch, visual detail, quality judgment, extraction result, or decision that depends on the media. It is not sufficient to only check for existence.  
- [ ] **Cross-modal reconciliation is tested when relevant.** Strong tasks ask the agent to connect media with another source: listing text, receipts vs transactions, photos vs invoices, calendar/context, API records, notes, or prior user preferences.  
- [ ] **Justification for rubrics that do not pass**: Include justification for rubrics which never pass so we know this is because of the task being hard and not the rubric being bad   
- [ ] **Safety boundaries are clear.** Medical images, homework screenshots, tax/financial documents, insurance claims, seller messaging, faces, children, IDs, and private images need explicit limits and should use mocked or synthetic data where appropriate.

**Important:** In addition to PassK@8 with 2 SOTA models we want to make sure the performance on the task is low without the multimodal inputs. We thus also ask you to report passK@8 for 2 models with and without multimodal assets. The performance without the assets should be \< 50% of the assets (threshold can be adjusted).

## Skills and CLIs

- Initially we will work with only 3 tools \-\> bash, browser, image view and skills created by the vendor describing procedures for using the APIs. Note that compared to previous collections these apis can return multimodal assets and we recommend using that. For example youtube-api returns a video while a ring-api returns a video recording at specific intervals.

We will be adding some additional APIs based on the use-cases but you can be creative here

| Existing in Previously collected data (E) | New APIs needed (N) |
| :---- | :---- |
| amazon-api | etsy-api |
| zillow-api | amazon-seller-api |
| health-api | pinterest-api |
| instacart-api | myfitnesspal-api |
| notion-api | instagram-api |
| slack-api | youtube-api |
| shopify (flat-file) | linear-api |
| fintrack (flat-file) | ring-api |
| obsidian-api | google-classroom-api |
| whatsapp-api | quickbooks-api |
| calendar-api |  |

## Pilot

- For pilot we would like you to provide **10 examples** (in priority)


| Commerce & Product | 2 |
| :---- | :---- |
| Creative & Media | 2 |
| Visual Learning | 2 |
| Property & Space | 1 |
| Operations & QA | 1 |
| Small Business & Personal Docs | 2 |


Volume expectations after pilot (may increase later):

| Commerce & Product | 50 |
| :---- | :---- |
| Creative & Media | 50 |
| Visual Learning | 50 |
| Property & Space | 30 |
| Operations & QA | 30 |
| Small Business & Personal Docs | 40 |

## Useful FAQs

Q: How to verify the quality of assets using rubrics.  
A: We strongly suggest only checking things via rubrics (text based judge) and pytest. If the team has experience with creating rubrics for quality we can add those in pilot or for a few samples. 

Q: What if a sample needs a new category in taxonomy.  
A: Feel free to suggest and we can make changes (adding new L2s is easier). There could also be overlap and we can have multiple tags for an example  
 

## Taxonomy

- Things marked in green are high-priority overall for us

|  | Priority | Category | Example | Comment on capability needed | Use-case |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Visual Learning  | P0 | Homework/Problem Solving | Worksheet pages photographed ,  printed problems, my kid's handwritten attempts, and diagrams (geometry, free-body, circuits). Solve, check her work, save [solutions.md](http://solutions.md) to obsidian value. | Cross-modal reasoning across artifacts, referencing, verifying, generating the reasoning  | Personal (student, parent) |
|  |  | Lab/Fieldwork Documentation | A folder containing 7 daily photos of a germinating bean seed, each with a metric ruler placed next to the growing root. Visually read the root length from the ruler in each of the 7 consecutive photos. Calculate the daily growth rate, write and execute a Python script to plot a matplotlib line graph of length-over-time, and output a lab report combining the graph with a textual summary of the growth trend. | MM understanding, reasoning across artifacts, coding, creating report from multiple sources | Personal/Semi-pro (someone doing this as a hobby or even small business)  |
|  |  | Textbook/Lecture Comprehension | 2-hour Org Chem lecture video. Generate timestamped notes with slide content, then build a quiz and flashcard deck for the exam. | Video understanding, cross-modality (might use speech), artifact generation | Personal |
| Commerce & Product | P0 | Visual Shopping/Comparison | I saw this lamp at my friend's house. Search for this exact lamp or the closest match in brushed brass and similar height. Check FB Marketplace, Amazon, and Craigslist; if you find the exact one on Marketplace, message the seller and ask if they'd take $50 for it. | Visual understanding, check exact matches | Personal |
|  | P1 | Product Listing QA | “I run a vintage furniture shop on Etsy and my listings are a mess. I just dumped 30 photos of my latest pieces into input\_files/ but half of them are blurry, poorly lit, or missing the required angles. I also think some of my existing live listings have photos that don't match the item description. Can you go through the new photos and tell me which ones are usable vs need reshooting, then audit my live Etsy listings and flag any where the photos don't match what the description says?” |  | Personal/semi-pro |
|  | P2 | Brand/Packaging Audit | We're launching a new line of organic snacks and I just got the packaging proofs back from the printer (uploaded to input\_files/). I need you to check every label against our brand guidelines doc and the FDA nutrition label requirements. Also pull our competitor products from the Amazon catalog and compare ,  are we standing out on the shelf or do we look like a generic knockoff? |  | Semi-pro |
| Creative & Media | P0 | Image/Video Editing | “Take this video of the last FIFA Wc final and I want you to create small video chunks for each goal. Name each chunk based on the player who made the goal \+ country. Then I want you to create a html report referring these chunks and writing 2 line description about the goal. Also add a table for stats covering player with maxim goals |  | Personal/Semi-pro |
|  | P0 | Social Media Content Audit | “I run the Instagram account for a boutique coffee shop and my boss says our feed looks inconsistent." Can you pull our last 50 posts, analyze the visual style (colors, filters, composition, branding), and identify which posts break the pattern? Create a style guide based on our best-performing posts and flag the ones that should be archived or re-edited. Also check our competitors' feeds and tell me what they're doing better visually.” |  | Personal |
|  | P0 | Design/Portfolio Review |  I'm a freelance graphic designer and I just sent 8 logo concepts to a client (all in input\_files/). They sent back super vague feedback like "make it pop more" and "the third one feels off." I also have their original brief and their competitor logos saved. Can you analyze each concept against the brief requirements, identify which ones best match their brand personality, and translate their vague feedback into specific design changes I can actually action? |  | Personal/Semi-pro |
| Operations & QA  | P0 | Document/Receipt Processing | Update the meal expense tracking document with the details from the dinner receipt picture. Follow the existing format of the expense document, ensuring the weekly and monthly textual summaries and visualizations are updated to reflect the new receipt data. | Cross-modal reasoning, artifact generation, cross-referencing, planning and reasoning | Personal |
|  | P1 | Inventory Visual Audit | Photos of a warehouse pallet before and after a delivery driver loads their van. Compare the two images to calculate exactly how many boxes of each product were removed. Verify the number against the record inputted by the delivery driver. Automatically update the central inventory database only after this verification is complete otherwise send a warning message to the owner. | Cross-modal reasoning, change detection, reasoning | Semi-pro |
|  | P0 | UI/UX Screenshot Audit/form-filling | 30-page web-form screenshots for a permit application \+ my profile data. Fill it out and submit to xyz \[some api\]. | Cross-referencing, artifact generation |  |
| Health and Wellness | P0 | Skin/Symptom Triage | Photos of my arm rash every few days for 2 weeks. Look at the progression, compare against common dermatological conditions, and write a clear summary for my doctor appointment with the photo timeline. |  | Personal |
|  | P1 | Nutrition/Meal Logging | Analyze the photo of my lunch and my meal logging history tracking sheet. Determine the nutritional content of the lunch and compare it with the tracked previous meals. Based on this comparison, generate a summary of my current nutritional intake and offer suggestions for improvement. Finally, integrate all this information into the logging sheet for ongoing reference. |  | Personal |
| Property and Space | P0 | Real Estate Listing Review | 100-page apartment lease (PDF) \+ 30-min property walkthrough video I recorded. Flag any mismatches between what's promised in the lease and what I saw. |  | Semi-pro |
|  | P1 | Interior Design/Renovation |  I've been renovating my kitchen for 3 months and I've been taking progress photos every week (all in input\_files/ organized by date). My contractor says we're 80% done but looking at the photos I'm not so sure. Can you create a visual timeline, estimate actual completion percentage based on what you see vs the original renovation plan, and flag anything that looks wrong or different from the approved design mockups I also uploaded?  |  | Personal/Semi-pro |

1. Visual learning: Student, parent, or self-learner uses academic media (worksheets, lecture slides, lab photos, textbook pages) to understand or document content. Agent OCRs handwriting, interprets diagrams, and produces study artifacts (notes, lab reports, solution sets, study guides).  
2. Commerce & Product: Shopper, online seller, or brand owner working with product or marketplace imagery. Agent visually matches items across listings, audits listing/photo quality, or checks brand/packaging against competitors and compliance rules.  
3. Creative & Media: Personal or semi-pro creator producing, editing, or auditing visual/video content. Inputs are user-shot footage, design concepts, or social feeds; outputs are edited media, style guides, or actionable design feedback. An important use-case here is video editing for personal or semi-professional use. Note this is not generation of new artifacts (like Sora, gemini-image) but apply some operation on previous image/video like cropping, editing, focusing, zooming-in.  
4. Operations & QA: Agent-as-back-office-operator. Visual evidence (receipts, screenshots, before/after photos) either updates an existing system of record (expense doc, form, inventory DB) or gates an action against a claim.   
5. Health & Wellness: User shares personal health or diet media (skin progression photos, meal photos, symptom timelines). Agent reasons over visual change or content, compares against references (dermatological conditions, nutrition targets, meal plan), and produces summaries for the user or their care provider.  
6. Property & Space: Homeowner, renter, or real-estate agent assessing a physical space. Inputs are listing photos, room shots, or renovation-progress images; agent does cross-source visual matching (listing vs reality), time-series change detection (progress vs plan), or staging/design review.
