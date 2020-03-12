from __future__ import print_function
import sys
import gzip
import json
import pickle
from collections import defaultdict


ac_to_entrez = defaultdict(set)
id_mapping_file = sys.argv[1]

for line in gzip.open(id_mapping_file):
    line = line.strip()
    ac, pred, obj = line.split('\t')
    if pred == 'GeneID':
        ac_to_entrez[ac].add(obj)

with open('ac_to_entrez.pk', 'wb') as f:
    pickle.dump(ac_to_entrez, f)
