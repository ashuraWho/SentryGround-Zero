#!/usr/bin/env python3
"""Simple test for climate models."""

import os
import sys
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

BASE_PATH = "/Users/ashura/Documents/GitHub/SentryGround-Zero/services/ground-segment/data"


class TemperaturePredictor:
    def __init__(self):
        self.sequence_length = 12
        self.model = None
        self.scaler = StandardScaler()
    
    def train(self, X, y):
        X = np.array(X, dtype=np.float64)
        y = np.array(y, dtype=np.float64)
        X_scaled = self.scaler.fit_transform(X.reshape(-1, 1)).reshape(X.shape)
        X_seq, y_seq = self._create_sequences(X_scaled)
        if len(X_seq) > 0:
            self.model = LinearRegression()
            self.model.fit(X_seq, y_seq)
    
    def _create_sequences(self, data):
        X, y = [], []
        for i in range(len(data) - self.sequence_length):
            X.append(data[i:i + self.sequence_length])
            y.append(data[i + self.sequence_length])
        return np.array(X), np.array(y)
    
    def predict_future(self, df, years=5):
        df = df.replace('NaN', np.nan).replace('', np.nan)
        annual = pd.to_numeric(df['Annual Anomaly'], errors='coerce').dropna().values
        
        if len(annual) < 10:
            return {'error': 'Insufficient data'}
        
        self.train(annual, annual)
        
        preds = []
        last_seq = annual[-self.sequence_length:].copy()
        for _ in range(years):
            if self.model:
                pred = self.model.predict(last_seq.reshape(1, -1))[0]
            else:
                pred = last_seq[-1]
            preds.append(float(pred))
            last_seq = np.append(last_seq[1:], pred)
        
        return {
            'years': list(range(int(df['Year'].max()) + 1, int(df['Year'].max()) + years + 1)),
            'predicted_anomalies': preds,
            'trend': 'increasing' if preds[-1] > preds[0] else 'decreasing'
        }


class SeaLevelPredictor:
    def __init__(self):
        self.model = None
    
    def train(self, X, y):
        self.model = LinearRegression()
        self.model.fit(X.reshape(-1, 1), y)
    
    def predict(self, X):
        return self.model.predict(X.reshape(-1, 1))
    
    def predict_future(self, df, years=30):
        df = df[df['Smoothed_GMSL_mm'] > 0]
        X = df['Year'].values
        y = df['Smoothed_GMSL_mm'].values
        
        self.train(X, y)
        
        current_year = int(df['Year'].max())
        future_years = np.arange(current_year + 1, current_year + years + 1)
        preds = self.predict(future_years)
        
        return {
            'years': future_years.tolist(),
            'predicted_mm': preds.tolist(),
            'rise_rate_mm_per_year': float((preds[-1] - preds[0]) / years)
        }


print("=== TESTING CLIMATE MODELS ===\n")

# Test Temperature
print("[1] Testing Temperature Predictor...")
temp_file = os.path.join(BASE_PATH, "global_temperatures/Global Temperatures.csv")
df_temp = pd.read_csv(temp_file)
df_temp.columns = df_temp.columns.str.strip()

temp_pred = TemperaturePredictor()
temp_result = temp_pred.predict_future(df_temp, years=5)
print(f"    Predictions: {temp_result.get('predicted_anomalies', [])}")
print(f"    Trend: {temp_result.get('trend')}")

# Test Sea Level  
print("\n[2] Testing Sea Level Predictor...")
sea_file = os.path.join(BASE_PATH, "sea_level/sea_level.csv")
df_sea = pd.read_csv(sea_file)

sea_pred = SeaLevelPredictor()
sea_result = sea_pred.predict_future(df_sea, years=10)
print(f"    Predictions: {sea_result.get('predicted_mm', [])[-1]:.1f}mm")

print("\n=== SUCCESS ===")
