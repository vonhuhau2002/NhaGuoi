"""Continuous resampling across model chunks for PCM generation diagnostics."""

from fractions import Fraction


class Cancelled(Exception):
    pass


class AudioResampler:
    """Preserve FIR history, future context and phase between audio chunks.

    Buffer origins stay at multiples of the denominator, so each local
    resample has the same phase as resampling the complete utterance.
    Only the short FIR overlap is kept, independent of answer length.
    """

    def __init__(self, ratio):
        ratio = Fraction(ratio)
        self.up, self.down = ratio.numerator, ratio.denominator
        self.margin = 32 * max(self.up, self.down) // self.up + 32
        self.buffer = None
        self.input_start = self.emitted = 0

    def push(self, samples, *, final=False):
        import numpy as np
        from scipy.signal import resample_poly

        samples = np.asarray(samples, dtype=np.float32).reshape(-1)
        if self.up == self.down:
            return samples
        self.buffer = samples if self.buffer is None else np.concatenate((self.buffer, samples))
        if not self.buffer.size:
            return samples
        output = resample_poly(self.buffer, self.up, self.down)
        origin = self.input_start * self.up // self.down
        start = self.emitted - origin
        end = len(output) if final else max(start, (len(self.buffer) - self.margin) * self.up // self.down)
        ready = output[start:end].copy()
        self.emitted = origin + end
        needed = self.emitted * self.down // self.up - self.margin
        trim = max(0, (needed - self.input_start) // self.down * self.down)
        self.buffer = self.buffer[trim:].copy()
        self.input_start += trim
        return ready
