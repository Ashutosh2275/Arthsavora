import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from datetime import datetime

def detect_anomalies(expense_data: list):
    """
    Identifies unusual transactions using the Isolation Forest algorithm.
    Returns a list of flagged expense IDs.
    """
    # Minimum 10 transactions needed to establish a 'normal' baseline
    if len(expense_data) < 10:
        return []

    # 1. Prepare Data
    df = pd.DataFrame(expense_data)
    
    # Feature Engineering: Use Amount and Day of the month
    df['day'] = pd.to_datetime(df['date']).dt.day
    features = df[['amount', 'day']]

    # 2. Initialize Model
    # contamination=0.05 means we expect ~5% of transactions might be anomalies
    model = IsolationForest(contamination=0.05, random_state=42)
    
    # 3. Fit and Predict
    # -1 indicates an anomaly, 1 indicates normal
    df['anomaly_score'] = model.fit_predict(features)

    # 4. Filter only anomalies
    anomalies = df[df['anomaly_score'] == -1]
    
    # Return the IDs of the flagged transactions
    return anomalies['_id'].astype(str).tolist()