"""Minimal Matrix client used by release announcements."""

import json
import re
import urllib.error
import urllib.parse
import urllib.request


KNOWN_ERRCODES = {
    "M_BAD_JSON",
    "M_FORBIDDEN",
    "M_INVALID_PARAM",
    "M_LIMIT_EXCEEDED",
    "M_NOT_FOUND",
    "M_NOT_JSON",
    "M_UNAUTHORIZED",
    "M_UNKNOWN_TOKEN",
    "M_UNAVAILABLE",
}
ROOM_ID_RE = re.compile(r"^![A-Za-z0-9._=+/\-]+:[A-Za-z0-9.-]+(?::[0-9]+)?$")


class MatrixError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        del req, fp, code, msg, headers, newurl
        return None


def _json_object(body):
    try:
        value = json.loads(body)
    except (UnicodeError, ValueError):
        raise MatrixError("Matrix returned invalid JSON") from None
    if not isinstance(value, dict):
        raise MatrixError("Matrix returned a malformed JSON object")
    return value


def _integer(value):
    return type(value) is int


class MatrixClient:
    def __init__(self, homeserver, token, timeout=8):
        self.homeserver = homeserver.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.opener = urllib.request.build_opener(NoRedirect())

    def request(self, method, path, payload=None, expected=(200,)):
        url = self.homeserver + path
        data = None
        headers = {"Authorization": "Bearer " + self.token, "Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        try:
            request = urllib.request.Request(url, data=data, headers=headers, method=method)
            with self.opener.open(request, timeout=self.timeout) as response:
                body = response.read(1024 * 1024 + 1)
                if len(body) > 1024 * 1024:
                    raise MatrixError("Matrix response exceeded the 1 MiB limit")
                if response.status not in expected:
                    raise MatrixError(f"Matrix returned HTTP {response.status}")
                return response.status, _json_object(body)
        except urllib.error.HTTPError as error:
            body = error.read(65537)
            if len(body) > 65536:
                value = None
            else:
                try:
                    value = _json_object(body)
                except MatrixError:
                    value = None
            if error.code in expected:
                if value is None:
                    raise MatrixError("Matrix returned malformed error JSON") from None
                return error.code, value
            errcode = value.get("errcode") if value is not None else None
            suffix = f" ({errcode})" if errcode in KNOWN_ERRCODES else ""
            raise MatrixError(f"Matrix returned HTTP {error.code}{suffix}") from None
        except MatrixError:
            raise
        except (OSError, UnicodeError, ValueError, urllib.error.URLError) as error:
            raise MatrixError(f"Matrix request failed: {error.__class__.__name__}") from None

    @staticmethod
    def quote(value):
        return urllib.parse.quote(value, safe="")

    def readiness(self, sender, alias):
        _, whoami = self.request("GET", "/_matrix/client/v3/account/whoami")
        user_id = whoami.get("user_id")
        if not isinstance(user_id, str):
            raise MatrixError("Matrix whoami response is malformed")
        if user_id != sender:
            raise MatrixError("credential belongs to a different Matrix user")
        _, resolved = self.request(
            "GET", "/_matrix/client/v3/directory/room/" + self.quote(alias)
        )
        room_id = resolved.get("room_id")
        if not isinstance(room_id, str) or not ROOM_ID_RE.fullmatch(room_id):
            raise MatrixError("room alias did not resolve to a valid room id")
        room = self.quote(room_id)
        _, members = self.request("GET", f"/_matrix/client/v3/rooms/{room}/joined_members")
        joined = members.get("joined")
        if not isinstance(joined, dict):
            raise MatrixError("Matrix joined-members state is malformed")
        if sender not in joined:
            raise MatrixError("configured sender is not joined to the resolved room")
        status, power = self.request(
            "GET", f"/_matrix/client/v3/rooms/{room}/state/m.room.power_levels",
            expected=(200, 404),
        )
        if status == 404:
            if power.get("errcode") != "M_NOT_FOUND":
                raise MatrixError("could not read Matrix message power state")
            power = {}
        users = power.get("users", {})
        events = power.get("events", {})
        if not isinstance(users, dict) or not isinstance(events, dict):
            raise MatrixError("Matrix power-level users/events maps are malformed")
        users_default = power.get("users_default", 0)
        events_default = power.get("events_default", 0)
        user_level = users.get(sender, users_default)
        required = events.get("m.room.message", events_default)
        if not all(_integer(value) for value in (users_default, events_default, user_level, required)):
            raise MatrixError("Matrix message power levels are malformed")
        if user_level < required:
            raise MatrixError("configured sender lacks power to send m.room.message")
        status, encryption = self.request(
            "GET", f"/_matrix/client/v3/rooms/{room}/state/m.room.encryption",
            expected=(200, 404),
        )
        if status == 200:
            raise MatrixError("encrypted rooms are not supported")
        if encryption.get("errcode") != "M_NOT_FOUND":
            raise MatrixError("could not prove that the room is unencrypted")
        return room_id

    def send(self, room_id, txn_id, content):
        room = self.quote(room_id)
        txn = self.quote(txn_id)
        _, response = self.request(
            "PUT", f"/_matrix/client/v3/rooms/{room}/send/m.room.message/{txn}", content
        )
        event_id = response.get("event_id")
        if (
            not isinstance(event_id, str)
            or not event_id.startswith("$")
            or any(ord(character) < 0x21 or ord(character) > 0x7e for character in event_id)
        ):
            raise MatrixError("Matrix send response omitted event_id")
        return event_id

    def event(self, room_id, event_id):
        room = self.quote(room_id)
        event = self.quote(event_id)
        _, response = self.request("GET", f"/_matrix/client/v3/rooms/{room}/event/{event}")
        return response

    def messages(self, room_id, limit=20):
        room = self.quote(room_id)
        query = urllib.parse.urlencode({"dir": "b", "limit": min(limit, 20)})
        _, response = self.request("GET", f"/_matrix/client/v3/rooms/{room}/messages?{query}")
        chunk = response.get("chunk")
        if not isinstance(chunk, list):
            raise MatrixError("Matrix messages response has invalid chunk")
        return chunk[:20]
