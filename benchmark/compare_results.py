#
# This is a helper file to compare the results of two benchmark runs.
# It generates a report.txt which can be sent as an email
#

import argparse
import json
import logging
import os
from datetime import datetime
from pathlib import Path


# Parse command-line arguments
def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--new", required=True, type=str, default="results.json", help="The name of the new results file. Should be located in the 'test_runs' directory.")
    parser.add_argument("--old", required=True, type=str, default="previous_results.json", help="The name of the previous results file. Should be located in the 'test_runs' directory.")
    parser.add_argument("--out", required=False, type=str, default="report.json", help="The name of the output file. Will be written to the 'test_runs' directory.")
    return parser.parse_args()


def compare_results():
    args = parse_arguments()

    cwd = Path.cwd()

    new_file = f'{cwd}/benchmark/test_runs/{args.new}'
    old_file = f'{cwd}/benchmark/test_runs/{args.old}'

    # Check if both files exist
    if not os.path.isfile(new_file):
        logging.warning(f"File '{new_file}' does not exist.")
        exit(1)
    if not os.path.isfile(old_file):
        logging.warning(f"File '{old_file}' does not exist.")
        exit(1)

    report = {}
    # Write results into json file
    with open(new_file, "r") as f_new, open(old_file, "r") as f_old, open(f"{cwd}/benchmark/test_runs/{args.out}", "w+") as f_report:
        new = json.loads(f_new.read())
        old = json.loads(f_old.read())

        report["date_previous_results"] = datetime.fromtimestamp(os.path.getmtime(old_file)).strftime('%Y-%m-%d %H:%M:%S')
        report["date_current_results"] = datetime.fromtimestamp(os.path.getmtime(new_file)).strftime('%Y-%m-%d %H:%M:%S')

        # Generate a report for each benchmarked method and model combination existing in both results
        for method in new.keys():

            # Check if method exists in both results
            if method not in old.keys():
                logging.warning(f'Method {method} was not found in old results. Skipping this method...')
                continue

            report[method] = {}
            for model in new[method].keys():

                # Check if model exists in both results
                if model not in old[method].keys():
                    logging.warning(f'Model {model} was not found in old results. Skipping this model...')
                    continue

                # Get the summary for both benchmark runs
                sum_old = old[method][model]["summary"]
                sum_new = new[method][model]["summary"]

                # Write the differences to the report
                report[method][model] = {
                    "correct_tool_difference": f'{(sum_new["correct_tool_usage"] / sum_new["questions"] - sum_old["correct_tool_usage"] / sum_old["questions"]) * 100:.2f}%',
                    "perfect_tool_difference": f'{(sum_new["perfect_tool_usage"] / sum_new["questions"] - sum_old["perfect_tool_usage"] / sum_old["questions"]) * 100:.2f}%',
                    "total_time_difference": f'{sum_new["total_time"] - sum_old["total_time"]:.2f}s',
                    "agent_time_difference": {
                        agent: f'{sum_new["agent_time"][agent] - sum_old["agent_time"][agent]:.2f}s' for agent in sum_new["agent_time"].keys() if agent in sum_old["agent_time"]
                    },
                    "total_token_usage_difference": f'{sum_new["total_token_usage"] - sum_old["total_token_usage"]} tokens',
                }

                # Check if the judge llm was used
                if "average_score" in sum_new.keys() and "average_score" in sum_old.keys() and sum_old["average_score"] != 0:
                    report[method][model]["average_score_difference"] = f'{sum_new["average_score"] / sum_old["average_score"] * 100}%'

                # Save the summaries to the report
                report[method][model]["summary_new"] = sum_new
                report[method][model]["summary_old"] = sum_old

        # Write the report to a file
        f_report.write(json.dumps(report, indent=4))


if __name__ == "__main__":
    compare_results()
