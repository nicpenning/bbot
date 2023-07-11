from bbot.modules.base import BaseModule
from bbot.core.errors import HttpCompareError
from bbot.core.helpers.misc import extract_params_json, extract_params_xml, extract_params_html


class paramminer_headers(BaseModule):
    """
    Inspired by https://github.com/PortSwigger/param-miner
    """

    watched_events = ["HTTP_RESPONSE"]
    produced_events = ["FINDING"]
    flags = ["active", "aggressive", "slow", "web-paramminer"]
    meta = {"description": "Use smart brute-force to check for common HTTP header parameters"}
    options = {
        "wordlist": "",  # default is defined within setup function
        "http_extract": True,
        "skip_boring_words": True,
    }
    options_desc = {
        "wordlist": "Define the wordlist to be used to derive headers",
        "http_extract": "Attempt to find additional wordlist words from the HTTP Response",
        "skip_boring_words": "Remove commonly uninteresting words from the wordlist",
    }
    scanned_hosts = []
    boring_words = {
        "accept",
        "accept-encoding",
        "accept-language",
        "action",
        "authorization",
        "cf-connecting-ip",
        "connection",
        "content-encoding",
        "content-length",
        "content-range",
        "content-type",
        "cookie",
        "date",
        "expect",
        "host",
        "if",
        "if-match",
        "if-modified-since",
        "if-none-match",
        "if-unmodified-since",
        "javascript",
        "keep-alive",
        "label",
        "negotiate",
        "proxy",
        "range",
        "referer",
        "start",
        "trailer",
        "transfer-encoding",
        "upgrade",
        "user-agent",
        "vary",
        "waf-stuff-below",
        "x-scanner",
        "x_alto_ajax_key",
        "zaccess-control-request-headers",
        "zaccess-control-request-method",
        "zmax-forwards",
        "zorigin",
        "zreferrer",
        "zvia",
        "zx-request-id",
        "zx-timer",
    }
    max_event_handlers = 12
    in_scope_only = True
    compare_mode = "header"
    default_wordlist = "paramminer_headers.txt"

    async def setup(self):
        self.event_dict = {}
        wordlist = self.config.get("wordlist", "")
        if not wordlist:
            wordlist = f"{self.helpers.wordlist_dir}/{self.default_wordlist}"
        self.debug(f"Using wordlist: [{wordlist}]")
        self.wl = set(
            h.strip().lower()
            for h in self.helpers.read_file(await self.helpers.wordlist(wordlist))
            if len(h) > 0 and "%" not in h
        )

        # check against the boring list (if the option is set)

        if self.config.get("skip_boring_words", True):
            self.wl -= self.boring_words
        self.matched_words = {}
        return True

    def rand_string(self, *args, **kwargs):
        return self.helpers.rand_string(*args, **kwargs)

    async def do_mining(self, wl, url, batch_size, compare_helper):
        results = set()
        abort_threshold = 25
        try:
            for group in self.helpers.grouper(wl, batch_size):
                async for result, reasons, reflection in self.binary_search(compare_helper, url, group):
                    results.add((result, ",".join(reasons), reflection))
                    if len(results) >= abort_threshold:
                        self.warning(
                            f"Abort threshold ({abort_threshold}) reached, too many {self.compare_mode}s found"
                        )
                        results.clear()
                        assert False
        except AssertionError:
            pass
        return results

    def process_results(self, event, results):
        url = event.data.get("url")
        for result, reasons, reflection in results:
            tags = []
            if reflection:
                tags = ["http_reflection"]
            description = f"[Paramminer] {self.compare_mode.capitalize()}: [{result}] Reasons: [{reasons}] Reflection: [{str(reflection)}]"
            self.emit_event(
                {"host": str(event.host), "url": url, "description": description},
                "FINDING",
                event,
                tags=tags,
            )

    async def handle_event(self, event):
        url = event.data.get("url")

        try:
            compare_helper = self.helpers.http_compare(url)
        except HttpCompareError as e:
            self.debug(e)
            return
        batch_size = await self.count_test(url)
        if batch_size == None or batch_size <= 0:
            self.debug(f"Failed to get baseline max {self.compare_mode} count, aborting")
            return
        self.debug(f"Resolved batch_size at {str(batch_size)}")

        self.event_dict[url] = (event, batch_size)

        if await compare_helper.canary_check(url, mode=self.compare_mode) == False:
            self.verbose(f'Aborting "{url}" due to failed canary check')
            return

        wl = set(self.wl)
        if self.config.get("http_extract"):
            extracted_words = self.load_extracted_words(event.data.get("body"), event.data.get("content_type"))
            self.matched_words[url] = extracted_words
            wl |= extracted_words
            if self.config.get("skip_boring_words", True):
                wl -= self.boring_words
        results = await self.do_mining(wl, url, batch_size, compare_helper)
        self.process_results(event, results)

    async def count_test(self, url):
        baseline = await self.helpers.request(url)
        if baseline is None:
            return
        if str(baseline.status_code)[0] in ("4", "5"):
            return
        for count, args, kwargs in self.gen_count_args(url):
            r = await self.helpers.request(*args, **kwargs)
            if r is not None and not ((str(r.status_code)[0] in ("4", "5"))):
                return count

    def gen_count_args(self, url):
        header_count = 95
        while 1:
            if header_count < 0:
                break
            fake_headers = {}
            for i in range(0, header_count):
                fake_headers[self.rand_string(14)] = self.rand_string(14)
            yield header_count, (url,), {"headers": fake_headers}
            header_count -= 5

    def load_extracted_words(self, body, content_type):
        if "json" in content_type.lower():
            return extract_params_json(body)
        elif "xml" in content_type.lower():
            return extract_params_xml(body)
        else:
            return set(extract_params_html(body))

    async def binary_search(self, compare_helper, url, group, reasons=None, reflection=False):
        if reasons is None:
            reasons = []
        self.debug(f"Entering recursive binary_search with {len(group):,} sized group")
        if len(group) == 1 and len(reasons) > 0:
            yield group[0], reasons, reflection
        elif len(group) > 1 or (len(group) == 1 and len(reasons) == 0):
            for group_slice in self.helpers.split_list(group):
                match, reasons, reflection, subject_response = await self.check_batch(compare_helper, url, group_slice)
                if match == False:
                    async for r in self.binary_search(compare_helper, url, group_slice, reasons, reflection):
                        yield r
        else:
            self.warning(f"Submitted group of size 0 to binary_search()")

    async def check_batch(self, compare_helper, url, header_list):
        rand = self.rand_string()
        test_headers = {}
        for header in header_list:
            test_headers[header] = rand
        return await compare_helper.compare(url, headers=test_headers, check_reflection=(len(header_list) == 1))

    async def finish(self):
        for url, (event, batch_size) in self.event_dict.items():
            compare_helper = self.helpers.http_compare(url)

            untested_matches = set()
            for k, s in self.matched_words.items():
                if k != url:
                    untested_matches.update(s)

            if self.config.get("skip_boring_words", True):
                untested_matches -= self.boring_words

            results = await self.do_mining(untested_matches, url, batch_size, compare_helper)
            self.process_results(event, results)
