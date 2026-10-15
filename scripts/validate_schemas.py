#!/usr/bin/env python3
"""Validate platform CRs against pinned operator and Flux CRDs; no cluster access.

Downloads the operator chart and Flux distribution using Helm/Flux CLI.
Does not print rendered chart data (which can contain generated secrets).
"""
import argparse
import os
from pathlib import Path
import re
import tempfile

import jsonschema
import validate as v


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operator-version', default='0.61.0')
    args = parser.parse_args()
    if not re.fullmatch(r'\d+\.\d+\.\d+', args.operator_version):
        parser.error('operator version must be an exact x.y.z chart version')
    parent = Path(os.environ.get('TMPDIR', str(v.ROOT / '.cache')))
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='infra-schemas-', dir=parent) as tmp:
        env = os.environ.copy()
        env.update(HELM_REPOSITORY_CONFIG=f'{tmp}/repositories.yaml', HELM_REPOSITORY_CACHE=f'{tmp}/repository', HELM_REGISTRY_CONFIG=f'{tmp}/registry.json', HELM_CACHE_HOME=f'{tmp}/cache', HELM_CONFIG_HOME=f'{tmp}/config', HELM_DATA_HOME=f'{tmp}/data')
        operator = v.documents(v.run(['helm', 'template', 'flux-operator', 'oci://ghcr.io/controlplaneio-fluxcd/charts/flux-operator', '--version', args.operator_version, '--namespace', 'flux-system', '--include-crds'], env))
        flux = v.documents(v.run(['flux', 'install', '--export', '--version=v2.8.3', '--components-extra=source-watcher']))
        schemas = {}
        for obj in operator + flux:
            if obj['kind'] != 'CustomResourceDefinition':
                continue
            for version in obj['spec']['versions']:
                if version.get('served'):
                    schemas[(obj['spec']['group'] + '/' + version['name'], obj['spec']['names']['kind'])] = version['schema']['openAPIV3Schema']
        # Fail rather than silently skipping the capabilities this platform promises.
        required = [('fluxcd.controlplane.io/v1', 'FluxInstance'), ('source.extensions.fluxcd.io/v1beta1', 'ArtifactGenerator'), ('source.toolkit.fluxcd.io/v1', 'ExternalArtifact'), ('source.toolkit.fluxcd.io/v1', 'Bucket')]
        for key in required:
            assert key in schemas, f'missing required served CRD: {key}'
        count = 0
        for path in sorted(v.ROOT.rglob('*.yaml')):
            if any(part in path.parts for part in ('.cache', '.venv')):
                continue
            for obj in v.documents(path.read_text()):
                if not isinstance(obj, dict):
                    continue
                key = (obj.get('apiVersion'), obj.get('kind'))
                if key not in schemas:
                    continue
                jsonschema.Draft7Validator(schemas[key]).validate(obj)
                count += 1
        print(f'PASS {count} custom resources against operator {args.operator_version} and Flux 2.8.3 CRDs (including ArtifactGenerator, ExternalArtifact consumer and Bucket)')


if __name__ == '__main__':
    main()
