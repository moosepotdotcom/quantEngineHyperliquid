import pandas as pd
import numpy as np
import logging
import os
import sys
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from research.feature_generator import AdvancedFeatureGenerator
from utils.logger import log_agent_action, log_optimization

logger = logging.getLogger(__name__)

class StrategyGenerator:
    """
    Analyzes feature importance and generates high-probability trading rules.
    """
    def __init__(self, data_path):
        self.data_path = data_path
        self.raw_df = pd.read_csv(data_path)
        
    def discover_rules(self):
        logger.info(f"🧠 Analyzing market rules for {self.data_path}...")
        
        # 1. Generate Features
        gen = AdvancedFeatureGenerator(self.raw_df)
        df = gen.generate_all()
        
        # 2. Train Model to find importance
        # Ensure only numeric columns are used
        df_numeric = df.select_dtypes(include=[np.number])
        
        cols_to_drop = ['target', 'open', 'high', 'low', 'close', 'volume']
        X = df_numeric.drop(columns=[c for c in cols_to_drop if c in df_numeric.columns], errors='ignore')
        y = df['target']
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
        
        model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
        model.fit(X_train, y_train)
        
        # 3. Get Top Features
        importances = model.feature_importances_
        feature_names = X.columns
        feature_importance = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)
        
        top_features = feature_importance[:5]
        logger.info(f"Top Features Discovered: {top_features}")
        
        # 4. Generate a synthetic "Rule-Based" Strategy logic
        rule_description = "Rule: Buy when "
        conditions = []
        for feat, imp in top_features:
            avg_val = X[feat].mean()
            std_val = X[feat].std()
            conditions.append(f"{feat} is within 1 std dev of {avg_val:.4f}")
            
        rule_description += " AND ".join(conditions)
        
        log_agent_action("AI Rule Discovery", f"Discovered new strategy logic: {rule_description}")
        
        return {
            'top_features': top_features,
            'rule_logic': rule_description,
            'model_accuracy': model.score(X_test, y_test)
        }

if __name__ == "__main__":
    # Use relative path for portability
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_dir, "datasets", "BTCUSD-1h-500wks-data.csv")
    if os.path.exists(data_path):
        sg = StrategyGenerator(data_path)
        results = sg.discover_rules()
        print("\n--- AI DISCOVERED RULES ---")
        print(f"Accuracy: {results['model_accuracy']:.2f}")
        print(f"Logic: {results['rule_logic']}")
