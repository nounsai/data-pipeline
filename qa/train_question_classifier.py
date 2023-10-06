import pandas as pd
from sklearn.model_selection import train_test_split
from transformers import TrainingArguments, Trainer, AutoTokenizer, AutoModelForSequenceClassification
import torch
from torch.utils.data import Dataset as TorchDataset

class Dataset(TorchDataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        item['labels'] = torch.tensor(self.labels[idx])
        return item

    def __len__(self):
        return len(self.labels)

# Load the CSV file into a pandas DataFrame
data = pd.read_csv('cleaned_questions.csv')

# Split the data into training and validation sets
train_data, val_data = train_test_split(data, test_size=0.1, random_state=42)

# Initialize the tokenizer
tokenizer = AutoTokenizer.from_pretrained('distilbert-base-uncased')

# Tokenize the content column for both training and validation sets
train_encodings = tokenizer(train_data['content'].tolist(), truncation=True, padding=True)
val_encodings = tokenizer(val_data['content'].tolist(), truncation=True, padding=True)

# Create PyTorch datasets
train_dataset = Dataset(train_encodings, train_data['label'].tolist())
val_dataset = Dataset(val_encodings, val_data['label'].tolist())

# Fine-tuning the model
model = AutoModelForSequenceClassification.from_pretrained('distilbert-base-uncased', num_labels=2)

training_args = TrainingArguments(
    output_dir='./results',
    num_train_epochs=3,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    logging_dir='./logs',
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
)

trainer.train()

model.save_pretrained('fine_tuned_model')
