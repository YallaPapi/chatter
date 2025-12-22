# -*- coding: utf-8 -*-
import json
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8')

approaches_wanted = ['playful', 'teasing', 'transactional', 'romantic', 'flirty', 'direct']
examples = {a: [] for a in approaches_wanted}

for f in Path('data/parsed_conversations').rglob('*.parsed.json'):
    try:
        d = json.load(open(f, encoding='utf-8'))
        parsed = d.get('parsed_data', {})
        approach = parsed.get('context', {}).get('creator_approach')

        if approach not in approaches_wanted:
            continue
        if len(examples[approach]) >= 3:
            continue

        messages = parsed.get('messages', [])
        creator_msgs = [m.get('text', '') for m in messages
                       if m.get('role') == 'creator' and m.get('text') and len(m.get('text', '')) > 40]

        if creator_msgs:
            msg = creator_msgs[0][:180].replace('\n', ' ')
            examples[approach].append(msg)
    except:
        pass

for approach in approaches_wanted:
    print(f'\n=== {approach.upper()} ===')
    for i, ex in enumerate(examples[approach], 1):
        print(f'{i}. "{ex}"')
