import sys
import pandas as pd
from sklearn.model_selection import train_test_split
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
import torch
from torch.utils.data import Dataset as TorchDataset
from sklearn.metrics import accuracy_score

class Dataset(TorchDataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        item['labels'] = torch.tensor(self.labels[idx], dtype=torch.long)  # change this line
        return item

    def __len__(self):
        return len(self.labels)


def compute_metrics(pred):
    labels = pred.label_ids
    preds = pred.predictions.argmax(-1)
    acc = accuracy_score(labels, preds)
    return {"accuracy": acc}


def main(mode, question=None):
    data = pd.read_csv('cleaned_questions.csv')

    train_data, val_data = train_test_split(data, test_size=0.1, random_state=42)

    tokenizer = AutoTokenizer.from_pretrained('distilbert-base-uncased')
    model = AutoModelForSequenceClassification.from_pretrained('fine_tuned_model')

    val_encodings = tokenizer(val_data['content'].tolist(), truncation=True, padding=True)
    #print("Unique labels in validation data:", val_data['label'].unique())
    val_dataset = Dataset(val_encodings, val_data['label'].tolist())

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
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
    )

    if mode == "evaluate":
        eval_results = trainer.evaluate()
        print(f"Evaluation results: {eval_results}")

    elif mode == "predict":
        inputs = tokenizer(question, return_tensors="pt", truncation=True, padding=True)
        outputs = model(**inputs)
        predictions = outputs.logits.argmax(-1).item()
        print(f"Prediction: {'Relevant' if predictions == 1 else 'Not Relevant'}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <mode> [question]")
        sys.exit(1)

    mode_arg = sys.argv[1]
    question_arg = sys.argv[2] if len(sys.argv) > 2 else None

    if mode_arg not in ["evaluate", "predict"]:
        print("Mode should be either 'evaluate' or 'predict'")
        sys.exit(1)

    main(mode_arg, question_arg)
