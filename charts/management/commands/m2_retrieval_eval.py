"""M2 retrieval evaluation under the owner's hard spending cap (OD-5a: US$1.50).

Every paid action needs --confirm-paid. Before each provider call the private
ledger reserves a conservative worst-case cost and refuses the call if the
cap could be exceeded. Passage text is written only to the git-ignored
private folder; committed outputs contain IDs, scores and hashes only.

Usage:
    manage.py m2_retrieval_eval --manifest --confirm-paid
    manage.py m2_retrieval_eval --run Q1,Q2,Q3 --adapters hosted,direct --confirm-paid
    manage.py m2_retrieval_eval --accuracy
    manage.py m2_retrieval_eval --summary
    manage.py m2_retrieval_eval --leakcheck
    manage.py m2_retrieval_eval --run Q1,S1 --adapters direct --label post_ocr --session-cap 0.03 --confirm-paid
"""
import csv
import hashlib
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import yaml
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts.usage_policy import cost_for, tariff_for
from astrology.rag.knowledge_contracts import HOSTED_OUTPUT_TOKENS, SearchRequest

CAP = Decimal('1.50')
BASE = Path(settings.BASE_DIR)
PRIVATE = BASE / 'astrology' / 'evaluation' / 'private' / 'm2'
MANIFEST = BASE / 'astrology' / 'evaluation' / 'corpus_manifest.yaml'
OWNER_BOOKS = [
    '250256424-Astrology-at-the-Speed-of-Light-pdf.pdf',
    '300 Astrology Yoga _ 300 Astrology Combinations _ Astrotalk.pdf',
    'Book. Bhrigu Samhita T.M.Rao_text (1).pdf',
    'conjunctions___the_speed_of_light.pdf',
    'predicting-through-jaimini-chara-dasha.pdf',
    'vargas-vedic-approach.pdf',
    'Yogini Dasha.pdf',
    'Comprehensive Prediction.pdf',  # Retained by the owner 2026-11-11 (V. P. Goel, divisional charts).
]
QUERIES = {
    'Q1': ('career-factual', 'Results of the 10th lord placed in the 11th house for career and gains'),
    'Q2': ('career-factual', 'Saturn aspecting the 10th house and its effect on profession'),
    'Q3': ('career-factual', 'Raja yoga formed by lords of the 9th and 10th houses'),
    'Q4': ('career-predictive', 'Mahadasha of the 10th lord and timing of career rise'),
    'Q5': ('career-predictive', 'Antardasha of Rahu for business and foreign work'),
    'Q6': ('jaimini', 'Amatyakaraka and its role in profession in Jaimini astrology'),
    'Q7': ('jaimini', 'Chara dasha of the 10th sign from Arudha Lagna and career events'),
    'Q8': ('yogini', 'Results of Sankata yogini dasha and its ruling planet'),
    'Q9': ('varga', 'Interpreting the 10th lord of the Dasamsa (D10) chart for career'),
    'Q10': ('varga', 'Strength of a planet in the Navamsa (D9) confirming the Rasi promise'),
    # Post-OCR probes (owner-approved, 2026-11-11) aimed at the repaired Speed of Light book.
    'S1': ('career-factual', 'Saturn placed in the 10th house and its results for career and profession'),
    'S2': ('career-predictive', 'Rahu in the 10th or 11th house for business, gains and foreign work'),
}
SHINGLE = 5
LEAK_SHINGLE = 12


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]


def words(text):
    return re.sub(r'[^a-z0-9]+', ' ', text.casefold()).split()


def shingles(tokens, size):
    return {' '.join(tokens[i:i + size]) for i in range(max(0, len(tokens) - size + 1))}


def domain_vocabulary():
    """Planet, sign and nakshatra names: lists of these are shared vocabulary, not prose."""
    from astrology.constants import NAKSHATRAS, PLANET_NAMES, SIGNS
    names = list(PLANET_NAMES.values()) + list(PLANET_NAMES) + [n for n, _ in NAKSHATRAS]
    names += [s if isinstance(s, str) else str(s.get('name', '')) if isinstance(s, dict) else str(s) for s in SIGNS]
    return {w for name in names for w in words(str(name))}


def prose_runs(grams, vocabulary):
    """Keep runs with at least 6 ordinary words (excludes name lists and number tables)."""
    return {g for g in grams if sum(1 for w in g.split() if w not in vocabulary and not w.isdigit()) >= 6}


class Ledger:
    def __init__(self, path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)

    def rows(self):
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding='utf-8').splitlines() if line.strip()]

    def spent(self):
        # Rated cost when known; otherwise the full reservation (never optimistic).
        return sum((Decimal(r['rated']) if r.get('rated') is not None else Decimal(r['reserved'])) for r in self.rows())

    def check(self, reserve):
        spent = self.spent()
        if spent + reserve > CAP:
            raise CommandError(f'Refused: reservation {reserve} would exceed the M2 cap ({spent} of {CAP} already counted).')

    def write(self, entry):
        entry = {'at': now(), **{k: (str(v) if isinstance(v, Decimal) else v) for k, v in entry.items()}}
        with self.path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(entry) + '\n')


class Command(BaseCommand):
    help = 'M2 retrieval evaluation (manifest, capped paid runs, accuracy, summary, leak check).'

    def add_arguments(self, parser):
        parser.add_argument('--manifest', action='store_true')
        parser.add_argument('--run')
        parser.add_argument('--adapters', default='hosted,direct')
        parser.add_argument('--accuracy', action='store_true')
        parser.add_argument('--summary', action='store_true')
        parser.add_argument('--leakcheck', action='store_true')
        parser.add_argument('--confirm-paid', action='store_true')
        parser.add_argument('--books-dir', default=str(BASE.parent))
        parser.add_argument('--label', default='',
                            help='Write hits to hits_<label>.jsonl / review_<label>.csv so the M2 baseline is never overwritten.')
        parser.add_argument('--session-cap', default=None,
                            help='Extra cap (US$) for this invocation, on top of the overall M2 cap.')
        parser.add_argument('--review', default='review_for_owner.csv',
                            help='Rated sheet inside the private M2 folder (offline; used by --summary).')

    def handle(self, *args, **options):
        self.ledger = Ledger(PRIVATE / 'ledger.jsonl')
        self.books_dir = Path(options['books_dir'])
        self.review = options['review']
        label = re.sub(r'[^a-z0-9_]', '', options['label'].lower())
        self.hits_name = f'hits_{label}.jsonl' if label else 'hits.jsonl'
        self.review_name = f'review_{label}.csv' if label else 'review_for_owner.csv'
        self.label = label or None
        self.suffix = f'_{label}' if label else ''
        self.session_cap = Decimal(options['session_cap']) if options['session_cap'] else None
        self.session_reserved = Decimal(0)
        if (options['manifest'] or options['run']) and not options['confirm_paid']:
            raise CommandError('Provider calls require --confirm-paid (owner-approved M2 cap).')
        if options['manifest']:
            self.manifest()
        if options['run']:
            self.run([q.strip() for q in options['run'].split(',') if q.strip()],
                     [a.strip() for a in options['adapters'].split(',') if a.strip()])
        if options['accuracy']:
            self.accuracy()
        if options['summary']:
            self.summary()
        if options['leakcheck']:
            self.leakcheck()
        self.stdout.write(f'M2 ledger total: US${self.ledger.spent()} of US${CAP}')

    # ── Provider access ─────────────────────────────────────────────────────

    def client(self):
        from openai import OpenAI
        from accounts.provider_transport import IPv4HttpClient
        if not (settings.OPENAI_API_KEY and settings.OPENAI_VECTOR_STORE_ID):
            raise CommandError('OPENAI_API_KEY and OPENAI_VECTOR_STORE_ID must be configured.')
        return OpenAI(api_key=settings.OPENAI_API_KEY, max_retries=0, timeout=30, http_client=IPv4HttpClient())

    def manifest(self):
        store_id = settings.OPENAI_VECTOR_STORE_ID
        client = self.client()
        calls = 0
        try:
            self.ledger.check(Decimal(0))
            store = client.vector_stores.retrieve(store_id)
            calls += 1
            files, after = [], None
            while True:
                page = client.vector_stores.files.list(store_id, limit=100, **({'after': after} if after else {}))
                calls += 1
                files.extend(page.data)
                if not getattr(page, 'has_more', False) or not page.data:
                    break
                after = page.data[-1].id
            entries = []
            for item in files:
                meta = client.files.retrieve(item.id)
                calls += 1
                error = getattr(item, 'last_error', None)
                entries.append({'file_id': item.id, 'filename': meta.filename, 'status': item.status,
                    'usage_bytes': getattr(item, 'usage_bytes', None), 'file_bytes': getattr(meta, 'bytes', None),
                    'attributes': getattr(item, 'attributes', None) or {},
                    'last_error': getattr(error, 'code', None) if error else None,
                    'tradition': 'pending_owner', 'rights_class': 'pending_owner', 'display_title': 'pending_owner'})
        finally:
            client.close()
            self.ledger.write({'kind': 'manifest', 'calls': calls, 'reserved': Decimal(0), 'rated': Decimal(0),
                               'note': 'management endpoints; believed unbilled (UNVERIFIED)'})
        names = {e['filename'] for e in entries}
        accounted = []
        for book in OWNER_BOOKS:
            match = next((e for e in entries if e['filename'] == book), None)
            accounted.append({'owner_listed': book, 'store_status': (
                'indexed' if match and match['status'] == 'completed' else 'failed' if match else 'missing'),
                'local_copy': (self.books_dir / book).exists()})
        document = {
            'generated_at': now(), 'store_id_sha256_16': sha(store_id),
            'store': {'name': getattr(store, 'name', None), 'status': getattr(store, 'status', None),
                      'usage_bytes': getattr(store, 'usage_bytes', None),
                      'file_counts': store.file_counts.model_dump() if getattr(store, 'file_counts', None) else None},
            'owner_list_reconciliation': accounted,
            'files_not_in_owner_list': sorted(n for n in names if n not in OWNER_BOOKS),
            'files': entries,
            'policy': {'OD-11': 'title and paraphrase only until rights are confirmed',
                       'flagged_for_possible_removal': [OWNER_BOOKS[1]]},
        }
        MANIFEST.write_text(yaml.safe_dump(document, sort_keys=False, allow_unicode=True), encoding='utf-8')
        self.stdout.write(f'Manifest: {len(entries)} files; written to {MANIFEST.relative_to(BASE)}')

    def reservation(self, adapter):
        tariff = tariff_for(getattr(settings, 'OPENAI_MODEL', '') or 'gpt-4o-mini')
        if adapter == 'hosted':
            return tariff, cost_for(tariff, tariff['context'], HOSTED_OUTPUT_TOKENS, file_searches=1)
        return tariff, cost_for(tariff, 0, 0, file_searches=1)

    def run(self, query_ids, adapters):
        from astrology.rag.direct import DirectVectorStoreSearch
        from astrology.rag.hosted import HostedFileSearch
        unknown = [q for q in query_ids if q not in QUERIES] + [a for a in adapters if a not in ('hosted', 'direct')]
        if unknown:
            raise CommandError(f'Unknown query/adapter: {unknown}')
        built = {'hosted': HostedFileSearch, 'direct': DirectVectorStoreSearch}
        hits_path = PRIVATE / self.hits_name
        for qid in query_ids:
            category, text = QUERIES[qid]
            for name in adapters:
                tariff, reserve = self.reservation(name)
                self.ledger.check(reserve)  # Stop before any call that might exceed the cap.
                if self.session_cap is not None and self.session_reserved + reserve > self.session_cap:
                    raise CommandError(f'Refused: reservation {reserve} would exceed the session cap '
                                       f'({self.session_reserved} of {self.session_cap} already reserved).')
                self.session_reserved += reserve
                adapter = built[name]()
                request = SearchRequest(0, category, (text[:80],), result_count=5)
                started = time.perf_counter()
                status, batch = 'ok', None
                try:
                    batch = adapter.retrieve(text, request, timeout=30)
                except Exception as exc:  # The call may still have been billed: count the reservation.
                    status = type(exc).__name__
                latency = round((time.perf_counter() - started) * 1000)
                if batch is not None:
                    rated = cost_for(tariff, batch.input_tokens, batch.output_tokens, file_searches=1)
                else:
                    rated = None
                self.ledger.write({'kind': 'search', 'label': self.label, 'query': qid, 'adapter': name, 'status': status,
                    'reserved': reserve, 'rated': rated, 'input_tokens': batch.input_tokens if batch else None,
                    'output_tokens': batch.output_tokens if batch else None, 'hits': len(batch.results) if batch else 0,
                    'latency_ms': latency, 'price_basis': 'provider-reported tokens + US$0.0025/search' if name == 'hosted'
                    else 'US$0.0025/search assumed (UNVERIFIED)'})
                with hits_path.open('a', encoding='utf-8') as handle:
                    for rank, row in enumerate((batch.results if batch else [])[:5], 1):
                        handle.write(json.dumps({'query': qid, 'adapter': name, 'rank': rank,
                            'file_id': row.get('file_id'), 'filename': row.get('filename'), 'score': row.get('score'),
                            'text': row.get('text') or ''}, ensure_ascii=False) + '\n')
                self.stdout.write(f'{qid} {name}: {status}, {len(batch.results) if batch else 0} hits, {latency} ms, '
                                  f'rated US${rated if rated is not None else reserve}')
        self.write_review()

    def write_review(self):
        """Private owner-labelling sheet (never committed): one row per hit, rating column blank."""
        hits = self.hits()
        path = PRIVATE / self.review_name
        previous = {}
        if path.exists():
            with path.open(encoding='utf-8-sig', newline='') as handle:
                previous = {(r['query'], r['adapter'], r['rank']): r.get('rating', '') for r in csv.DictReader(handle)}
        with path.open('w', encoding='utf-8-sig', newline='') as handle:
            writer = csv.writer(handle)
            writer.writerow(['query', 'question', 'adapter', 'rank', 'filename', 'score', 'passage', 'rating'])
            for h in hits:
                key = (h['query'], h['adapter'], str(h['rank']))
                writer.writerow([h['query'], QUERIES[h['query']][1], h['adapter'], h['rank'], h['filename'],
                                 h['score'], h['text'][:1500], previous.get(key, '')])

    def hits(self):
        path = PRIVATE / self.hits_name
        if not path.exists():
            return []
        rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
        latest = {}
        for row in rows:  # A repeated run of the same query/adapter supersedes the earlier one.
            latest[(row['query'], row['adapter'], row['rank'])] = row
        return sorted(latest.values(), key=lambda r: (int(r['query'][1:]), r['adapter'], r['rank']))

    # ── Offline analysis ────────────────────────────────────────────────────

    def book_text(self, filename):
        source = self.books_dir / filename
        if not source.exists():
            return None
        stat = source.stat()  # Keyed by size and mtime so a replaced (re-OCR'd) book is re-extracted.
        cache = PRIVATE / 'text' / (sha(f'{filename}|{stat.st_size}|{stat.st_mtime_ns}') + '.txt')
        if cache.exists():
            return cache.read_text(encoding='utf-8')
        from pypdf import PdfReader
        text = '\n'.join((page.extract_text() or '') for page in PdfReader(str(source)).pages)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(text, encoding='utf-8')
        return text

    def accuracy(self):
        books = {}
        for name in OWNER_BOOKS:
            text = self.book_text(name)
            if text is not None:
                books[name] = shingles(words(text), SHINGLE)
        results = []
        for h in self.hits():
            grams = shingles(words(h['text']), SHINGLE)
            scores = {name: (len(grams & s) / len(grams) if grams else 0.0) for name, s in books.items()}
            best = max(scores, key=scores.get) if scores else None
            results.append({'query': h['query'], 'adapter': h['adapter'], 'rank': h['rank'], 'filename': h['filename'],
                            'text_sha256_16': sha(h['text']), 'local_copy': h['filename'] in books,
                            'match_attributed': round(scores.get(h['filename'], 0.0), 3) if h['filename'] in books else None,
                            'best_local_book': best, 'match_best': round(scores[best], 3) if best else None})
        (PRIVATE / f'accuracy{self.suffix}.json').write_text(json.dumps(results, indent=1), encoding='utf-8')
        extract = {name: len(s) for name, s in books.items()}
        self.stdout.write(f'Accuracy: {len(results)} hits scored; local books with extractable text (5-gram counts): {extract}')

    def summary(self):
        rows = [r for r in self.ledger.rows() if r['kind'] == 'search' and r.get('label') == self.label]
        ratings = {}
        review = PRIVATE / Path(self.review).name  # always inside the private folder
        if review.exists():
            with review.open(encoding='utf-8-sig', newline='') as handle:
                for r in csv.DictReader(handle):
                    if r.get('rating', '').strip() in ('0', '1', '2'):
                        ratings[(r['query'], r['adapter'], r['rank'])] = int(r['rating'])
        acc_path = PRIVATE / f'accuracy{self.suffix}.json'
        accuracy = json.loads(acc_path.read_text()) if acc_path.exists() else []
        out = {}
        for name in sorted({r['adapter'] for r in rows}):
            mine = [r for r in rows if r['adapter'] == name and r['status'] == 'ok']
            queries = sorted({r['query'] for r in mine}, key=lambda q: int(q[1:]))
            rated = [ratings.get((q, name, str(k))) for q in queries for k in range(1, 6)]
            per_query = [[ratings.get((q, name, str(k))) for k in range(1, 6)] for q in queries]
            labelled = [v for v in rated if v is not None]
            acc = [a for a in accuracy if a['adapter'] == name and a['match_attributed'] is not None]
            out[name] = {
                'queries': queries, 'calls': len(mine),
                'mean_latency_ms': round(sum(r['latency_ms'] for r in mine) / len(mine)) if mine else None,
                'rated_cost_total': str(sum(Decimal(r['rated']) for r in mine if r.get('rated') is not None)),
                'rated_cost_per_query': str((sum(Decimal(r['rated']) for r in mine if r.get('rated') is not None) / len(mine)).quantize(Decimal('0.00001'))) if mine else None,
                'mean_input_tokens': round(sum(r['input_tokens'] or 0 for r in mine) / len(mine)) if mine else None,
                'hits_labelled': f'{len(labelled)}/{len(rated)}',
                'mean_relevance_at_5': round(sum(labelled) / len(labelled), 3) if labelled else None,
                'share_queries_with_a_2': round(sum(any(v == 2 for v in q) for q in per_query) / len(per_query), 3) if per_query and labelled else None,
                'share_hits_relevant_ge_1': round(sum(v >= 1 for v in labelled) / len(labelled), 3) if labelled else None,
                'top1_mean': round(sum(q[0] for q in per_query if q[0] is not None) / len(per_query), 3) if labelled else None,
                'per_query_ratings': {q: per_query[i] for i, q in enumerate(queries)},
                'accuracy_hits_with_local_book': len(acc),
                'accuracy_share_at_or_above_0_6': round(sum(a['match_attributed'] >= 0.6 for a in acc) / len(acc), 3) if acc else None,
                'hits_without_local_book': sum(1 for a in accuracy if a['adapter'] == name and not a['local_copy']),
                'misattributed_candidates': sum(1 for a in acc if a['match_attributed'] < 0.6 and a['best_local_book'] != a['filename'] and (a['match_best'] or 0) >= 0.6),
            }
        out['review_file'] = review.name
        (PRIVATE / f'summary{self.suffix}.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
        self.stdout.write(json.dumps(out, indent=1))

    def leakcheck(self):
        """M2-AC10: no 12-word prose run from any local book appears in a git-tracked file."""
        grams, vocabulary = set(), domain_vocabulary()
        for name in OWNER_BOOKS:
            text = self.book_text(name)
            if text:
                grams |= prose_runs(shingles(words(text), LEAK_SHINGLE), vocabulary)
        tracked = subprocess.run(['git', 'ls-files'], cwd=BASE, capture_output=True, text=True, check=True).stdout.split('\n')
        leaks = []
        for rel in filter(None, tracked):
            path = BASE / rel
            if path.suffix.lower() not in ('.py', '.md', '.txt', '.yaml', '.yml', '.json', '.html', '.csv') or not path.exists():
                continue
            found = shingles(words(path.read_text(encoding='utf-8', errors='ignore')), LEAK_SHINGLE) & grams
            if found:
                leaks.append((rel, len(found)))
        self.stdout.write(f'Leak check: {len(grams)} book 12-word runs; tracked files with matches: {leaks or "none"}')
