import duckdb

con = duckdb.connect("data/mdm.duckdb", read_only=True)

con.sql("""
SELECT count(*) FILTER (WHERE given_name    IS NULL) AS no_given_name,
       count(*) FILTER (WHERE surname       IS NULL) AS no_surname,
       count(*) FILTER (WHERE date_of_birth IS NULL) AS no_dob,
       count(*) FILTER (WHERE state         IS NULL) AS no_state,
       count(*) FILTER (WHERE given_name IS NULL AND surname IS NULL) AS no_name_at_all
FROM raw_customers
""").show()

con.sql("""
SELECT rec_id, given_name, surname, date_of_birth, state
FROM raw_customers
WHERE given_name IS NULL OR surname IS NULL OR date_of_birth IS NULL
LIMIT 5
""").show()

con.close()