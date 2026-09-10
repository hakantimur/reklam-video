"""Normalized-coordinate action layer over app.device.adb.

Spec 11.2: tap coordinates are normalized [0,1] at the API boundary; this
module converts to native pixels. Every action must reference the
observation_id of the observation it was decided from — a stale orientation
or an unknown observation is rejected outright (spec 11.2, AT-13).
"""

import time
import uuid
from dataclasses import dataclass, field

from app.device import adb


class StaleObservationError(RuntimeError):
    pass


@dataclass
class Observation:
    id: str
    serial: str
    width: int
    height: int
    orientation: int
    png_bytes: bytes
    captured_at: float = field(default_factory=time.time)


class DeviceController:
    """One instance == one owned control session for one device serial.

    Spec 11.2/6.2: at most one control owner per device; this class does not
    itself enforce cross-process locking (that is DeviceSession's job at the
    API layer) but it does refuse to act on an observation that is no longer
    the latest one it produced, which prevents acting on stale coordinates
    after a rotation or screen change.
    """

    def __init__(self, serial: str):
        self.serial = serial
        self._latest_observation_id: str | None = None

    def observe(self) -> Observation:
        width, height = adb.screen_size(self.serial)
        rotation = adb.orientation(self.serial)
        png_bytes = adb.screenshot_png(self.serial)
        observation = Observation(
            id=str(uuid.uuid4()),
            serial=self.serial,
            width=width,
            height=height,
            orientation=rotation,
            png_bytes=png_bytes,
        )
        self._latest_observation_id = observation.id
        return observation

    def _require_current(self, observation_id: str) -> None:
        if observation_id != self._latest_observation_id:
            raise StaleObservationError(
                f"observation_id {observation_id} is not the latest "
                f"({self._latest_observation_id}); re-observe before acting"
            )

    def tap(self, observation: Observation, x_norm: float, y_norm: float) -> None:
        self._require_current(observation.id)
        if not (0.0 <= x_norm <= 1.0 and 0.0 <= y_norm <= 1.0):
            raise ValueError(f"coordinates must be normalized [0,1], got ({x_norm}, {y_norm})")
        x_px = round(x_norm * observation.width)
        y_px = round(y_norm * observation.height)
        adb.tap(self.serial, x_px, y_px)

    def swipe(
        self,
        observation: Observation,
        x1_norm: float,
        y1_norm: float,
        x2_norm: float,
        y2_norm: float,
        duration_ms: int = 300,
    ) -> None:
        self._require_current(observation.id)
        x1 = round(x1_norm * observation.width)
        y1 = round(y1_norm * observation.height)
        x2 = round(x2_norm * observation.width)
        y2 = round(y2_norm * observation.height)
        adb.swipe(self.serial, x1, y1, x2, y2, duration_ms)

    def press_back(self, observation: Observation) -> None:
        self._require_current(observation.id)
        adb.press_back(self.serial)
