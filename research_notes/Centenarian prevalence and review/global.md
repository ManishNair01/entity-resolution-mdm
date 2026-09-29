# Global and national centenarian prevalence

## What is the global prevalence of centenarians?

### Takeaway
Centenarians are globally rare. The UN's 2024 medium projection implies roughly 722,000 people aged 100 or older among 8.162 billion people, about 8.8 per 100,000 people (0.0088%). A dataset share of 26.59% is therefore about 3,006 times this global population benchmark.

### Cited Findings
- The United Nations World Population Prospects 2024 series explicitly publishes “Population aged 100+, both sexes combined”; it treats 1950–2023 as estimates and 2024–2100 as projections. Thus, any 2024 figure must be labelled a projection rather than an observed count. — [UNdata, World Population Prospects 2024](https://data.un.org/Data.aspx?d=PopDiv&f=variableID%3A1110)
- A published extraction of the UN 2024 projection reports approximately 722,000 centenarians worldwide in 2024. — [Pew Research Center summary of UN projections](https://www.pewresearch.org/short-reads/2024/01/09/us-centenarian-population-is-projected-to-quadruple-over-the-next-30-years/)
- The UN Population Division reports a 2024 world population of 8,161,972,573. — [UN Population Division Data Portal](https://population.un.org/dataportal/data/indicators/49/locations/900/start/2024/end/2025/table)
- Dividing 722,000 by 8,161,972,573 gives approximately 8.85 centenarians per 100,000 people, or 0.00885%. This is a calculation from the two cited UN-derived quantities above. — [UN centenarian series](https://data.un.org/Data.aspx?d=PopDiv&f=variableID%3A1110); [UN total-population series](https://population.un.org/dataportal/data/indicators/49/locations/900/start/2024/end/2025/table)

### Inferences
- A 26.59% age-100-plus share equals 26,590 per 100,000. Relative to the global projection of about 8.85 per 100,000, the dataset rate is about 3,006 times higher.
- This comparison strongly supports treating the dataset's age distribution as anomalous unless the dataset was deliberately sampled from centenarians or from historical records. It does not identify the cause of any individual record's age.

### Gaps
- The UN interface exposed the indicator and total-population value directly, but the 722,000 centenarian value was easiest to verify through a Pew extraction that cites the UN projection. A reproducible download or authenticated UN API query would be preferable for an implementation audit.
- The dataset is not necessarily a representative population sample. Population prevalence is therefore a reasonableness benchmark, not a statistical expectation that can be applied without considering the dataset-generation process.

## What rates do official statistics report in countries with reliable age data?

### Takeaway
Official national figures cluster around roughly 20–60 centenarians per 100,000 in countries with older populations. Australia, the most relevant comparator for Febrl-style Australian data, recorded about 22 per 100,000 in its 2021 Census. Even Japan's much higher official rate was only 63.7 per 100,000.

### Cited Findings
- Australia's 2021 Census counted 5,547 people aged 100 or older, compared with an unrebased Estimated Resident Population of 8,258 for that age band. — [Australian Bureau of Statistics, 2021 Census quality review](https://www.abs.gov.au/census/about-census/census-statistical-independent-assurance-panel-report/34-population-counts-and-age-sex-distributions)
- Australia's 2021 Census counted 25,422,788 usual residents, excluding overseas visitors. — [Australian Bureau of Statistics, Population: Census 2021](https://www.abs.gov.au/statistics/people/population/population-census/2021)
- The Australian Census figures imply approximately 21.82 centenarians per 100,000 people (0.0218%). This is calculated as 5,547 divided by 25,422,788. — [ABS centenarian count](https://www.abs.gov.au/census/about-census/census-statistical-independent-assurance-panel-report/34-population-counts-and-age-sex-distributions); [ABS total population](https://www.abs.gov.au/statistics/people/population/population-census/2021)
- The UK Office for National Statistics estimated 16,140 centenarians in 2023, or 23.6 per 100,000 people (0.02% after rounding). — [UK Office for National Statistics, Estimates of the very old: 2002 to 2023](https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/ageing/bulletins/estimatesoftheveryoldincludingcentenarians/uk2002to2023)
- The 2020 U.S. Census counted 80,139 centenarians among 331 million people, equal to 2.42 per 10,000, or 24.2 per 100,000 (0.0242%). — [U.S. Census Bureau, Centenarians: 2020](https://www2.census.gov/library/publications/decennial/2020/c2020sr-02.pdf)
- Statistics Canada estimated 12,822 centenarians in 2021, equal to 34 per 100,000 people. — [Statistics Canada, Annual Demographic Estimates 2021](https://www150.statcan.gc.ca/n1/pub/91-215-x/91-215-x2021001-eng.htm)
- The U.S. Census Bureau's international comparison reports 2023 rates of 2.48 per 10,000 in Italy and 6.37 per 10,000 in Japan, equivalent to 24.8 and 63.7 per 100,000. — [U.S. Census Bureau, Centenarians: 2020](https://www2.census.gov/library/publications/decennial/2020/c2020sr-02.pdf)

### Inferences
- The dataset's 26,590 per 100,000 is about 1,219 times Australia's 2021 Census prevalence, 1,127 times the UK's 2023 rate, 1,099 times the U.S. 2020 rate, 782 times Canada's 2021 rate, and 417 times Japan's reported 2023 rate.
- Even allowing for census-versus-estimate differences, reference-year differences, population ageing, and the possibility of a customer base older than the general population, those factors cannot plausibly bridge a gap of three orders of magnitude.
- The evidence supports an “enhanced review” flag for ages 100 and over and a broader investigation into the synthetic dataset's DOB-generation or reference-date assumptions. It does not support labelling every flagged record as deceased, fraudulent, or invalid.

### Gaps
- No demographic comparator can establish the correct DOB for a particular record.
- Customer populations can differ from national populations. A business-specific expected age distribution would be needed to turn this benchmark into a calibrated anomaly threshold.

## How much uncertainty or age misreporting exists at extreme ages?

### Takeaway
Official agencies explicitly warn that extreme-age counts are sensitive to reporting, processing, and verification errors. The appropriate operational response is corroboration and review, rather than treating age 100+ as proof of fraud, death, or a bad DOB.

### Cited Findings
- The U.S. Census Bureau says centenarian data can be affected by question-design problems, assigning extreme ages to records with missing age, deliberate age exaggeration, processing, privacy protection, and the high sensitivity of a very small population to such issues. — [U.S. Census Bureau, Centenarians: 2020](https://www2.census.gov/library/publications/decennial/2020/c2020sr-02.pdf)
- The same Census report notes that an apparent 1980 count of 32,194 centenarians was revised to a preferred estimate of about 15,000 after examining original census forms; only 271 of a 585-record sample, 46%, were confirmed as centenarians from the original forms. — [U.S. Census Bureau, Centenarians: 2020](https://www2.census.gov/library/publications/decennial/2020/c2020sr-02.pdf)
- For the 2020 U.S. Census, a comparison with vital-statistics life expectancy suggested that the centenarian count may have been somewhat high. Restricting analysis to higher-quality age and DOB reporting yielded 43.5% growth from 2010, versus 50.2% for the full count, though the Bureau concluded that accelerated growth was still real. — [U.S. Census Bureau, Centenarians: 2020](https://www2.census.gov/library/publications/decennial/2020/c2020sr-02.pdf)
- UK ONS derives very-old-age estimates from death registrations using the Kannisto–Thatcher method, constrained to age-90-plus population totals. ONS warns that reported age at death may be inaccurate because the date of birth supplied by the death registrant is not checked against birth certificates. — [UK Office for National Statistics, data sources and quality](https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/ageing/bulletins/estimatesoftheveryoldincludingcentenarians/uk2002to2023)
- ONS removed a very small number of death records recorded as age 110 or older after finding evidence that those ages were highly unlikely. — [UK Office for National Statistics, data sources and quality](https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/ageing/bulletins/estimatesoftheveryoldincludingcentenarians/uk2002to2023)
- Australia's 2021 sources themselves differed materially at age 100+: the Census counted 5,547 people while the then-unrebased Estimated Resident Population was 8,258; ABS said it would correct older ages during population-estimate recalculation. — [Australian Bureau of Statistics, 2021 Census quality review](https://www.abs.gov.au/census/about-census/census-statistical-independent-assurance-panel-report/34-population-counts-and-age-sex-distributions)

### Inferences
- Extreme ages warrant stronger provenance checks because ordinary formatting and calendar-validity checks cannot detect a plausible but incorrect birth year.
- Suitable corroboration would compare DOB or age across independent source systems or trusted documentation and check whether the record has recent verified activity. The current sources support those checks as a general principle, but do not establish which evidence exists in this project.
- A review table should use a neutral reason such as `age_100_plus` and preserve the source DOB. Statuses such as deceased, fraud, or invalid should require separate evidence.

### Gaps
- These official sources quantify population prevalence and describe error mechanisms, but they do not provide a universal false-reporting rate that can be applied to this dataset.
- The research does not establish whether the dataset's unusually high ages were intentionally generated, reflect a historical reference year, or resulted from corruption. That requires inspection of the dataset documentation and generation process.
