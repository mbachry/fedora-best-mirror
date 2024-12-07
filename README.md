# fedora-best-mirror

Fedora mirrorlist API used by DNF returns mirrors sorted by closest
proximity from your geoip location. Often times, however, it's better
to pick a mirror that's farther away, but with better internet
connection to your ISP. The `fedora-best-mirror` script lets you run
speed tests again all servers from the mirror list.

## Install

Install poetry:

```
dnf install poetry
```

Install dependencies:

```
poetry install
```

## Usage

Take your favorite general speed test to make sure your internet
speeds are currently as advertised by the ISP,
eg. [fast.com](https://fast.com). Make sure there are no active
downloads running or anything that may skew the tests.

Run the script with the defaults:

```
poetry run fedora-best-mirror
```

By default the script does 5 second tests of all mirrors and prints
results sorted by average and peak speed. Pick the best mirror and
replace metalinks with `baseurl=` in `/etc/yum.repos.d/fedora.repo`,
`/etc/yum.repos.d/fedora-updates.repo`, etc.

Pass `--download-timeout` param to change test duration from 5
seconds. Use longer timeouts for more reliable averages.

Use `--max-mirrors` to limit how many mirrors are checked,
eg. `--max-mirrors=5` to test only 5 nearest mirrors.
