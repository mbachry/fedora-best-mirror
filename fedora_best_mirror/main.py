import argparse
import asyncio
import platform
import sys
import time
from dataclasses import dataclass
from operator import attrgetter
from urllib.parse import urljoin, urlparse

import niquests
from niquests import AsyncSession

MIRRORS_BASE_URL = 'https://mirrors.fedoraproject.org/mirrorlist'
DEFAULT_TIMEOUT = 10
DEFAULT_MAX_MIRRORS = None
TEST_FILE = 'images/boot.iso'


@dataclass
class TestResult:
    url: str
    avg_rate: float
    max_rate: float


def get_fedora_version():
    release = platform.freedesktop_os_release()
    if 'REDHAT_SUPPORT_PRODUCT' not in release:
        raise ValueError('not a redhat distribution')
    return release['VERSION_ID']


def get_mirror_list(base_url, version, arch):
    resp = niquests.get(base_url, {'repo': f'fedora-{version}', 'arch': arch}, timeout=5)
    resp.raise_for_status()
    content = resp.text
    assert content is not None
    return [line.strip() for line in content.splitlines() if not line.startswith('#')]


async def check_speed(base_url, timeout):
    domain = urlparse(base_url).netloc
    url = urljoin(base_url, TEST_FILE)
    total = 0
    max_rate = 0

    async def print_stats():
        nonlocal max_rate

        last = total
        try:
            while True:
                await asyncio.sleep(1)
                this_chunk = total - last
                assert this_chunk >= 0
                rate = this_chunk / 1024 / 1024
                print(f'\r{domain:30}  {rate:6.02f} Mb/s', end='')
                if rate > max_rate:
                    max_rate = rate
                last = total
        finally:
            print()

    async with AsyncSession() as session:
        resp = await session.get(url, stream=True, timeout=5)
        resp.raise_for_status()
        start_time = time.monotonic()
        stats_task = asyncio.create_task(print_stats())
        try:
            async with asyncio.timeout(timeout):
                async for chunk in await resp.iter_content(128 * 1024):
                    total += len(chunk)
        except TimeoutError:
            pass
        finally:
            if stats_task.done():
                stats_task.result()
            stats_task.cancel()
        elapsed = time.monotonic() - start_time

    avg_rate = total / elapsed / 1024 / 1024
    return avg_rate, max_rate


def get_top_urls(mirrors, timeout) -> list[TestResult]:
    stats = []
    for mirror in mirrors:
        try:
            avg_rate, max_rate = asyncio.run(check_speed(mirror, timeout))
        except OSError as e:
            print(f'ERROR: {mirror}: {e}', file=sys.stderr)
            continue
        stats.append(TestResult(url=mirror, avg_rate=avg_rate, max_rate=max_rate))
    return stats


def to_repo_url(url, version, arch):
    replaced_path = f'releases/{version}/Everything/{arch}/os'
    assert replaced_path in url
    return url.replace(replaced_path, 'releases/$releasever/Everything/$basearch/os')


def print_stats(stats: list[TestResult], version, arch, column):
    for stat in stats:
        repo_url = to_repo_url(stat.url, version, arch)
        metric = getattr(stat, column)
        print(f'{metric:6.02f} Mb/s  baseurl={repo_url}')


def _main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mirrors-url', default=MIRRORS_BASE_URL, help='mirrors list API endpoint')
    parser.add_argument('--download-timeout', default=DEFAULT_TIMEOUT, type=int, help='max download time (s)')
    parser.add_argument('--max-mirrors', default=DEFAULT_MAX_MIRRORS, type=int, help='max numer of mirrors to try')
    args = parser.parse_args()

    version = get_fedora_version()
    arch = platform.machine()

    mirrors = get_mirror_list(args.mirrors_url, version, arch)
    if args.max_mirrors:
        mirrors = mirrors[: args.max_mirrors]

    print(f'Testing {len(mirrors)} mirrors')
    stats = get_top_urls(mirrors, args.download_timeout)

    stats.sort(key=attrgetter('avg_rate'), reverse=True)
    print('\nTop mirrors by mean download rate:')
    print_stats(stats, version, arch, 'avg_rate')

    stats.sort(key=attrgetter('max_rate'), reverse=True)
    print('\nTop mirrors by peak download rate:')
    print_stats(stats, version, arch, 'max_rate')


def main():
    try:
        _main()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
