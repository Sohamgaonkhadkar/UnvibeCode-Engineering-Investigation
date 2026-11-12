"""Prepare disposable, pinned go-redis A/B/C inputs without editing the checkout.

B binds the receiver at callback formation, then forwards the exact arguments.
C is an intentionally different no-op callback: an extraction negative control,
not a behavior-equivalent alternative. No hosted calls are made by this script.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

PIN = "5cba5e182946cf18a757718938bc43910e589466"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--work", type=Path, required=True)
    a = p.parse_args()
    repo = a.repo.resolve()
    git = ["git", "-c", "safe.directory="+repo.as_posix(), "-C", str(repo)]
    assert subprocess.check_output(git+["rev-parse", "HEAD"], text=True).strip() == PIN
    assert not subprocess.check_output(git+["status", "--porcelain"], text=True).strip()
    raw = subprocess.check_output(git+["archive", "HEAD"])
    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        for member in archive:
            if member.isfile():
                assert not Path(member.name).is_absolute() and ".." not in Path(member.name).parts
                files[member.name] = archive.extractfile(member).read()
    edits = [
        ("himport_cluster.go", "c.ForEachMaster", "ClusterClient", "himportForEach", "ctx context.Context, fn func(context.Context, *Client) error", "ctx, fn", 3),
        ("himport_cluster.go", "c.ForEachShard", "Ring", "himportForEach", "ctx context.Context, fn func(context.Context, *Client) error", "ctx, fn", 3),
        ("autopipeline_cluster_fd.go", "cc.processPipelineRetries", "ClusterClient", "func(context.Context, []Cmder, int) error", "ctx context.Context, cmds []Cmder, retries int", "ctx, cmds, retries", 1),
        ("multidb.go", "core.processPipeline", "multidbCore", "func(context.Context, []Cmder) error", "ctx context.Context, cmds []Cmder", "ctx, cmds", 1),
    ]
    result = {"repository":"https://github.com/redis/go-redis", "commit":PIN,
              "input_archive_sha256":digest(raw), "states":{}, "edits":[]}
    variants = {k:dict(files) for k in ("A", "B", "C")}
    for file, old, owner, returns, params, args, count in edits:
        # Avoid matching the longer core.processPipelineRetries selector.
        import re
        pattern = re.escape(old)+r"(?![A-Za-z0-9_])"
        symbol = old.split(".")[1]
        receiver = old.split(".")[0]
        wrapper = f"func(receiver *{owner}) {returns} {{ return func({params}) error {{ return receiver.{symbol}({args}) }} }}({receiver})"
        negative = f"func(receiver *{owner}) {returns} {{ return func({params}) error {{ return nil }} }}({receiver})"
        original = files[file].decode("utf-8")
        assert len(re.findall(pattern, original)) == count
        for state, value in (("B",wrapper), ("C",negative)):
            text = variants[state][file].decode("utf-8")
            text, n = re.subn(pattern, lambda _:value, text)
            assert n == count
            variants[state][file] = text.encode()
        result["edits"].append({"file":file,"selector":old,"count":count,"wrapper":wrapper,"negative":negative})
    for state, contents in variants.items():
        target = a.work/state
        assert not target.exists(), "Choose a fresh work directory"
        for file, data in contents.items():
            output = target/file
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(data)
        changed = [f for f in files if files[f] != contents[f]]
        assert len(changed) == (0 if state=="A" else 3)
        result["states"][state] = {"changed_files":changed,"files":len(contents),
            "source_hashes":{f:digest(v) for f,v in contents.items() if f.endswith(".go")},
            "go_mod_sha256":digest(contents["go.mod"])}
    result["boundaries"] = ["Eight original selector occurrences in three files; single-line edits preserve target definition coordinates.",
        "B freezes each pointer receiver at formation; no function runs until invocation.",
        "C changes behavior deliberately and is used only as a negative extraction control.",
        "The 0.4.0 uploader omits go.mod in every state; same-package targets isolate this from #662."]
    (a.work/"inputs.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("Prepared pinned A/B/C copies: 8 selector changes in B/C; original checkout unchanged")


if __name__ == "__main__":
    main()
