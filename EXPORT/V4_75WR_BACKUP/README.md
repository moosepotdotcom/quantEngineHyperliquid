
# 🛡️ V4 Model Backup (75% Win Rate)

**Saved on**: Jan 15, 2026
**Model**: XGBoost (Retrained Jan 2025)
**Validation**: 75% Win Rate on Jan 2-14, 2026 Out-of-Sample Data.

## 📂 Contents
- `weights/mtf_scalper_v4.pkl`: The trained XGBoost model.
- `logic.py`: Independent logic class ensuring strict V4 loading.
- `quant_engine.py`: Standalone execution script.

## 🚀 How to Run
```bash
cd EXPORT/V4_75WR_BACKUP
python3 quant_engine.py
```

## 📊 Logic Settings
- **Threshold**: 0.80 (High Confidence)
- **Features**: 231 MTF Features
- **Behavior**: Approx 1 trade/day (Sniper Mode)
