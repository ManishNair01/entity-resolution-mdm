# Centenarian prevalence and review policy

## What official sources say about age misstatement and verification at very old ages

### Takeaway

Centenarians are real but rare, and official statistical agencies apply extra scrutiny to extreme-age data because reporting, capture, and processing errors can disproportionately distort such a small population. Verification should reconcile the claimed birth details with authoritative records rather than reject a date merely because it implies age 100 or older.

### Cited Findings

- The UK Office for National Statistics estimated 16,600 people aged 100 or over in the UK in 2024, equal to 24.0 per 100,000 people, or about one in 4,200. — [ONS, *Estimates of the very old, including centenarians, UK: 2002 to 2024*](https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/ageing/bulletins/estimatesoftheveryoldincludingcentenarians/latest)
- The U.S. Census Bureau counted 80,139 centenarians in 2020, equal to 2.42 per 10,000 people; even among people aged 65 or older, centenarians were 0.14 percent. — [U.S. Census Bureau, *Centenarians: 2020*](https://www2.census.gov/library/publications/decennial/2020/c2020sr-02.pdf)
- The Census Bureau says extreme-age data can be affected by question-design problems, allocation of extreme ages during processing, deliberate age exaggeration, and the sensitivity of a small population to data-quality problems. — [U.S. Census Bureau, *Centenarians: 2020*](https://www2.census.gov/library/publications/decennial/2020/c2020sr-02.pdf)
- ONS validates deaths at age 105 and above by matching the death record to a birth record using date and place of birth, full name, and aliases; a transcription error can be accepted when it does not invalidate the age. — [ONS, *Accuracy of official high-age population estimates, in England and Wales: an evaluation*](https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/ageing/methodologies/accuracyofofficialhighagepopulationestimatesinenglandandwalesanevaluation)
- In its current methodology, ONS reassigns a record when evidence establishes the correct younger age, removes a record when evidence shows the person was not 110 or over but the correct age is unknown, and excludes unvalidated deaths above 113 for males and 115 for females. — [ONS, *Estimates of the very old, including centenarians, QMI*](https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/ageing/methodologies/estimatesoftheveryoldincludingcentenariansukqmi)

### Inferences

- A customer population in which roughly one quarter of valid-DOB records imply age 100 or older is not representative of contemporary UK or U.S. population prevalence; that discrepancy is a strong dataset-level reason to examine provenance, reference dates, and date-generation logic. This comparison does not identify which individual DOBs are wrong. — [ONS prevalence](https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/ageing/bulletins/estimatesoftheveryoldincludingcentenarians/latest); [U.S. Census prevalence](https://www2.census.gov/library/publications/decennial/2020/c2020sr-02.pdf)
- For this portfolio pipeline, age 100+ is defensible as an `enhanced_age_review` flag. It is not defensible as an automatic invalid-DOB rule because official agencies recognize and validate real centenarians. — [ONS validation methodology](https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/ageing/methodologies/accuracyofofficialhighagepopulationestimatesinenglandandwalesanevaluation)

### Gaps

- The official sources do not supply a universal customer-data cutoff at which a plausible calendar DOB becomes invalid. The appropriate threshold depends on the population, jurisdiction, reference date, and purpose of the check.
- The Febrl 3 data is synthetic, so comparison with national prevalence can reveal implausibility but cannot establish the intended DOB for any record.

## Whether age alone is evidence of fraud or death

### Takeaway

Age 100+ alone is evidence of elevated uncertainty, not evidence that a person is dead or committing fraud. Official processes distinguish a risk signal from a verified fact and require corroboration before changing life status or alleging fraud.

### Cited Findings

- U.S. Social Security Administration guidance treats a death certificate, certified public death record, physician or funeral-director statement, coroner report, or specified official government report as evidence of death. Age by itself is not on the accepted-evidence list. — [SSA Handbook §1720, *Evidence of Death*](https://www.ssa.gov/OP_Home/handbook/handbook.17/handbook-1720.html)
- SSA's preferred evidence includes a death certificate, funeral-director statement, or a death record marked proven or derived from electronic death registration; an obituary is only a lead and is not proof. — [SSA POMS GN 00304.005, *Preferred Evidence of Death*](https://secure.ssa.gov/poms.nsf/lnx/0200304005)
- SSA's inspector general found millions of records for people aged 112 or older without death information, but described almost all as *very likely* deceased based on additional facts such as very old birth dates, no recorded earnings, and no benefit payments. It separately matched those records against earnings and employment-verification systems to identify potential SSN misuse. — [SSA OIG, *Examining Federal Improper Payments and Errors in the Death Master File*](https://oig.ssa.gov/congressional-testimony/2015-03-17-newsroom-congressional-testimony-march16-hsgac/)
- The same SSA testimony says a person's absence from the Death Master File does not necessarily mean the person is alive, and that death information may require verification depending on its source before benefits are terminated. — [SSA OIG, *Examining Federal Improper Payments and Errors in the Death Master File*](https://oig.ssa.gov/congressional-testimony/2015-03-17-newsroom-congressional-testimony-march16-hsgac/)
- SSA also documents that living people can be erroneously included in the Death Master File and sends corrections to reduce the harm caused by erroneous death status. — [SSA POMS GN 03316.095, *Erroneous Death Included on the DMF*](https://secure.ssa.gov/apps10/poms.nsf/links/0203316095)

### Inferences

- An age threshold can route a record to review, but labels such as `deceased`, `fraudulent`, `identity_theft`, or `stale` require distinct evidence. Collapsing them into one age-derived outcome would mix four different hypotheses and create false positives. — [SSA death-evidence requirements](https://www.ssa.gov/OP_Home/handbook/handbook.17/handbook-1720.html); [SSA OIG treatment of potential misuse](https://oig.ssa.gov/congressional-testimony/2015-03-17-newsroom-congressional-testimony-march16-hsgac/)
- A very old age plus contradictory recent activity may justify investigation, but neither item alone establishes fraud. The SSA example uses cross-system evidence to identify *potential* misuse and then refers suspicious cases for investigation. — [SSA OIG](https://oig.ssa.gov/congressional-testimony/2015-03-17-newsroom-congressional-testimony-march16-hsgac/)

### Gaps

- No authoritative source found defines `stale customer record` from age alone. Staleness should be measured from record freshness, last verified interaction, or source-system update history rather than the customer's age.
- This synthetic dataset does not contain authoritative death registration, document verification, biometric checks, transaction history, or investigation outcomes; it therefore cannot substantiate death or fraud classifications.

## Corroboration needed before classifying a record as deceased, stale, or fraudulent

### Takeaway

The portfolio project should record age as a review reason and keep the final disposition unresolved unless independent evidence exists. Any verification workflow described in the project must be framed as a proposed production control, because the supplied synthetic data cannot perform it.

### Cited Findings

- UK government identity guidance says authoritative sources must protect the integrity of their information and keep it up to date; higher-confidence fraud checks use authoritative counter-fraud sources and, at the highest score, more than one independent authoritative source. — [GOV.UK, *How to prove and verify someone's identity*](https://www.gov.uk/government/publications/identity-proofing-and-verification-of-an-individual/how-to-prove-and-verify-someones-identity)
- The same guidance treats checking that an identity belongs to someone still alive as an authoritative-source check, separate from checking whether details were stolen or the identity is suspected to be synthetic. — [GOV.UK, *How to prove and verify someone's identity*](https://www.gov.uk/government/publications/identity-proofing-and-verification-of-an-individual/how-to-prove-and-verify-someones-identity)
- HMRC guidance says a single electronic data source is normally insufficient by itself for identity verification; satisfactory checking uses multiple sources across time, qualitative strength checks, or a suitably governed authoritative system, and the organisation should retain the evidence or assurance level used. — [HMRC, *Electronic verification*](https://www.gov.uk/hmrc-internal-manuals/economic-crime-supervision-handbook/ecsh33357)
- ONS high-age validation matches birth and death records on several attributes, including date and place of birth, full name, and aliases, illustrating corroboration across records rather than reliance on calculated age alone. — [ONS, *Accuracy of official high-age population estimates, in England and Wales: an evaluation*](https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/ageing/methodologies/accuracyofofficialhighagepopulationestimatesinenglandandwalesanevaluation)

### Inferences

- A defensible project rule is: `Age 0-18 inclusive and age 100+ trigger enhanced review. The age flag does not alter the DOB, exclude the record from entity resolution, or classify the customer as deceased, stale, or fraudulent.` — [GOV.UK identity guidance](https://www.gov.uk/government/publications/identity-proofing-and-verification-of-an-individual/how-to-prove-and-verify-someones-identity); [ONS high-age validation](https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/ageing/methodologies/accuracyofofficialhighagepopulationestimatesinenglandandwalesanevaluation)
- Suggested review outcomes are `unreviewed`, `age_verified`, `dob_corrected_from_authoritative_source`, `deceased_confirmed`, `potential_identity_misuse_referred`, and `unable_to_verify`. These names keep verified facts separate from suspicions and mirror the distinction official sources make between evidence, risk checking, and investigation. — [SSA evidence of death](https://secure.ssa.gov/poms.nsf/lnx/0200304005); [GOV.UK identity fraud checks](https://www.gov.uk/government/publications/identity-proofing-and-verification-of-an-individual/how-to-prove-and-verify-someones-identity)
- For a production system, `deceased_confirmed` would require an authoritative death record or accepted death evidence; `stale` would require an explicit inactivity or verification-age rule; and `potential_identity_misuse_referred` would require a contradiction such as activity associated with a confirmed deceased identity or evidence from an authoritative counter-fraud source. — [SSA preferred death evidence](https://secure.ssa.gov/poms.nsf/lnx/0200304005); [GOV.UK identity fraud checks](https://www.gov.uk/government/publications/identity-proofing-and-verification-of-an-individual/how-to-prove-and-verify-someones-identity)
- The separate review table should store a record key, calculated age, fixed calculation date, trigger reason, review status, evidence source or assurance level, and review timestamp. This makes the flag auditable without copying the full customer record and aligns with HMRC's expectation that verification evidence or assurance be retained. — [HMRC, *Electronic verification*](https://www.gov.uk/hmrc-internal-manuals/economic-crime-supervision-handbook/ecsh33357)
- Defensible portfolio wording: `Extreme age is used as a data-quality and verification-risk indicator. It is not treated as proof of death, fraud, or identity theft. Because the project dataset contains no authoritative life-status or fraud evidence, flagged records remain unresolved and are reported for enhanced review.` — [SSA evidence standards](https://www.ssa.gov/OP_Home/handbook/handbook.17/handbook-1720.html); [GOV.UK authoritative-source checks](https://www.gov.uk/government/publications/identity-proofing-and-verification-of-an-individual/how-to-prove-and-verify-someones-identity)

### Gaps

- The project owner still needs to decide whether the lower review band is ages 0-17 or 0-18 inclusive; legal adulthood and business eligibility rules vary by jurisdiction and use case.
- The project owner still needs to define what `stale` means operationally, including the relevant timestamp and inactivity period. No such definition can be inferred from DOB.
- The project has no authoritative verification source, so implementation in the current phase can only flag and route records; it cannot clear them or assign final fraud, death, or stale-record outcomes.
