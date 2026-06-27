"""Sentinel memory — learning from past incidents.

The second time a similar problem happens, Sentinel should solve it faster. This
package provides the pieces:

- :mod:`packages.memory.fingerprint` — a stable signature (service + alert type +
  main error) for quick matching.
- :mod:`packages.memory.recall` — given a new incident, find the most similar
  solved ones (fingerprint + meaning similarity, weighted by past accuracy).
- :mod:`packages.memory.writer` — save each solved incident, and update memory
  weights from human-confirmed causes.
- :mod:`packages.memory.patterns` — a background job that merges similar past
  incidents into reusable patterns.
"""

from __future__ import annotations

from packages.memory.fingerprint import IncidentSignature, fingerprint, signature_from_alert
from packages.memory.recall import Recollection, recall, recall_for_alert
from packages.memory.writer import record_confirmation, remember

__all__ = [
    "IncidentSignature",
    "Recollection",
    "fingerprint",
    "recall",
    "recall_for_alert",
    "record_confirmation",
    "remember",
    "signature_from_alert",
]
