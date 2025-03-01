import pandas as pd
import torch
from transformers import BertTokenizerFast, AutoModel
from joblib import load
import numpy as np
import tensorflow as tf
import platform
import os

BASE_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BASE_DIR, 'final_model.h5')
LABEL_ENCODER_PATH = os.path.join(BASE_DIR, 'label_encoder_80_keras.joblib')


class BertModel():

    def __init__(self) -> None:
        if 'Darwin' in platform.system():
            self.device = torch.device('mps' if torch.backends.mps.is_built() else 'cpu')
        else:
            self.device = torch.device('cuda' if torch.backends.mps.is_built() else 'cpu')
        self.tokenizer = BertTokenizerFast.from_pretrained('ckiplab/bert-base-chinese')
        self.bertModel = AutoModel.from_pretrained('ckiplab/bert-base-chinese').to(self.device)
        self.model = tf.keras.models.load_model(MODEL_PATH)
        self.labelEncoder = load(LABEL_ENCODER_PATH)

    def extractEmbeddings(self, text):
        inputs = self.tokenizer(text, padding=True, truncation=True, return_tensors="pt").to(self.device)
        with torch.no_grad():
            outputs = self.bertModel(**inputs)
        return outputs.last_hidden_state[:, 0, :].cpu().numpy().squeeze()

    def addItemTag(self, df):
        embeddings = np.array([self.extractEmbeddings(item) for item in df['item_name']])
        predictions = self.model.predict(embeddings)
        predictedLabels = np.argmax(predictions, axis=1)
        decodedLabels = self.labelEncoder.inverse_transform(predictedLabels)
        df['item_tag'] = decodedLabels
        return df
