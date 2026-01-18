import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
import warnings

warnings.filterwarnings("ignore")

def predict_monthly_spend(expense_data: list):
    """
    Predicts next month's total spending using ARIMA.
    Input: List of expense dicts
    """
    if len(expense_data) < 5:
        return {"prediction": 0, "status": "Insufficient Data"}

    # 1. Convert to DataFrame
    df = pd.DataFrame(expense_data)
    df['date'] = pd.to_datetime(df['date'])
    
    # 2. Resample to Daily Sums
    daily_series = df.set_index('date')['amount'].resample('D').sum().fillna(0)

    try:
        # 3. Fit ARIMA Model (Order 1,1,1 is a good baseline for spending)
        model = ARIMA(daily_series, order=(1, 1, 1))
        model_fit = model.fit()
        
        # 4. Forecast next 30 days
        forecast = model_fit.forecast(steps=30)
        predicted_total = float(forecast.sum())
        
        return {
            "prediction": round(predicted_total, 2),
            "status": "Success",
            "confidence": "Medium"
        }
    except Exception as e:
        # Fallback: Simple Moving Average
        avg_spend = daily_series.mean()
        return {
            "prediction": round(avg_spend * 30, 2),
            "status": "Fallback (Simple Average)",
            "confidence": "Low"
        }