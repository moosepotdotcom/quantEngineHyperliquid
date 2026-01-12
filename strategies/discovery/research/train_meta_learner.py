
import pandas as pd
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.model_selection import train_test_split
import numpy as np

def find_gem_rules():
    print("🧠 META-LEARNING: Training the Precision Engine")
    print("="*70)
    
    # Load dataset
    try:
        df = pd.read_csv('trade_genome.csv')
        print(f"📊 Dataset Loaded: {len(df)} samples")
    except:
        print("❌ Dataset not found")
        return

    # Features and Target
    features = ['conf', 'disagreement', 'rsi', 'hurst', 'atr']
    target = 'TARGET_WIN'
    
    X = df[features]
    y = df[target]
    
    # Train Decision Tree
    # Max depth limited to keep rules readable and "Gem-like"
    clf = DecisionTreeClassifier(max_depth=3, min_samples_leaf=10, random_state=42)
    clf.fit(X, y)
    
    # Export rules
    tree_rules = export_text(clf, feature_names=features)
    print("\n🌳 DECISION TREE RULES:")
    print(tree_rules)
    
    # Precise Cluster Analysis
    # We will iterate through leaves to find purity
    n_nodes = clf.tree_.node_count
    children_left = clf.tree_.children_left
    children_right = clf.tree_.children_right
    feature = clf.tree_.feature
    threshold = clf.tree_.threshold
    values = clf.tree_.value
    
    print("\n💎 GEM CLUSTERS (100% Purity Search):")
    print("-" * 70)
    
    found_gem = False
    
    def normalize_value(val):
        # [Loss_count, Win_count]
        total = val[0][0] + val[0][1]
        win_rate = val[0][1] / total
        return total, win_rate

    # Traverse
    stack = [(0, "")] # node_id, path
    
    while len(stack) > 0:
        node_id, path = stack.pop()
        
        # If leaf
        if children_left[node_id] == children_right[node_id]:
            count, win_rate = normalize_value(values[node_id])
            
            if win_rate >= 0.98 and count >= 5: # Tolerance 98%
                print(f"✅ GEM FOUND! (WR: {win_rate:.1%} | Count: {int(count)})")
                print(f"   Rule: {path}")
                found_gem = True
            elif win_rate > 0.90 and count > 20: 
                print(f"✨ STRONG CANDIDATE (WR: {win_rate:.1%} | Count: {int(count)})")
                print(f"   Rule: {path}")
        else:
            fname = features[feature[node_id]]
            th = threshold[node_id]
            
            stack.append((children_right[node_id], path + f"{fname} > {th:.3f} AND "))
            stack.append((children_left[node_id], path + f"{fname} <= {th:.3f} AND "))

    if not found_gem:
        print("⚠️ No perfect 100% clusters found. Try relaxing constraints or extracting more data.")

if __name__ == "__main__":
    find_gem_rules()
