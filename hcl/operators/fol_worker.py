"""Fixed-purpose bounded FOL worker. Only formula JSON is accepted on stdin.

This is not an arbitrary-code sandbox. It has no model, filesystem-path, command
or network operation in its input language. OS CPU/address-space limits and a
parent wall deadline bound solver work; no network-syscall isolation is claimed.
"""
import json
import sys


def main():
    try:
        data = json.loads(sys.stdin.buffer.read(262145))
        if (type(data) is not dict or set(data) != {'schema', 'readings', 'timeout_ms', 'cpu_seconds', 'memory_bytes'}
                or data['schema'] != 'hcl-fol-worker-1' or type(data['readings']) is not list
                or not 1 <= len(data['readings']) <= 64):
            raise ValueError('invalid worker request')
        for key, low, high in (('timeout_ms', 1, 2000), ('cpu_seconds', 1, 120),
                               ('memory_bytes', 128*1024*1024, 2*1024*1024*1024)):
            if type(data[key]) is not int or not low <= data[key] <= high:
                raise ValueError('invalid worker bound')
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_CPU, (data['cpu_seconds'], data['cpu_seconds']))
            resource.setrlimit(resource.RLIMIT_AS, (data['memory_bytes'], data['memory_bytes']))
        except (ImportError, AttributeError, OSError, ValueError):
            print(json.dumps({'fatal': 'RESOURCE_ISOLATION_UNAVAILABLE'}))
            return
        try:
            from hcl.argument_readings import classify_reading
            from hcl.quantified_logic import FormulaError
            import z3  # Existing pinned dependency, not installed or network-loaded here.
        except ImportError:
            print(json.dumps({'fatal': 'SOLVER_UNAVAILABLE'}))
            return
        rows = []
        for reading in data['readings']:
            if type(reading) is not dict or set(reading) != {'id', 'premises', 'conclusion'}:
                raise ValueError('invalid worker reading')
            try:
                result = classify_reading(reading['premises'], reading['conclusion'], data['timeout_ms'])
            except FormulaError:
                result = {'status': 'INVALID_FORMAL_INPUT', 'label': None}
            rows.append({'id': reading['id'], 'result': result})
        print(json.dumps({'schema': 'hcl-fol-worker-result-1', 'readings': rows,
                          'classification_batches_completed': len(rows), 'solver_checks_upper_bound': 15*len(rows),
                          'resource_limits_applied': True, 'solver_version': z3.get_version_string()}, allow_nan=False))
    except (MemoryError, RecursionError):
        print(json.dumps({'fatal': 'SOLVER_RESOURCE_EXHAUSTED'}))
    except Exception:
        # Do not print native exception payloads, source data or filesystem paths.
        print(json.dumps({'fatal': 'SOLVER_WORKER_FAILURE'}))


if __name__ == '__main__':
    main()
