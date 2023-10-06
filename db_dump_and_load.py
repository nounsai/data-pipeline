import os
import sys
import subprocess
import argparse
from dotenv import load_dotenv

load_dotenv()

def dump_and_load_table(src, target, table_name):
    src_conn = os.getenv(f"{src}_DB_CONN")
    target_conn = os.getenv(f"{target}_DB_CONN")
    print(f"Dumping {table_name} from src_conn: {src_conn}")
    # exit from program
    cmd = f"pg_dump --data-only -U postgres -f {table_name}.sql -t {table_name} {src_conn}"
    subprocess.run(cmd, shell=True)

    print(f"Loading {table_name} to target_conn: {target_conn}")
    cmd = f"psql {target_conn} < {table_name}.sql"
    subprocess.run(cmd, shell=True)

    os.remove(f"{table_name}.sql")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("table_name", type=str, help="Name of the table to dump and load")
    parser.add_argument("--src", type=str, default="PROD", help="Source environment")
    parser.add_argument("--target", type=str, default="LOCAL", help="Target environment")
    args = parser.parse_args()


    dump_and_load_table(args.src.upper(), args.target.upper(), args.table_name)
