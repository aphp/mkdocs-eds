"""
Small collection of numeric utilities for the demo docs.
"""

from __future__ import annotations

from collections import deque
from typing import Iterable


def add(a: float, b: float) -> float:
    """
    Add two numbers.

    Parameters
    ----------
    a: float
        First value.
    b: float
        Second value.

    Returns
    -------
    float
        The sum of both numbers.

    Examples
    --------

    ```python
    add(1, 2)
    ```
    """

    return a + b


def scale_values(values: Iterable[float], *, factor: float = 1.0) -> list[float]:
    """
    Scale every value by a factor.

    Parameters
    ----------
    values: Iterable[float]
        Iterable of numbers to scale.
    factor: float
        Multiplier applied to each value.

    Returns
    -------
    list[float]
        Scaled values as a list.

    Raises
    ------
    ValueError
        If the factor is zero.
    """

    if factor == 0:
        raise ValueError("factor must be non-zero to avoid losing information")
    return [v * factor for v in values]


class MovingAverage:
    """
    Compute a moving average over the most recent values.

    Parameters
    ----------
    window: int
        Number of samples used to compute the average. Must be positive.
    """

    def __init__(self, window: int = 3):
        if window <= 0:
            raise ValueError("window must be positive")
        self.window = window
        self._values: deque[float] = deque(maxlen=window)

    def update(self, value: float) -> float:
        """
        Add a value to the window and return the current average.

        Parameters
        ----------
        value: float
            New data point.

        Returns
        -------
        float
            The average of the recorded values.
        """

        self._values.append(value)
        return sum(self._values) / len(self._values)

    def as_dict(self) -> dict[str, float]:
        """
        Serialize the current state.

        Returns
        -------
        dict[str, float]
            Dictionary with the window size and the number of values seen.
        """

        return {"window": self.window, "count": len(self._values)}
