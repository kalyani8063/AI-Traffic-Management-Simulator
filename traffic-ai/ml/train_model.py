import csv
import pickle
from pathlib import Path
from typing import Any

from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


BASE_DIR = Path(__file__).resolve().parents[1]
DATASET_PATH = BASE_DIR / 'data' / 'ai_traffic_dataset_5000.csv'
MODEL_DIR = BASE_DIR / 'models'
MODEL_PATH = MODEL_DIR / 'congestion_model.pkl'
SECTOR_NAMES = ['North', 'South', 'East', 'West', 'Central', 'NorthEast', 'NorthWest', 'SouthEast', 'SouthWest']
HEADINGS = ['Northbound', 'NorthEast', 'Eastbound', 'SouthEast', 'Southbound', 'SouthWest', 'Westbound', 'NorthWest']

FEATURE_COLUMNS = [
    'time_of_day',
    'hour',
    'day_of_week',
    'weather',
    'traffic_density',
    'num_vehicles',
    'avg_speed_kph',
    'num_accidents',
    'road_block',
    'signal_delay_sec',
    'reroute_count',
    'route_distance_km',
    'travel_time_min',
    'source_sector',
    'destination_sector',
    'route_heading',
    'route_span_km',
    'route_directness',
    'route_turn_density',
    'route_signal_pressure',
    'route_context',
]
TARGET_COLUMN = 'congestion_level'


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def build_route_features(row: dict[str, Any], row_index: int) -> dict[str, object]:
    route_distance_km = float(row['route_distance_km'])
    signal_delay_sec = int(row['signal_delay_sec'])
    reroute_count = int(row['reroute_count'])
    traffic_density = int(row['traffic_density'])
    travel_time_min = float(row['travel_time_min'])
    road_block = int(row['road_block'])
    num_accidents = int(row['num_accidents'])
    hour = int(row['hour'])

    detour_factor = clamp(
        1.04 + reroute_count * 0.08 + signal_delay_sec / 420.0 + road_block * 0.15,
        1.04,
        1.95,
    )
    route_span_km = round(max(0.35, route_distance_km / detour_factor), 2)
    route_directness = round(clamp(route_distance_km / max(route_span_km, 0.35), 1.0, 2.6), 2)
    route_turn_density = round(clamp((signal_delay_sec / max(route_distance_km, 0.5)) / 18.0, 0.2, 9.5), 2)
    route_signal_pressure = round(clamp(signal_delay_sec / max(travel_time_min, 2.0), 0.5, 35.0), 2)

    source_sector = SECTOR_NAMES[(row_index + hour + num_accidents) % len(SECTOR_NAMES)]
    destination_sector = SECTOR_NAMES[
        (row_index * 2 + traffic_density // 10 + reroute_count + road_block) % len(SECTOR_NAMES)
    ]
    route_heading = HEADINGS[(row_index + hour // 3 + reroute_count) % len(HEADINGS)]

    if route_distance_km < 4:
        route_context = 'InnerCore'
    elif route_directness > 1.45:
        route_context = 'DetourHeavy'
    elif traffic_density >= 70 or signal_delay_sec >= 100:
        route_context = 'CongestedCorridor'
    elif route_distance_km >= 18:
        route_context = 'CrossCity'
    else:
        route_context = 'Connector'

    return {
        'source_sector': source_sector,
        'destination_sector': destination_sector,
        'route_heading': route_heading,
        'route_span_km': route_span_km,
        'route_directness': route_directness,
        'route_turn_density': route_turn_density,
        'route_signal_pressure': route_signal_pressure,
        'route_context': route_context,
    }


def load_dataset(path: Path) -> list[dict[str, object]]:
    with path.open(newline='', encoding='utf-8') as file_obj:
        reader = csv.DictReader(file_obj)
        rows = list(reader)

    cleaned_rows: list[dict[str, object]] = []
    for index, row in enumerate(rows):
        cleaned_row: dict[str, object] = {
            'time_of_day': row['time_of_day'].strip(),
            'hour': int(row['hour']),
            'day_of_week': row['day_of_week'].strip(),
            'weather': row['weather'].strip(),
            'traffic_density': int(row['traffic_density']),
            'num_vehicles': int(row['num_vehicles']),
            'avg_speed_kph': float(row['avg_speed_kph']),
            'num_accidents': int(row['num_accidents']),
            'road_block': int(row['road_block']),
            'signal_delay_sec': int(row['signal_delay_sec']),
            'reroute_count': int(row['reroute_count']),
            'route_distance_km': float(row['route_distance_km']),
            'travel_time_min': float(row['travel_time_min']),
            TARGET_COLUMN: row[TARGET_COLUMN].strip(),
        }
        cleaned_row.update(build_route_features(cleaned_row, index))
        cleaned_rows.append(cleaned_row)
    return cleaned_rows


def build_pipeline() -> Pipeline:
    return Pipeline(
        steps=[
            ('vectorizer', DictVectorizer(sparse=False)),
            (
                'model',
                RandomForestClassifier(
                    n_estimators=220,
                    max_depth=14,
                    min_samples_leaf=2,
                    random_state=42,
                ),
            ),
        ]
    )


def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f'Dataset not found: {DATASET_PATH}')

    rows = load_dataset(DATASET_PATH)
    features = [{column: row[column] for column in FEATURE_COLUMNS} for row in rows]
    targets = [row[TARGET_COLUMN] for row in rows]

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        targets,
        test_size=0.2,
        random_state=42,
        stratify=targets,
    )

    pipeline = build_pipeline()
    pipeline.fit(x_train, y_train)

    predictions = pipeline.predict(x_test)
    accuracy = accuracy_score(y_test, predictions)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    with MODEL_PATH.open('wb') as file_obj:
        pickle.dump(
            {
                'pipeline': pipeline,
                'feature_columns': FEATURE_COLUMNS,
                'target_column': TARGET_COLUMN,
                'accuracy': accuracy,
                'labels': sorted(set(targets)),
            },
            file_obj,
        )

    print(f'Model saved to {MODEL_PATH}')
    print(f'Accuracy: {accuracy:.4f}')
    print(classification_report(y_test, predictions))


if __name__ == '__main__':
    main()
