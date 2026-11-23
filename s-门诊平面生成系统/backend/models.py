"""Adapt the repository's trained models without changing their training code."""

from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
import sys

from inputs import DesignError, pair_key


ROOT = Path(__file__).resolve().parents[2]
VOCABULARY = ROOT / "p-平面标注与数据处理/训练数据/单层医院_v1/vocabulary.json"
RELATION_WEIGHTS = ROOT / "e-实验评估/20261114_Windows显卡训练/batch_20261114_103153_574675/seed_7/weights.pt"
LAYOUT_WEIGHTS = ROOT / "e-实验评估/20261116_边界条件布局训练/run_20261116_134811_740695/fold_0_seed_7/weights.pt"


def read_vocabulary():
    return json.loads(VOCABULARY.read_text(encoding="utf-8"))


def feature_rows(rooms, feature_order):
    return [[float(column in {f"type:{room['type']}", "level:room", "function_known"})
             for column in feature_order] for room in rooms]


def infer(boundary, program, vocabulary):
    import torch
    from shapely.geometry import Polygon

    model_directory = str(ROOT / "m-GCN模型")
    if model_directory not in sys.path:
        sys.path.insert(0, model_directory)
    from relation_prediction.model import load_checkpoint
    from boundary_layout.predict import predict

    if any(not path.is_file() for path in (RELATION_WEIGHTS, LAYOUT_WEIGHTS)):
        raise DesignError("The repository's trained relation or layout checkpoint is missing")
    torch.set_num_threads(2)
    rooms = program["rooms"]
    ids = [room["id"] for room in rooms]
    order = vocabulary["node_feature_order"]
    rows = feature_rows(rooms, order)
    xmin, ymin, xmax, ymax = Polygon(boundary["local_ring"]).bounds
    span = max(xmax - xmin, ymax - ymin)
    ring = [[(point[0] - xmin) / span, (point[1] - ymin) / span] for point in boundary["local_ring"]]
    graph_source = {"node_ids": ids, "feature_order": order,
                    "inputs": {"node_features": rows, "boundary": [{"outer": ring}]}}
    pairs = list(combinations(range(len(ids)), 2))
    with torch.inference_mode():
        model, checkpoint = load_checkpoint(RELATION_WEIGHTS)
        if checkpoint["configuration"]["feature_order"] != order:
            raise DesignError("Relation model feature order differs from the repository vocabulary")
        scores = model.score_pairs(torch.tensor(rows, dtype=torch.float32), torch.tensor(pairs)).sigmoid()
        layout = predict(LAYOUT_WEIGHTS, graph_source, device="cpu")
    boxes = {room_id: [box[0] * span + xmin, box[1] * span + ymin, box[2] * span, box[3] * span]
             for room_id, box in zip(ids, layout["predicted_boxes"], strict=True)}
    return {"access_scores": [{"pair": list(pair_key(ids[left], ids[right])), "score": score}
                              for (left, right), score in zip(pairs, scores.tolist(), strict=True)],
            "layout_boxes_local_m": boxes, "candidate_selection": layout["candidate_selection"],
            "models": {name: {"checkpoint": path.relative_to(ROOT).as_posix(),
                              "sha256": sha256(path.read_bytes()).hexdigest()}
                       for name, path in (("access_gcn", RELATION_WEIGHTS), ("boundary_layout_gcn", LAYOUT_WEIGHTS))}}
