#!/usr/bin/env python3
"""Read-only local validation. Never contacts a Kubernetes cluster.

--helm fetches pinned upstream charts and renders every cluster overlay.
Use TMPDIR for all temporary chart/config files. No user's Helm config is used.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[1]


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f'duplicate YAML key: {key}')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)
# Prometheus CRD CEL enums include a bare '=' scalar (YAML 1.1 value tag).
UniqueLoader.add_constructor('tag:yaml.org,2002:value', lambda loader, node: loader.construct_scalar(node))


def documents(text):
    return [d for d in yaml.load_all(text, Loader=UniqueLoader) if d is not None]


def run(args, env=None):
    result = subprocess.run(args, cwd=ROOT, env=env, text=True, capture_output=True, timeout=180)
    if result.returncode:
        raise RuntimeError(f'{" ".join(map(str, args))}\n{result.stdout}\n{result.stderr}')
    return result.stdout


def identity(obj):
    meta = obj.get('metadata', {})
    return obj['apiVersion'], obj['kind'], meta.get('namespace', ''), meta['name']


def check_build(objects, path):
    ids = [identity(o) for o in objects]
    assert len(ids) == len(set(ids)), f'duplicate objects in {path}'
    for obj in objects:
        kind, spec = obj['kind'], obj.get('spec', {})
        if kind == 'Secret':
            assert not obj.get('data') and not obj.get('stringData'), f'plaintext secret in {path}'
        if kind == 'HelmRelease':
            namespace = obj['metadata']['namespace']
            assert 'values' not in spec, f'inline values in {path}'
            for ref in spec['valuesFrom']:
                found = [x for x in objects if x['kind'] == ref['kind'] and x['metadata']['name'] == ref['name'] and x['metadata'].get('namespace') == namespace]
                assert len(found) == 1, f'missing values ConfigMap: {path}: {ref}'
                assert ref.get('valuesKey', 'values.yaml') in found[0]['data']
                documents(found[0]['data']['values.yaml'])
                assert found[0]['metadata']['labels']['reconcile.fluxcd.io/watch'] == 'Enabled'
            ref = spec.get('chartRef') or spec['chart']['spec']['sourceRef']
            assert not ref.get('namespace') or ref['namespace'] == namespace
            sources = [x for x in objects if x['kind'] == ref['kind'] and x['metadata']['name'] == ref['name'] and x['metadata']['namespace'] == namespace]
            assert len(sources) == 1, f'missing Helm source in {path}'
            version = sources[0]['spec']['ref']['tag'] if 'chartRef' in spec else spec['chart']['spec']['version']
            assert re.fullmatch(r'v?\d+\.\d+\.\d+(?:[-+][\w.-]+)?', version), f'unpinned chart: {path}'
            assert spec['install']['remediation']['retries'] in range(1, 6)


def check_cluster(objects, path):
    nodes = {o['metadata']['name']: o for o in objects if o['kind'] == 'Kustomization' and o['apiVersion'].startswith('kustomize.toolkit.fluxcd.io/')}
    graph = {}
    for name, obj in nodes.items():
        spec = obj['spec']
        target = (ROOT / spec['path']).resolve()
        assert target.is_relative_to(ROOT) and target.is_dir(), f'bad Flux path: {name}'
        assert spec['sourceRef'] == {'kind': 'GitRepository', 'name': 'flux-system'}
        assert spec.get('wait') is True
        assert spec.get('serviceAccountName') == 'kustomize-controller'
        assert spec.get('deletionPolicy') == 'Orphan'
        graph[name] = [d['name'] for d in spec.get('dependsOn', [])]
        assert all(d in nodes for d in graph[name]), f'missing dependency: {name}'
    assert nodes, f'empty cluster: {path}'
    visiting, visited = set(), set()

    def visit(name):
        assert name not in visiting, f'dependency cycle at {name}'
        if name in visited:
            return
        visiting.add(name)
        for dep in graph[name]:
            visit(dep)
        visiting.remove(name)
        visited.add(name)

    for name in graph:
        visit(name)


def render_chart(name, app_builds, tmp):
    sample = app_builds[0][1]
    hr = next(x for x in sample if x['kind'] == 'HelmRelease')
    spec = hr['spec']
    source = next(x for x in sample if x['kind'] in ('HelmRepository', 'OCIRepository'))
    work = tmp / name
    work.mkdir()
    env = os.environ.copy()
    env.update(HELM_REPOSITORY_CONFIG=str(work / 'repositories.yaml'), HELM_REPOSITORY_CACHE=str(work / 'repository'), HELM_REGISTRY_CONFIG=str(work / 'registry.json'), HELM_CACHE_HOME=str(work / 'cache'), HELM_CONFIG_HOME=str(work / 'config'), HELM_DATA_HOME=str(work / 'data'))
    if source['kind'] == 'OCIRepository':
        version = source['spec']['ref']['tag']
        args = [source['spec']['url'], '--version', version]
    else:
        chart = spec['chart']['spec']
        version = chart['version']
        args = [chart['chart'], '--repo', source['spec']['url'], '--version', version]
    run(['helm', 'pull', *args, '--destination', str(work)], env)
    packages = list(work.glob('*.tgz'))
    assert len(packages) == 1, f'unexpected chart archives: {name}'
    count = 0
    for cluster, objects in app_builds:
        hr = next(x for x in objects if x['kind'] == 'HelmRelease')
        cmd = ['helm', 'template', hr['spec']['releaseName'], str(packages[0]), '--namespace', hr['metadata']['namespace'], '--kube-version', '1.34.0', '--include-crds']
        for idx, ref in enumerate(hr['spec']['valuesFrom']):
            cm = next(x for x in objects if x['kind'] == 'ConfigMap' and x['metadata']['name'] == ref['name'])
            values = work / f'{cluster}-{idx}.yaml'
            values.write_text(cm['data']['values.yaml'])
            cmd += ['--values', str(values)]
        output = run(cmd, env)
        rendered = documents(output)
        assert rendered, f'empty chart render: {cluster}/{name}'
        # Helm's output can contain generated credentials. Never persist or print it.
        count += len(rendered)
        if name == 'alloy':
            roles = [o for o in rendered if o['kind'] == 'ClusterRole']
            assert any('pods/log' in rule.get('resources', []) and 'get' in rule.get('verbs', []) for o in roles for rule in o.get('rules', [])), 'Alloy lacks pod log RBAC'
    return f'PASS helm {name}@{version}: {len(app_builds)} overlays, {count} objects'


def check_instance(obj, cluster):
    assert obj['apiVersion'] == 'fluxcd.controlplane.io/v1' and obj['kind'] == 'FluxInstance'
    assert obj['metadata']['name'] == 'flux' and obj['metadata']['namespace'] == 'flux-system'
    spec = obj['spec']
    assert 'source-watcher' in spec['components']
    assert spec['sync']['path'] == f'clusters/{cluster}'
    assert spec['sync']['kind'] == 'GitRepository'
    assert 'pullSecret' not in spec['sync'], 'public seed must not require private Git credentials'
    assert re.fullmatch(r'\d+\.\d+\.\d+', spec['distribution']['version']), 'pin the Flux distribution version'
    assert spec['cluster']['networkPolicy'] is True


def check_registrations(objects, projects):
    for obj in objects:
        assert obj['kind'] == 'Application' and obj['apiVersion'] == 'argoproj.io/v1alpha1', 'tenant directories may contain only Argo Applications'
        assert obj['metadata']['namespace'] == 'argocd', 'Application must live in argocd'
        assert not obj['metadata'].get('finalizers'), 'cascading app deletion requires a separate reviewed policy'
        spec = obj['spec']
        assert spec['project'] != 'default' and spec['project'] in projects, 'unknown or default AppProject'
        project = projects[spec['project']]['spec']
        assert spec['destination'] in project['destinations'], 'destination is outside team project'
        sources = spec.get('sources', [spec.get('source', {})])
        assert all(s['repoURL'] in project['sourceRepos'] for s in sources), 'repository is outside team project'
        assert 'CreateNamespace=true' not in spec.get('syncPolicy', {}).get('syncOptions', []), 'namespaces belong to platform'


def build_catalog():
    """Exercise every catalog toggle through the actual environment overlays."""
    import shutil
    parent = Path(os.environ.get('TMPDIR', str(ROOT / '.cache')))
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='infra-catalog-', dir=parent) as tmp:
        controllers = Path(tmp) / 'controllers'
        shutil.copytree(ROOT / 'infrastructure/controllers', controllers)
        base = controllers / 'base'
        index = documents((base / 'kustomization.yaml').read_text())[0]
        index['resources'] = ['namespaces'] + sorted(p.name for p in base.iterdir() if (p / 'helmrelease.yaml').exists())
        (base / 'kustomization.yaml').write_text(yaml.safe_dump(index, sort_keys=False))
        result = {}
        for cluster in ('staging', 'prod'):
            objects = documents(run(['kustomize', 'build', str(controllers / cluster)]))
            check_build(objects, cluster)
            result[cluster] = objects
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--helm', action='store_true', help='download and render every pinned chart (network required)')
    args = parser.parse_args()
    for path in ROOT.rglob('*.yaml'):
        if not any(p in path.parts for p in ('.cache', '.venv')):
            documents(path.read_text())
    json.loads((ROOT / 'renovate.json').read_text())
    builds = {}
    for path in sorted(ROOT.rglob('kustomization.yaml')):
        if any(p in path.parts for p in ('.cache', '.venv')):
            continue
        objects = documents(run(['kustomize', 'build', str(path.parent)]))
        check_build(objects, path)
        builds[path.parent.relative_to(ROOT)] = objects
    for cluster in ('staging', 'prod'):
        path = Path('clusters') / cluster
        check_cluster(builds[path], path)
        check_instance(next(o for o in builds[path] if o['kind'] == 'FluxInstance'), cluster)
    catalog = build_catalog()
    print(f'PASS YAML, refs, pins, FluxInstance, dependency graph and tenant contracts; {len(builds)} Kustomize builds + 2 full-catalog builds')
    if args.helm:
        parent = os.environ.get('TMPDIR', str(ROOT / '.cache'))
        Path(parent).mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='infra-helm-', dir=parent) as tmpdir:
            groups = {}
            for cluster, objects in catalog.items():
                for hr in (o for o in objects if o['kind'] == 'HelmRelease'):
                    name = hr['metadata']['name']
                    selected = [hr] + [o for o in objects if o['metadata'].get('namespace') == hr['metadata']['namespace'] and o['kind'] in ('ConfigMap', 'HelmRepository', 'OCIRepository') and (o['metadata']['name'] == name or o['metadata']['name'].startswith(name + '-'))]
                    groups.setdefault(name, []).append((cluster, selected))
            failures = []
            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = {pool.submit(render_chart, name, group, Path(tmpdir)): name for name, group in groups.items()}
                for future in as_completed(futures):
                    try:
                        print(future.result(), flush=True)
                    except Exception as exc:
                        failures.append(futures[future])
                        print(f'FAIL {futures[future]}: {exc}', file=sys.stderr, flush=True)
            assert not failures, f'chart validation failed: {", ".join(failures)}'
            print(f'PASS {len(groups)} pinned charts, {sum(map(len, groups.values()))} cluster chart renders')


if __name__ == '__main__':
    try:
        main()
    except (AssertionError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        sys.exit(1)
