"""상류(upstream) 변경을 minions Teams(system-alert)로 알린다.

sync-upstream 워크플로가 fork main<-upstream 병합 후 변경이 있을 때 호출.
gh compare(BEFORE...AFTER) 결과(/tmp/compare.json)에서 커밋/변경파일/영향 carrier를
요약해 AlertMessage(asdict 형식)를 stdout으로 출력 → 워크플로가 Lambda
minions-supports-alert_messenger 로 invoke 한다.

usage: python3 upstream_alert.py <TEAMS_WEBHOOK_URL>
env: REPO, BEFORE, AFTER, COMPARE_FILE(기본 /tmp/compare.json)
"""
import json
import os
import sys

# 우리가 실제 사용하는 택배사(부분 문자열) — 변경 파일 경로 매칭용
OUR_CARRIERS = [
    "cjlogistics", "hanjin", "lotte", "logen", "epost", "kdexp", "cvsnet",
    "daesin", "chunil", "cway", "epantos", "goodstoluck", "homepick",
    "honam", "ilyang", "kunyoung", "slx", "yongma",
]


def main() -> None:
    url = sys.argv[1]
    repo = os.environ["REPO"]
    before = os.environ["BEFORE"]
    after = os.environ["AFTER"]
    compare_file = os.environ.get("COMPARE_FILE", "/tmp/compare.json")

    with open(compare_file, encoding="utf-8") as fh:
        compare = json.load(fh)

    commits = compare.get("commits", []) or []
    files = [f.get("filename", "") for f in (compare.get("files", []) or [])]
    affected = sorted({c for c in OUR_CARRIERS for fn in files if c in fn.lower()})
    recent_msgs = [
        (c.get("commit", {}).get("message", "") or "").splitlines()[0][:80]
        for c in commits[-8:]
    ]

    rows = [
        {"title": "커밋", "value": str(len(commits))},
        {"title": "변경 파일", "value": str(len(files))},
        {
            "title": "영향 가능 carrier",
            "value": ", ".join(affected) if affected else "carrier 어댑터 변경 없음(코어/기타)",
        },
    ]
    body = [
        {
            "text": "delivery-tracker 상류(shlee322)에 새 변경이 병합됐습니다. 검토 후 필요 시 업데이트하세요.",
            "wrap": True, "size": "default", "weight": "bolder", "separator": False,
        },
        {"rows": rows},
    ]
    if recent_msgs:
        body.append({
            "text": "최근 커밋:\n- " + "\n- ".join(recent_msgs),
            "wrap": True, "size": "small", "weight": "default", "separator": True,
        })

    message = {
        "channel_url": url,
        "channel_type": "TEAMS",
        "body": {
            "title": f"\U0001F4E6 delivery-tracker 상류 업데이트 {len(commits)}건",
            "subtitle": "self-host 이미지 재빌드되어 ECR 준비 · 배포는 수동(digest bump PR)",
            "body": body,
            "bottom_open_url_buttons": [
                {"title": "변경 diff 보기", "url": f"https://github.com/{repo}/compare/{before}...{after}"},
            ],
            # 우리 carrier 영향 시 노랑(warning), 아니면 파랑(accent)
            "theme_color": "warning" if affected else "accent",
        },
    }
    print(json.dumps(message, ensure_ascii=False))


if __name__ == "__main__":
    main()
