"""Read supplied answer artifacts; never invoke providers or write database rows."""
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from astrology.evaluation.harness import blinded_packet, summarize


class Command(BaseCommand):
    help = 'Create blinded P6 evaluation files from explicitly supplied response artifacts (no API calls).'

    def add_arguments(self, parser):
        parser.add_argument('--responses', required=True)
        parser.add_argument('--output-dir', required=True)
        parser.add_argument('--seed', required=True)
        parser.add_argument('--human-scores')
        parser.add_argument('--policy', help='JSON containing previously agreed evaluation thresholds; omission keeps the gate blocked.')

    def handle(self, *args, **options):
        try:
            source = Path(options['responses'])
            if source.stat().st_size > 8 * 1024 * 1024:
                raise ValueError('Response input exceeds 8 MiB.')
            records = json.loads(source.read_text(encoding='utf-8'))
            scores = []
            if options['human_scores']:
                scored = Path(options['human_scores'])
                if scored.stat().st_size > 1024 * 1024: raise ValueError('Score input exceeds 1 MiB.')
                scores = json.loads(scored.read_text(encoding='utf-8'))
            policy = {}
            if options['policy']:
                policy_path = Path(options['policy'])
                if policy_path.stat().st_size > 4096: raise ValueError('Policy exceeds size limit.')
                policy = json.loads(policy_path.read_text(encoding='utf-8'))
                if type(policy) is not dict or set(policy) - {'preference_target', 'threshold_agreed', 'latency_ratio_limit', 'cost_ratio_limit'}:
                    raise ValueError('Invalid evaluation policy')
            packet, key = blinded_packet(records, seed=options['seed'])
            report = summarize(records, key, scores, **policy)
            target = Path(options['output_dir'])
            target.mkdir(parents=True, exist_ok=True)
            if any((target / name).exists() for name in ('blind_packet.json', 'PRIVATE_unblinding_key.json', 'evaluation_report.json')):
                raise ValueError('Choose a fresh output directory to preserve prior evaluation artifacts.')
            for name, data in [('blind_packet.json', packet), ('PRIVATE_unblinding_key.json', key), ('evaluation_report.json', report)]:
                (target / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        except (ValueError, TypeError, OSError, KeyError) as exc:
            raise CommandError('Evaluation artifacts are invalid or unavailable; no provider was called.') from None
        self.stdout.write(f"Created {len(packet)} blinded pairs; gate={report['gate']}. Keep the private key away from graders.")
