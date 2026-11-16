"""A real two-layer GCN and per-node box head, with NumPy backpropagation."""
import numpy as np


class GraphRegressor:
    def __init__(self, features, seed=7, hidden=(64, 32)):
        rng = np.random.default_rng(seed)
        widths = [features, *hidden, 4]
        self.params = {}
        for layer, (a, b) in enumerate(zip(widths, widths[1:])):
            self.params[f'w{layer}'] = rng.normal(0, np.sqrt(2 / a), (a, b))
            self.params[f'b{layer}'] = np.full(b, 0.02)

    def forward(self, x, adjacency, cache=False):
        p = self.params
        a0 = adjacency @ x
        z0 = a0 @ p['w0'] + p['b0']
        h0 = np.maximum(z0, 0)
        a1 = adjacency @ h0
        z1 = a1 @ p['w1'] + p['b1']
        h1 = np.maximum(z1, 0)
        z2 = h1 @ p['w2'] + p['b2']
        out = 1 / (1 + np.exp(-np.clip(z2, -40, 40)))
        if cache:
            return out, (a0, z0, a1, z1, h1)
        return out

    def loss_and_grad(self, x, adjacency, target, mask):
        out, (a0, z0, a1, z1, h1) = self.forward(x, adjacency, cache=True)
        residual = out - target
        weight = np.asarray(mask, dtype=float)[:, None]
        denominator = float(np.asarray(mask).sum() * target.shape[1])
        loss = float(np.sum(residual**2 * weight) / denominator)
        delta = 2 * residual * weight / denominator * out * (1-out)
        grads = dict(w2=h1.T @ delta, b2=delta.sum(axis=0))
        delta1 = (delta @ self.params['w2'].T) * (z1 > 0)
        grads.update(w1=a1.T @ delta1, b1=delta1.sum(axis=0))
        delta0 = (adjacency.T @ (delta1 @ self.params['w1'].T)) * (z0 > 0)
        grads.update(w0=a0.T @ delta0, b0=delta0.sum(axis=0))
        return loss, grads


def train(sample, seed, epochs=6000, graph=True, learning_rate=0.01):
    """Same-graph fitting diagnostic; no held-out validation or test set."""
    model = GraphRegressor(sample['x'].shape[1], seed=seed)
    n = len(sample['x'])
    # A random permutation prevents accidental dependence on annotation order.
    order = np.random.default_rng(seed + 1000).permutation(n)
    operator = sample['adjacency'] if graph else np.eye(n)
    operator = operator[order][:, order]
    x, y, mask = (sample[k][order] for k in ['x', 'y', 'supervised_mask'])
    first = {k: np.zeros_like(v) for k, v in model.params.items()}
    second = {k: np.zeros_like(v) for k, v in model.params.items()}
    best_loss, best_step = float('inf'), 0
    best_params, history = None, []
    for step in range(epochs + 1):
        loss, grads = model.loss_and_grad(x, operator, y, mask)
        if not np.isfinite(loss):
            raise FloatingPointError(f'Non-finite loss at step {step}')
        if loss < best_loss:
            best_loss, best_step = loss, step
            best_params = {k: v.copy() for k, v in model.params.items()}
        if step % 100 == 0 or step == epochs:
            history.append(dict(step=step, normalized_box_mse=loss))
        if step == epochs:
            break
        t = step + 1
        for key, param in model.params.items():
            grad = grads[key]
            first[key] = 0.9 * first[key] + 0.1 * grad
            second[key] = 0.999 * second[key] + 0.001 * grad**2
            moment = first[key] / (1 - 0.9**t)
            variance = second[key] / (1 - 0.999**t)
            param -= learning_rate * moment / (np.sqrt(variance) + 1e-8)
    model.params = best_params
    prediction = model.forward(sample['x'], sample['adjacency'] if graph else np.eye(n))
    return dict(model=model, prediction=prediction, history=history,
                seed=seed, best_step=best_step, best_train_mse=best_loss,
                parameters=sum(p.size for p in model.params.values()))
