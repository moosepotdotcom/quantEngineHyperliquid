import json
import hashlib
import os
import sys

def calculate_file_hash(filepath):
    """Calculate SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def verify_golden_state():
    print("🛡️  VERIFYING GOLDEN STATE INTEGRITY")
    print("="*70)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "golden_config.json")
    
    if not os.path.exists(config_path):
        print("❌ CRITICAL: golden_config.json not found!")
        return False
        
    with open(config_path, 'r') as f:
        golden_config = json.load(f)
        
    print(f"📄 Loaded Config: {golden_config['description']}")
    print("-" * 70)
    
    # NEW: PRE-FLIGHT CHECKLIST
    print("📋 DEPLOYMENT CHECKLIST:")
    
    critical_files = [
        ("quant_engine.py", "Core Trading Logic"),
        ("requirements.txt", "Dependency List"),
        ("models/", "AI Models Directory"),
        ("utils/", "Utility Scripts Directory"),
        ("monitoring/", "Monitoring Scripts Directory")
    ]
    
    checklist_passed = True
    for fname, desc in critical_files:
        full_path = os.path.join(base_dir, fname)
        if os.path.exists(full_path):
            print(f"   [x] Found {desc} ({fname})")
        else:
            print(f"   [ ] MISSING {desc} ({fname})")
            checklist_passed = False
            
    if not checklist_passed:
        print("\n❌ Checklist Failed: Missing critical directories/files.")
        return False
        
    print("-" * 70)
    
    # 1. Verify File Integrity
    print("🔍 Deep Integrity Scan (SHA256):")
    total_files = len(golden_config['file_integrity'])
    passed_files = 0
    
    for rel_path, expected_hash in golden_config['file_integrity'].items():
        full_path = os.path.join(base_dir, rel_path)
        
        if not os.path.exists(full_path):
            print(f"   ❌ MISSING: {rel_path}")
            continue
            
        current_hash = calculate_file_hash(full_path)
        if current_hash == expected_hash:
            # print(f"   ✅ {rel_path}")  # Optional: Silence success to keep output clean
            passed_files += 1
        else:
            print(f"   ⚠️  HASH MISMATCH: {rel_path}")
            print(f"       Expected: {expected_hash[:10]}...")
            print(f"       Got:      {current_hash[:10]}...")
            
    print(f"   ✅ Verified {passed_files}/{total_files} files exactly match the Golden State.")
            
    if passed_files != total_files:
        print("🛑 INTEGRITY CONTROL FAILED: File content mismatch.")
        return False

    print("-" * 70)

    # 2. Verify Runtime Logic (Simple Check)
    print("🔍 Code Logic Signatures:")
    engine_path = os.path.join(base_dir, "quant_engine.py")
    with open(engine_path, 'r') as f:
        content = f.read()
        
    signatures = {
        "Circuit Breaker": "class CircuitBreaker",
        "Mandalorian Shield": "MANDALORIAN SHIELD",
        "Adaptive Volatility": "ADAPTIVE SHIELD",
        "AI Smart Filter": "AI SMART FILTER",
        "Trio Ensemble": "get_ensemble_proba"
    }
    
    logic_passed = True
    for name, sig in signatures.items():
        if sig in content:
            print(f"   [x] {name} Logic verified")
        else:
            print(f"   [ ] MISSING {name} Logic Code!")
            logic_passed = False

    print("="*70)
    if logic_passed and passed_files == total_files:
        print("🎉 SYSTEM INTEGRITY: 100% (READY TO DEPLOY)")
        return True
    else:
        print("🛑 INTEGRITY CONTROL FAILED: DO NOT DEPLOY")
        return False

if __name__ == "__main__":
    success = verify_golden_state()
    sys.exit(0 if success else 1)
