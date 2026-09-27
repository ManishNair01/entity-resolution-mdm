SELECT count(*) AS invalid_records,
       count(DISTINCT state) AS invalid_codes
FROM raw_customers
WHERE state IS NOT NULL
  AND state NOT IN ('nsw','vic','qld','wa','sa','tas','act','nt')