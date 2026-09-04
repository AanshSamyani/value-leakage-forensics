"""Functions that run INSIDE vLLM worker processes via `LLM.apply_model(fn)`.

vLLM's decoder layers return `(hidden_states, residual)`; the next layer's fused add+RMSNorm sums them,
so the residual stream after layer i is `hidden_states + residual`. Adding `alpha * v` to hidden_states
therefore adds it to the residual stream (steering); reading `hidden_states + residual` gives the stream
(capture). Hooks are registered AFTER engine init, so the engine must run with enforce_eager=True and
compilation disabled (the sampler does this) — otherwise CUDA graphs / torch.compile bypass them.

State lives in this module (one copy per worker process). All functions take `model` first so they can
be passed to apply_model directly or through functools.partial.
"""

from __future__ import annotations

import numpy as np
import torch

STATE: dict = {"handles": [], "steer": None, "capture": None, "layers_name": None}


def find_decoder_layers(model):
    """The ModuleList of decoder layers (largest list whose children are *DecoderLayer)."""
    import torch.nn as nn
    best = None
    for name, mod in model.named_modules():
        if isinstance(mod, nn.ModuleList) and len(mod) > 0 and "DecoderLayer" in type(mod[0]).__name__:
            if best is None or len(mod) > len(best[1]):
                best = (name, mod)
    if best is None:
        raise RuntimeError(f"no DecoderLayer ModuleList found in {type(model).__name__}")
    STATE["layers_name"] = best[0]
    return best


def _stream(output):
    if isinstance(output, tuple):
        h, r = output[0], output[1] if len(output) > 1 else None
        return h + r if r is not None else h
    return output


def remove_all(model=None):
    for h in STATE["handles"]:
        h.remove()
    STATE["handles"] = []
    STATE["steer"] = None
    STATE["capture"] = None
    STATE.pop("_steer_logged", None)
    return "ok"


def describe(model):
    name, mods = find_decoder_layers(model)
    p = next(mods[0].parameters())
    return {"model_class": type(model).__name__, "layers_path": name, "n_layers": len(mods),
            "dtype": str(p.dtype), "device": str(p.device), "hidden": int(p.shape[-1]) if p.dim() > 1 else None,
            "steer": None if STATE["steer"] is None else {k: v for k, v in STATE["steer"].items() if k != "vecs"},
            "capture": None if STATE["capture"] is None else {"mode": STATE["capture"]["mode"], "layers": STATE["capture"]["layers"]}}


# --------------------------------------------------------------------------- steering

def install_steering(model, vec_path: str, layers: list[int], alpha: float):
    """Add alpha * v_layer to the residual stream at every position of each listed layer."""
    remove_all(model)
    blob = torch.load(vec_path, map_location="cpu", weights_only=False)
    name, mods = find_decoder_layers(model)
    STATE["steer"] = {"alpha": float(alpha), "layers": [int(l) for l in layers], "vec_path": vec_path, "vecs": {}}
    for li in STATE["steer"]["layers"]:
        v = blob["vectors"][li]
        p = next(mods[li].parameters())
        v = v.to(device=p.device, dtype=p.dtype)
        STATE["steer"]["vecs"][li] = v

        def hook(module, args, output, v=v, li=li):
            a = STATE["steer"]["alpha"] if STATE["steer"] else 0.0
            if a == 0.0:
                return output
            # Log the layer-output shape once. Steering assumes a vLLM decoder layer returns
            # (hidden_states, residual) and that adding to hidden_states adds to the stream; if a vLLM
            # release changes that, steering would silently do the wrong thing rather than fail.
            if not STATE.get("_steer_logged"):
                STATE["_steer_logged"] = True
                kind = (f"tuple(len={len(output)}, shapes="
                        f"{[tuple(o.shape) for o in output if hasattr(o, 'shape')]})"
                        if isinstance(output, tuple) else f"tensor{tuple(output.shape)}")
                print(f"[steer] layer {li} output is {kind}; adding {a:+.4f} * v "
                      f"(||v||={float(v.float().norm()):.3f}) to hidden_states", flush=True)
            if isinstance(output, tuple):
                return (output[0] + a * v, *output[1:])
            return output + a * v

        STATE["handles"].append(mods[li].register_forward_hook(hook))
    return describe(model)


def set_alpha(model, alpha: float):
    if STATE["steer"] is None:
        raise RuntimeError("steering not installed")
    STATE["steer"]["alpha"] = float(alpha)
    return STATE["steer"]["alpha"]


# --------------------------------------------------------------------------- capture

def install_capture(model, layers: list[int], mode: str = "last", vec_path: str | None = None):
    """mode='last': keep the residual stream at the LAST position of each forward call (per layer).
    mode='proj': append per-position projections of the stream onto the vectors in vec_path (per layer).
    Use with max_num_seqs=1, prefix caching off, one prompt per generate() call, then flush_capture()."""
    remove_all(model)
    name, mods = find_decoder_layers(model)
    layers = [int(l) for l in layers]
    cap = {"mode": mode, "layers": layers, "buf": {li: [] for li in layers}, "V": {}}
    if mode == "proj":
        blob = torch.load(vec_path, map_location="cpu", weights_only=False)
        for li in layers:
            v = blob["vectors"][li].float()
            v = v / v.norm()
            cap["V"][li] = v.to(next(mods[li].parameters()).device)
    STATE["capture"] = cap
    for li in layers:
        def hook(module, args, output, li=li):
            s = _stream(output)
            if cap["mode"] == "last":
                cap["buf"][li] = [s[-1].detach().float().cpu().numpy()]
            else:
                cap["buf"][li].append((s.detach().float() @ cap["V"][li]).cpu().numpy())
        STATE["handles"].append(mods[li].register_forward_hook(hook))
    return describe(model)


def flush_capture(model):
    """Return {layer: array} for the prompt(s) processed since the last flush, then clear."""
    cap = STATE["capture"]
    out = {}
    for li, chunks in cap["buf"].items():
        if not chunks:
            out[li] = None
        elif cap["mode"] == "last":
            out[li] = chunks[-1].astype(np.float32)
        else:
            out[li] = np.concatenate(chunks).astype(np.float32)
        cap["buf"][li] = []
    return out
