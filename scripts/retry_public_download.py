"""Bounded transport recovery around an unchanged pinned public download.

No alternate URL, cache, source substitution or validation relaxation. The
caller still performs all original byte/hash and semantic checks afterward.
"""

import time
from urllib.error import HTTPError


def retry_public_download(download, *, sleep=time.sleep):
    for attempt in range(4):
        try:
            return download()
        except HTTPError as error:
            if error.code not in (503, 504) or attempt == 3:
                raise
            delay = 2 ** (attempt + 1)
            print(
                f"Transient public-source HTTP {error.code}; retry {attempt + 2}/4 after {delay}s.",
                flush=True,
            )
            sleep(delay)
