"""Bounded JSON-lines requests to a persistent local CBOM JVM subprocess."""

from __future__ import annotations

import json
import math
import queue
import subprocess
import tempfile
import threading


class JavaBridge:
    """Own exactly one JVM, including cleanup after malformed replies or timeout."""

    max_response_bytes = 8 * 1024 * 1024

    def __init__(self, command: list[str], timeout: float):
        if isinstance(timeout, bool) or not isinstance(timeout, (float, int)):
            raise ValueError("request_timeout must be a positive finite number")
        if not 0 < timeout <= 600 or not math.isfinite(timeout):
            raise ValueError("request_timeout must be positive and at most 600 seconds")
        self.timeout = float(timeout)
        self.process = None
        self._reader = None
        self._writer = None
        self._closed = threading.Event()
        self._responses = queue.Queue(maxsize=1)
        self._stderr = tempfile.TemporaryFile()
        try:
            self.process = subprocess.Popen(  # pylint: disable=consider-using-with
                command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=self._stderr,
            )  # nosec B603
            self._reader = threading.Thread(target=self._read_responses, daemon=True)
            self._reader.start()
        except BaseException:
            self.close()
            raise

    def _read_responses(self):
        try:
            while not self._closed.is_set():
                line = self.process.stdout.readline(self.max_response_bytes + 1)
                if len(line) > self.max_response_bytes:
                    item = ValueError("CBOM Java response exceeds the size limit")
                elif not line:
                    item = RuntimeError("CBOM Java exited before returning a response")
                else:
                    item = line
                while not self._closed.is_set():
                    try:
                        self._responses.put(item, timeout=.1)
                        break
                    except queue.Full:
                        continue
                if isinstance(item, Exception):
                    return
        except (OSError, ValueError) as error:
            if not self._closed.is_set():
                try:
                    self._responses.put_nowait(error)
                except queue.Full:
                    pass

    def _write_request(self, raw: bytes) -> None:
        try:
            self.process.stdin.write(raw)
            self.process.stdin.flush()
        except (OSError, ValueError) as error:
            if not self._closed.is_set():
                try:
                    self._responses.put_nowait(error)
                except queue.Full:
                    pass

    def request(self, payload: dict) -> dict:
        if self._closed.is_set():
            raise RuntimeError("CBOM Java process is closed")
        try:
            raw = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"
            if len(raw) > self.max_response_bytes:
                raise ValueError("CBOM Java request exceeds the size limit")
            # A peer that stops reading must not block the session in write().
            # The same request timeout covers both pipe writing and reading.
            self._writer = threading.Thread(target=self._write_request, args=(raw,), daemon=True)
            self._writer.start()
            try:
                response = self._responses.get(timeout=self.timeout)
            except queue.Empty as error:
                raise TimeoutError("CBOM Java response timed out") from error
            if isinstance(response, Exception):
                raise response
            result = json.loads(response)
            if not isinstance(result, dict) or not isinstance(result.get("ok"), bool):
                raise ValueError("Invalid CBOM Java response envelope")
            if not result["ok"]:
                raise ValueError(f"CBOM Java rejected the request: {result.get('error', 'unknown error')}")
            self._writer.join(timeout=1.)
            return result
        except BaseException:
            # Session's callback timeout raises SystemExit in its worker thread.
            # Catch it for cleanup too, then preserve the original exception.
            self.close()
            raise

    def close(self) -> None:
        """Reap the child and release pipe/thread resources; safe before init."""
        if self._closed.is_set():
            return
        self._closed.set()
        process = self.process
        if process is not None:
            if process.poll() is None:
                try:
                    process.terminate()
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=1.)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=1.)
            if self._reader is not None:
                self._reader.join(timeout=1.)
            if self._writer is not None:
                self._writer.join(timeout=1.)
            for pipe in (process.stdin, process.stdout):
                if pipe is not None:
                    pipe.close()
        self._stderr.close()
