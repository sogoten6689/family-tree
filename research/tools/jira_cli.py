"""Công cụ dòng lệnh nhỏ để đọc/ghi Jira Cloud (giapha.atlassian.net, project SCRUM) qua REST API.

Khoá đọc từ biến môi trường (nạp từ .env.local, đã bị gitignore):
  JIRA_EMAIL, JIRA_API_TOKEN, JIRA_SITE (mặc định https://giapha.atlassian.net), JIRA_PROJECT (mặc định SCRUM)

Lệnh đọc chạy thẳng; lệnh ghi (comment, move) chỉ chạy khi có --yes.
  python research/tools/jira_cli.py whoami
  python research/tools/jira_cli.py list [--jql "..."]
  python research/tools/jira_cli.py get SCRUM-1
  python research/tools/jira_cli.py comment SCRUM-1 "nội dung" --yes
  python research/tools/jira_cli.py move SCRUM-1 "Done" --yes
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

SITE = os.environ.get("JIRA_SITE", "https://giapha.atlassian.net").rstrip("/")
PROJECT = os.environ.get("JIRA_PROJECT", "SCRUM")


def _request(method: str, path: str, body: dict | None = None) -> dict:
    email, token = os.environ.get("JIRA_EMAIL"), os.environ.get("JIRA_API_TOKEN")
    if not email or not token:
        sys.exit("Thiếu JIRA_EMAIL hoặc JIRA_API_TOKEN (đặt trong .env.local rồi `set -a; source .env.local; set +a`).")
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    req = urllib.request.Request(
        SITE + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={"Authorization": f"Basic {auth}", "Accept": "application/json", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as error:
        sys.exit(f"HTTP {error.code}: {error.read().decode(errors='replace')[:300]}")
    return json.loads(raw) if raw else {}


def _adf(text: str) -> dict:
    return {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]}


def _plain(node) -> str:
    if isinstance(node, dict):
        return node.get("text", "") + "".join(_plain(c) for c in node.get("content", []))
    return ""


def _need_yes(args) -> None:
    if not args.yes:
        sys.exit("Lệnh ghi lên Jira cần --yes (nội dung hiển thị cho cả nhóm).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("whoami")
    p = sub.add_parser("list"); p.add_argument("--jql", default=f"project = {PROJECT} ORDER BY created DESC")
    p = sub.add_parser("get"); p.add_argument("key")
    p = sub.add_parser("comment"); p.add_argument("key"); p.add_argument("text"); p.add_argument("--yes", action="store_true")
    p = sub.add_parser("move"); p.add_argument("key"); p.add_argument("status"); p.add_argument("--yes", action="store_true")
    args = parser.parse_args()

    if args.cmd == "whoami":
        me = _request("GET", "/rest/api/3/myself")
        print(f"{me.get('displayName')} <{me.get('emailAddress')}> — {SITE}")
    elif args.cmd == "list":
        data = _request("POST", "/rest/api/3/search/jql", {"jql": args.jql, "fields": ["summary", "status", "assignee", "issuetype"], "maxResults": 100})
        for issue in data.get("issues", []):
            f = issue["fields"]
            who = (f.get("assignee") or {}).get("displayName", "-")
            print(f"{issue['key']:10} [{f['status']['name']}] {f['summary']}  ({who})")
    elif args.cmd == "get":
        issue = _request("GET", f"/rest/api/3/issue/{args.key}?fields=summary,status,description,assignee,comment")
        f = issue["fields"]
        print(f"{issue['key']} [{f['status']['name']}] {f['summary']}")
        print(_plain(f.get("description")) or "(không có mô tả)")
        for c in f.get("comment", {}).get("comments", []):
            print(f"-- {c['author']['displayName']}: {_plain(c['body'])}")
    elif args.cmd == "comment":
        _need_yes(args)
        _request("POST", f"/rest/api/3/issue/{args.key}/comment", {"body": _adf(args.text)})
        print("đã bình luận")
    elif args.cmd == "move":
        _need_yes(args)
        transitions = _request("GET", f"/rest/api/3/issue/{args.key}/transitions")["transitions"]
        match = [t for t in transitions if t["name"].lower() == args.status.lower()]
        if not match:
            sys.exit("Không có trạng thái này; có: " + ", ".join(t["name"] for t in transitions))
        _request("POST", f"/rest/api/3/issue/{args.key}/transitions", {"transition": {"id": match[0]["id"]}})
        print("đã chuyển trạng thái")


if __name__ == "__main__":
    main()
