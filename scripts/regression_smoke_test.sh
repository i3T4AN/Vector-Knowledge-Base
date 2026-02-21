#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
WORKDIR="$(mktemp -d /tmp/vkb_smoke.XXXXXX)"
ARTIFACTS="$WORKDIR/artifacts"
mkdir -p "$ARTIFACTS"

cleanup() {
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

say() { echo "[smoke] $*"; }
fail() { echo "[smoke][FAIL] $*" >&2; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "missing required command: $1"
}

require_cmd curl
require_cmd python3

api_get() {
  local path="$1"
  curl -fsS "${BASE_URL}${path}"
}

api_delete() {
  local path="$1"
  curl -fsS -X DELETE "${BASE_URL}${path}"
}

api_post_json() {
  local path="$1"
  local body="$2"
  curl -fsS -X POST "${BASE_URL}${path}" \
    -H "Content-Type: application/json" \
    -d "$body"
}

assert_py() {
  local msg="$1"
  local code="$2"
  python3 - <<PY || fail "$msg"
$code
PY
}

say "checking health"
health_json="$(api_get /health)" || fail "backend unreachable at ${BASE_URL}"
assert_py "health check failed" "import json; d=json.loads('''$health_json'''); assert d.get('status')=='healthy'"

say "checking allowed extensions"
ext_json="$(api_get /config/allowed-extensions)"
assert_py "allowed extensions missing .md" "import json; d=json.loads('''$ext_json'''); assert '.md' in d.get('extensions',[])"

say "resetting data"
api_delete /reset >"$ARTIFACTS/reset.json"

say "preparing duplicate-name fixtures"
mkdir -p "$WORKDIR/A" "$WORKDIR/B"
printf 'content from folder A\n' > "$WORKDIR/A/README.md"
printf 'content from folder B\n' > "$WORKDIR/B/README.md"

say "uploading A/README.md"
curl -fsS -X POST "${BASE_URL}/upload" \
  -F "file=@$WORKDIR/A/README.md" \
  -F "category=smoke" \
  -F "relative_path=A" > "$ARTIFACTS/upload_a.json"

say "uploading B/README.md"
curl -fsS -X POST "${BASE_URL}/upload" \
  -F "file=@$WORKDIR/B/README.md" \
  -F "category=smoke" \
  -F "relative_path=B" > "$ARTIFACTS/upload_b.json"

doc_a="$(python3 - <<PY
import json
with open('$ARTIFACTS/upload_a.json') as f:
    print(json.load(f)['document_id'])
PY
)"
doc_b="$(python3 - <<PY
import json
with open('$ARTIFACTS/upload_b.json') as f:
    print(json.load(f)['document_id'])
PY
)"

say "checking /documents"
api_get /documents > "$ARTIFACTS/documents.json"
assert_py "documents list does not contain two README.md entries" "
import json
with open('$ARTIFACTS/documents.json') as f:
    docs=json.load(f)
readmes=[d for d in docs if d.get('filename')=='README.md']
assert len(readmes)==2
ids={d.get('id') for d in readmes}
assert '$doc_a' in ids and '$doc_b' in ids
"

say "checking file retrieval by document_id"
content_a="$(curl -fsS "${BASE_URL}/files/content/README.md?document_id=${doc_a}" | tr -d '\r')"
content_b="$(curl -fsS "${BASE_URL}/files/content/README.md?document_id=${doc_b}" | tr -d '\r')"
[[ "$content_a" == "content from folder A" ]] || fail "content mismatch for doc A"
[[ "$content_b" == "content from folder B" ]] || fail "content mismatch for doc B"

say "checking folders and in-folder mappings"
api_get /folders > "$ARTIFACTS/folders.json"
api_get /files/in_folders > "$ARTIFACTS/files_in_folders.json"
assert_py "expected folders A and B or file mappings missing" "
import json
with open('$ARTIFACTS/folders.json') as f:
    folders=json.load(f)
names={f['name'] for f in folders}
assert 'A' in names and 'B' in names
with open('$ARTIFACTS/files_in_folders.json') as f:
    m=json.load(f)
all_docs={entry.get('document_id') for entries in m.values() for entry in entries}
assert '$doc_a' in all_docs and '$doc_b' in all_docs
"

say "search smoke test"
search_json="$(api_post_json /search '{"query":"folder A","limit":5,"filters":null,"cluster_filter":"all"}')"
assert_py "search returned no results" "import json; d=json.loads('''$search_json'''); assert d.get('count',0) >= 1"

say "creating folder + moving one file"
create_folder_json="$(api_post_json /folders '{"name":"Moved","parent_id":null}')"
folder_id="$(python3 - <<PY
import json
print(json.loads('''$create_folder_json''')['id'])
PY
)"
api_post_json /files/move "{\"document_id\":\"${doc_a}\",\"filename\":\"README.md\",\"folder_id\":\"${folder_id}\"}" > "$ARTIFACTS/move.json"
api_get /files/in_folders > "$ARTIFACTS/files_in_folders_after_move.json"
assert_py "move file did not persist mapping" "
import json
with open('$ARTIFACTS/files_in_folders_after_move.json') as f:
    m=json.load(f)
entries=m.get('$folder_id', [])
assert any(e.get('document_id')=='$doc_a' for e in entries)
"

say "export smoke test"
curl -fsS "${BASE_URL}/export" -o "$ARTIFACTS/export.zip"
assert_py "export zip missing expected readme names" "
import zipfile
with zipfile.ZipFile('$ARTIFACTS/export.zip') as z:
    names=z.namelist()
assert any(name.endswith('/README.md') or name=='README.md' for name in names)
"

say "mcp create-document smoke test"
mcp_json="$(api_post_json /mcp/create-document '{"filename":"mcp-note.md","content":"mcp smoke content","folder_id":null}')"
assert_py "mcp create-document failed" "import json; d=json.loads('''$mcp_json'''); assert d.get('status')=='success'"

say "cluster job smoke test"
cluster_start="$(api_post_json /api/cluster '{}')"
job_id="$(python3 - <<PY
import json
print(json.loads('''$cluster_start''')['job_id'])
PY
)"

for _ in $(seq 1 120); do
  job_json="$(api_get "/api/jobs/${job_id}")"
  job_status="$(python3 - <<PY
import json
print(json.loads('''$job_json''')['status'])
PY
)"
  if [[ "$job_status" == "completed" ]]; then
    break
  fi
  if [[ "$job_status" == "failed" ]]; then
    fail "cluster job failed: $job_json"
  fi
  sleep 1
done

[[ "$job_status" == "completed" ]] || fail "cluster job timed out"

say "delete one duplicate and verify remaining count"
api_delete "/documents/README.md" > "$ARTIFACTS/delete_readme.json"
api_get /documents > "$ARTIFACTS/documents_after_delete.json"
assert_py "delete did not reduce documents list" "
import json
with open('$ARTIFACTS/documents_after_delete.json') as f:
    docs=json.load(f)
assert len(docs) >= 1
"

say "smoke regression suite PASSED"
