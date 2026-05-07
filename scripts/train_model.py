from backend.app.ml.preprocessing import run_full_pipeline
from backend.app.ml.model import (
    train_model,
    evaluate_model,
    save_artifacts,
)

pipeline = run_full_pipeline(
    training_path="backend/data/floodsense_training_data.csv",
    elevation_path="backend/data/district_elevation_reference.csv",
    ndma_path="backend/data/ndma_flood_impact_2022.csv",
)

model, threshold = train_model(
    pipeline["X_train"],
    pipeline["y_train"],
    pipeline["X_val"],
    pipeline["y_val"],
    model_type="both",
)

metrics = evaluate_model(
    model,
    pipeline["X_test"],
    pipeline["y_test"],
    threshold,
    pipeline["feature_names"],
)

save_artifacts(
    model=model,
    scaler=pipeline["scaler"],
    feature_names=pipeline["feature_names"],
    threshold=threshold,
    metrics=metrics,
)

print("Training Complete")
print(metrics)