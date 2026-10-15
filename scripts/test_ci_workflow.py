#!/usr/bin/env python3
"""Check that validation jobs declare their tools and use the unittest runner."""
from pathlib import Path
import unittest

import yaml


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.jobs = yaml.safe_load((root / '.github/workflows/validate.yaml').read_text())['jobs']

    def test_precommit_installs_kustomize_before_validation(self):
        steps = self.jobs['pre-commit']['steps']
        runner = next(i for i, step in enumerate(steps) if 'pre-commit run' in step.get('run', ''))
        self.assertTrue(any(step.get('uses', '').startswith('imranismail/setup-kustomize@')
                            for step in steps[:runner]), 'pre-commit needs Kustomize for repository validation')

    def test_ci_discovers_unittest_suite_without_pytest_dependency(self):
        steps = self.jobs['validate']['steps']
        command = next(step['run'] for step in steps if step.get('name') == 'Unit tests')
        self.assertIn('python -m unittest discover -s scripts', command)
        self.assertNotIn('pytest', command)


if __name__ == '__main__':
    unittest.main(verbosity=2)
