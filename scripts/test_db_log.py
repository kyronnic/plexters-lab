from plexter.db import log_script_run

run_id = log_script_run(
    script_name="test_db_log",
    status="success",
    message="Postgres logging from plexters-lab works.",
    metadata={"source": "manual_test"},
)

print(f"Inserted script_runs id={run_id}")