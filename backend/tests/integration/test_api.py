import csv
import io

from fastapi.testclient import TestClient

from atc.directory.phones import service_phone
from atc.domain import AccountType


def test_runs_list_has_default_run(client: TestClient, run_id: str) -> None:
    runs = client.get("/runs").json()
    run = next(r for r in runs if r["id"] == run_id)
    assert run["kind"] == "atc"
    assert run["headline"]["critical_rate"] == 100.0
    assert run["config"]["pipeline"][0] == "critical_bypass"


def test_summary_headline(client: TestClient, run_id: str) -> None:
    s = client.get(f"/runs/{run_id}/summary").json()
    assert s["delivered"]["baseline"] == s["requested"]
    assert s["delivered"]["atc"] < s["requested"]
    assert s["reduction_pct"] > 0
    assert sum(s["outcomes"].values()) == s["requested"]
    assert s["critical"]["rate"] == 100.0
    assert s["critical"]["delivered"] == s["critical"]["requested"] > 0
    assert s["critical"]["suppressed"] == s["critical"]["delayed"] == 0
    assert 0 < s["critical"]["median_latency_s"] < 5
    assert s["preference_violations"]["atc"] == 0
    assert s["night_interruptions"]["atc"] < s["night_interruptions"]["baseline"]
    assert s["avg_fatigue"]["atc"] < s["avg_fatigue"]["baseline"]
    assert "critical alerts" in s["insight"]
    assert isinstance(s["delivered"]["atc"], int)


def test_flows_conserve_volume(client: TestClient, run_id: str) -> None:
    flows = client.get(f"/runs/{run_id}/flows").json()
    kinds = [n["kind"] for n in flows["nodes"]]
    assert kinds == sorted(kinds, key=["event", "rule", "outcome"].index)
    by_kind = {i: n["kind"] for i, n in enumerate(flows["nodes"])}
    stage1 = sum(link["value"] for link in flows["links"] if by_kind[link["source"]] == "event")
    stage2 = sum(link["value"] for link in flows["links"] if by_kind[link["source"]] == "rule")
    requested = client.get(f"/runs/{run_id}/summary").json()["requested"]
    assert stage1 == stage2 == requested
    critical = next(n for n in flows["nodes"] if n["key"] == "critical_bypass")
    assert critical["kind"] == "rule"


def test_timeseries_covers_the_month(client: TestClient, run_id: str) -> None:
    points = client.get(f"/runs/{run_id}/timeseries").json()
    assert 30 <= len(points) <= 32
    assert sum(p["atc"] for p in points) < sum(p["baseline"] for p in points)
    assert all(p["critical"] <= p["atc"] for p in points)


def test_replay_is_columnar_and_complete(client: TestClient, run_id: str) -> None:
    replay = client.get(f"/runs/{run_id}/replay").json()
    n = len(replay["t"])
    assert n == client.get(f"/runs/{run_id}/summary").json()["requested"]
    for key in ("type", "priority", "outcome", "rule", "customer"):
        assert len(replay[key]) == n
    assert replay["t"] == sorted(replay["t"])


def test_alerts_filter_and_paginate(client: TestClient, run_id: str) -> None:
    page = client.get(
        f"/runs/{run_id}/alerts", params={"outcome": "DELAYED", "page_size": 5}
    ).json()
    assert page["total"] > 5 and len(page["items"]) == 5
    assert all(item["outcome"] == "DELAYED" for item in page["items"])
    assert all(item["customer_name"] for item in page["items"])

    page2 = client.get(
        f"/runs/{run_id}/alerts", params={"outcome": "DELAYED", "page_size": 5, "page": 2}
    ).json()
    assert {i["alert_id"] for i in page["items"]}.isdisjoint(i["alert_id"] for i in page2["items"])


def test_alerts_multi_value_filters_and_sort(client: TestClient, run_id: str) -> None:
    params = {"priority": ["critical"], "sort": "-requested_at", "page_size": 200}
    items = client.get(f"/runs/{run_id}/alerts", params=params).json()["items"]
    assert items and all(i["outcome"] == "SENT" and "sms" in i["channels"] for i in items)
    times = [i["requested_at"] for i in items]
    assert times == sorted(times, reverse=True)

    both = client.get(
        f"/runs/{run_id}/alerts", params={"rule": ["dedup", "fatigue_gate"], "page_size": 1}
    ).json()["total"]
    dedup = client.get(f"/runs/{run_id}/alerts", params={"rule": "dedup"}).json()["total"]
    assert both > dedup > 0


def test_alerts_date_and_customer_filters(client: TestClient, run_id: str) -> None:
    params = {
        "customer_id": 7,
        "date_from": "2026-10-25T00:00:00Z",
        "date_to": "2026-10-27T00:00:00Z",
        "page_size": 200,
    }
    items = client.get(f"/runs/{run_id}/alerts", params=params).json()["items"]
    assert all(i["customer_id"] == 7 for i in items)
    assert all("2026-10-25" <= i["requested_at"][:10] <= "2026-10-26" for i in items)


def test_csv_export_matches_filter(client: TestClient, run_id: str) -> None:
    response = client.get(f"/runs/{run_id}/alerts.csv", params={"outcome": "SUPPRESSED"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(response.text)))
    total = client.get(f"/runs/{run_id}/alerts", params={"outcome": "SUPPRESSED"}).json()["total"]
    assert len(rows) == total
    assert {r["outcome"] for r in rows} == {"SUPPRESSED"}
    assert rows[0]["reason"]


def test_customer_search_and_detail(client: TestClient, run_id: str) -> None:
    found = client.get("/customers", params={"q": "7", "limit": 50}).json()
    assert any(c["id"] == 7 for c in found)
    assert all(c["fatigue_atc"] is not None for c in found)

    everyone = client.get("/customers").json()
    assert len(everyone) == 500


def test_customer_accounts_show_correct_service_phone(client: TestClient) -> None:
    for customer in client.get("/customers").json():
        detail = client.get(f"/customers/{customer['id']}").json()
        cobrand = [a for a in detail["accounts"] if a["account_type"] == "cobrand_card"]
        if not cobrand:
            continue
        account = cobrand[0]
        expected = service_phone(AccountType.COBRAND_CARD, account["partner_code"])
        assert account["service_phone"] == expected.phone
        assert account["service_phone"] != "1-800-555-0100"
        return
    raise AssertionError("no cobrand customer found")


def test_timeline_explains_every_alert(client: TestClient, run_id: str) -> None:
    tl = client.get("/customers/7/timeline", params={"run": run_id}).json()
    assert tl["baseline"] and tl["atc"]
    assert all(i["outcome"] == "SENT" for i in tl["baseline"])
    for item in tl["atc"]:
        assert item["explanation"]
        if item["kind"] == "alert" and item["event_type"] != "marketing_offer":
            assert item["service_phone"] is None or item["service_phone"].startswith("1-800-555")
    alerts = [i for i in tl["atc"] if i["kind"] == "alert"]
    assert len(alerts) == len(tl["baseline"])


def test_not_found_and_bad_requests(client: TestClient, run_id: str) -> None:
    assert client.get("/runs/nope/summary").status_code == 404
    baseline = client.get(f"/runs/{run_id}/summary").json()["baseline_run_id"]
    assert client.get(f"/runs/{baseline}/summary").status_code == 400
    assert client.get("/customers/99999").status_code == 404
    assert client.get("/customers/99999/timeline").status_code == 404
    assert client.get(f"/runs/{run_id}/alerts", params={"page_size": 999}).status_code == 422


def test_config_round_trip(client: TestClient) -> None:
    config = client.get("/config").json()
    assert config["pipeline"][0] == "critical_bypass"
    config["rules"]["frequency_cap"]["daily_cap"] = 7
    saved = client.put("/config", json=config)
    assert saved.status_code == 200
    assert client.get("/config").json()["rules"]["frequency_cap"]["daily_cap"] == 7


def test_config_rejects_unsafe_changes(client: TestClient) -> None:
    config = client.get("/config").json()
    moved = {**config, "pipeline": [*config["pipeline"][1:], "critical_bypass"]}
    assert client.put("/config", json=moved).status_code == 422
    disabled = {**config}
    disabled["rules"] = {**config["rules"], "critical_bypass": {"enabled": False}}
    assert client.put("/config", json=disabled).status_code == 422


def test_simulate_with_overrides(client: TestClient) -> None:
    response = client.post(
        "/simulate",
        json={"overrides": {"rules": {"digest": {"enabled": False}}}, "label": "no digest"},
    )
    assert response.status_code == 201
    new_id = response.json()["run_id"]
    summary = client.get(f"/runs/{new_id}/summary").json()
    assert summary["digests"] == 0
    assert summary["label"] == "no digest"
    assert summary["critical"]["rate"] == 100.0


def test_simulate_aggressive_config_never_touches_critical(client: TestClient) -> None:
    overrides = {
        "rules": {
            "frequency_cap": {"daily_cap": 1, "hourly_cap": 1, "marketing_daily_cap": 0},
            "quiet_hours": {"start": "00:00", "end": "23:59"},
            "fatigue_gate": {"threshold": 0},
        }
    }
    new_id = client.post("/simulate", json={"overrides": overrides}).json()["run_id"]
    critical = client.get(f"/runs/{new_id}/summary").json()["critical"]
    assert critical["delivered"] == critical["requested"]
    assert critical["delayed"] == critical["suppressed"] == 0


def test_simulate_rejects_invalid_overrides(client: TestClient) -> None:
    bad = client.post("/simulate", json={"overrides": {"pipeline": ["dedup"]}})
    assert bad.status_code == 422


def test_openapi_docs_available(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    for path in ("/simulate", "/runs/{run_id}/summary", "/customers/{customer_id}/timeline"):
        assert path in paths
