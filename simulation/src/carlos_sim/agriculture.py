"""Finite planted crops: seed, water, soil, sunlight and one day of logical time.

A farmer first uses a genuine 60-second seed -> crop_seeded production recipe.
An authenticated growth event consumes that seedling and a *finite* water unit.
The clock matures the crop to one ripe unit plus one biological seed. No rain,
money, or materials are refilled silently; all events replay from SQLite.
"""
from __future__ import annotations
from typing import Any
from .domain import DomainEvent, WorldState

MAX_STOCK = 2**31 - 1
MAX_GROWTH = 30 * 86400
KEYS = ("seed", "crop_seeded", "crop_ready", "water", "hoe")


def _known(value: Any) -> bool:
    return type(value) is int and 0 <= value <= MAX_STOCK


def _sid(site: str, cycle: int) -> str:
    return f"crop-growth:{site}:{cycle}"


def configure_plot(state: dict[str, Any], event: DomainEvent, *, bootstrap: bool) -> None:
    p = event.data
    if (not bootstrap or event.actor_id is not None or state["time"] != 0
            or set(p) != {"site_id", "growth_seconds", "capacity"}):
        raise ValueError("plot requires trusted time-zero configuration")
    site, seconds, capacity = p["site_id"], p["growth_seconds"], p["capacity"]
    if (type(site) is not str or site not in state["locations"]
            or site in state["farm_plots"] or not 1 <= len(site) <= 32
            or not site.isascii() or not all(c.isalnum() or c in "._-" for c in site)
            or type(seconds) is not int or not 60 <= seconds <= MAX_GROWTH
            or type(capacity) is not int or capacity != 1):
        raise ValueError("invalid physical crop plot")
    stock = state["resources"].get(site, {})
    if (not all(_known(stock.get(k)) for k in KEYS)
            or stock["crop_seeded"] != 0 or stock["crop_ready"] != 0):
        raise ValueError("plot requires initialized empty seedling/ripe balances")
    planting = [r for r in state["production_recipes"].values()
                if r["site_id"] == site and r["role"] == "farmer"
                and r["input_resource"] == "seed" and r["input_amount"] == 1
                and r["output_resource"] == "crop_seeded" and r["output_amount"] == 1
                and r["tool_resource"] == "hoe"]
    if len(planting) != 1:
        raise ValueError("plot requires a unique material-backed planting recipe")
    state["farm_plots"][site] = {
        "site_id": site, "growth_seconds": seconds, "capacity": capacity,
        "status": "idle", "started": 0, "matured": 0,
        "planted_at": None, "due": None, "last_matured_at": None,
    }


def choose_local_growth(state: WorldState, site: str) -> bool:
    plot = state.farm_plots.get(site)
    if plot is None or plot["status"] != "idle":
        return False
    stock = state.resources.get(site, {})
    return (all(_known(stock.get(k)) for k in ("crop_seeded", "crop_ready", "water", "seed"))
            and stock["crop_seeded"] == 1 and stock["crop_ready"] == 0
            and stock["water"] >= 1 and stock["seed"] < MAX_STOCK)


def start_crop_growth(state: dict[str, Any], event: DomainEvent,
                      *, agriculture_authorized: bool) -> None:
    p = event.data
    if (not agriculture_authorized or event.actor_id is not None
            or set(p) != {"site_id"} or type(p["site_id"]) is not str):
        raise ValueError("growth requires explicit trusted agriculture authority")
    site = p["site_id"]
    plot = state["farm_plots"].get(site)
    stock = state["resources"].get(site, {})
    if (plot is None or plot["status"] != "idle"
            or not all(_known(stock.get(k)) for k in ("crop_seeded", "crop_ready", "water", "seed"))
            or stock["crop_seeded"] != 1 or stock["crop_ready"] != 0
            or stock["water"] < 1 or stock["seed"] == MAX_STOCK):
        raise ValueError("crop requires real seedling, free soil and known finite water")
    if not any(j["status"] == "completed" and j["site_id"] == site
               and j["finished_at"] <= state["time"]
               and state["production_recipes"][j["recipe_id"]]["output_resource"] == "crop_seeded"
               for j in state["production_jobs"].values()):
        raise ValueError("fictitious crop seedling")
    cycle = plot["started"] + 1
    due = state["time"] + plot["growth_seconds"]
    sid = _sid(site, cycle)
    if due > 2**63 - 1 or sid in state["scheduled"]:
        raise ValueError("crop timing overflow or duplicate")
    stock["crop_seeded"] -= 1
    stock["water"] -= 1
    plot["status"] = "growing"
    plot["started"] = cycle
    plot["planted_at"] = state["time"]
    plot["due"] = due
    state["scheduled"][sid] = {
        "due": due, "order": state["next_schedule_order"], "kind": "signal",
        "payload": {"__crop_growth": site, "cycle": cycle},
        "interrupt": False,
    }
    state["next_schedule_order"] += 1


def mature_crop(state: dict[str, Any], schedule_id: str,
                payload: dict[str, Any], now: int) -> None:
    if set(payload) != {"__crop_growth", "cycle"}:
        raise ValueError("malformed crop maturation signal")
    site, number = payload["__crop_growth"], payload["cycle"]
    plot = state["farm_plots"].get(site) if type(site) is str else None
    if (plot is None or plot["status"] != "growing"
            or type(number) is not int or number != plot["started"]
            or schedule_id != _sid(site, number) or now != plot["due"]):
        raise ValueError("crop maturation needs its exact committed appointment")
    stock = state["resources"][site]
    if (not _known(stock.get("crop_ready")) or not _known(stock.get("seed"))
            or stock["crop_ready"] + 1 > plot["capacity"]
            or stock["seed"] >= MAX_STOCK):
        raise ValueError("crop maturity cannot overflow soil or seed")
    stock["crop_ready"] += 1
    stock["seed"] += 1
    plot["status"] = "idle"
    plot["matured"] += 1
    plot["due"] = None
    plot["planted_at"] = None
    plot["last_matured_at"] = now


def validate_farm_plots(state: dict[str, Any]) -> None:
    plots = state["farm_plots"]
    if type(plots) is not dict:
        raise ValueError("farm plots must be a mapping")
    expected = set()
    for site, p in plots.items():
        if (type(site) is not str or site not in state["locations"]
                or not 1 <= len(site) <= 32 or not site.isascii()
                or not all(c.isalnum() or c in "._-" for c in site)
                or type(p) is not dict
                or set(p) != {"site_id", "growth_seconds", "capacity", "status",
                               "started", "matured", "planted_at", "due", "last_matured_at"}
                or p["site_id"] != site or p["capacity"] != 1
                or type(p["growth_seconds"]) is not int
                or not 60 <= p["growth_seconds"] <= MAX_GROWTH
                or p["status"] not in ("idle", "growing")
                or type(p["started"]) is not int or p["started"] < 0
                or type(p["matured"]) is not int or p["matured"] < 0):
            raise ValueError("invalid persisted farm plot")
        stock = state["resources"].get(site, {})
        if (not all(_known(stock.get(k)) for k in KEYS)
                or stock["crop_ready"] > p["capacity"]):
            raise ValueError("invalid farm stock or soil capacity")
        last = p["last_matured_at"]
        if last is not None and (type(last) is not int or not 0 <= last <= state["time"]):
            raise ValueError("invalid last crop maturity")
        if p["status"] == "idle":
            if (p["started"] != p["matured"] or p["planted_at"] is not None
                    or p["due"] is not None):
                raise ValueError("idle plot with unresolved crop")
        else:
            if (p["started"] != p["matured"] + 1
                    or type(p["planted_at"]) is not int or type(p["due"]) is not int
                    or p["due"] != p["planted_at"] + p["growth_seconds"]
                    or not p["planted_at"] <= state["time"] <= p["due"]
                    or stock["crop_ready"] != 0):
                raise ValueError("invalid growing crop chronology")
            sid = _sid(site, p["started"])
            item = state["scheduled"].get(sid)
            if (item is None or item["due"] != p["due"] or item["interrupt"]
                    or item["payload"] != {"__crop_growth": site, "cycle": p["started"]}):
                raise ValueError("growing crop missing authenticated appointment")
            expected.add(sid)
    for sid, item in state["scheduled"].items():
        if "__crop_growth" in item["payload"] and sid not in expected:
            raise ValueError("forged crop schedule")
