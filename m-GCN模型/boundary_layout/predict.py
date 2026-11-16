"""Generate normalized room rectangles from a saved model and target-free inputs."""
import argparse
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from boundary_layout.data import prepare_inputs
from boundary_layout.loss import generate
from boundary_layout.model import BoundaryLayoutModel
from room_layout_pilot.evaluate import boxes


def predict(checkpoint_path, source, device='cpu'):
    checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=True)
    if source.get('feature_order', checkpoint['feature_order']) != checkpoint['feature_order']:
        raise ValueError('Input feature order differs from the trained vocabulary')
    inputs = prepare_inputs(source, checkpoint['resolution'])
    inputs = {key: value.to(device) for key, value in inputs.items()}
    ids = source.get('node_ids', [f'slot_{i + 1}' for i in range(len(inputs['x']))])
    if len(ids) != len(inputs['x']) or len(set(ids)) != len(ids):
        raise ValueError('Node IDs must be unique and match the program length')
    model = BoundaryLayoutModel(**checkpoint['model_specification']).to(device)
    model.load_state_dict(checkpoint['state_dict'])
    prediction, selection = generate(model, inputs, checkpoint['candidates'])
    polygons = [[[float(x0), float(y0)], [float(x1), float(y0)],
                 [float(x1), float(y1)], [float(x0), float(y1)]]
                for x0, y0, x1, y1 in boxes(prediction.cpu().numpy())]
    return {'node_ids': ids, 'predicted_boxes': prediction.cpu().tolist(),
            'predicted_polygons': polygons, 'candidate_selection': selection,
            'coordinate_unit': 'provided_boundary_long_side_one_y_up',
            'coordinate_frame': source.get('coordinate_frame'),
            'input_contract': checkpoint['input_contract']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--input-json', type=Path, required=True)
    parser.add_argument('--output-json', type=Path, required=True)
    parser.add_argument('--device', default='cpu')
    args = parser.parse_args()
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    source = json.loads(args.input_json.read_text(encoding='utf-8'))
    result = predict(args.checkpoint, source, args.device)
    with args.output_json.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
