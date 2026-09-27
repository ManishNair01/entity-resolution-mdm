import duckdb

con = duckdb.connect("data/mdm.duckdb", read_only=True)

# 1. For people with 2+ records: how many have more than one distinct value per field?
#    count(DISTINCT ...) ignores NULLs, so a missing value doesn't count as a disagreement.
con.sql("""
SELECT count(*)                                AS people_with_duplicates,
       count(*) FILTER (WHERE n_postcode > 1)  AS postcode_disagrees,
       count(*) FILTER (WHERE n_ssn > 1)       AS ssn_disagrees,
       count(*) FILTER (WHERE n_dob > 1)       AS dob_disagrees
FROM (
    SELECT true_cluster_id,
           count(DISTINCT postcode)      AS n_postcode,
           count(DISTINCT soc_sec_id)    AS n_ssn,
           count(DISTINCT date_of_birth) AS n_dob
    FROM raw_customers
    GROUP BY true_cluster_id
    HAVING count(*) > 1
)
""").show()

# 2. Two example people per field, with all their records side by side.
for field in ["postcode", "soc_sec_id", "date_of_birth"]:
    print(f"\n=== {field} ===")
    con.sql(f"""
    WITH examples AS (
        SELECT true_cluster_id
        FROM raw_customers
        GROUP BY true_cluster_id
        HAVING count(DISTINCT {field}) > 1
        ORDER BY true_cluster_id
        LIMIT 2
    )
    SELECT rec_id, given_name, surname, {field}
    FROM raw_customers
    WHERE true_cluster_id IN (SELECT true_cluster_id FROM examples)
    ORDER BY true_cluster_id, rec_id
    """).show()

# 3. Given name and surname swapped between two records of the same person.
print("\n=== name swaps ===")
con.sql("""
SELECT count(DISTINCT a.true_cluster_id) AS people_with_swap
FROM raw_customers a
JOIN raw_customers b
  ON a.true_cluster_id = b.true_cluster_id AND a.rec_id < b.rec_id
WHERE a.given_name = b.surname AND a.surname = b.given_name
""").show()
con.sql("""
SELECT a.rec_id, a.given_name, a.surname, b.rec_id AS other_rec_id,
       b.given_name AS other_given, b.surname AS other_surname
FROM raw_customers a
JOIN raw_customers b
  ON a.true_cluster_id = b.true_cluster_id AND a.rec_id < b.rec_id
WHERE a.given_name = b.surname AND a.surname = b.given_name
LIMIT 3
""").show()

con.close()