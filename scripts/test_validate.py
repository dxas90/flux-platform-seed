#!/usr/bin/env python3
"""Exercise registration boundary and operator bootstrap without a cluster."""
import copy
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import validate as v


class ValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.controllers = v.documents(v.run(['kustomize', 'build', 'infrastructure/controllers/staging']))
        cls.cluster = v.documents(v.run(['kustomize', 'build', 'clusters/staging']))
        cls.app = v.documents((v.ROOT / 'examples/onboarding/application.yaml').read_text())
        cls.projects = {o['metadata']['name']: o for o in v.documents((v.ROOT / 'examples/onboarding/team-platform.yaml').read_text()) if o['kind'] == 'AppProject'}

    def test_valid_build(self):
        v.check_build(self.controllers, 'staging')
        v.check_cluster(self.cluster, 'staging')
        v.check_registrations(self.app, self.projects)

    def test_missing_values(self):
        changed = [o for o in self.controllers if o['metadata']['name'] != 'alloy-overrides']
        with self.assertRaisesRegex(AssertionError, 'missing values'):
            v.check_build(changed, 'staging')

    def test_cycle(self):
        changed = copy.deepcopy(self.cluster)
        next(o for o in changed if o['metadata']['name'] == 'infra-controllers')['spec']['dependsOn'] = [{'name': 'infra-configs'}]
        with self.assertRaisesRegex(AssertionError, 'cycle'):
            v.check_cluster(changed, 'staging')

    def test_infrastructure_rejects_unprivileged_service_account(self):
        changed = copy.deepcopy(self.cluster)
        next(o for o in changed if o['metadata']['name'] == 'infra-controllers')['spec']['serviceAccountName'] = 'unprivileged'
        with self.assertRaises(AssertionError):
            v.check_cluster(changed, 'staging')

    def test_default_project_rejected(self):
        changed = copy.deepcopy(self.app)
        changed[0]['spec']['project'] = 'default'
        with self.assertRaisesRegex(AssertionError, 'AppProject'):
            v.check_registrations(changed, self.projects)

    def test_infrastructure_namespace_rejected(self):
        changed = copy.deepcopy(self.app)
        changed[0]['spec']['destination']['namespace'] = 'flux-system'
        with self.assertRaisesRegex(AssertionError, 'destination'):
            v.check_registrations(changed, self.projects)

    def test_foreign_repo_rejected(self):
        changed = copy.deepcopy(self.app)
        changed[0]['spec']['source']['repoURL'] = 'https://example.invalid/unapproved'
        with self.assertRaisesRegex(AssertionError, 'repository'):
            v.check_registrations(changed, self.projects)

    def test_workload_registration_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'only Argo Applications'):
            v.check_registrations([{'apiVersion': 'v1', 'kind': 'Secret'}], self.projects)

    def test_duplicate_keys(self):
        with self.assertRaisesRegex(ValueError, 'duplicate YAML key'):
            v.documents('key: one\nkey: two\n')

    def test_operator_requires_confirmation(self):
        result = subprocess.run(['bash', str(v.ROOT / 'scripts/bootstrap.sh'), 'staging', 'fake-context'], env={'PATH': '/usr/bin:/bin'}, text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('CONFIRM_BOOTSTRAP', result.stderr)

    def test_missing_source_watcher(self):
        instance = copy.deepcopy(next(o for o in self.cluster if o['kind'] == 'FluxInstance'))
        instance['spec']['components'].remove('source-watcher')
        with self.assertRaises(AssertionError):
            v.check_instance(instance, 'staging')


if __name__ == '__main__':
    unittest.main(verbosity=2)
