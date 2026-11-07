"""Diagnostic reference correction; modifies a loaded engine in memory only."""
import inspect
import textwrap
from contextlib import contextmanager


@contextmanager
def corrected(engine):
    cls = engine.TreeSitterAstAdapter
    original = cls._collect_go_usages
    source = textwrap.dedent(inspect.getsource(original))
    anchor = '            local_env.update(parameter_types(child_by_field_name(node, "parameters")))\n'
    assert source.count(anchor) == 1, "Unexpected engine source; refusing to patch"
    source = source.replace(anchor, anchor + '            local_env.update(parameter_types(child_by_field_name(node, "result")))\n')
    namespace = {}
    exec(compile(source, "<named-result-reference>", "exec"), engine.__dict__, namespace)
    cls._collect_go_usages = namespace['_collect_go_usages']
    try:
        yield
    finally:
        cls._collect_go_usages = original
