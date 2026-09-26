# pyright: reportUninitializedInstanceVariable=false
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
ANNOUNCE = ROOT / "src" / "bin" / "pkg-announce"


class MatrixFixture:
    def __init__(self):
        self.sender = "@bot:example.invalid"
        self.alias = "#demo:example.invalid"
        self.room_id = "!room:example.invalid"
        self.token = "secret-fixture-token"
        self.encrypted = False
        self.joined = True
        self.power = True
        self.drop_next_put = False
        self.fail_event_get = False
        self.origin_server_ts = 1_700_000_000_123
        self.auth_error = {"errcode": "M_UNKNOWN_TOKEN"}
        self.whoami_value: Any = None
        self.directory_value: Any = None
        self.joined_value: Any = None
        self.power_status = 200
        self.power_value: Any = None
        self.encryption_status: Any = None
        self.encryption_value: Any = None
        self.messages_value: Any = None
        self.requests = []
        self.events = {}
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                del format, args

            def answer(self, status, value):
                body = json.dumps(value, separators=(",", ":")).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def authorized(self):
                return self.headers.get("Authorization") == f"Bearer {fixture.token}"

            def do_GET(self):
                fixture.requests.append(("GET", self.path, None))
                if not self.authorized():
                    self.answer(401, fixture.auth_error)
                    return
                path = urlsplit(self.path).path
                if path.endswith("/account/whoami"):
                    self.answer(200, fixture.whoami_value if fixture.whoami_value is not None else {"user_id": fixture.sender})
                elif "/directory/room/" in path:
                    self.answer(200, fixture.directory_value if fixture.directory_value is not None else {"room_id": fixture.room_id})
                elif path.endswith("/joined_members"):
                    joined = {fixture.sender: {}} if fixture.joined else {}
                    self.answer(200, fixture.joined_value if fixture.joined_value is not None else {"joined": joined})
                elif path.endswith("/state/m.room.power_levels"):
                    level = 100 if fixture.power else 0
                    value = fixture.power_value if fixture.power_value is not None else {"users": {fixture.sender: level}, "events": {"m.room.message": 50}}
                    self.answer(fixture.power_status, value)
                elif path.endswith("/state/m.room.encryption"):
                    if fixture.encryption_status is not None:
                        self.answer(fixture.encryption_status, fixture.encryption_value)
                    elif fixture.encrypted:
                        self.answer(200, {"algorithm": "m.megolm.v1.aes-sha2"})
                    else:
                        self.answer(404, {"errcode": "M_NOT_FOUND"})
                elif "/event/" in path:
                    if fixture.fail_event_get:
                        self.answer(503, {"errcode": "M_UNAVAILABLE"})
                        return
                    event_id = unquote(path.rsplit("/", 1)[-1])
                    event = fixture.events.get(event_id)
                    self.answer(200, event) if event else self.answer(404, {"errcode": "M_NOT_FOUND"})
                elif path.endswith("/messages"):
                    if fixture.messages_value is not None:
                        self.answer(200, fixture.messages_value)
                    else:
                        chunk = [
                            {"event_id": "$general", "origin_server_ts": fixture.origin_server_ts - 1000, "sender": "@other:example.invalid", "type": "m.room.message", "content": {"msgtype": "m.text", "body": "general room text"}}
                        ]
                        self.answer(200, {"chunk": chunk, "end": "next"})
                else:
                    self.answer(404, {"errcode": "M_NOT_FOUND"})

            def do_PUT(self):
                size = int(self.headers.get("Content-Length", "0"))
                content = json.loads(self.rfile.read(size))
                fixture.requests.append(("PUT", self.path, content))
                if not self.authorized():
                    self.answer(401, {"errcode": "M_UNKNOWN_TOKEN"})
                    return
                txn = unquote(urlsplit(self.path).path.rsplit("/", 1)[-1])
                event_id = f"$event-{txn}"
                fixture.events[event_id] = {
                    "event_id": event_id,
                    "room_id": fixture.room_id,
                    "sender": fixture.sender,
                    "type": "m.room.message",
                    "content": content,
                    "origin_server_ts": fixture.origin_server_ts,
                }
                if fixture.drop_next_put:
                    fixture.drop_next_put = False
                    self.connection.shutdown(2)
                    self.connection.close()
                    return
                self.answer(200, {"event_id": event_id})

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def homeserver(self):
        return f"http://127.0.0.1:{self.server.server_port}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    @property
    def puts(self):
        return [request for request in self.requests if request[0] == "PUT"]


class AnnounceTest(unittest.TestCase):
    temp: tempfile.TemporaryDirectory[str]
    root: Path
    matrix: MatrixFixture
    config: Path
    state: Path
    message: Path

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "project"
        self.root.mkdir()
        templates = Path(self.temp.name) / "git-templates"
        templates.mkdir()
        subprocess.run(["git", "init", "-q", f"--template={templates}"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=self.root, check=True)
        (self.root / "tracked").write_text("fixture\n")
        subprocess.run(["git", "add", "tracked"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "new: fixture"], cwd=self.root, check=True)
        subprocess.run(["git", "tag", "1.0.0"], cwd=self.root, check=True)
        self.matrix = MatrixFixture()
        self.config = Path(self.temp.name) / "config"
        self.state = Path(self.temp.name) / "state"
        self.message = Path(self.temp.name) / "message.txt"
        self.message.write_bytes("Release exact body\n".encode())
        self.write_project()
        self.write_account()

    def tearDown(self):
        self.matrix.close()
        self.temp.cleanup()

    def write_project(self, extra=""):
        package = self.root / ".package.d"
        package.mkdir(exist_ok=True)
        (package / "announcements.yaml").write_text(
            "announcements:\n"
            "  - name: demo\n"
            "    transport: matrix\n"
            f"    room: '{self.matrix.alias}'\n"
            f"    sender: '{self.matrix.sender}'\n"
            "    language: en\n"
            "    audience: users\n"
            "    changes-since: last-announcement\n"
            "    style: short\n" + extra
        )

    def write_account(self, token=None, sender=None, command=None):
        account_dir = self.config / "pkg"
        account_dir.mkdir(parents=True, exist_ok=True)
        token_file = Path(self.temp.name) / "token"
        token_file.write_text((token or self.matrix.token) + "\n")
        sender = sender or self.matrix.sender
        if command is None:
            credential = f"    token-file: '{token_file}'\n"
        else:
            credential = "    credential-command:\n" + "".join(f"      - '{part}'\n" for part in command)
        (account_dir / "announcements.yaml").write_text(
            "accounts:\n"
            f"  '{sender}':\n"
            f"    homeserver: '{self.matrix.homeserver}'\n" + credential
        )
        return token_file

    def invoke(self, *args, expect=0, cwd=None) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        env = os.environ.copy()
        env.update({"XDG_CONFIG_HOME": str(self.config), "XDG_STATE_HOME": str(self.state)})
        proc = subprocess.run(
            [str(ANNOUNCE), *map(str, args)], cwd=cwd or self.root, env=env,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.assertEqual(expect, proc.returncode, proc.stderr)
        return proc, json.loads(proc.stdout) if proc.stdout else {}

    def preview(self, release="1.0.0"):
        _, result = self.invoke("check", "--target", "demo", "--draft", self.message, "--release", release)
        return result

    def send(self, digest, expect=0, release="1.0.0"):
        return self.invoke("send", "--target", "demo", "--message", self.message,
                        "--release", release, "--approved-sha256", digest, expect=expect)

    def test_project_schema_rejections(self):
        self.write_project("    unknown: value\n")
        proc, _ = self.invoke("check", expect=2)
        self.assertIn("unknown key 'unknown'", proc.stderr)
        self.assertNotIn(self.matrix.token, proc.stderr)
        self.write_project()
        with (self.root / ".package.d" / "announcements.yaml").open("a") as stream:
            stream.write((self.root / ".package.d" / "announcements.yaml").read_text().split("announcements:\n", 1)[1])
        proc, _ = self.invoke("check", expect=2)
        self.assertIn("duplicate announcement name", proc.stderr)
        self.write_project()
        metadata = self.root / ".package.d" / "announcements.yaml"
        metadata.write_text(metadata.read_text().replace("transport: matrix", "transport: smtp"))
        proc, _ = self.invoke("check", expect=2)
        self.assertIn("unsupported transport", proc.stderr)
        self.write_project()
        metadata.write_text(metadata.read_text().replace("language: en", "language: [en]"))
        proc, _ = self.invoke("check", expect=2)
        self.assertIn("must be a non-empty string", proc.stderr)

    def test_matrix_identifiers_rejected_before_credentials(self):
        metadata = self.root / ".package.d" / "announcements.yaml"
        self.write_project()
        metadata.write_text(metadata.read_text().replace("#demo:example.invalid", "demo room"))
        (self.config / "pkg" / "announcements.yaml").write_text("SENTINEL_LOCAL_SECRET: [\n")
        proc, _ = self.invoke("check", expect=2)
        self.assertIn("room", proc.stderr)
        self.assertNotIn("SENTINEL_LOCAL_SECRET", proc.stderr)
        self.write_project()
        metadata.write_text(metadata.read_text().replace("@bot:example.invalid", "bot user"))
        proc, _ = self.invoke("check", expect=2)
        self.assertIn("sender", proc.stderr)
        self.assertNotIn("SENTINEL_LOCAL_SECRET", proc.stderr)

    def test_target_selection(self):
        _, result = self.invoke("check")
        self.assertEqual(["demo"], [item["target"] for item in result["targets"]])
        proc, _ = self.invoke("context", "--target", "missing", expect=2)
        self.assertIn("unknown announcement target", proc.stderr)

    def test_account_schema_and_transport_policy(self):
        config = self.config / "pkg" / "announcements.yaml"
        config.write_text("accounts:\n  '@bot:example.invalid':\n    homeserver: 'http://example.invalid'\n    token-file: '/nope'\n")
        proc, _ = self.invoke("check", expect=2)
        self.assertIn("HTTPS", proc.stderr)
        self.write_account(command=["/bin/sh", "-c", "printf unsafe"])
        proc, _ = self.invoke("check", expect=2)
        self.assertIn("shell interpreters are not allowed", proc.stderr)

    def test_non_ascii_and_command_decode_credentials_are_sanitized(self):
        for bad_token in ("sécret", "bad token", "bad\ttoken"):
            self.write_account(token=bad_token)
            proc, _ = self.invoke("check", expect=2)
            self.assertIn("invalid token", proc.stderr)
            self.assertNotIn(bad_token, proc.stderr)
        token_file = Path(self.temp.name) / "token"
        token_file.write_bytes(b"valid\xfftoken")
        proc, _ = self.invoke("check", expect=2)
        self.assertIn("unreadable", proc.stderr)
        command = [sys.executable, "-c", "import sys;sys.stdout.buffer.write(bytes([255]))"]
        self.write_account(command=command)
        proc, _ = self.invoke("check", expect=2)
        self.assertEqual("Error: credential-command returned invalid output\n", proc.stderr)

    def test_credential_failures_do_not_leak_or_write_state(self):
        token_file = self.write_account(token="revoked-secret")
        proc, _ = self.invoke("check", expect=3)
        self.assertNotIn("revoked-secret", proc.stderr)
        self.assertFalse(self.state.exists())
        token_file.unlink()
        proc, _ = self.invoke("check", expect=2)
        self.assertNotIn("revoked-secret", proc.stderr)
        self.assertFalse(self.state.exists())
        self.write_account(sender="@wrong:example.invalid")
        proc, _ = self.invoke("check", expect=2)
        self.assertIn("no local account", proc.stderr)
        self.write_account()
        self.matrix.sender = "@different:example.invalid"
        proc, _ = self.invoke("check", expect=3)
        self.assertIn("different Matrix user", proc.stderr)

    def test_readiness_rejections_never_put(self):
        for attr, value, text in (("joined", False, "not joined"), ("power", False, "power"), ("encrypted", True, "encrypted")):
            setattr(self.matrix, attr, value)
            proc, _ = self.invoke("check", expect=3)
            self.assertIn(text, proc.stderr)
            self.assertEqual([], self.matrix.puts)
            setattr(self.matrix, attr, not value)

    def test_matrix_errors_and_malformed_state_are_sanitized(self):
        self.write_account(token="wrong-token")
        self.matrix.auth_error = {"errcode": "SENTINEL_SERVER_SECRET"}
        proc, _ = self.invoke("check", expect=3)
        self.assertEqual("Error: Matrix returned HTTP 401\n", proc.stderr)
        self.assertNotIn("SENTINEL", proc.stderr)
        self.write_account()
        cases = [
            ("whoami_value", [], "malformed"),
            ("joined_value", {"joined": []}, "joined"),
            ("power_value", {"users": [], "events": {}}, "power"),
            ("power_value", {"users": {self.matrix.sender: True}, "events": {"m.room.message": 0}}, "power"),
            ("power_value", {"users": {self.matrix.sender: 100}, "events": {"m.room.message": "50"}}, "power"),
        ]
        for attr, value, text in cases:
            setattr(self.matrix, attr, value)
            proc, _ = self.invoke("check", expect=3)
            self.assertIn(text, proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)
            setattr(self.matrix, attr, None)
        self.matrix.power_status = 404
        self.matrix.power_value = {"errcode": "M_FORBIDDEN"}
        proc, _ = self.invoke("check", expect=3)
        self.assertIn("power", proc.stderr)
        self.matrix.power_status = 200
        self.matrix.power_value = None
        self.matrix.encryption_status = 404
        self.matrix.encryption_value = {"errcode": "M_FORBIDDEN"}
        proc, _ = self.invoke("check", expect=3)
        self.assertIn("unencrypted", proc.stderr)

    def test_preview_digest_and_drift_rejections(self):
        preview = self.preview()
        self.assertEqual(self.message.read_text(), preview["preview"]["body"])
        self.assertEqual(64, len(preview["approved_sha256"]))
        self.message.write_bytes(b"changed\n")
        self.send(preview["approved_sha256"], expect=4)
        self.assertEqual([], self.matrix.puts)
        self.message.write_bytes(b"Release exact body\n")
        preview = self.preview()
        self.matrix.room_id = "!retargeted:example.invalid"
        self.send(preview["approved_sha256"], expect=4)
        self.assertEqual([], self.matrix.puts)
        self.matrix.room_id = "!room:example.invalid"
        preview = self.preview()
        (self.root / "second").write_text("second\n")
        subprocess.run(["git", "add", "second"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "chg: second"], cwd=self.root, check=True)
        subprocess.run(["git", "tag", "-f", "1.0.0"], cwd=self.root, check=True,
                       stdout=subprocess.DEVNULL)
        self.send(preview["approved_sha256"], expect=4)
        self.assertEqual([], self.matrix.puts)

    def test_release_tag_and_project_origin_are_safe(self):
        proc, _ = self.invoke("check", "--target", "demo", "--draft", self.message,
                              "--release", "1.0.0^{commit}", expect=2)
        self.assertIn("invalid release tag", proc.stderr)
        subprocess.run(["git", "remote", "add", "origin", "https://user:SENTINEL@example.invalid/project.git?x=1"], cwd=self.root, check=True)
        proc, _ = self.invoke("check", "--target", "demo", "--draft", self.message,
                              "--release", "1.0.0", expect=2)
        self.assertIn("remote", proc.stderr)
        self.assertNotIn("SENTINEL", proc.stdout + proc.stderr)

    def test_ssh_origin_normalizes_without_userinfo(self):
        subprocess.run(["git", "remote", "add", "origin", "git@example.invalid:org/project.git"], cwd=self.root, check=True)
        preview = self.preview()
        _, receipt = self.send(preview["approved_sha256"])
        self.assertEqual("https://example.invalid/org/project", receipt["identity"]["project"])
        self.assertNotIn("git@", json.dumps(receipt))

    def test_preview_send_and_verified_receipt(self):
        preview = self.preview()
        _, receipt = self.send(preview["approved_sha256"])
        self.assertEqual("complete", receipt["status"])
        self.assertEqual("Release exact body\n", self.matrix.puts[0][2]["body"])
        self.assertNotIn(self.matrix.token, json.dumps(receipt))
        self.assertEqual(self.matrix.origin_server_ts, receipt["origin_server_ts"])
        expected_time = datetime.fromtimestamp(self.matrix.origin_server_ts / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        self.assertEqual(expected_time, receipt["posted_at"])
        self.assertIn("matrix.to/#/", receipt["event_permalink"])
        self.assertEqual(1, receipt["receipt_version"])

    def test_verification_failure_preserves_event_pending(self):
        preview = self.preview()
        self.matrix.fail_event_get = True
        self.send(preview["approved_sha256"], expect=3)
        pending = list(self.state.rglob("pending.json"))
        self.assertEqual(1, len(pending))
        self.assertIn("event_id", json.loads(pending[0].read_text()))
        self.matrix.fail_event_get = False
        self.send(preview["approved_sha256"])
        self.assertEqual(1, len(self.matrix.puts))

    def test_duplicate_concurrent_and_dropped_response_deduplicate(self):
        preview = self.preview()
        self.matrix.drop_next_put = True
        self.send(preview["approved_sha256"], expect=3)
        self.send(preview["approved_sha256"])
        txns = [path.rsplit("/", 1)[-1] for _, path, _ in self.matrix.puts]
        self.assertEqual(1, len(set(txns)))
        self.send(preview["approved_sha256"])
        self.assertEqual(2, len(self.matrix.puts))

    def test_concurrent_sends_issue_one_matrix_put(self):
        subprocess.run(["git", "tag", "1.0.1"], cwd=self.root, check=True)
        preview = self.preview("1.0.1")
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(self.send, preview["approved_sha256"], 0, "1.0.1")
                for _ in range(2)
            ]
            results = [future.result()[1] for future in futures]
        self.assertEqual(["complete", "complete"], [item["status"] for item in results])
        self.assertEqual(1, len(self.matrix.puts))

    def test_pending_token_change_refuses_retry(self):
        preview = self.preview()
        self.matrix.drop_next_put = True
        self.send(preview["approved_sha256"], expect=3)
        before = len(self.matrix.puts)
        self.write_account(token="different-secret")
        self.send(preview["approved_sha256"], expect=4)
        self.assertEqual(before, len(self.matrix.puts))

    def test_completed_replay_ignores_pending_token_fingerprint(self):
        preview = self.preview()
        _, first = self.send(preview["approved_sha256"])
        puts = len(self.matrix.puts)
        self.matrix.token = "rotated-valid-token"
        self.write_account(token=self.matrix.token)
        pending = next(self.state.rglob("pending.json"))
        pending.write_text("malformed pending evidence")
        _, replay = self.send(preview["approved_sha256"])
        self.assertEqual(first["event_id"], replay["event_id"])
        self.assertEqual(puts, len(self.matrix.puts))
        self.assertTrue(any("/event/" in path for method, path, _ in self.matrix.requests if method == "GET"))

    def test_tampered_receipt_fails_closed(self):
        preview = self.preview()
        self.send(preview["approved_sha256"])
        complete = next(self.state.rglob("complete.json"))
        complete.write_text("{}")
        self.send(preview["approved_sha256"], expect=4)
        self.assertEqual("{}", complete.read_text())

    def test_context_receipt_is_project_scoped_and_fails_tampering(self):
        preview = self.preview()
        self.send(preview["approved_sha256"])
        other = Path(self.temp.name) / "other-project"
        other.mkdir()
        templates = Path(self.temp.name) / "other-templates"
        templates.mkdir()
        subprocess.run(["git", "init", "-q", f"--template={templates}"], cwd=other, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=other, check=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=other, check=True)
        (other / "tracked").write_text("other\n")
        (other / ".package.d").mkdir()
        (other / ".package.d" / "announcements.yaml").write_text((self.root / ".package.d" / "announcements.yaml").read_text())
        subprocess.run(["git", "add", "."], cwd=other, check=True)
        subprocess.run(["git", "commit", "-qm", "new: other"], cwd=other, check=True)
        subprocess.run(["git", "tag", "1.0.0"], cwd=other, check=True)
        _, context = self.invoke("context", "--target", "demo", cwd=other)
        self.assertEqual("room-fallback", context["source"])
        complete = next(self.state.rglob("complete.json"))
        receipt = json.loads(complete.read_text())
        receipt["digest"] = "0" * 64
        complete.write_text(json.dumps(receipt))
        proc, _ = self.invoke("context", "--target", "demo", expect=4)
        self.assertIn("receipt", proc.stderr)

    def test_context_receipt_rejects_alias_sender_version_and_room_drift(self):
        preview = self.preview()
        self.send(preview["approved_sha256"])
        complete = next(self.state.rglob("complete.json"))
        original = complete.read_text()
        for key, value in (("receipt_version", 999),):
            receipt = json.loads(original)
            receipt[key] = value
            complete.write_text(json.dumps(receipt))
            proc, _ = self.invoke("context", "--target", "demo", expect=4)
            self.assertIn("receipt", proc.stderr)
        complete.write_text(original)
        self.matrix.room_id = "!retargeted:example.invalid"
        proc, _ = self.invoke("context", "--target", "demo", expect=4)
        self.assertIn("receipt", proc.stderr)
        self.matrix.room_id = "!room:example.invalid"
        self.matrix.sender = "@replacement:example.invalid"
        self.write_project()
        self.write_account(sender=self.matrix.sender)
        proc, _ = self.invoke("context", "--target", "demo", expect=4)
        self.assertIn("receipt", proc.stderr)

    def test_context_verified_and_bounded_untrusted_fallback(self):
        _, fallback = self.invoke("context", "--target", "demo")
        self.assertFalse(fallback["trusted"])
        self.assertEqual("room-fallback", fallback["source"])
        self.assertEqual(self.matrix.origin_server_ts - 1000, fallback["messages"][0]["origin_server_ts"])
        self.assertFalse(fallback["messages"][0]["body_truncated"])
        self.assertTrue(fallback["text_is_untrusted"])
        long_body = "x" * 5000
        self.matrix.messages_value = {"chunk": [
            {"event_id": f"${index}", "origin_server_ts": self.matrix.origin_server_ts - index,
             "sender": "@other:example.invalid", "type": "m.room.message",
             "content": {"msgtype": "m.text", "body": long_body}}
            for index in range(30)
        ]}
        _, bounded = self.invoke("context", "--target", "demo")
        self.assertEqual(20, len(bounded["messages"]))
        self.assertEqual(4096, len(bounded["messages"][0]["body"]))
        self.assertTrue(bounded["messages"][0]["body_truncated"])
        preview = self.preview()
        self.send(preview["approved_sha256"])
        _, verified = self.invoke("context", "--target", "demo")
        self.assertFalse(verified["trusted"])
        self.assertTrue(verified["verified_origin"])
        self.assertTrue(verified["text_is_untrusted"])
        self.assertEqual("receipt", verified["source"])

    def test_context_orders_receipts_by_verified_matrix_timestamp(self):
        first = self.preview()
        self.send(first["approved_sha256"])
        subprocess.run(["git", "tag", "1.0.1"], cwd=self.root, check=True)
        self.matrix.origin_server_ts += 10_000
        second = self.preview("1.0.1")
        self.send(second["approved_sha256"], release="1.0.1")
        receipts = list(self.state.rglob("complete.json"))
        older = next(path for path in receipts if json.loads(path.read_text())["identity"]["release"] == "1.0.0")
        newer = next(path for path in receipts if json.loads(path.read_text())["identity"]["release"] == "1.0.1")
        os.utime(older, (2_000_000_000, 2_000_000_000))
        os.utime(newer, (1_000_000_000, 1_000_000_000))
        _, context = self.invoke("context", "--target", "demo")
        self.assertEqual("1.0.1", context["announcement"]["identity"]["release"])

    def test_context_authentication_failure_never_falls_back(self):
        self.write_account(token="wrong-token")
        proc, _ = self.invoke("context", "--target", "demo", expect=3)
        self.assertIn("HTTP 401", proc.stderr)
        self.assertFalse(self.state.exists())

    def test_context_refuses_state_symlinks_and_does_not_write_state(self):
        self.assertFalse(self.state.exists())
        self.invoke("context", "--target", "demo")
        self.assertFalse(self.state.exists())
        external = Path(self.temp.name) / "external-state"
        external.mkdir()
        self.state.symlink_to(external, target_is_directory=True)
        proc, _ = self.invoke("context", "--target", "demo", expect=4)
        self.assertIn("unsafe", proc.stderr)

    def test_context_refuses_symlinked_feature_state_ancestor(self):
        pkg_dir = self.state / "pkg"
        pkg_dir.mkdir(parents=True)
        external = Path(self.temp.name) / "external-announcements"
        external.mkdir()
        (pkg_dir / "announcements").symlink_to(external, target_is_directory=True)
        proc, _ = self.invoke("context", "--target", "demo", expect=4)
        self.assertIn("unsafe", proc.stderr)

    def test_send_keeps_existing_parent_modes_and_makes_private_feature_tree(self):
        self.state.mkdir(mode=0o755)
        pkg_dir = self.state / "pkg"
        pkg_dir.mkdir(mode=0o755)
        preview = self.preview()
        self.send(preview["approved_sha256"])
        self.assertEqual(0o755, self.state.stat().st_mode & 0o777)
        self.assertEqual(0o755, pkg_dir.stat().st_mode & 0o777)
        self.assertEqual(0o700, (pkg_dir / "announcements").stat().st_mode & 0o777)

    # ── Markdown rendering ──────────────────────────────────────────

    def test_markdown_draft_is_sent_with_its_html_rendering(self):
        self.message.write_text("**Bold** and `code`\n\n- one\n- two\n\n📦 https://e.invalid/x\n🔧 line\n")
        preview = self.preview()
        self.send(preview["approved_sha256"])
        self.assertEqual(
            {
                "msgtype": "m.text",
                "body": self.message.read_text(),
                "format": "org.matrix.custom.html",
                "formatted_body": (
                    "<p><strong>Bold</strong> and <code>code</code></p>\n"
                    "<ul>\n<li>one</li>\n<li>two</li>\n</ul>\n"
                    '<p>📦 <a href="https://e.invalid/x" class="uri">https://e.invalid/x</a><br />\n'
                    "🔧 line</p>"
                ),
            },
            self.matrix.puts[0][2],
        )
        self.assertEqual(self.matrix.puts[0][2], preview["preview"]["content"])

    def test_raw_html_in_draft_is_escaped_not_injected(self):
        self.message.write_text("<img src=x onerror=alert(1)> <b>x</b>\n")
        preview = self.preview()
        self.assertEqual(
            "<p>&lt;img src=x onerror=alert(1)&gt; &lt;b&gt;x&lt;/b&gt;</p>",
            preview["preview"]["content"]["formatted_body"],
        )

    def test_missing_pandoc_fails_before_any_matrix_write(self):
        bin_dir = Path(self.temp.name) / "no-pandoc-bin"
        bin_dir.mkdir()
        for tool in ("git", "yq", "python3", "bash", "dirname", "realpath", "mktemp", "rm"):
            found = subprocess.run(["bash", "-c", f"command -v {tool}"], text=True, stdout=subprocess.PIPE).stdout.strip()
            if found:
                (bin_dir / tool).symlink_to(found)
        env_path = os.environ["PATH"]
        os.environ["PATH"] = str(bin_dir)
        try:
            proc, _ = self.invoke("check", "--target", "demo", "--draft", self.message, "--release", "1.0.0", expect=2)
        finally:
            os.environ["PATH"] = env_path
        self.assertEqual("Error: announcement Markdown rendering requires pandoc\n", proc.stderr)
        self.assertEqual([], self.matrix.puts)

    def test_receipt_written_before_html_support_still_validates(self):
        _, receipt = self.send(self.preview()["approved_sha256"])
        legacy = json.loads(json.dumps(receipt))
        legacy["identity"]["content"] = {"msgtype": "m.text", "body": receipt["identity"]["content"]["body"]}
        encoded = json.dumps(legacy["identity"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        legacy["digest"] = hashlib.sha256(encoded.encode()).hexdigest()
        self.matrix.events[legacy["event_id"]]["content"] = legacy["identity"]["content"]
        next(self.state.rglob("complete.json")).write_text(json.dumps(legacy))
        _, context = self.invoke("context", "--target", "demo")
        self.assertEqual(("receipt", legacy["event_id"]), (context["source"], context["announcement"]["event_id"]))

    # ── --replace ──────────────────────────────────────────────────

    def replace_preview(self, expect=0):
        return self.invoke("check", "--target", "demo", "--draft", self.message,
                           "--release", "1.0.0", "--replace", expect=expect)

    def replace_send(self, digest, expect=0):
        return self.invoke("send", "--target", "demo", "--message", self.message,
                           "--release", "1.0.0", "--approved-sha256", digest,
                           "--replace", expect=expect)

    def test_replace_edits_the_original_announcement_in_place(self):
        original_preview = self.preview()
        _, original = self.send(original_preview["approved_sha256"])
        self.message.write_text("Corrected **body**\n")
        _, preview = self.replace_preview()
        self.assertEqual(original["event_id"], preview["preview"]["replaces"])
        _, receipt = self.replace_send(preview["approved_sha256"])
        self.assertEqual(
            {
                "msgtype": "m.text",
                "body": "* Corrected **body**\n",
                "format": "org.matrix.custom.html",
                "formatted_body": "* <p>Corrected <strong>body</strong></p>",
                "m.new_content": {
                    "msgtype": "m.text",
                    "body": "Corrected **body**\n",
                    "format": "org.matrix.custom.html",
                    "formatted_body": "<p>Corrected <strong>body</strong></p>",
                },
                "m.relates_to": {"rel_type": "m.replace", "event_id": original["event_id"]},
            },
            self.matrix.puts[-1][2],
        )
        self.assertEqual(("complete", original["event_id"]), (receipt["status"], receipt["identity"]["replaces"]))
        # The release's original receipt is left as it was.
        self.message.write_text("Release exact body\n")
        _, replay = self.send(original_preview["approved_sha256"])
        self.assertEqual(original, replay)

    def test_replace_is_retry_safe_and_every_edit_targets_the_original(self):
        _, original = self.send(self.preview()["approved_sha256"])
        self.message.write_text("First fix\n")
        _, first = self.replace_preview()
        self.replace_send(first["approved_sha256"])
        self.replace_send(first["approved_sha256"])
        self.assertEqual(2, len(self.matrix.puts))
        self.message.write_text("Second fix\n")
        _, second = self.replace_preview()
        self.replace_send(second["approved_sha256"])
        self.assertEqual(3, len(self.matrix.puts))
        self.assertEqual(original["event_id"], self.matrix.puts[-1][2]["m.relates_to"]["event_id"])

    def test_plain_approval_cannot_authorize_an_edit(self):
        self.send(self.preview()["approved_sha256"])
        self.message.write_text("Fix\n")
        proc, _ = self.replace_send(self.preview()["approved_sha256"], expect=4)
        self.assertIn("approved digest does not match", proc.stderr)
        self.assertEqual(1, len(self.matrix.puts))

    def test_replace_without_announcement_refuses(self):
        proc, _ = self.replace_preview(expect=2)
        self.assertEqual("Error: no completed announcement for release '1.0.0' to replace\n", proc.stderr)
        self.assertEqual([], self.matrix.puts)


if __name__ == "__main__":
    unittest.main()
