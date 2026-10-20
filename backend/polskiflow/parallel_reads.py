"""Bounded request-local concurrency for independent HTTP repository reads.

Never pass ORM work, writes or mutable request state. Owner tokens and
repository timeouts remain unchanged; no data is cached.
"""
from concurrent.futures import ThreadPoolExecutor


def parallel_reads(*operations):
    if not operations:
        return ()
    with ThreadPoolExecutor(max_workers=min(4, len(operations)), thread_name_prefix='lf-read') as pool:
        futures = [pool.submit(operation) for operation in operations]
        return tuple(future.result() for future in futures)
