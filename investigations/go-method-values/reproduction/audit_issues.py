"""Reuse the full-snapshot auditor with callback-specific terms and neighbors."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'risk-evidence-summary/reproduction'))
import audit_issues as audit

audit.TERMS = [r'method.?value', r'method.?reference', r'method.?expression',
               r'callback', r'non.?call.*selector', r'context.{0,10}value',
               r'package_selector', r'ForEachShard', r'processTxPipeline']
audit.NEAREST = {234,302,325,341,360,364,415,417,446,454,481,497,498,542,547,573,596}

if __name__ == '__main__':
    audit.main()
