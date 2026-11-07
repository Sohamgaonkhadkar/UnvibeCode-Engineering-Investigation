"""Conservative reference correction, applied only to a loaded module in memory.

Resolve typed method values as symbol references, never direct invocations.
Unresolved selectors (including ordinary fields) remain unpromoted.
"""
import inspect
import textwrap
from contextlib import contextmanager


def replacement(engine, original, edits):
    source = textwrap.dedent(inspect.getsource(original))
    for anchor, value in edits:
        assert source.count(anchor) == 1, f'Unexpected source: {original.__name__}'
        source = source.replace(anchor, value)
    namespace = {}
    exec(compile(source, '<method-value-reference>', 'exec'), engine.__dict__, namespace)
    return namespace[original.__name__]


@contextmanager
def corrected(engine):
    adapter = engine.TreeSitterAstAdapter
    builder = engine.ShipReadyV2DeepGraphBuilder
    old_collect = adapter._collect_go_usages
    old_resolve = builder._resolve_go_usages
    collect = replacement(engine, old_collect, [(
        '        if node.type == "selector_expression":\n            package_selector(node, env, "value")',
        '''        if node.type == "selector_expression":
            operand = child_by_field_name(node, "operand")
            field = child_by_field_name(node, "field")
            if operand is not None and field is not None and operand.type == "identifier" and text(operand) in env:
                usages.append({
                    "kind": "method_reference", "receiver": text(operand),
                    "receiver_type": env.get(text(operand)), "symbol": text(field),
                    "context": "value", "line": line_range_from_ts_node(node)["start_line"],
                })
            else:
                package_selector(node, env, "value")''')])
    resolve = replacement(engine, old_resolve, [
        ('if kind == "method_call":', 'if kind in {"method_call", "method_reference"}:'),
        ('            if resolved is None:\n                if reason',
         '            if resolved is None:\n                if kind == "method_reference":\n                    continue\n                if reason'),
        ('            if problem is not None:\n                problem["receiver"]',
         '            if problem is not None:\n                if kind == "method_reference":\n                    continue\n                problem["receiver"]'),
        ('                "method_call",\n                symbol,\n                line,\n                "go_method_resolution",',
         '                "imports_symbol" if kind == "method_reference" else "method_call",\n                symbol,\n                line,\n                "go_method_reference" if kind == "method_reference" else "go_method_resolution",'),
        ('                "method_call",\n                owner=owner,',
         '                "go_method_value" if kind == "method_reference" else "method_call",\n                owner=owner,'),
    ])
    # Compile both replacements before changing either method.
    adapter._collect_go_usages = collect
    builder._resolve_go_usages = resolve
    try:
        yield
    finally:
        adapter._collect_go_usages = old_collect
        builder._resolve_go_usages = old_resolve
