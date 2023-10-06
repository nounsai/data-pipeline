import subprocess
import sys
import traceback
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

scripts = [
    '1_retrieve_questions.py',
    '2_classify_questions.py',
    '3_answer_questions.py',
    '4_create_embeddings.py',
    '5_hide_downvoted_questions.py',
]


def main():
    for script in scripts:
        print(f"Running {script}...")
        result = subprocess.run(
            ['python', script], capture_output=True, text=True)

        if result.returncode != 0:
            print(
                f"Error executing {script}: {result.stderr}", file=sys.stderr)
            sys.exit(result.returncode)

        print(f"Completed {script}.")

    print("All scripts executed successfully.")


if __name__ == '__main__':
    try: 
        main()
    
