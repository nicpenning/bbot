![bbot_banner](https://user-images.githubusercontent.com/20261699/158000235-6c1ace81-a267-4f8e-90a1-f4c16884ebac.png)

# BEE·bot
### OSINT automation for hackers.

[![Python Version](https://img.shields.io/badge/python-3.9+-FF8400)](https://www.python.org) [![Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![License](https://img.shields.io/badge/license-GPLv3-FF8400.svg)](https://github.com/blacklanternsecurity/bbot/blob/dev/LICENSE) [![Tests](https://github.com/blacklanternsecurity/bbot/workflows/tests/badge.svg)](https://github.com/blacklanternsecurity/bbot/actions?query=workflow%3A"tests") [![Codecov](https://codecov.io/gh/blacklanternsecurity/bbot/branch/dev/graph/badge.svg?token=IR5AZBDM5K)](https://codecov.io/gh/blacklanternsecurity/bbot)

## Installation
~~~bash
pip install poetry

git clone git@github.com:blacklanternsecurity/bbot.git && cd bbot
poetry install
poetry shell

bbot --help
~~~

## Examples
~~~bash
# subdomain enumeration
bbot --flags subdomain-enum --targets evilcorp.com

# custom modules
bbot --modules naabu httpx nuclei --targets evilcorp.com 1.2.3.4/28 4.3.2.1

# agent mode
bbot --agent-mode
~~~

## Output to Neo4j
~~~bash
# start Neo4j in docker
docker run --rm -p 7687:7687 -p 7474:7474 --env NEO4J_AUTH=neo4j/bbotislife neo4j

# run bbot with -o neo4j
bbot -f subdomain-enum -t evilcorp.com -o human neo4j
~~~
![neo4j](https://user-images.githubusercontent.com/20261699/172188763-fcbbcc57-5410-46f2-a3ff-8c3d40b9a025.png)

## Tests
~~~bash
# run tests
bbot/test/run_tests.sh

# format with black
black .
~~~

## Adding a dependency
~~~
1. poetry add <package>
2. poetry export --without-hashes > requirements.txt
3. poetry export --dev --without-hashes > requirements-dev.txt
~~~

## Usage
~~~bash
$ bbot --help
usage: bbot [-h] [-t TARGET [TARGET ...]] [-w TARGET [TARGET ...]] [-b BLACKLIST [BLACKLIST ...]] [-m MODULE [MODULE ...]]
            [-em MODULE [MODULE ...]] [-f FLAG [FLAG ...]] [-rf FLAG [FLAG ...]] [-ef FLAG [FLAG ...]] [-o MODULE [MODULE ...]]
            [-oA BASE_FILENAME] [-c [CONFIGURATION ...]] [-v] [-d] [--current-config] [--save-wordcloud FILE]
            [--load-wordcloud FILE | --load-last-wordcloud] [--ignore-failed-deps] [--no-deps | --force-deps | --retry-deps] [-a]

Bighuge BLS OSINT Tool

options:
  -h, --help            show this help message and exit
  -m MODULE [MODULE ...], --modules MODULE [MODULE ...]
                        Modules to enable. Choices: aspnet_viewstate,azure_tenant,bypass403,c99,cookie_brute,crobat,crt,dnscommonsrv,dnsdumpster,dnsgrep,dnszonetransfer,emailformat,ffuf,ffuf_shortnames,getparam_brute,gowitness,header_brute,httpx,hunterio,iis_shortnames,ipneighbor,leakix,massdns,naabu,nuclei,securitytrails,shodan_dns,skymem,smuggler,sslcert,sublist3r,telerik,urlscan,vhost,viewdns,wappalyzer,wayback
  -em MODULE [MODULE ...], --exclude-modules MODULE [MODULE ...]
                        Exclude these modules.
  -f FLAG [FLAG ...], --flags FLAG [FLAG ...]
                        Enable modules by flag. Choices: active,brute-force,passive,subdomain-enum
  -rf FLAG [FLAG ...], --require-flags FLAG [FLAG ...]
                        Disable modules that don't have these flags (e.g. --require-flags passive)
  -ef FLAG [FLAG ...], --exclude-flags FLAG [FLAG ...]
                        Disable modules with these flags. (e.g. --exclude-flags brute-force)
  -o MODULE [MODULE ...], --output-modules MODULE [MODULE ...]
                        Output module(s). Choices: csv,http,human,json,neo4j,websocket
  -oA BASE_FILENAME, --output-all BASE_FILENAME
                        Output in CSV, JSON, and TXT at this file location
  -c [CONFIGURATION ...], --configuration [CONFIGURATION ...]
                        additional configuration options in key=value format
  -v, --verbose         Be more verbose
  -d, --debug           Enable debugging
  --current-config      Show current config in YAML format

Target:
  -t TARGET [TARGET ...], --targets TARGET [TARGET ...]
                        Targets to seed the scan
  -w TARGET [TARGET ...], --whitelist TARGET [TARGET ...]
                        What's considered in-scope (by default it's the same as --targets)
  -b BLACKLIST [BLACKLIST ...], --blacklist BLACKLIST [BLACKLIST ...]
                        Don't touch these things

Word cloud:
  Save/load wordlist of common words gathered during a scan

  --save-wordcloud FILE
                        Output wordcloud to file when the scan completes
  --load-wordcloud FILE
                        Load wordcloud from a file and use it in the scan
  --load-last-wordcloud
                        Load the wordcloud from the last scan (from $BBOT_HOME)

Module dependencies:
  Control how modules install their dependencies

  --ignore-failed-deps  Run modules even if their dependency setup failed
  --no-deps             Don't install module dependencies
  --force-deps          Force install all module dependencies
  --retry-deps          Retry failed module dependencies

Agent:
  Report back to a central server

  -a, --agent-mode      Start in agent mode
~~~

## Generate config
To generate a full config file from the current config (including module defaults, etc.), run the following command:
~~~
$ bbot --current-config > bbot.conf
~~~

## Writing modules
Modules have easy access to scan information and helper functions:
~~~python
# Access scan target:
if event in self.scan.target:
    self.info(f"{event} is part of target!")

# Use a helper function
if not self.helpers.is_domain(event.data):
    self.warning(f"{event} is not a domain.")

# Access module config
if not self.config.api_key:
    self.error(f"No API key specified for module.{self.name}!")

# Download a file
filename = self.helpers.download(self.config.get("wordlist"), cache_hrs=720)

# Make a web request
response = self.helpers.request("https://evilcorp.com")

# Make a DNS query
mx_records = self.helpers.resolve("evilcorp.com", type="mx")

# Reverse resolve IP
ptrs = self.helpers.resolve("8.8.8.8")

# Execute a shell command
process = self.helpers.run(["ls", "-lah"])
log.info(process.stdout)

# Use the shared thread pool
# limit threads by setting self.config.max_threads
futures = {}
for url in urls:
    future = self.submit_task(self.helpers.request, url)
    futures[future] = url

for future in self.helpers.as_completed(futures):
    url = futures[future]
    response = future.result()
    if getattr(response, "status_code", 0) == 200:
        log.success(f"Found URL: {url}")

# Access the global word cloud
# The word cloud contains commonly-encountered words from the scan
# These words come from dns names, etc., and you can use them for 
# smart brute-forcing of subdomains, vhosts, storage buckets, etc.
self.helpers.word_cloud
# {"www": 1, black": 3, "lantern": 1, "security": 1, ...}
self.helpers.word_cloud.modifiers()
# {"1", "2", "3", "dev", "api", "test", "qa", ...}
self.helpers.word_cloud.mutations("www")
"""
[
    ("www", "dev"),
    ("dev", "www"),
    ("www", "api"),
    ("api", "www"),
    ("www", "1"),
    ("1", "www")
]
"""
~~~