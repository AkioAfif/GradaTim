"""
train_model.py — GradaTim Mood Capacity Classifier Training Script

Tujuan:
    Melatih model ML untuk memprediksi kapasitas kerja pengguna (LOW/MEDIUM/HIGH)
    berdasarkan 5 jawaban kuesioner mood mereka.

Pendekatan yang digunakan:
    Random Forest Classifier — dipilih karena:
    1. Mudah dipahami & diinterpretasi (ada feature importance)
    2. Tidak perlu normalisasi data
    3. Performa baik untuk dataset kecil
    4. Bisa divisualisasikan untuk keperluan laporan/presentasi

Output:
    - mood_model.pkl : Model terlatih (siap dipakai oleh FastAPI backend)
    - evaluation_report.txt : Laporan akurasi & metrik evaluasi
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import json
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score
)
from sklearn.preprocessing import LabelEncoder

from generate_data import generate_mood_dataset


# ============================================================
# LANGKAH 1: SIAPKAN DATA
# ============================================================

print("=" * 60)
print("GRADATIM — MOOD CAPACITY MODEL TRAINING")
print("=" * 60)

print("\n[DATA] Langkah 1: Generate & load dataset...")
df = generate_mood_dataset(n=2000)  # 2000 sampel untuk training

FEATURE_COLUMNS = ['q1_focus', 'q2_calm', 'q3_motivated', 'q4_sleep', 'q5_readiness', 'total_score']
TARGET_COLUMN = 'capacity_level'

X = df[FEATURE_COLUMNS].values   # Shape: (2000, 6)
y = df[TARGET_COLUMN].values      # Shape: (2000,)

print(f"Total sampel  : {len(X)}")
print(f"Jumlah fitur  : {X.shape[1]}")
print(f"Distribusi label:")
unique, counts = np.unique(y, return_counts=True)
label_names = {0: "LOW", 1: "MEDIUM", 2: "HIGH"}
for val, cnt in zip(unique, counts):
    print(f"     {label_names[val]:8s} ({val}): {cnt} sampel ({cnt/len(y)*100:.1f}%)")


# ============================================================
# LANGKAH 2: SPLIT TRAIN / TEST
# ============================================================

print("\n[SPLIT]  Langkah 2: Split data train/test (80% / 20%)...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y            # Jaga proporsi label di train & test tetap sama
)
print(f"Training set : {len(X_train)} sampel")
print(f"Testing set  : {len(X_test)} sampel")


# ============================================================
# LANGKAH 3: TRAIN MODEL
# ============================================================

print("\n[TRAIN]  Langkah 3: Training Random Forest Classifier...")
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=8,
    min_samples_split=10,
    random_state=42,
    class_weight='balanced'  # Handle jika distribusi label tidak rata
)

model.fit(X_train, y_train)
print("Training selesai!")


# ============================================================
# LANGKAH 4: EVALUASI MODEL
# ============================================================

print("\n[EVAL] Langkah 4: Evaluasi performa model...")

y_pred = model.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)
print(f"\nAkurasi Test Set: {accuracy:.4f} ({accuracy*100:.2f}%)")

cv_scores = cross_val_score(model, X, y, cv=5, scoring='accuracy')
print(f"Cross-Validation (5-Fold):")
print(f"Rata-rata : {cv_scores.mean():.4f} ({cv_scores.mean()*100:.2f}%)")
print(f"Std Dev   : {cv_scores.std():.4f}")
print(f"Per Fold  : {[f'{s:.3f}' for s in cv_scores]}")

print(f"\nClassification Report:")
report = classification_report(
    y_test, y_pred,
    target_names=["LOW (0)", "MEDIUM (1)", "HIGH (2)"]
)
print(report)


# ============================================================
# LANGKAH 5: VISUALISASI 
# ============================================================

print("\n[VIS] Langkah 5: Membuat visualisasi...")

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle('GradaTim — Mood Capacity Model Evaluation', fontsize=14, fontweight='bold')

# --- Plot 1: Confusion Matrix ---
cm = confusion_matrix(y_test, y_pred)
sns.heatmap(
    cm, annot=True, fmt='d', cmap='Blues',
    xticklabels=["LOW", "MEDIUM", "HIGH"],
    yticklabels=["LOW", "MEDIUM", "HIGH"],
    ax=axes[0]
)
axes[0].set_title('Confusion Matrix')
axes[0].set_xlabel('Predicted Label')
axes[0].set_ylabel('True Label')

# --- Plot 2: Feature Importance ---
# Feature importance menunjukkan FITUR MANA yang paling berpengaruh
importances = model.feature_importances_
feature_names = ['Fokus (Q1)', 'Tenang (Q2)', 'Motivasi (Q3)', 'Tidur (Q4)', 'Siap (Q5)', 'Total Skor']

sorted_idx = np.argsort(importances)[::-1]
axes[1].bar(
    [feature_names[i] for i in sorted_idx],
    [importances[i] for i in sorted_idx],
    color=['#4A90D9', '#5BA85A', '#E8A838', '#D9534F', '#9B59B6', '#1ABC9C']
)
axes[1].set_title('Feature Importance\n(Fitur mana yang paling mempengaruhi prediksi?)')
axes[1].set_xlabel('Fitur')
axes[1].set_ylabel('Importance Score')
axes[1].tick_params(axis='x', rotation=20)

plt.tight_layout()
plt.savefig('model_evaluation.png', dpi=150, bbox_inches='tight')
print("Grafik disimpan ke 'model_evaluation.png'")


# ============================================================
# LANGKAH 6: SIMPAN MODEL
# ============================================================

print("\n[SAVE] Langkah 6: Menyimpan model terlatih...")

output_dir = Path(".")
model_path = output_dir / "mood_model.pkl"
joblib.dump(model, model_path)
print(f"Model disimpan ke '{model_path}'")

# Metadata model untuk dokumentasi
metadata = {
    "model_type": "RandomForestClassifier",
    "feature_columns": FEATURE_COLUMNS,
    "label_map": {"0": "LOW", "1": "MEDIUM", "2": "HIGH"},
    "accuracy": round(float(accuracy), 4),
    "cv_mean_accuracy": round(float(cv_scores.mean()), 4),
    "n_estimators": 100,
    "trained_on_samples": len(X_train),
    "version": "1.0.0"
}
with open("model_metadata.json", "w") as f:
    json.dump(metadata, f, indent=2)
print("Metadata disimpan ke 'model_metadata.json'")


# ============================================================
# LANGKAH 7: TEST CEPAT
# ============================================================

print("\n[TEST] Langkah 7: Sanity check prediksi...")

test_cases = [
    # q1, q2, q3, q4, q5 → expected
    ([5, 5, 5, 5, 5], "HIGH"),    # Semua sempurna
    ([1, 1, 1, 1, 1], "LOW"),     # Semua buruk
    ([3, 3, 3, 3, 3], "MEDIUM"), # Semua biasa
    ([5, 4, 5, 3, 4], "HIGH"),   # Mayoritas baik
    ([2, 1, 2, 1, 2], "LOW"),    # Mayoritas buruk
]

print(f"\n   {'Input (Q1-Q5)':<20} {'Prediksi':<12} {'Expected':<12} {'Match?'}")
print(f"   {'-'*60}")
for answers, expected in test_cases:
    total = sum(answers)
    features = np.array(answers + [total]).reshape(1, -1)
    pred_idx = model.predict(features)[0]
    pred_proba = model.predict_proba(features)[0]
    pred_label = label_names[pred_idx]
    match = "[OK]" if pred_label == expected else "⚠️"
    print(f"   {str(answers):<20} {pred_label:<12} {expected:<12} {match}")

print("\n" + "=" * 60)
print("TRAINING SELESAI!")
print("=" * 60)

