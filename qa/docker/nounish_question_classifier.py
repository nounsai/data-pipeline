import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

class NounishQuestionClassifier:
    def __init__(self, model_path='fine_tuned_model'):
        self.tokenizer = AutoTokenizer.from_pretrained('distilbert-base-uncased')
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
    
    def predict(self, question):
        inputs = self.tokenizer(question, return_tensors="pt", truncation=True, padding=True)
        outputs = self.model(**inputs)
        predictions = outputs.logits.argmax(-1).item()
        return 'Relevant' if predictions == 1 else 'Not Relevant'