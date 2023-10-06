import csv

def read_and_clean_csv(input_file_name, output_file_name):
    count_1 = 0
    count_0 = 0
    total_rows = 0
    unlabeled_rows = 0
    cleaned_data = []

    with open(input_file_name, 'r') as csvfile:
        csvreader = csv.reader(csvfile)
        headers = next(csvreader)  # Skip the header row
        cleaned_data.append(headers)

        for row in csvreader:
            total_rows += 1
            label = row[2]
            if label == '1':
                count_1 += 1
                cleaned_data.append(row[:-1])
            elif label == '0':
                count_0 += 1
                cleaned_data.append(row[:-1])
            else:
                unlabeled_rows += 1

    with open(output_file_name, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerows(cleaned_data)

    return count_1, count_0, total_rows, unlabeled_rows

count_relevant, count_irrelevant, total_rows, unlabeled_rows = read_and_clean_csv('random_questions_filled.csv', 'cleaned_questions.csv')

print(f"Relevant (1s): {count_relevant}")
print(f"Irrelevant (0s): {count_irrelevant}")
print(f"Total rows: {total_rows}")
print(f"Unlabeled rows: {unlabeled_rows}")
