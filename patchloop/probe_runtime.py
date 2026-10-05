"""Reviewed public probe runtimes; never evaluator images or automatic image acquisition."""
from patchloop.errors import ContractError

RUNTIMES = {
    "python312-v1": ("3.12", "python@sha256:"
                     "57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de"),
    "python310-v1": ("3.10", "python@sha256:"
                     "c1aaf3d03e14944a039a1647e0b3f6f34c6bee517bac6ff380215ee099c4e808"),
    "python312-graphics-v1": ("3.12", "patchloop-probe-graphics@sha256:"
                              "d6e04205b8eb12521966beb25247e164d5799ba019a53d13c556654ad8477a9b"),
}


def runtime(profile="python312-v1"):
    try:
        return RUNTIMES[profile]
    except KeyError as exc:
        raise ContractError("unsupported public probe runtime") from exc
