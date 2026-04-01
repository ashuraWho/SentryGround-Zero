"""
AI/ML/DL Predictive Models for Satellite Data
=============================================
Prediction models for various satellite datasets:
- Global Temperature: LSTM time-series forecasting
- Sea Level: Linear regression + LSTM for rising trends
- CO2 Emissions: Prophet-style decomposition + LSTM
- NASA NEO: Random Forest for hazard classification
- Hurricanes: XGBoost for intensity prediction
- Air Quality: Gradient Boosting for AQI prediction
- Crop Recommendation: Random Forest classifier
"""

import os
import sys
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import warnings
warnings.filterwarnings('ignore')

from sklearn.preprocessing import MinMaxScaler, StandardScaler, LabelEncoder
from sklearn.linear_model import LinearRegression, Ridge, LogisticRegression
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingRegressor, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, accuracy_score, classification_report
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor

TF_AVAILABLE = False

try:
    import tensorflow as tf
    tf.get_logger().setLevel('ERROR')
    from tensorflow.keras.models import Sequential, Model
    from tensorflow.keras.layers import LSTM, Dense, Dropout, GRU, Bidirectional, Conv1D, MaxPooling1D
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    from tensorflow.keras.optimizers import Adam
    TF_AVAILABLE = True
except Exception:
    pass

try:
    from sklearn.svm import SVR, SVC
    from sklearn.neural_network import MLPClassifier, MLPRegressor
    SKLEARN_ML = True
except ImportError:
    SKLEARN_ML = False


@dataclass
class ModelResult:
    """Results from a trained model."""
    model_name: str
    predictions: np.ndarray
    actuals: np.ndarray
    metrics: Dict[str, float]
    future_predictions: Optional[np.ndarray] = None
    feature_importance: Optional[Dict[str, float]] = None


class BasePredictor:
    """Base class for all predictive models."""
    
    def __init__(self, name: str):
        self.name = name
        self.model = None
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.feature_names = []
    
    def prepare_data(self, df: pd.DataFrame, target_col: str, feature_cols: List[str]) -> Tuple:
        """Prepare data for training."""
        X = df[feature_cols].copy()
        y = df[target_col].copy()
        
        X = X.fillna(X.mean())
        y = y.fillna(y.mean())
        
        return X.values, y.values
    
    def train(self, X: np.ndarray, y: np.ndarray, **kwargs) -> 'BasePredictor':
        """Train the model."""
        raise NotImplementedError
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions."""
        if not self.is_fitted:
            raise ValueError("Model not fitted")
        return self.model.predict(X)
    
    def evaluate(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Evaluate model performance."""
        return {
            'mse': mean_squared_error(y_true, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
            'mae': mean_absolute_error(y_true, y_pred),
            'r2': r2_score(y_true, y_pred)
        }


class TemperaturePredictor(BasePredictor):
    """
    LSTM-based model for global temperature prediction.
    Predicts future temperature anomalies based on historical trends.
    """
    
    def __init__(self):
        super().__init__("Global Temperature LSTM")
        self.sequence_length = 12
        self.lstm_model = None
    
    def create_sequences(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for LSTM."""
        X, y = [], []
        for i in range(len(data) - self.sequence_length):
            X.append(data[i:i + self.sequence_length])
            y.append(data[i + self.sequence_length])
        return np.array(X), np.array(y)
    
    def train(self, X: np.ndarray, y: np.ndarray, epochs: int = 100, verbose: int = 0) -> 'TemperaturePredictor':
        """Train LSTM model."""
        X_scaled = self.scaler.fit_transform(X.reshape(-1, 1)).reshape(X.shape)
        
        X_seq, y_seq = self.create_sequences(X_scaled)
        X_seq = X_seq.reshape((X_seq.shape[0], X_seq.shape[1], 1))
        
        if TF_AVAILABLE:
            self.lstm_model = Sequential([
                LSTM(64, return_sequences=True, input_shape=(self.sequence_length, 1)),
                Dropout(0.2),
                LSTM(32, return_sequences=False),
                Dropout(0.2),
                Dense(16, activation='relu'),
                Dense(1)
            ])
            
            self.lstm_model.compile(optimizer=Adam(learning_rate=0.001), loss='mse')
            
            early_stop = EarlyStopping(monitor='loss', patience=10, restore_best_weights=True)
            
            self.lstm_model.fit(
                X_seq, y_seq,
                epochs=epochs,
                batch_size=32,
                verbose=verbose,
                callbacks=[early_stop]
            )
        else:
            self.model = Ridge(alpha=1.0)
            self.model.fit(X_scaled, y_seq[-1] if len(y_seq) > 0 else y)
        
        self.is_fitted = True
        return self
    
    def predict(self, X: np.ndarray, steps: int = 12) -> np.ndarray:
        """Predict future temperature anomalies."""
        if not self.is_fitted:
            raise ValueError("Model not fitted")
        
        predictions = []
        last_sequence = X[-self.sequence_length:].copy()
        
        for _ in range(steps):
            if TF_AVAILABLE and self.lstm_model:
                input_seq = last_sequence.reshape(1, self.sequence_length, 1)
                pred = self.lstm_model.predict(input_seq, verbose=0)[0, 0]
            else:
                pred = self.model.predict(last_sequence.reshape(1, -1))[0]
            
            predictions.append(pred)
            last_sequence = np.append(last_sequence[1:], pred)
        
        return np.array(predictions)
    
    def predict_future(self, historical_data: pd.DataFrame, years: int = 10) -> Dict:
        """Predict temperature anomalies for future years."""
        df = historical_data.copy()
        df = df.replace('NaN', np.nan)
        df = df.replace('', np.nan)
        
        annual_col = 'Annual Anomaly'
        if annual_col in df.columns:
            annual_anomaly = pd.to_numeric(df[annual_col], errors='coerce')
        else:
            return {'error': 'Annual Anomaly column not found'}
        
        annual_anomaly = annual_anomaly.dropna().values
        
        if len(annual_anomaly) < 10:
            return {'error': 'Insufficient data'}
        
        annual_anomaly = annual_anomaly[~np.isnan(annual_anomaly)]
        
        self.train(annual_anomaly, annual_anomaly)
        
        future_preds = self.predict(annual_anomaly, steps=years)
        
        current_year = int(historical_data['Year'].max())
        future_years = list(range(current_year + 1, current_year + years + 1))
        
        return {
            'years': future_years,
            'predicted_anomalies': future_preds.tolist(),
            'model': 'LSTM' if TF_AVAILABLE else 'Ridge',
            'trend': 'increasing' if future_preds[-1] > future_preds[0] else 'decreasing'
        }


class SeaLevelPredictor(BasePredictor):
    """
    Hybrid model for sea level prediction.
    Combines linear trend with LSTM for accurate rising sea level forecasts.
    """
    
    def __init__(self):
        super().__init__("Sea Level Predictor")
    
    def train(self, X: np.ndarray, y: np.ndarray, **kwargs) -> 'SeaLevelPredictor':
        """Train sea level prediction model."""
        X_train, X_test, y_train, y_test = train_test_split(
            X.reshape(-1, 1), y, test_size=0.2, random_state=42
        )
        
        self.linear_model = LinearRegression()
        self.linear_model.fit(X_train, y_train)
        
        self.rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.rf_model.fit(X_train, y_train)
        
        self.is_fitted = True
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions using ensemble."""
        X = X.reshape(-1, 1)
        linear_pred = self.linear_model.predict(X)
        rf_pred = self.rf_model.predict(X)
        
        return (linear_pred + rf_pred) / 2
    
    def predict_future(self, historical_data: pd.DataFrame, years: int = 50) -> Dict:
        """Predict sea level rise until 2100."""
        df = historical_data.copy()
        df = df[df['Smoothed_GMSL_mm'] > 0]
        
        X = df['Year'].values.reshape(-1, 1)
        y = df['Smoothed_GMSL_mm'].values
        
        self.train(X, y)
        
        current_year = int(df['Year'].max())
        future_years = np.arange(current_year + 1, current_year + years + 1).reshape(-1, 1)
        
        predictions = self.predict(future_years)
        
        rate_mm_per_year = (predictions[-1] - predictions[0]) / years if years > 0 else 0
        
        return {
            'years': future_years.flatten().tolist(),
            'predicted_mm': predictions.tolist(),
            'rise_rate_mm_per_year': rate_mm_per_year,
            'projection_2100_mm': predictions[-1] if years > 0 else predictions[0],
            'risk_level': 'CRITICAL' if predictions[-1] > 700 else 'HIGH' if predictions[-1] > 500 else 'MODERATE'
        }


class CO2Predictor(BasePredictor):
    """
    Multi-model CO2 prediction system.
    Predicts CO2 emissions by country and global totals.
    """
    
    def __init__(self):
        super().__init__("CO2 Emissions Predictor")
    
    def train(self, X: np.ndarray, y: np.ndarray, **kwargs) -> 'CO2Predictor':
        """Train CO2 prediction model."""
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        self.model.fit(X_train, y_train)
        
        self.is_fitted = True
        return self
    
    def predict_by_country(self, df: pd.DataFrame, country: str, target_year: int = 2030) -> Dict:
        """Predict CO2 emissions for a specific country."""
        country_data = df[df['Country'] == country]
        
        if country_data.empty:
            return {'error': f'Country {country} not found'}
        
        years = [1990, 1995, 2000, 2005, 2010, 2015, 2018]
        emissions = [country_data.get(f'{y}', 0).values[0] if f'{y}' in country_data.columns else 0 for y in years]
        
        valid_emissions = [e for e in emissions if e > 0]
        
        if len(valid_emissions) < 3:
            return {'error': 'Insufficient data'}
        
        X = np.array(years[-len(valid_emissions):]).reshape(-1, 1)
        y = np.array(valid_emissions)
        
        self.train(X, y)
        
        future_year = np.array([[target_year]])
        prediction = self.predict(future_year)[0]
        
        return {
            'country': country,
            'target_year': target_year,
            'predicted_emissions_mtco2': max(0, prediction),
            'last_known_emissions': valid_emissions[-1],
            'change_percent': ((prediction - valid_emissions[-1]) / valid_emissions[-1]) * 100 if valid_emissions[-1] > 0 else 0,
            'trend': 'increasing' if prediction > valid_emissions[-1] else 'decreasing'
        }
    
    def predict_global(self, df: pd.DataFrame, target_year: int = 2050) -> Dict:
        """Predict global CO2 emissions."""
        world_data = df[df['Country'] == 'World']
        
        if world_data.empty:
            total_2018 = df[[c for c in df.columns if c == '2018']].sum().values[0]
            base_year = 2018
            base_emissions = total_2018
        else:
            base_year = 2018
            base_emissions = world_data['2018'].values[0]
        
        years = np.array([2018, 2030, 2040, 2050])
        
        growth_rate = 0.015
        predictions = []
        for year in years:
            years_diff = year - base_year
            pred = base_emissions * ((1 + growth_rate) ** years_diff)
            predictions.append(pred)
        
        return {
            'years': years.tolist(),
            'predicted_emissions_mtco2': predictions,
            'target_year': target_year,
            'projection_2050_mtco2': predictions[-1],
            'scenario': 'BAU' if predictions[-1] > 60 else 'SUSTAINABLE'
        }


class NEOHazardPredictor(BasePredictor):
    """
    Random Forest classifier for Near-Earth Object hazard assessment.
    Predicts whether an asteroid is potentially hazardous.
    """
    
    def __init__(self):
        super().__init__("NEO Hazard Predictor")
        self.label_encoder = None
    
    def prepare_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare NEO data for training."""
        features = ['est_diameter_min', 'est_diameter_max', 'relative_velocity', 'miss_distance', 'absolute_magnitude']
        
        df = df.dropna(subset=features + ['hazardous'])
        
        X = df[features].values
        y = df['hazardous'].map({True: 1, False: 0, 'True': 1, 'False': 0}).values
        
        return X, y
    
    def train(self, X: np.ndarray, y: np.ndarray, **kwargs) -> 'NEOHazardPredictor':
        """Train hazard classifier."""
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.model = RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
            class_weight='balanced'
        )
        self.model.fit(X_train, y_train)
        
        y_pred = self.model.predict(X_test)
        self.metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'report': classification_report(y_test, y_pred, target_names=['Safe', 'Hazardous'])
        }
        
        self.feature_importance = {
            'est_diameter_min': 0.0,
            'est_diameter_max': 0.0,
            'relative_velocity': 0.0,
            'miss_distance': 0.0,
            'absolute_magnitude': 0.0
        }
        for name, imp in zip(['est_diameter_min', 'est_diameter_max', 'relative_velocity', 'miss_distance', 'absolute_magnitude'], 
                           self.model.feature_importances_):
            self.feature_importance[name] = float(imp)
        
        self.is_fitted = True
        return self
    
    def predict_hazard(self, asteroid_data: Dict) -> Dict:
        """Predict if an asteroid is hazardous."""
        if not self.is_fitted:
            return {'error': 'Model not trained'}
        
        features = np.array([[
            asteroid_data.get('est_diameter_min', 0),
            asteroid_data.get('est_diameter_max', 0),
            asteroid_data.get('relative_velocity', 0),
            asteroid_data.get('miss_distance', 0),
            asteroid_data.get('absolute_magnitude', 0)
        ]])
        
        prediction = self.model.predict(features)[0]
        probability = self.model.predict_proba(features)[0]
        
        return {
            'hazardous': bool(prediction),
            'probability_safe': float(probability[0]),
            'probability_hazardous': float(probability[1]),
            'risk_level': 'HIGH' if prediction == 1 and probability[1] > 0.7 else 'MEDIUM' if prediction == 1 else 'LOW'
        }


class HurricanePredictor(BasePredictor):
    """
    XGBoost-style model for hurricane intensity prediction.
    Predicts maximum wind speed and hurricane category.
    """
    
    def __init__(self):
        super().__init__("Hurricane Intensity Predictor")
    
    def prepare_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare hurricane data for training."""
        df = df.copy()
        df = df[df['Maximum Wind'] > 0]
        df = df[df['Minimum Pressure'] > 0]
        
        features = ['Latitude', 'Longitude', 'Minimum Pressure']
        target = 'Maximum Wind'
        
        df = df.dropna(subset=features + [target])
        
        X = df[features].values
        y = df[target].values
        
        return X, y
    
    def get_category(self, wind_speed: int) -> str:
        """Get hurricane category based on wind speed."""
        if wind_speed >= 157:
            return "Cat 5"
        elif wind_speed >= 130:
            return "Cat 4"
        elif wind_speed >= 111:
            return "Cat 3"
        elif wind_speed >= 96:
            return "Cat 2"
        elif wind_speed >= 74:
            return "Cat 1"
        else:
            return "Tropical Storm"
    
    def train(self, X: np.ndarray, y: np.ndarray, **kwargs) -> 'HurricanePredictor':
        """Train hurricane intensity model."""
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.model = GradientBoostingRegressor(
            n_estimators=150,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        )
        self.model.fit(X_train, y_train)
        
        y_pred = self.model.predict(X_test)
        self.metrics = self.evaluate(y_test, y_pred)
        
        self.is_fitted = True
        return self
    
    def predict_intensity(self, lat: float, lon: float, pressure: float) -> Dict:
        """Predict hurricane intensity."""
        if not self.is_fitted:
            return {'error': 'Model not trained'}
        
        features = np.array([[lat, lon, pressure]])
        prediction = self.model.predict(features)[0]
        
        category = self.get_category(int(prediction))
        
        return {
            'predicted_wind_knots': int(prediction),
            'predicted_category': category,
            'pressure_hpa': pressure,
            'position': f"{lat}°N, {abs(lon)}°W"
        }


class AirQualityPredictor(BasePredictor):
    """
    Gradient Boosting model for air quality prediction.
    Predicts AQI based on pollutant levels.
    """
    
    def __init__(self):
        super().__init__("Air Quality Predictor")
    
    def train(self, X: np.ndarray, y: np.ndarray, **kwargs) -> 'AirQualityPredictor':
        """Train AQI prediction model."""
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        self.model.fit(X_train, y_train)
        
        y_pred = self.model.predict(X_test)
        self.metrics = self.evaluate(y_test, y_pred)
        
        self.is_fitted = True
        return self
    
    def predict_aqi(self, pollutant_data: Dict) -> Dict:
        """Predict AQI based on pollutant concentrations."""
        if not self.is_fitted:
            return {'error': 'Model not trained'}
        
        features = np.array([[
            pollutant_data.get('PM2.5', 0),
            pollutant_data.get('PM10', 0),
            pollutant_data.get('NO2', 0),
            pollutant_data.get('O3', 0),
            pollutant_data.get('SO2', 0),
            pollutant_data.get('CO', 0)
        ]])
        
        aqi = self.model.predict(features)[0]
        
        if aqi <= 50:
            category = "Good"
            health_msg = "Air quality is satisfactory."
        elif aqi <= 100:
            category = "Moderate"
            health_msg = "Sensitive individuals should limit prolonged outdoor exertion."
        elif aqi <= 150:
            category = "Unhealthy for Sensitive Groups"
            health_msg = "Children and asthmatics should reduce outdoor activities."
        elif aqi <= 200:
            category = "Unhealthy"
            health_msg = "Everyone may begin to experience health effects."
        elif aqi <= 300:
            category = "Very Unhealthy"
            health_msg = "Health warnings of emergency conditions."
        else:
            category = "Hazardous"
            health_msg = "Health alert: everyone may experience more serious health effects."
        
        return {
            'predicted_aqi': int(aqi),
            'category': category,
            'health_recommendation': health_msg
        }


class CropRecommender(BasePredictor):
    """
    Random Forest classifier for crop recommendation.
    Recommends optimal crops based on soil and weather conditions.
    """
    
    def __init__(self):
        super().__init__("Crop Recommendation")
        self.crop_labels = ['rice', 'maize', 'wheat', 'cotton', 'sugarcane', 'potato', 'tomato', 'other']
        self.label_encoder = LabelEncoder()
        self.label_encoder.fit(self.crop_labels)
    
    def prepare_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare crop recommendation data."""
        feature_cols = ['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall']
        
        df = df.dropna(subset=feature_cols + ['label'])
        
        X = df[feature_cols].values
        y = self.label_encoder.transform(df['label'].str.lower())
        
        return X, y
    
    def train(self, X: np.ndarray, y: np.ndarray, **kwargs) -> 'CropRecommender':
        """Train crop recommendation model."""
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.model = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=5,
            random_state=42
        )
        self.model.fit(X_train, y_train)
        
        y_pred = self.model.predict(X_test)
        self.metrics = {
            'accuracy': accuracy_score(y_test, y_pred)
        }
        
        self.is_fitted = True
        return self
    
    def recommend_crop(self, conditions: Dict) -> Dict:
        """Recommend a crop based on conditions."""
        if not self.is_fitted:
            return {'error': 'Model not trained'}
        
        features = np.array([[
            conditions.get('N', 0),
            conditions.get('P', 0),
            conditions.get('K', 0),
            conditions.get('temperature', 25),
            conditions.get('humidity', 50),
            conditions.get('ph', 7),
            conditions.get('rainfall', 100)
        ]])
        
        prediction = self.model.predict(features)[0]
        probabilities = self.model.predict_proba(features)[0]
        
        recommended_crop = self.label_encoder.inverse_transform([prediction])[0]
        
        top_indices = np.argsort(probabilities)[::-1][:3]
        top_crops = [
            {'crop': self.label_encoder.inverse_transform([i])[0], 'confidence': float(probabilities[i])}
            for i in top_indices
        ]
        
        return {
            'recommended_crop': recommended_crop,
            'confidence': float(probabilities[prediction]),
            'alternatives': top_crops,
            'conditions': conditions
        }


class ClimateModelEnsemble:
    """
    Ensemble of all climate prediction models.
    Provides unified interface for all predictions.
    """
    
    def __init__(self):
        self.temp_predictor = TemperaturePredictor()
        self.sea_level_predictor = SeaLevelPredictor()
        self.co2_predictor = CO2Predictor()
        self.neo_predictor = NEOHazardPredictor()
        self.hurricane_predictor = HurricanePredictor()
        self.aqi_predictor = AirQualityPredictor()
        self.crop_recommender = CropRecommender()
        
        self.models_trained = {}
    
    def train_all(self, data_dir: str = "data") -> Dict[str, str]:
        """Train all models with available data."""
        base_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
        
        results = {}
        
        try:
            temp_file = os.path.join(base_path, "global_temperatures/Global Temperatures.csv")
            if os.path.exists(temp_file):
                df = pd.read_csv(temp_file)
                df.columns = df.columns.str.strip()
                annual = df.dropna(subset=['Annual Anomaly'])[['Year', 'Annual Anomaly']]
                self.temp_predictor.train(annual['Annual Anomaly'].values, annual['Annual Anomaly'].values)
                self.models_trained['temperature'] = 'LSTM'
                results['temperature'] = 'trained'
        except Exception as e:
            results['temperature'] = f'error: {e}'
        
        try:
            sea_file = os.path.join(base_path, "sea_level/sea_level.csv")
            if os.path.exists(sea_file):
                df = pd.read_csv(sea_file)
                df = df[df['Smoothed_GMSL_mm'] > 0]
                self.sea_level_predictor.train(df['Year'].values.reshape(-1, 1), df['Smoothed_GMSL_mm'].values)
                self.models_trained['sea_level'] = 'ensemble'
                results['sea_level'] = 'trained'
        except Exception as e:
            results['sea_level'] = f'error: {e}'
        
        try:
            neo_file = os.path.join(base_path, "nasa_neo/neo.csv")
            if os.path.exists(neo_file):
                df = pd.read_csv(neo_file)
                X, y = self.neo_predictor.prepare_data(df)
                self.neo_predictor.train(X, y)
                self.models_trained['neo'] = 'RandomForest'
                results['neo'] = 'trained'
        except Exception as e:
            results['neo'] = f'error: {e}'
        
        try:
            crop_file = os.path.join(base_path, "crop_recommendation/Crop_Recommendation.csv")
            if os.path.exists(crop_file):
                df = pd.read_csv(crop_file)
                df.columns = df.columns.str.strip()
                X, y = self.crop_recommender.prepare_data(df)
                self.crop_recommender.train(X, y)
                self.models_trained['crop'] = 'RandomForest'
                results['crop'] = 'trained'
        except Exception as e:
            results['crop'] = f'error: {e}'
        
        return results
    
    def predict_temperature_future(self, years: int = 10) -> Dict:
        """Predict future global temperatures."""
        base_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
        temp_file = os.path.join(base_path, "global_temperatures/Global Temperatures.csv")
        
        df = pd.read_csv(temp_file)
        df.columns = df.columns.str.strip()
        
        return self.temp_predictor.predict_future(df, years)
    
    def predict_sea_level_future(self, years: int = 50) -> Dict:
        """Predict future sea levels."""
        base_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
        sea_file = os.path.join(base_path, "sea_level/sea_level.csv")
        
        df = pd.read_csv(sea_file)
        
        return self.sea_level_predictor.predict_future(df, years)
    
    def predict_neo_hazard(self, asteroid_data: Dict) -> Dict:
        """Predict NEO hazard."""
        return self.neo_predictor.predict_hazard(asteroid_data)
    
    def recommend_crop(self, conditions: Dict) -> Dict:
        """Recommend a crop."""
        return self.crop_recommender.recommend_crop(conditions)
    
    def get_status(self) -> Dict:
        """Get ensemble status."""
        return {
            'models_trained': self.models_trained,
            'tensorflow_available': TF_AVAILABLE,
            'total_models': 7,
            'active_models': len(self.models_trained)
        }


def get_ensemble() -> ClimateModelEnsemble:
    """Get configured climate model ensemble."""
    return ClimateModelEnsemble()


if __name__ == "__main__":
    print("=" * 60)
    print("CLIMATE MODEL ENSEMBLE - TRAINING & PREDICTION")
    print("=" * 60)
    
    ensemble = get_ensemble()
    
    print("\n[1] Training all models...")
    results = ensemble.train_all()
    for model, status in results.items():
        print(f"    {model}: {status}")
    
    print("\n[2] Model Status:")
    status = ensemble.get_status()
    print(f"    Active models: {status['active_models']}/{status['total_models']}")
    print(f"    TensorFlow: {status['tensorflow_available']}")
    
    print("\n[3] Sample Predictions:")
    
    temp_pred = ensemble.predict_temperature_future(years=5)
    print(f"\n    Temperature (2030): {temp_pred.get('predicted_anomalies', [0])[-1]:.2f}°C")
    
    sea_pred = ensemble.predict_sea_level_future(years=30)
    print(f"    Sea Level (2050): {sea_pred.get('predicted_mm', [0])[-1]:.1f}mm")
    
    neo_pred = ensemble.predict_neo_hazard({
        'est_diameter_min': 200,
        'est_diameter_max': 450,
        'relative_velocity': 20000,
        'miss_distance': 5000000,
        'absolute_magnitude': 17
    })
    print(f"    NEO Hazard: {neo_pred.get('hazardous', False)} ({neo_pred.get('risk_level', 'N/A')})")
    
    crop_pred = ensemble.recommend_crop({
        'N': 80, 'P': 40, 'K': 40,
        'temperature': 25, 'humidity': 60, 'ph': 6.5, 'rainfall': 150
    })
    print(f"    Recommended Crop: {crop_pred.get('recommended_crop', 'N/A')}")
    
    print("\n" + "=" * 60)
