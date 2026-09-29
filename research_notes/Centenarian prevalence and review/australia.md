# Centenarian prevalence in Australia

## How many centenarians are reported in recent Australian official statistics, and what share of the population are they?

### Takeaway
Australia had an estimated 6,181 people aged 100 or more in 2022, equivalent to 238 per million residents (0.0238%, or about 1 in 4,202). Centenarians are therefore real but very rare in the Australian population.

### Cited Findings
- The Australian Institute of Health and Welfare (AIHW), using Australian Bureau of Statistics population estimates, reports that Australia's centenarian population increased from 226 in 1973 to 6,181 in 2022. — [AIHW, *How long can Australians live?*, pp. 3 and 7](https://www.aihw.gov.au/getmedia/da6b92c7-60c2-4c66-aab7-63bb26fc71fd/aihw-phe-324.pdf.aspx?inline=true)
- AIHW reports 16 centenarians per million Australians in 1971 and 238 per million in 2022. The latter equals 0.0238% of the population, or approximately 1 centenarian per 4,202 residents. — [AIHW, *How long can Australians live?*, p. 7](https://www.aihw.gov.au/getmedia/da6b92c7-60c2-4c66-aab7-63bb26fc71fd/aihw-phe-324.pdf.aspx?inline=true)
- AIHW explicitly characterises the centenarian population as a "very small portion" of Australia's total population. — [AIHW report summary](https://www.aihw.gov.au/reports/life-expectancy-deaths/how-long-can-australians-live/summary)

### Inferences
- In a population-like sample of 4,810 people, the 2022 Australian rate of 238 per million would correspond to about 1.14 centenarians. The project has 1,279 records with implied age 100+, or 26.59% of its 4,810 valid-DOB records. That record-level share is about 1,117 times the Australian population rate.
- The project dataset is not necessarily intended to be population-representative, and records include duplicates. Even so, the gap is too large to regard the 100+ values as ordinary Australian demographic variation. It supports an enhanced-review flag and investigation of the dataset's date semantics, reference period, and synthetic generation process.
- The comparison supports treating age 100+ as an anomaly signal, not as proof that an individual record is fraudulent, stale, or belongs to a deceased customer.

### Gaps
- The 2022 official population estimate is grouped as age 100 and over; it does not reveal the exact age distribution above 100.
- A current official living-centenarian count for 2024 or 2025 was not found in an accessible narrative release during this search. The latest directly stated official figure located was for 2022.

## What demographic trends and sex differences provide context?

### Takeaway
The number of Australian centenarians has grown substantially, but survival to extreme ages remains uncommon and is strongly female-skewed in mortality data.

### Cited Findings
- Australia's centenarian population grew 27-fold, from 226 in 1973 to 6,181 in 2022, while the prevalence rose from 16 per million in 1971 to 238 per million in 2022. — [AIHW, *How long can Australians live?*, pp. 3 and 7](https://www.aihw.gov.au/getmedia/da6b92c7-60c2-4c66-aab7-63bb26fc71fd/aihw-phe-324.pdf.aspx?inline=true)
- Centenarian deaths rose from 83 in 1964 (1 in 1,214 deaths) to 2,247 in 2021 (1 in 72 deaths). Across 1964–2021, 94% of centenarian deaths occurred at ages 100–104. — [AIHW report summary](https://www.aihw.gov.au/reports/life-expectancy-deaths/how-long-can-australians-live/summary)
- In 2024, Australia registered 2,896 deaths at age 100+: 669 male and 2,227 female. Females represented about 76.9% of registered centenarian deaths that year. This is a death count, not a count of living centenarians. — [ABS, *Deaths, Australia, 2024*](https://www.abs.gov.au/statistics/people/population/deaths-australia/2024)
- For 1964–2021, AIHW identified 2,643 deaths at age 105 or older: 348 male and 2,295 female. Of the 84 deaths at age 110 or older, 12 were male and 72 female. — [AIHW, *How long can Australians live?*, p. 11](https://www.aihw.gov.au/getmedia/da6b92c7-60c2-4c66-aab7-63bb26fc71fd/aihw-phe-324.pdf.aspx?inline=true)
- Australian life expectancy at birth in 2022–2024 was 81.1 years for males and 85.1 years for females. — [ABS, *Life expectancy, 2022–2024*](https://www.abs.gov.au/statistics/people/population/life-expectancy/2022-2024)

### Inferences
- The sex imbalance in centenarian deaths is consistent with greater female longevity, but it cannot be used to derive the sex composition of the living centenarian population without a corresponding living-population table.
- Rising centenarian counts do not make a dataset share of 26.59% demographically plausible for a general Australian customer population.

### Gaps
- A directly stated recent sex breakdown for Australia's living centenarian population was not found in the accessible official narrative sources. The available sex breakdown above concerns registered deaths.

## What caveats apply to census and estimated-resident-population age data?

### Takeaway
Official centenarian estimates are useful benchmarks, but extreme-age measurement is intrinsically fragile. Official sources group everyone aged 100+ together, and small age errors can materially distort this rare population.

### Cited Findings
- AIHW states that Australian population data by single year of age are capped at 100, with everyone aged 100 and over combined. It also notes that the sparseness of very elderly populations causes loss of information even where civil registration is adequate. — [AIHW, *How long can Australians live?*, pp. 3 and 25](https://www.aihw.gov.au/getmedia/da6b92c7-60c2-4c66-aab7-63bb26fc71fd/aihw-phe-324.pdf.aspx?inline=true)
- AIHW warns that errors in age ascertainment have a high impact because deaths at very old ages are rare; a birth year recorded as 1875 instead of 1895 would add 20 years to an apparent lifespan. Australian death ages are not validated as rigorously as ages in specialist longevity databases. — [AIHW, *How long can Australians live?*, pp. 24–25](https://www.aihw.gov.au/getmedia/da6b92c7-60c2-4c66-aab7-63bb26fc71fd/aihw-phe-324.pdf.aspx?inline=true)
- In the 2021 Census, age was calculated from date of birth where available, otherwise from stated age; errors, inconsistencies, or non-response could lead to imputation. The age non-response rate was 4.4%. — [ABS, Age (AGEP), 2021 Census](https://www.abs.gov.au/census/guide-census-data/census-dictionary/2021/variables-topic/population/age-agep)
- The ABS says Census age, sex, marital status, usual residence, and place of work are imputed for non-responding dwellings, and that Census data are subject to respondent error, processing error, non-response, and undercount. — [ABS, 2021 Census quality declaration](https://www.abs.gov.au/census/guide-census-data/census-methodology/2021/quality-declaration)
- The 2021 Census count and Estimated Resident Population use different residence concepts. The comparison at national level extended only through age 100, and the ABS said it would correct older ages during recalculation of Estimated Resident Population. — [ABS, 2021 Census Statistical Independent Assurance Panel, population counts and age-sex distributions](https://www.abs.gov.au/census/about-census/census-statistical-independent-assurance-panel-report/34-population-counts-and-age-sex-distributions)
- The ABS describes Estimated Resident Population as the official population estimate; unlike the Census count, official population estimates incorporate adjustments including usual residents temporarily overseas on Census night. — [ABS, 2021 Census overcount and undercount methodology](https://www.abs.gov.au/methodologies/2021-census-overcount-and-undercount-methodology/2021)

### Inferences
- An extreme-age review process should seek corroborating evidence for the birth year rather than infer fraud, death, or staleness from age alone.
- For this project, retaining the source DOB, flagging the record, excluding an unverified extreme age from decisive matching evidence, and recording the reason for review would be defensible. A 100+ flag identifies heightened uncertainty; it does not determine the record's real-world status.
- Because the project's statistic counts records rather than unique people, deduplication may reduce the number of distinct flagged customers, but it cannot make the observed record-level share comparable to the Australian rate without a large reduction.

### Gaps
- Official aggregate data cannot validate any individual customer's age or establish whether a record is stale, fraudulent, or associated with a deceased person.
- The Australian benchmark does not establish that every customer dataset should match the national age distribution; customer base, product eligibility, historical reference date, and sampling design could legitimately change the expected rate.
