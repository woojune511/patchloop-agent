"""Reviewed public probe runtimes; never evaluator images or automatic image acquisition."""
from patchloop.errors import ContractError

RUNTIMES = {
    "python39-v1": ("3.9", "python@sha256:"
                    "dad5b29e3506c35e0fd222736f4d4ef25d21b219acdd73f7bb41d59996ca8e0d"),
    "python312-v1": ("3.12", "patchloop-probe-python312@sha256:"
                     "3b37b00de42a063f990e9b55d3918bb0a64cf5ec533a79e9650ca3ce9ccbe3b1"),
    "python310-v1": ("3.10", "python@sha256:"
                     "c1aaf3d03e14944a039a1647e0b3f6f34c6bee517bac6ff380215ee099c4e808"),
    "python312-graphics-v1": ("3.12", "patchloop-probe-graphics@sha256:"
                              "6248b974b62a3ee356fadf6ce1afa00ff3272e703662b206d553fb22486bdb5c"),
}


def runtime(profile="python312-v1"):
    try:
        return RUNTIMES[profile]
    except KeyError as exc:
        raise ContractError("unsupported public probe runtime") from exc
