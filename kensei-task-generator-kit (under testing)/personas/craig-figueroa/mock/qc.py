#!/usr/bin/env python3
"""QC script for the mock API fixtures folder.

Validates that:
  1. The set of `*-api` folders matches the embedded baseline exactly (no missing, no extra).
  2. Each folder contains exactly the expected `.json` files (no missing, no extra).
  3. Every JSON file is non-empty and parses successfully.
  4. Every JSON file's key structure matches the baseline at every nesting level
     (no added / removed / renamed keys; primitive-type changes are also flagged).

Self-contained: the baseline lives between the BASELINE markers at the bottom of
this file, and `--update` rewrites this file in place. No external files.

Usage:
    python3 qc.py              # run QC against the embedded baseline
    python3 qc.py --update     # regenerate the embedded baseline from current contents
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

MOCK_DIR = Path(__file__).resolve().parent
SELF_PATH = Path(__file__).resolve()

_MARKER_BEGIN = "# ===" + " BEGIN BASELINE ==="
_MARKER_END = "# ===" + " END BASELINE ==="


def extract_schema(value):
    if isinstance(value, dict):
        return {
            "type": "object",
            "keys": {k: extract_schema(v) for k, v in sorted(value.items())},
        }
    if isinstance(value, list):
        merged = None
        for item in value:
            schema = extract_schema(item)
            merged = schema if merged is None else merge_schema(merged, schema)
        return {"type": "array", "items": merged}
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, (int, float)):
        return {"type": "number"}
    if isinstance(value, str):
        return {"type": "string"}
    if value is None:
        return {"type": "null"}
    return {"type": "unknown"}


def merge_schema(a, b):
    if a is None:
        return b
    if b is None:
        return a
    if a.get("type") != b.get("type"):
        return {"type": f"{a.get('type')}|{b.get('type')}"}
    if a["type"] == "object":
        keys = dict(a["keys"])
        for k, v in b["keys"].items():
            keys[k] = merge_schema(keys[k], v) if k in keys else v
        return {"type": "object", "keys": dict(sorted(keys.items()))}
    if a["type"] == "array":
        return {"type": "array", "items": merge_schema(a.get("items"), b.get("items"))}
    return a


def list_api_dirs(root: Path) -> list[str]:
    return sorted(p.name for p in root.iterdir() if p.is_dir() and p.name.endswith("-api"))


def list_json_files(api_dir: Path) -> list[str]:
    return sorted(p.name for p in api_dir.iterdir() if p.is_file() and p.suffix == ".json")


def build_snapshot(root: Path) -> dict:
    snapshot = {}
    for api in list_api_dirs(root):
        api_path = root / api
        files = {}
        for fname in list_json_files(api_path):
            fpath = api_path / fname
            with fpath.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            files[fname] = extract_schema(data)
        snapshot[api] = files
    return snapshot


def schema_diff(expected, actual, path=""):
    diffs = []
    if expected.get("type") != actual.get("type"):
        diffs.append((path or "<root>", f"type changed: {expected.get('type')} -> {actual.get('type')}"))
        return diffs
    if expected["type"] == "object":
        e_keys = set(expected["keys"])
        a_keys = set(actual["keys"])
        for k in sorted(e_keys - a_keys):
            diffs.append((f"{path}.{k}" if path else k, "missing key"))
        for k in sorted(a_keys - e_keys):
            diffs.append((f"{path}.{k}" if path else k, "unexpected key"))
        for k in sorted(e_keys & a_keys):
            sub = f"{path}.{k}" if path else k
            diffs.extend(schema_diff(expected["keys"][k], actual["keys"][k], sub))
    elif expected["type"] == "array":
        e_items = expected.get("items")
        a_items = actual.get("items")
        if e_items is None and a_items is None:
            return diffs
        if e_items is None:
            diffs.append((f"{path}[]", "array now has items (baseline empty)"))
        elif a_items is None:
            diffs.append((f"{path}[]", "array is now empty (baseline had items)"))
        else:
            diffs.extend(schema_diff(e_items, a_items, f"{path}[]"))
    return diffs


def qc(root: Path, baseline: dict) -> int:
    if not baseline:
        print("FAIL: embedded baseline is empty. Run `python3 qc.py --update` to populate it.",
              file=sys.stderr)
        return 2

    failures: list[str] = []

    expected_apis = sorted(baseline.keys())
    actual_apis = list_api_dirs(root)
    for a in sorted(set(expected_apis) - set(actual_apis)):
        failures.append(f"missing API folder: {a}")
    for a in sorted(set(actual_apis) - set(expected_apis)):
        failures.append(f"unexpected API folder: {a}")

    for api in sorted(set(expected_apis) & set(actual_apis)):
        api_path = root / api
        expected_files = sorted(baseline[api].keys())
        actual_files = list_json_files(api_path)

        for f in sorted(set(expected_files) - set(actual_files)):
            failures.append(f"[{api}] missing file: {f}")
        for f in sorted(set(actual_files) - set(expected_files)):
            failures.append(f"[{api}] unexpected file: {f}")

        for fname in sorted(set(expected_files) & set(actual_files)):
            fpath = api_path / fname
            if fpath.stat().st_size == 0:
                failures.append(f"[{api}/{fname}] empty file")
                continue
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                failures.append(f"[{api}/{fname}] invalid JSON: {e}")
                continue
            actual_schema = extract_schema(data)
            for p, msg in schema_diff(baseline[api][fname], actual_schema):
                failures.append(f"[{api}/{fname}] {p}: {msg}")

    api_count = len(expected_apis)
    file_count = sum(len(v) for v in baseline.values())

    if failures:
        print(f"QC FAILED  ({len(failures)} issue(s) across {api_count} APIs / {file_count} files)")
        for line in failures:
            print(f"  - {line}")
        return 1

    print(f"QC PASSED  {api_count} APIs, {file_count} JSON files, all valid and schema-aligned.")
    return 0


def update_baseline(root: Path) -> int:
    snapshot = build_snapshot(root)
    serialized = json.dumps(snapshot, indent=2, sort_keys=True)
    block = f'{_MARKER_BEGIN}\nBASELINE = json.loads(r"""\n{serialized}\n""")\n{_MARKER_END}'

    source = SELF_PATH.read_text(encoding="utf-8")
    pattern = re.compile(
        r"^" + re.escape(_MARKER_BEGIN) + r"\n.*?^" + re.escape(_MARKER_END),
        re.DOTALL | re.MULTILINE,
    )
    if not pattern.search(source):
        print(f"FAIL: could not find baseline markers in {SELF_PATH}", file=sys.stderr)
        return 2
    new_source = pattern.sub(block, source, count=1)
    SELF_PATH.write_text(new_source, encoding="utf-8")

    api_count = len(snapshot)
    file_count = sum(len(v) for v in snapshot.values())
    print(f"Baseline updated in place: {SELF_PATH}")
    print(f"  APIs: {api_count}")
    print(f"  JSON files: {file_count}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="QC the mock API fixtures folder.")
    parser.add_argument(
        "--update",
        action="store_true",
        help="Regenerate the embedded baseline from the current folder contents.",
    )
    args = parser.parse_args()

    if args.update:
        return update_baseline(MOCK_DIR)
    return qc(MOCK_DIR, BASELINE)


# === BEGIN BASELINE ===
BASELINE = json.loads(r"""
{
  "activecampaign-api": {
    "campaigns.json": {
      "items": {
        "keys": {
          "clicks": {
            "type": "string"
          },
          "created_timestamp": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "list_id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "opens": {
            "type": "string"
          },
          "sdate": {
            "type": "string"
          },
          "send_amt": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "subject": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "contacts.json": {
      "items": {
        "keys": {
          "created_timestamp": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "first_name": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "last_name": {
            "type": "string"
          },
          "phone": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "updated_timestamp": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "deals.json": {
      "items": {
        "keys": {
          "contact_id": {
            "type": "string"
          },
          "created_timestamp": {
            "type": "string"
          },
          "currency": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "owner": {
            "type": "string"
          },
          "stage": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "updated_timestamp": {
            "type": "string"
          },
          "value": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "lists.json": {
      "items": {
        "keys": {
          "created_timestamp": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "sender_reminder": {
            "type": "string"
          },
          "sender_url": {
            "type": "string"
          },
          "stringid": {
            "type": "string"
          },
          "subscriber_count": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "airbnb-api": {
    "availability.json": {
      "items": {
        "keys": {
          "available": {
            "type": "string"
          },
          "end_date": {
            "type": "string"
          },
          "listing_id": {
            "type": "string"
          },
          "start_date": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "hosts.json": {
      "items": {
        "keys": {
          "host_id": {
            "type": "string"
          },
          "joined_year": {
            "type": "string"
          },
          "languages": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "response_rate": {
            "type": "string"
          },
          "superhost": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "listings.json": {
      "items": {
        "keys": {
          "baths": {
            "type": "string"
          },
          "beds": {
            "type": "string"
          },
          "city": {
            "type": "string"
          },
          "cleaning_fee": {
            "type": "string"
          },
          "country": {
            "type": "string"
          },
          "host_id": {
            "type": "string"
          },
          "instant_book": {
            "type": "string"
          },
          "listing_id": {
            "type": "string"
          },
          "max_guests": {
            "type": "string"
          },
          "price_per_night": {
            "type": "string"
          },
          "rating": {
            "type": "string"
          },
          "review_count": {
            "type": "string"
          },
          "room_type": {
            "type": "string"
          },
          "title": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "reviews.json": {
      "items": {
        "keys": {
          "comment": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "guest_name": {
            "type": "string"
          },
          "listing_id": {
            "type": "string"
          },
          "rating": {
            "type": "string"
          },
          "review_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "airtable-api": {
    "bases.json": {
      "items": {
        "keys": {
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "permissionLevel": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "fields.json": {
      "items": {
        "keys": {
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "tableId": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "records_contacts.json": {
      "items": {
        "keys": {
          "Company": {
            "type": "string"
          },
          "Email": {
            "type": "string"
          },
          "Name": {
            "type": "string"
          },
          "Role": {
            "type": "string"
          },
          "createdTime": {
            "type": "string"
          },
          "id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "records_projects.json": {
      "items": {
        "keys": {
          "Budget": {
            "type": "string"
          },
          "Name": {
            "type": "string"
          },
          "Owner": {
            "type": "string"
          },
          "Status": {
            "type": "string"
          },
          "createdTime": {
            "type": "string"
          },
          "id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "records_tasks.json": {
      "items": {
        "keys": {
          "Done": {
            "type": "string"
          },
          "EstimateHours": {
            "type": "string"
          },
          "Name": {
            "type": "string"
          },
          "Project": {
            "type": "string"
          },
          "Status": {
            "type": "string"
          },
          "createdTime": {
            "type": "string"
          },
          "id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "tables.json": {
      "items": {
        "keys": {
          "baseId": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "primaryFieldId": {
            "type": "string"
          },
          "records_csv": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "algolia-api": {
    "indices.json": {
      "items": {
        "keys": {
          "created_at": {
            "type": "string"
          },
          "data_size": {
            "type": "string"
          },
          "entries": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "records_csv": {
            "type": "string"
          },
          "updated_at": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "records_docs.json": {
      "items": {
        "keys": {
          "body": {
            "type": "string"
          },
          "objectID": {
            "type": "string"
          },
          "section": {
            "type": "string"
          },
          "tags": {
            "type": "string"
          },
          "title": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "records_products.json": {
      "items": {
        "keys": {
          "brand": {
            "type": "string"
          },
          "category": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "in_stock": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "objectID": {
            "type": "string"
          },
          "price": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "settings.json": {
      "items": {
        "keys": {
          "attributesForFaceting": {
            "type": "string"
          },
          "hitsPerPage": {
            "type": "string"
          },
          "index": {
            "type": "string"
          },
          "ranking": {
            "type": "string"
          },
          "searchableAttributes": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "alpaca-api": {
    "account.json": {
      "keys": {
        "account_blocked": {
          "type": "boolean"
        },
        "account_number": {
          "type": "string"
        },
        "buying_power": {
          "type": "string"
        },
        "cash": {
          "type": "string"
        },
        "created_at": {
          "type": "string"
        },
        "currency": {
          "type": "string"
        },
        "equity": {
          "type": "string"
        },
        "id": {
          "type": "string"
        },
        "long_market_value": {
          "type": "string"
        },
        "pattern_day_trader": {
          "type": "boolean"
        },
        "portfolio_value": {
          "type": "string"
        },
        "status": {
          "type": "string"
        },
        "trading_blocked": {
          "type": "boolean"
        }
      },
      "type": "object"
    },
    "assets.json": {
      "items": {
        "keys": {
          "asset_class": {
            "type": "string"
          },
          "exchange": {
            "type": "string"
          },
          "fractionable": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "symbol": {
            "type": "string"
          },
          "tradable": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "orders.json": {
      "items": {
        "keys": {
          "client_order_id": {
            "type": "string"
          },
          "filled_at": {
            "type": "string"
          },
          "filled_avg_price": {
            "type": "string"
          },
          "filled_qty": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "limit_price": {
            "type": "string"
          },
          "qty": {
            "type": "string"
          },
          "side": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "submitted_at": {
            "type": "string"
          },
          "symbol": {
            "type": "string"
          },
          "time_in_force": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "positions.json": {
      "items": {
        "keys": {
          "asset_id": {
            "type": "string"
          },
          "avg_entry_price": {
            "type": "string"
          },
          "cost_basis": {
            "type": "string"
          },
          "current_price": {
            "type": "string"
          },
          "market_value": {
            "type": "string"
          },
          "qty": {
            "type": "string"
          },
          "side": {
            "type": "string"
          },
          "symbol": {
            "type": "string"
          },
          "unrealized_pl": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "quotes.json": {
      "items": {
        "keys": {
          "ask_price": {
            "type": "string"
          },
          "ask_size": {
            "type": "string"
          },
          "bid_price": {
            "type": "string"
          },
          "bid_size": {
            "type": "string"
          },
          "symbol": {
            "type": "string"
          },
          "timestamp": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "amadeus-api": {
    "airlines.json": {
      "items": {
        "keys": {
          "business_name": {
            "type": "string"
          },
          "common_name": {
            "type": "string"
          },
          "country_code": {
            "type": "string"
          },
          "iata_code": {
            "type": "string"
          },
          "icao_code": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "airports.json": {
      "items": {
        "keys": {
          "city_code": {
            "type": "string"
          },
          "city_name": {
            "type": "string"
          },
          "country_code": {
            "type": "string"
          },
          "country_name": {
            "type": "string"
          },
          "iata_code": {
            "type": "string"
          },
          "latitude": {
            "type": "string"
          },
          "longitude": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "timezone": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "flight_offers.json": {
      "items": {
        "keys": {
          "departureDate": {
            "type": "string"
          },
          "destinationLocationCode": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "itineraries": {
            "items": {
              "keys": {
                "duration": {
                  "type": "string"
                },
                "segments": {
                  "items": {
                    "keys": {
                      "aircraft": {
                        "keys": {
                          "code": {
                            "type": "string"
                          }
                        },
                        "type": "object"
                      },
                      "arrival": {
                        "keys": {
                          "at": {
                            "type": "string"
                          },
                          "iataCode": {
                            "type": "string"
                          },
                          "terminal": {
                            "type": "string"
                          }
                        },
                        "type": "object"
                      },
                      "carrierCode": {
                        "type": "string"
                      },
                      "departure": {
                        "keys": {
                          "at": {
                            "type": "string"
                          },
                          "iataCode": {
                            "type": "string"
                          },
                          "terminal": {
                            "type": "string"
                          }
                        },
                        "type": "object"
                      },
                      "duration": {
                        "type": "string"
                      },
                      "number": {
                        "type": "string"
                      },
                      "numberOfStops": {
                        "type": "number"
                      }
                    },
                    "type": "object"
                  },
                  "type": "array"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "numberOfBookableSeats": {
            "type": "number"
          },
          "oneWay": {
            "type": "boolean"
          },
          "originLocationCode": {
            "type": "string"
          },
          "price": {
            "keys": {
              "base": {
                "type": "string"
              },
              "currency": {
                "type": "string"
              },
              "grandTotal": {
                "type": "string"
              },
              "total": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "source": {
            "type": "string"
          },
          "travelerPricings": {
            "items": {
              "keys": {
                "fareOption": {
                  "type": "string"
                },
                "price": {
                  "keys": {
                    "currency": {
                      "type": "string"
                    },
                    "total": {
                      "type": "string"
                    }
                  },
                  "type": "object"
                },
                "travelerId": {
                  "type": "string"
                },
                "travelerType": {
                  "type": "string"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "type": {
            "type": "string"
          },
          "validatingAirlineCodes": {
            "items": {
              "type": "string"
            },
            "type": "array"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "amazon-seller-api": {
    "buying_notes_fw26.json": {
      "keys": {
        "category_restrictions": {
          "keys": {
            "blazers_max_skus": {
              "type": "number"
            },
            "knitwear_max_skus": {
              "type": "number"
            },
            "no_leather_outerwear": {
              "type": "boolean"
            },
            "outerwear_max_skus": {
              "type": "number"
            }
          },
          "type": "object"
        },
        "color_exclusions": {
          "keys": {
            "max_black_percent_of_assortment": {
              "type": "number"
            },
            "no_neon_or_fluorescent": {
              "type": "boolean"
            },
            "preferred_tones": {
              "items": {
                "type": "string"
              },
              "type": "array"
            }
          },
          "type": "object"
        },
        "delivery_and_timeline": {
          "keys": {
            "final_submission_date": {
              "type": "string"
            },
            "max_lead_time_months_without_vp_approval": {
              "type": "number"
            },
            "priority_reorder_brands": {
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            "vendor_delivery_deadline": {
              "type": "string"
            }
          },
          "type": "object"
        },
        "fabrication_exclusions": {
          "keys": {
            "max_acrylic_percent": {
              "type": "number"
            },
            "max_mohair_percent": {
              "type": "number"
            },
            "no_faux_fur": {
              "type": "boolean"
            },
            "no_fur": {
              "type": "boolean"
            }
          },
          "type": "object"
        },
        "notes": {
          "keys": {
            "korean_designers_premium_positioning": {
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            "mijeong_park_max_skus_without_sizing_confirmation": {
              "type": "number"
            },
            "total_sku_budget": {
              "type": "number"
            }
          },
          "type": "object"
        },
        "pricing_limits": {
          "keys": {
            "max_category_budget_percent": {
              "type": "number"
            },
            "max_retail_cap_per_unit": {
              "type": "number"
            },
            "opening_price_point_min": {
              "type": "number"
            }
          },
          "type": "object"
        },
        "submitted_by": {
          "type": "string"
        },
        "title": {
          "type": "string"
        },
        "updated": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "catalog_items.json": {
      "items": {
        "keys": {
          "asin": {
            "type": "string"
          },
          "brand": {
            "type": "string"
          },
          "bulletPoints": {
            "type": "string"
          },
          "category": {
            "type": "string"
          },
          "condition": {
            "type": "string"
          },
          "createdDate": {
            "type": "string"
          },
          "currency": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "fulfillmentChannel": {
            "type": "string"
          },
          "itemDimensionsUnit": {
            "type": "string"
          },
          "itemHeight": {
            "type": "string"
          },
          "itemLength": {
            "type": "string"
          },
          "itemWeight": {
            "type": "string"
          },
          "itemWeightUnit": {
            "type": "string"
          },
          "itemWidth": {
            "type": "string"
          },
          "lastUpdatedDate": {
            "type": "string"
          },
          "mainImageUrl": {
            "type": "string"
          },
          "price": {
            "type": "string"
          },
          "productType": {
            "type": "string"
          },
          "quantity": {
            "type": "string"
          },
          "sellerId": {
            "type": "string"
          },
          "sku": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "title": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "inventory.json": {
      "items": {
        "keys": {
          "asin": {
            "type": "string"
          },
          "condition": {
            "type": "string"
          },
          "fnSku": {
            "type": "string"
          },
          "fulfillmentChannel": {
            "type": "string"
          },
          "inStockSupplyQuantity": {
            "type": "string"
          },
          "inboundReceivingQuantity": {
            "type": "string"
          },
          "inboundShippedQuantity": {
            "type": "string"
          },
          "inboundWorkingQuantity": {
            "type": "string"
          },
          "lastUpdatedTime": {
            "type": "string"
          },
          "productName": {
            "type": "string"
          },
          "reservedQuantity": {
            "type": "string"
          },
          "sellerSku": {
            "type": "string"
          },
          "totalQuantity": {
            "type": "string"
          },
          "unfulfillableQuantity": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "order_items.json": {
      "items": {
        "keys": {
          "ASIN": {
            "type": "string"
          },
          "AmazonOrderId": {
            "type": "string"
          },
          "Condition": {
            "type": "string"
          },
          "IsGift": {
            "type": "string"
          },
          "ItemPrice_Amount": {
            "type": "string"
          },
          "ItemPrice_CurrencyCode": {
            "type": "string"
          },
          "ItemTax_Amount": {
            "type": "string"
          },
          "OrderItemId": {
            "type": "string"
          },
          "PromotionDiscount_Amount": {
            "type": "string"
          },
          "QuantityOrdered": {
            "type": "string"
          },
          "QuantityShipped": {
            "type": "string"
          },
          "SellerSKU": {
            "type": "string"
          },
          "Title": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "orders.json": {
      "items": {
        "keys": {
          "AmazonOrderId": {
            "type": "string"
          },
          "BuyerEmail": {
            "type": "string"
          },
          "BuyerName": {
            "type": "string"
          },
          "EarliestShipDate": {
            "type": "string"
          },
          "FulfillmentChannel": {
            "type": "string"
          },
          "IsBusinessOrder": {
            "type": "string"
          },
          "IsPrime": {
            "type": "string"
          },
          "IsSoldByAB": {
            "type": "string"
          },
          "LastUpdateDate": {
            "type": "string"
          },
          "LatestShipDate": {
            "type": "string"
          },
          "MarketplaceId": {
            "type": "string"
          },
          "NumberOfItemsShipped": {
            "type": "string"
          },
          "NumberOfItemsUnshipped": {
            "type": "string"
          },
          "OrderStatus": {
            "type": "string"
          },
          "OrderTotal_Amount": {
            "type": "string"
          },
          "OrderTotal_CurrencyCode": {
            "type": "string"
          },
          "OrderType": {
            "type": "string"
          },
          "PaymentMethod": {
            "type": "string"
          },
          "PurchaseDate": {
            "type": "string"
          },
          "SalesChannel": {
            "type": "string"
          },
          "ShipServiceLevel": {
            "type": "string"
          },
          "ShipmentServiceLevelCategory": {
            "type": "string"
          },
          "ShippingAddress_AddressLine1": {
            "type": "string"
          },
          "ShippingAddress_City": {
            "type": "string"
          },
          "ShippingAddress_CountryCode": {
            "type": "string"
          },
          "ShippingAddress_Name": {
            "type": "string"
          },
          "ShippingAddress_PostalCode": {
            "type": "string"
          },
          "ShippingAddress_StateOrRegion": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "pricing.json": {
      "items": {
        "keys": {
          "asin": {
            "type": "string"
          },
          "buyBoxPrice_Amount": {
            "type": "string"
          },
          "buyBoxPrice_CurrencyCode": {
            "type": "string"
          },
          "buyBoxWinner": {
            "type": "string"
          },
          "competitivePrice_Amount": {
            "type": "string"
          },
          "competitivePrice_Condition": {
            "type": "string"
          },
          "competitivePrice_CurrencyCode": {
            "type": "string"
          },
          "landedPrice_Amount": {
            "type": "string"
          },
          "listingPrice_Amount": {
            "type": "string"
          },
          "listingPrice_CurrencyCode": {
            "type": "string"
          },
          "numberOfOffers": {
            "type": "string"
          },
          "sellerSku": {
            "type": "string"
          },
          "shipping_Amount": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "reports.json": {
      "items": {
        "keys": {
          "createdTime": {
            "type": "string"
          },
          "dataEndTime": {
            "type": "string"
          },
          "dataStartTime": {
            "type": "string"
          },
          "processingEndTime": {
            "type": "string"
          },
          "reportDocumentId": {
            "type": "string"
          },
          "reportId": {
            "type": "string"
          },
          "reportStatus": {
            "type": "string"
          },
          "reportType": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "returns.json": {
      "items": {
        "keys": {
          "AmazonOrderId": {
            "type": "string"
          },
          "asin": {
            "type": "string"
          },
          "buyerComments": {
            "type": "string"
          },
          "refundAmount": {
            "type": "string"
          },
          "refundCurrency": {
            "type": "string"
          },
          "resolution": {
            "type": "string"
          },
          "returnDate": {
            "type": "string"
          },
          "returnId": {
            "type": "string"
          },
          "returnQuantity": {
            "type": "string"
          },
          "returnReason": {
            "type": "string"
          },
          "returnStatus": {
            "type": "string"
          },
          "sellerSKU": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "seller_account.json": {
      "keys": {
        "accountHealth": {
          "keys": {
            "accountStatus": {
              "type": "string"
            },
            "customerServiceDissatisfactionRate": {
              "type": "number"
            },
            "customerServiceDissatisfactionRateTarget": {
              "type": "number"
            },
            "lateShipmentRate": {
              "type": "number"
            },
            "lateShipmentRateTarget": {
              "type": "number"
            },
            "onTimeDeliveryRate": {
              "type": "number"
            },
            "onTimeDeliveryRateTarget": {
              "type": "number"
            },
            "orderDefectRate": {
              "type": "number"
            },
            "orderDefectRateTarget": {
              "type": "number"
            },
            "policyViolations": {
              "type": "number"
            },
            "preFulfillmentCancelRate": {
              "type": "number"
            },
            "preFulfillmentCancelRateTarget": {
              "type": "number"
            },
            "returnDissatisfactionRate": {
              "type": "number"
            },
            "returnDissatisfactionRateTarget": {
              "type": "number"
            },
            "validTrackingRate": {
              "type": "number"
            },
            "validTrackingRateTarget": {
              "type": "number"
            }
          },
          "type": "object"
        },
        "businessAddress": {
          "keys": {
            "AddressLine1": {
              "type": "string"
            },
            "AddressLine2": {
              "type": "string"
            },
            "City": {
              "type": "string"
            },
            "CountryCode": {
              "type": "string"
            },
            "Name": {
              "type": "string"
            },
            "PostalCode": {
              "type": "string"
            },
            "StateOrRegion": {
              "type": "string"
            }
          },
          "type": "object"
        },
        "businessName": {
          "type": "string"
        },
        "marketplaceId": {
          "type": "string"
        },
        "performanceNotifications": {
          "items": {
            "keys": {
              "createdDate": {
                "type": "string"
              },
              "isRead": {
                "type": "boolean"
              },
              "message": {
                "type": "string"
              },
              "notificationId": {
                "type": "string"
              },
              "severity": {
                "type": "string"
              },
              "title": {
                "type": "string"
              },
              "type": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "type": "array"
        },
        "primaryContactEmail": {
          "type": "string"
        },
        "registrationDate": {
          "type": "string"
        },
        "sellerId": {
          "type": "string"
        },
        "storeName": {
          "type": "string"
        },
        "storeUrl": {
          "type": "string"
        }
      },
      "type": "object"
    }
  },
  "amplitude-api": {
    "events.json": {
      "items": {
        "keys": {
          "device_id": {
            "type": "string"
          },
          "event_id": {
            "type": "string"
          },
          "event_properties": {
            "type": "string"
          },
          "event_time": {
            "type": "string"
          },
          "event_type": {
            "type": "string"
          },
          "user_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "segmentation.json": {
      "items": {
        "keys": {
          "count": {
            "type": "string"
          },
          "date": {
            "type": "string"
          },
          "event_type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "users.json": {
      "items": {
        "keys": {
          "country": {
            "type": "string"
          },
          "device_id": {
            "type": "string"
          },
          "first_seen": {
            "type": "string"
          },
          "last_seen": {
            "type": "string"
          },
          "platform": {
            "type": "string"
          },
          "user_id": {
            "type": "string"
          },
          "version": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "asana-api": {
    "projects.json": {
      "items": {
        "keys": {
          "archived": {
            "type": "string"
          },
          "color": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "gid": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "notes": {
            "type": "string"
          },
          "owner_gid": {
            "type": "string"
          },
          "workspace_gid": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "sections.json": {
      "items": {
        "keys": {
          "created_at": {
            "type": "string"
          },
          "gid": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "project_gid": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "tasks.json": {
      "items": {
        "keys": {
          "assignee_gid": {
            "type": "string"
          },
          "completed": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "due_on": {
            "type": "string"
          },
          "gid": {
            "type": "string"
          },
          "modified_at": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "notes": {
            "type": "string"
          },
          "project_gid": {
            "type": "string"
          },
          "section_gid": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "users.json": {
      "items": {
        "keys": {
          "email": {
            "type": "string"
          },
          "gid": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "workspace_gid": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "workspace.json": {
      "keys": {
        "email_domains": {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        "gid": {
          "type": "string"
        },
        "is_organization": {
          "type": "boolean"
        },
        "name": {
          "type": "string"
        },
        "resource_type": {
          "type": "string"
        }
      },
      "type": "object"
    }
  },
  "bamboohr-api": {
    "company.json": {
      "keys": {
        "employeeCount": {
          "type": "number"
        },
        "fiscalYearStart": {
          "type": "string"
        },
        "headquarters": {
          "type": "string"
        },
        "industry": {
          "type": "string"
        },
        "name": {
          "type": "string"
        },
        "subdomain": {
          "type": "string"
        },
        "timeOffPolicies": {
          "items": {
            "type": "string"
          },
          "type": "array"
        }
      },
      "type": "object"
    },
    "employees.json": {
      "items": {
        "keys": {
          "department": {
            "type": "string"
          },
          "firstName": {
            "type": "string"
          },
          "hireDate": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "jobTitle": {
            "type": "string"
          },
          "lastName": {
            "type": "string"
          },
          "location": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "supervisorId": {
            "type": "string"
          },
          "workEmail": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "time_off_requests.json": {
      "items": {
        "keys": {
          "amount": {
            "type": "string"
          },
          "created": {
            "type": "string"
          },
          "employeeId": {
            "type": "string"
          },
          "end": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "notes": {
            "type": "string"
          },
          "start": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "type": {
            "type": "string"
          },
          "unit": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "whos_out.json": {
      "items": {
        "keys": {
          "employeeId": {
            "type": "string"
          },
          "end": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "start": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "bigcommerce-api": {
    "customers.json": {
      "items": {
        "keys": {
          "company": {
            "type": "string"
          },
          "customer_group_id": {
            "type": "string"
          },
          "date_created": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "first_name": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "last_name": {
            "type": "string"
          },
          "phone": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "orders.json": {
      "items": {
        "keys": {
          "billing_email": {
            "type": "string"
          },
          "billing_first_name": {
            "type": "string"
          },
          "billing_last_name": {
            "type": "string"
          },
          "currency_code": {
            "type": "string"
          },
          "customer_id": {
            "type": "string"
          },
          "date_created": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "items_total": {
            "type": "string"
          },
          "payment_method": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "status_id": {
            "type": "string"
          },
          "subtotal_inc_tax": {
            "type": "string"
          },
          "total_inc_tax": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "products.json": {
      "items": {
        "keys": {
          "brand_id": {
            "type": "string"
          },
          "categories": {
            "type": "string"
          },
          "cost_price": {
            "type": "string"
          },
          "date_created": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "inventory_level": {
            "type": "string"
          },
          "inventory_tracking": {
            "type": "string"
          },
          "is_visible": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "price": {
            "type": "string"
          },
          "sale_price": {
            "type": "string"
          },
          "sku": {
            "type": "string"
          },
          "type": {
            "type": "string"
          },
          "weight": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "binance-api": {
    "balances.json": {
      "items": {
        "keys": {
          "asset": {
            "type": "string"
          },
          "free": {
            "type": "string"
          },
          "locked": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "depth.json": {
      "items": {
        "keys": {
          "price": {
            "type": "string"
          },
          "qty": {
            "type": "string"
          },
          "side": {
            "type": "string"
          },
          "symbol": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "klines.json": {
      "items": {
        "keys": {
          "close": {
            "type": "string"
          },
          "close_time": {
            "type": "string"
          },
          "high": {
            "type": "string"
          },
          "interval": {
            "type": "string"
          },
          "low": {
            "type": "string"
          },
          "open": {
            "type": "string"
          },
          "open_time": {
            "type": "string"
          },
          "symbol": {
            "type": "string"
          },
          "volume": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "prices.json": {
      "items": {
        "keys": {
          "highPrice": {
            "type": "string"
          },
          "lowPrice": {
            "type": "string"
          },
          "price": {
            "type": "string"
          },
          "priceChange": {
            "type": "string"
          },
          "priceChangePercent": {
            "type": "string"
          },
          "symbol": {
            "type": "string"
          },
          "volume": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "box-api": {
    "files.json": {
      "items": {
        "keys": {
          "created_at": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "extension": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "modified_at": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "owner_id": {
            "type": "string"
          },
          "parent_id": {
            "type": "string"
          },
          "sha1": {
            "type": "string"
          },
          "size": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "folders.json": {
      "items": {
        "keys": {
          "created_at": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "item_count": {
            "type": "string"
          },
          "modified_at": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "owner_id": {
            "type": "string"
          },
          "parent_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "users.json": {
      "items": {
        "keys": {
          "created_at": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "job_title": {
            "type": "string"
          },
          "language": {
            "type": "string"
          },
          "login": {
            "type": "string"
          },
          "max_upload_size": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "phone": {
            "type": "string"
          },
          "role": {
            "type": "string"
          },
          "space_amount": {
            "type": "string"
          },
          "space_used": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "timezone": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "calendly-api": {
    "availability.json": {
      "items": {
        "keys": {
          "end_time": {
            "type": "string"
          },
          "owner": {
            "type": "string"
          },
          "start_time": {
            "type": "string"
          },
          "timezone": {
            "type": "string"
          },
          "weekday": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "event_types.json": {
      "items": {
        "keys": {
          "active": {
            "type": "string"
          },
          "color": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "duration": {
            "type": "string"
          },
          "kind": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "owner": {
            "type": "string"
          },
          "scheduling_url": {
            "type": "string"
          },
          "slug": {
            "type": "string"
          },
          "uuid": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "invitees.json": {
      "items": {
        "keys": {
          "created_at": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "event": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "questions_and_answers": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "timezone": {
            "type": "string"
          },
          "uuid": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "scheduled_events.json": {
      "items": {
        "keys": {
          "canceled_reason": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "end_time": {
            "type": "string"
          },
          "event_type": {
            "type": "string"
          },
          "location": {
            "type": "string"
          },
          "location_type": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "owner": {
            "type": "string"
          },
          "start_time": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "uuid": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "user.json": {
      "keys": {
        "created_at": {
          "type": "string"
        },
        "current_organization": {
          "type": "string"
        },
        "email": {
          "type": "string"
        },
        "name": {
          "type": "string"
        },
        "scheduling_url": {
          "type": "string"
        },
        "slug": {
          "type": "string"
        },
        "timezone": {
          "type": "string"
        },
        "updated_at": {
          "type": "string"
        },
        "uuid": {
          "type": "string"
        }
      },
      "type": "object"
    }
  },
  "cloudflare-api": {
    "dns_records.json": {
      "items": {
        "keys": {
          "content": {
            "type": "string"
          },
          "created_on": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "modified_on": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "priority": {
            "type": "string"
          },
          "proxied": {
            "type": "string"
          },
          "ttl": {
            "type": "string"
          },
          "type": {
            "type": "string"
          },
          "zone_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "firewall_rules.json": {
      "items": {
        "keys": {
          "action": {
            "type": "string"
          },
          "created_on": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "expression": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "paused": {
            "type": "string"
          },
          "priority": {
            "type": "string"
          },
          "zone_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "page_rules.json": {
      "items": {
        "keys": {
          "created_on": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "priority": {
            "type": "string"
          },
          "setting": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "target": {
            "type": "string"
          },
          "value": {
            "type": "string"
          },
          "zone_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "zones.json": {
      "items": {
        "keys": {
          "created_on": {
            "type": "string"
          },
          "development_mode": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "modified_on": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "paused": {
            "type": "string"
          },
          "plan": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "coinbase-api": {
    "accounts.json": {
      "items": {
        "keys": {
          "balance_amount": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "currency_code": {
            "type": "string"
          },
          "currency_name": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "native_balance_amount": {
            "type": "string"
          },
          "native_currency": {
            "type": "string"
          },
          "primary": {
            "type": "string"
          },
          "type": {
            "type": "string"
          },
          "updated_at": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "prices.json": {
      "items": {
        "keys": {
          "amount": {
            "type": "string"
          },
          "base": {
            "type": "string"
          },
          "currency": {
            "type": "string"
          },
          "pair": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "transactions.json": {
      "items": {
        "keys": {
          "account_id": {
            "type": "string"
          },
          "amount": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "currency": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "native_amount": {
            "type": "string"
          },
          "native_currency": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "user.json": {
      "keys": {
        "country": {
          "keys": {
            "code": {
              "type": "string"
            },
            "name": {
              "type": "string"
            }
          },
          "type": "object"
        },
        "created_at": {
          "type": "string"
        },
        "email": {
          "type": "string"
        },
        "id": {
          "type": "string"
        },
        "name": {
          "type": "string"
        },
        "native_currency": {
          "type": "string"
        },
        "profile_location": {
          "type": "string"
        },
        "username": {
          "type": "string"
        }
      },
      "type": "object"
    }
  },
  "confluence-api": {
    "comments.json": {
      "items": {
        "keys": {
          "author": {
            "type": "string"
          },
          "body": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "page_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "labels.json": {
      "items": {
        "keys": {
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "page_id": {
            "type": "string"
          },
          "prefix": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "pages.json": {
      "items": {
        "keys": {
          "body": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "created_by": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "parent_id": {
            "type": "string"
          },
          "space_key": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "type": {
            "type": "string"
          },
          "version": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "spaces.json": {
      "items": {
        "keys": {
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "key": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "contentful-api": {
    "assets.json": {
      "items": {
        "keys": {
          "content_type": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "file_name": {
            "type": "string"
          },
          "file_url": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "published_version": {
            "type": "string"
          },
          "size": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "updated_at": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "content_types.json": {
      "items": {
        "keys": {
          "description": {
            "type": "string"
          },
          "displayField": {
            "type": "string"
          },
          "fields_json": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "entries.json": {
      "items": {
        "keys": {
          "content_type": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "fields_json": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "published_version": {
            "type": "string"
          },
          "updated_at": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "space.json": {
      "keys": {
        "created_at": {
          "type": "string"
        },
        "default_environment": {
          "type": "string"
        },
        "id": {
          "type": "string"
        },
        "locales": {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        "name": {
          "type": "string"
        },
        "organization": {
          "type": "string"
        }
      },
      "type": "object"
    }
  },
  "datadog-api": {
    "dashboards.json": {
      "items": {
        "keys": {
          "author": {
            "type": "string"
          },
          "created": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "is_read_only": {
            "type": "string"
          },
          "layout_type": {
            "type": "string"
          },
          "modified": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "widget_count": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "events.json": {
      "items": {
        "keys": {
          "alert_type": {
            "type": "string"
          },
          "date_happened": {
            "type": "string"
          },
          "host": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "priority": {
            "type": "string"
          },
          "tags": {
            "type": "string"
          },
          "text": {
            "type": "string"
          },
          "title": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "hosts.json": {
      "items": {
        "keys": {
          "apps": {
            "type": "string"
          },
          "cpu_pct": {
            "type": "string"
          },
          "last_reported": {
            "type": "string"
          },
          "mem_pct": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "sources": {
            "type": "string"
          },
          "up": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "metrics.json": {
      "items": {
        "keys": {
          "amplitude": {
            "type": "string"
          },
          "base_value": {
            "type": "string"
          },
          "metric": {
            "type": "string"
          },
          "scope": {
            "type": "string"
          },
          "unit": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "monitors.json": {
      "items": {
        "keys": {
          "created": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "modified": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "overall_state": {
            "type": "string"
          },
          "priority": {
            "type": "string"
          },
          "query": {
            "type": "string"
          },
          "tags": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "discord-api": {
    "channels.json": {
      "items": {
        "keys": {
          "guild_id": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "nsfw": {
            "type": "string"
          },
          "position": {
            "type": "string"
          },
          "topic": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "guilds.json": {
      "items": {
        "keys": {
          "description": {
            "type": "string"
          },
          "icon": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "member_count": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "owner_id": {
            "type": "string"
          },
          "region": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "me.json": {
      "keys": {
        "avatar": {
          "type": "string"
        },
        "bot": {
          "type": "boolean"
        },
        "discriminator": {
          "type": "string"
        },
        "email": {
          "type": "string"
        },
        "flags": {
          "type": "number"
        },
        "global_name": {
          "type": "string"
        },
        "id": {
          "type": "string"
        },
        "username": {
          "type": "string"
        },
        "verified": {
          "type": "boolean"
        }
      },
      "type": "object"
    },
    "members.json": {
      "items": {
        "keys": {
          "bot": {
            "type": "string"
          },
          "global_name": {
            "type": "string"
          },
          "guild_id": {
            "type": "string"
          },
          "joined_at": {
            "type": "string"
          },
          "nick": {
            "type": "string"
          },
          "roles": {
            "type": "string"
          },
          "user_id": {
            "type": "string"
          },
          "username": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "messages.json": {
      "items": {
        "keys": {
          "author_id": {
            "type": "string"
          },
          "author_username": {
            "type": "string"
          },
          "channel_id": {
            "type": "string"
          },
          "content": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "pinned": {
            "type": "string"
          },
          "timestamp": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "roles.json": {
      "items": {
        "keys": {
          "color": {
            "type": "string"
          },
          "guild_id": {
            "type": "string"
          },
          "hoist": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "mentionable": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "permissions": {
            "type": "string"
          },
          "position": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "docusign-api": {
    "documents.json": {
      "items": {
        "keys": {
          "document_id": {
            "type": "string"
          },
          "document_type": {
            "type": "string"
          },
          "envelope_id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "order": {
            "type": "string"
          },
          "page_count": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "envelopes.json": {
      "items": {
        "keys": {
          "completed_time": {
            "type": "string"
          },
          "created_time": {
            "type": "string"
          },
          "email_subject": {
            "type": "string"
          },
          "envelope_id": {
            "type": "string"
          },
          "sender_email": {
            "type": "string"
          },
          "sender_name": {
            "type": "string"
          },
          "sent_time": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "template_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "recipients.json": {
      "items": {
        "keys": {
          "email": {
            "type": "string"
          },
          "envelope_id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "recipient_id": {
            "type": "string"
          },
          "recipient_type": {
            "type": "string"
          },
          "routing_order": {
            "type": "string"
          },
          "signed_time": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "templates.json": {
      "items": {
        "keys": {
          "created_time": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "owner_name": {
            "type": "string"
          },
          "shared": {
            "type": "string"
          },
          "template_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "doordash-api": {
    "menu_items.json": {
      "items": {
        "keys": {
          "available": {
            "type": "string"
          },
          "calories": {
            "type": "string"
          },
          "category": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "item_id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "popular": {
            "type": "string"
          },
          "price": {
            "type": "string"
          },
          "store_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "order_items.json": {
      "items": {
        "keys": {
          "item_id": {
            "type": "string"
          },
          "line_total": {
            "type": "string"
          },
          "order_id": {
            "type": "string"
          },
          "quantity": {
            "type": "string"
          },
          "unit_price": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "orders.json": {
      "items": {
        "keys": {
          "customer_name": {
            "type": "string"
          },
          "dasher_name": {
            "type": "string"
          },
          "delivery_fee": {
            "type": "string"
          },
          "order_id": {
            "type": "string"
          },
          "placed_at": {
            "type": "string"
          },
          "service_fee": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "store_id": {
            "type": "string"
          },
          "subtotal": {
            "type": "string"
          },
          "tip": {
            "type": "string"
          },
          "total": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "stores.json": {
      "items": {
        "keys": {
          "address": {
            "type": "string"
          },
          "cuisine": {
            "type": "string"
          },
          "delivery_fee": {
            "type": "string"
          },
          "eta_minutes": {
            "type": "string"
          },
          "is_open": {
            "type": "string"
          },
          "latitude": {
            "type": "string"
          },
          "longitude": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "price_range": {
            "type": "string"
          },
          "rating": {
            "type": "string"
          },
          "review_count": {
            "type": "string"
          },
          "store_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "dropbox-api": {
    "account.json": {
      "items": {
        "keys": {
          "account_id": {
            "type": "string"
          },
          "account_type": {
            "type": "string"
          },
          "country": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "email_verified": {
            "type": "string"
          },
          "locale": {
            "type": "string"
          },
          "name_display": {
            "type": "string"
          },
          "name_given": {
            "type": "string"
          },
          "name_surname": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "files.json": {
      "items": {
        "keys": {
          "client_modified": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "is_folder": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "path_display": {
            "type": "string"
          },
          "path_lower": {
            "type": "string"
          },
          "rev": {
            "type": "string"
          },
          "size": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "shared_links.json": {
      "items": {
        "keys": {
          "file_id": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "path_lower": {
            "type": "string"
          },
          "url": {
            "type": "string"
          },
          "visibility": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "etsy-api": {
    "listing_images.json": {
      "items": {
        "keys": {
          "alt_text": {
            "type": "string"
          },
          "created_timestamp": {
            "type": "string"
          },
          "listing_id": {
            "type": "string"
          },
          "listing_image_id": {
            "type": "string"
          },
          "rank": {
            "type": "string"
          },
          "shop_id": {
            "type": "string"
          },
          "url_170x135": {
            "type": "string"
          },
          "url_570xN": {
            "type": "string"
          },
          "url_75x75": {
            "type": "string"
          },
          "url_fullxfull": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "listings.json": {
      "items": {
        "keys": {
          "created_timestamp": {
            "type": "string"
          },
          "currency_code": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "ending_timestamp": {
            "type": "string"
          },
          "is_customizable": {
            "type": "string"
          },
          "is_personalizable": {
            "type": "string"
          },
          "is_supply": {
            "type": "string"
          },
          "item_dimensions_unit": {
            "type": "string"
          },
          "item_height": {
            "type": "string"
          },
          "item_length": {
            "type": "string"
          },
          "item_weight": {
            "type": "string"
          },
          "item_weight_unit": {
            "type": "string"
          },
          "item_width": {
            "type": "string"
          },
          "listing_id": {
            "type": "string"
          },
          "materials": {
            "type": "string"
          },
          "num_favorers": {
            "type": "string"
          },
          "price": {
            "type": "string"
          },
          "processing_max": {
            "type": "string"
          },
          "processing_min": {
            "type": "string"
          },
          "quantity": {
            "type": "string"
          },
          "return_policy_id": {
            "type": "string"
          },
          "shipping_profile_id": {
            "type": "string"
          },
          "shop_id": {
            "type": "string"
          },
          "shop_section_id": {
            "type": "string"
          },
          "state": {
            "type": "string"
          },
          "tags": {
            "type": "string"
          },
          "taxonomy_id": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "updated_timestamp": {
            "type": "string"
          },
          "views": {
            "type": "string"
          },
          "when_made": {
            "type": "string"
          },
          "who_made": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "receipts.json": {
      "items": {
        "keys": {
          "address_city": {
            "type": "string"
          },
          "address_country": {
            "type": "string"
          },
          "address_first_line": {
            "type": "string"
          },
          "address_state": {
            "type": "string"
          },
          "address_zip": {
            "type": "string"
          },
          "buyer_email": {
            "type": "string"
          },
          "buyer_user_id": {
            "type": "string"
          },
          "created_timestamp": {
            "type": "string"
          },
          "discount_amt": {
            "type": "string"
          },
          "estimated_delivery": {
            "type": "string"
          },
          "gift_message": {
            "type": "string"
          },
          "grandtotal": {
            "type": "string"
          },
          "is_gift": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "payment_method": {
            "type": "string"
          },
          "receipt_id": {
            "type": "string"
          },
          "shipped_timestamp": {
            "type": "string"
          },
          "shipping_carrier": {
            "type": "string"
          },
          "shop_id": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "subtotal": {
            "type": "string"
          },
          "total_shipping_cost": {
            "type": "string"
          },
          "total_tax_cost": {
            "type": "string"
          },
          "tracking_code": {
            "type": "string"
          },
          "updated_timestamp": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "return_policies.json": {
      "items": {
        "keys": {
          "accepts_exchanges": {
            "type": "string"
          },
          "accepts_returns": {
            "type": "string"
          },
          "return_deadline": {
            "type": "string"
          },
          "return_policy_id": {
            "type": "string"
          },
          "shop_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "reviews.json": {
      "items": {
        "keys": {
          "buyer_user_id": {
            "type": "string"
          },
          "created_timestamp": {
            "type": "string"
          },
          "image_url": {
            "type": "string"
          },
          "language": {
            "type": "string"
          },
          "listing_id": {
            "type": "string"
          },
          "rating": {
            "type": "string"
          },
          "review": {
            "type": "string"
          },
          "review_id": {
            "type": "string"
          },
          "shop_id": {
            "type": "string"
          },
          "updated_timestamp": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "shipping_profiles.json": {
      "items": {
        "keys": {
          "cost": {
            "type": "string"
          },
          "max_delivery_days": {
            "type": "string"
          },
          "min_delivery_days": {
            "type": "string"
          },
          "origin_country": {
            "type": "string"
          },
          "origin_postal_code": {
            "type": "string"
          },
          "processing_max": {
            "type": "string"
          },
          "processing_min": {
            "type": "string"
          },
          "secondary_cost": {
            "type": "string"
          },
          "shipping_profile_id": {
            "type": "string"
          },
          "shop_id": {
            "type": "string"
          },
          "title": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "shop.json": {
      "keys": {
        "accepts_custom_requests": {
          "type": "boolean"
        },
        "announcement": {
          "type": "string"
        },
        "create_date": {
          "type": "string"
        },
        "currency_code": {
          "type": "string"
        },
        "digital_listing_count": {
          "type": "number"
        },
        "digital_sale_message": {
          "type": "null"
        },
        "icon_url_fullxfull": {
          "type": "string"
        },
        "image_url_760x100": {
          "type": "string"
        },
        "is_vacation": {
          "type": "boolean"
        },
        "listing_active_count": {
          "type": "number"
        },
        "login_name": {
          "type": "string"
        },
        "num_favorers": {
          "type": "number"
        },
        "policy_payment": {
          "type": "string"
        },
        "policy_refunds": {
          "type": "string"
        },
        "policy_shipping": {
          "type": "string"
        },
        "policy_welcome": {
          "type": "string"
        },
        "review_average": {
          "type": "number"
        },
        "review_count": {
          "type": "number"
        },
        "sale_message": {
          "type": "string"
        },
        "shop_id": {
          "type": "number"
        },
        "shop_name": {
          "type": "string"
        },
        "title": {
          "type": "string"
        },
        "update_date": {
          "type": "string"
        },
        "url": {
          "type": "string"
        },
        "user_id": {
          "type": "number"
        },
        "vacation_message": {
          "type": "null"
        }
      },
      "type": "object"
    },
    "shop_sections.json": {
      "items": {
        "keys": {
          "active_listing_count": {
            "type": "string"
          },
          "rank": {
            "type": "string"
          },
          "shop_id": {
            "type": "string"
          },
          "shop_section_id": {
            "type": "string"
          },
          "title": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "transactions.json": {
      "items": {
        "keys": {
          "buyer_user_id": {
            "type": "string"
          },
          "created_timestamp": {
            "type": "string"
          },
          "is_digital": {
            "type": "string"
          },
          "listing_id": {
            "type": "string"
          },
          "price": {
            "type": "string"
          },
          "quantity": {
            "type": "string"
          },
          "receipt_id": {
            "type": "string"
          },
          "shipping_cost": {
            "type": "string"
          },
          "shop_id": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "transaction_id": {
            "type": "string"
          },
          "variations": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "eventbrite-api": {
    "attendees.json": {
      "items": {
        "keys": {
          "checked_in": {
            "type": "string"
          },
          "created": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "event_id": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "ticket_class_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "events.json": {
      "items": {
        "keys": {
          "capacity": {
            "type": "string"
          },
          "created": {
            "type": "string"
          },
          "end_utc": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "is_free": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "online_event": {
            "type": "string"
          },
          "organization_id": {
            "type": "string"
          },
          "start_utc": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "summary": {
            "type": "string"
          },
          "timezone": {
            "type": "string"
          },
          "url": {
            "type": "string"
          },
          "venue_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "organizations.json": {
      "items": {
        "keys": {
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "image_url": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "vertical": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "ticket_classes.json": {
      "items": {
        "keys": {
          "cost": {
            "type": "string"
          },
          "event_id": {
            "type": "string"
          },
          "fee": {
            "type": "string"
          },
          "free": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "quantity_sold": {
            "type": "string"
          },
          "quantity_total": {
            "type": "string"
          },
          "sales_end": {
            "type": "string"
          },
          "sales_start": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "venues.json": {
      "items": {
        "keys": {
          "address1": {
            "type": "string"
          },
          "city": {
            "type": "string"
          },
          "country": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "latitude": {
            "type": "string"
          },
          "longitude": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "postal_code": {
            "type": "string"
          },
          "region": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "fedex-api": {
    "rates.json": {
      "items": {
        "keys": {
          "currency": {
            "type": "string"
          },
          "delivery_day": {
            "type": "string"
          },
          "dest_zip": {
            "type": "string"
          },
          "net_charge": {
            "type": "string"
          },
          "origin_zip": {
            "type": "string"
          },
          "service_name": {
            "type": "string"
          },
          "service_type": {
            "type": "string"
          },
          "transit_days": {
            "type": "string"
          },
          "weight_lb": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "shipments.json": {
      "items": {
        "keys": {
          "currency": {
            "type": "string"
          },
          "dest_zip": {
            "type": "string"
          },
          "label_url": {
            "type": "string"
          },
          "net_charge": {
            "type": "string"
          },
          "origin_zip": {
            "type": "string"
          },
          "service_name": {
            "type": "string"
          },
          "service_type": {
            "type": "string"
          },
          "ship_date": {
            "type": "string"
          },
          "tracking_number": {
            "type": "string"
          },
          "weight_lb": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "tracking.json": {
      "items": {
        "keys": {
          "carrier_code": {
            "type": "string"
          },
          "estimated_delivery": {
            "type": "string"
          },
          "latest_event": {
            "type": "string"
          },
          "latest_event_location": {
            "type": "string"
          },
          "latest_event_time": {
            "type": "string"
          },
          "service_name": {
            "type": "string"
          },
          "ship_date": {
            "type": "string"
          },
          "status_code": {
            "type": "string"
          },
          "status_description": {
            "type": "string"
          },
          "tracking_number": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "figma-api": {
    "comments.json": {
      "items": {
        "keys": {
          "comment_id": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "file_key": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "node_id": {
            "type": "string"
          },
          "resolved": {
            "type": "string"
          },
          "user_handle": {
            "type": "string"
          },
          "user_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "components.json": {
      "items": {
        "keys": {
          "component_key": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "file_key": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "node_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "file_nodes.json": {
      "keys": {
        "FK001abcdefg": {
          "keys": {
            "children": {
              "items": {
                "keys": {
                  "backgroundColor": {
                    "keys": {
                      "a": {
                        "type": "number"
                      },
                      "b": {
                        "type": "number"
                      },
                      "g": {
                        "type": "number"
                      },
                      "r": {
                        "type": "number"
                      }
                    },
                    "type": "object"
                  },
                  "children": {
                    "items": {
                      "keys": {
                        "absoluteBoundingBox": {
                          "keys": {
                            "height": {
                              "type": "number"
                            },
                            "width": {
                              "type": "number"
                            },
                            "x": {
                              "type": "number"
                            },
                            "y": {
                              "type": "number"
                            }
                          },
                          "type": "object"
                        },
                        "children": {
                          "items": {
                            "keys": {
                              "characters": {
                                "type": "string"
                              },
                              "componentId": {
                                "type": "string"
                              },
                              "id": {
                                "type": "string"
                              },
                              "name": {
                                "type": "string"
                              },
                              "type": {
                                "type": "string"
                              }
                            },
                            "type": "object"
                          },
                          "type": "array"
                        },
                        "id": {
                          "type": "string"
                        },
                        "name": {
                          "type": "string"
                        },
                        "type": {
                          "type": "string"
                        }
                      },
                      "type": "object"
                    },
                    "type": "array"
                  },
                  "id": {
                    "type": "string"
                  },
                  "name": {
                    "type": "string"
                  },
                  "type": {
                    "type": "string"
                  }
                },
                "type": "object"
              },
              "type": "array"
            },
            "id": {
              "type": "string"
            },
            "name": {
              "type": "string"
            },
            "type": {
              "type": "string"
            }
          },
          "type": "object"
        },
        "FK002hijklmn": {
          "keys": {
            "children": {
              "items": {
                "keys": {
                  "backgroundColor": {
                    "keys": {
                      "a": {
                        "type": "number"
                      },
                      "b": {
                        "type": "number"
                      },
                      "g": {
                        "type": "number"
                      },
                      "r": {
                        "type": "number"
                      }
                    },
                    "type": "object"
                  },
                  "children": {
                    "items": {
                      "keys": {
                        "absoluteBoundingBox": {
                          "keys": {
                            "height": {
                              "type": "number"
                            },
                            "width": {
                              "type": "number"
                            },
                            "x": {
                              "type": "number"
                            },
                            "y": {
                              "type": "number"
                            }
                          },
                          "type": "object"
                        },
                        "children": {
                          "items": {
                            "keys": {
                              "characters": {
                                "type": "string"
                              },
                              "id": {
                                "type": "string"
                              },
                              "name": {
                                "type": "string"
                              },
                              "type": {
                                "type": "string"
                              }
                            },
                            "type": "object"
                          },
                          "type": "array"
                        },
                        "id": {
                          "type": "string"
                        },
                        "name": {
                          "type": "string"
                        },
                        "type": {
                          "type": "string"
                        }
                      },
                      "type": "object"
                    },
                    "type": "array"
                  },
                  "id": {
                    "type": "string"
                  },
                  "name": {
                    "type": "string"
                  },
                  "type": {
                    "type": "string"
                  }
                },
                "type": "object"
              },
              "type": "array"
            },
            "id": {
              "type": "string"
            },
            "name": {
              "type": "string"
            },
            "type": {
              "type": "string"
            }
          },
          "type": "object"
        },
        "FK003opqrstu": {
          "keys": {
            "children": {
              "items": {
                "keys": {
                  "backgroundColor": {
                    "keys": {
                      "a": {
                        "type": "number"
                      },
                      "b": {
                        "type": "number"
                      },
                      "g": {
                        "type": "number"
                      },
                      "r": {
                        "type": "number"
                      }
                    },
                    "type": "object"
                  },
                  "children": {
                    "items": {
                      "keys": {
                        "absoluteBoundingBox": {
                          "keys": {
                            "height": {
                              "type": "number"
                            },
                            "width": {
                              "type": "number"
                            },
                            "x": {
                              "type": "number"
                            },
                            "y": {
                              "type": "number"
                            }
                          },
                          "type": "object"
                        },
                        "children": {
                          "items": {
                            "keys": {
                              "characters": {
                                "type": "string"
                              },
                              "id": {
                                "type": "string"
                              },
                              "name": {
                                "type": "string"
                              },
                              "type": {
                                "type": "string"
                              }
                            },
                            "type": "object"
                          },
                          "type": "array"
                        },
                        "id": {
                          "type": "string"
                        },
                        "name": {
                          "type": "string"
                        },
                        "type": {
                          "type": "string"
                        }
                      },
                      "type": "object"
                    },
                    "type": "array"
                  },
                  "id": {
                    "type": "string"
                  },
                  "name": {
                    "type": "string"
                  },
                  "type": {
                    "type": "string"
                  }
                },
                "type": "object"
              },
              "type": "array"
            },
            "id": {
              "type": "string"
            },
            "name": {
              "type": "string"
            },
            "type": {
              "type": "string"
            }
          },
          "type": "object"
        },
        "FK004vwxyz12": {
          "keys": {
            "children": {
              "items": {
                "keys": {
                  "backgroundColor": {
                    "keys": {
                      "a": {
                        "type": "number"
                      },
                      "b": {
                        "type": "number"
                      },
                      "g": {
                        "type": "number"
                      },
                      "r": {
                        "type": "number"
                      }
                    },
                    "type": "object"
                  },
                  "children": {
                    "items": {
                      "keys": {
                        "absoluteBoundingBox": {
                          "keys": {
                            "height": {
                              "type": "number"
                            },
                            "width": {
                              "type": "number"
                            },
                            "x": {
                              "type": "number"
                            },
                            "y": {
                              "type": "number"
                            }
                          },
                          "type": "object"
                        },
                        "children": {
                          "items": {
                            "keys": {
                              "componentId": {
                                "type": "string"
                              },
                              "id": {
                                "type": "string"
                              },
                              "name": {
                                "type": "string"
                              },
                              "type": {
                                "type": "string"
                              }
                            },
                            "type": "object"
                          },
                          "type": "array"
                        },
                        "id": {
                          "type": "string"
                        },
                        "name": {
                          "type": "string"
                        },
                        "type": {
                          "type": "string"
                        }
                      },
                      "type": "object"
                    },
                    "type": "array"
                  },
                  "id": {
                    "type": "string"
                  },
                  "name": {
                    "type": "string"
                  },
                  "type": {
                    "type": "string"
                  }
                },
                "type": "object"
              },
              "type": "array"
            },
            "id": {
              "type": "string"
            },
            "name": {
              "type": "string"
            },
            "type": {
              "type": "string"
            }
          },
          "type": "object"
        }
      },
      "type": "object"
    },
    "files.json": {
      "items": {
        "keys": {
          "editor_type": {
            "type": "string"
          },
          "file_key": {
            "type": "string"
          },
          "last_modified": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "project_id": {
            "type": "string"
          },
          "role": {
            "type": "string"
          },
          "thumbnail_url": {
            "type": "string"
          },
          "version": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "projects.json": {
      "items": {
        "keys": {
          "name": {
            "type": "string"
          },
          "project_id": {
            "type": "string"
          },
          "team_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "team.json": {
      "keys": {
        "me": {
          "keys": {
            "email": {
              "type": "string"
            },
            "handle": {
              "type": "string"
            },
            "id": {
              "type": "string"
            },
            "img_url": {
              "type": "string"
            }
          },
          "type": "object"
        },
        "team": {
          "keys": {
            "id": {
              "type": "string"
            },
            "name": {
              "type": "string"
            }
          },
          "type": "object"
        },
        "users": {
          "items": {
            "keys": {
              "email": {
                "type": "string"
              },
              "handle": {
                "type": "string"
              },
              "id": {
                "type": "string"
              },
              "img_url": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "type": "array"
        }
      },
      "type": "object"
    }
  },
  "freshdesk-api": {
    "agents.json": {
      "items": {
        "keys": {
          "available": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "occasional": {
            "type": "string"
          },
          "ticket_scope": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "contacts.json": {
      "items": {
        "keys": {
          "active": {
            "type": "string"
          },
          "company_id": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "phone": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "tickets.json": {
      "items": {
        "keys": {
          "created_at": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "priority": {
            "type": "string"
          },
          "requester_id": {
            "type": "string"
          },
          "responder_id": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "subject": {
            "type": "string"
          },
          "tags": {
            "type": "string"
          },
          "type": {
            "type": "string"
          },
          "updated_at": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "github-api": {
    "comments.json": {
      "items": {
        "keys": {
          "body": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "issue_number": {
            "type": "string"
          },
          "repo": {
            "type": "string"
          },
          "user": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "issues.json": {
      "items": {
        "keys": {
          "assignee": {
            "type": "string"
          },
          "body": {
            "type": "string"
          },
          "closed_at": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "is_pull_request": {
            "type": "string"
          },
          "labels": {
            "type": "string"
          },
          "milestone": {
            "type": "string"
          },
          "number": {
            "type": "string"
          },
          "repo": {
            "type": "string"
          },
          "state": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "updated_at": {
            "type": "string"
          },
          "user": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "pulls.json": {
      "items": {
        "keys": {
          "additions": {
            "type": "string"
          },
          "base_branch": {
            "type": "string"
          },
          "changed_files": {
            "type": "string"
          },
          "checks_status": {
            "type": "string"
          },
          "deletions": {
            "type": "string"
          },
          "draft": {
            "type": "string"
          },
          "head_branch": {
            "type": "string"
          },
          "mergeable": {
            "type": "string"
          },
          "merged": {
            "type": "string"
          },
          "number": {
            "type": "string"
          },
          "repo": {
            "type": "string"
          },
          "review_state": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "repos.json": {
      "items": {
        "keys": {
          "created_at": {
            "type": "string"
          },
          "default_branch": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "forks": {
            "type": "string"
          },
          "full_name": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "language": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "open_issues": {
            "type": "string"
          },
          "owner": {
            "type": "string"
          },
          "private": {
            "type": "string"
          },
          "stars": {
            "type": "string"
          },
          "updated_at": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "user.json": {
      "keys": {
        "avatar_url": {
          "type": "string"
        },
        "company": {
          "type": "string"
        },
        "email": {
          "type": "string"
        },
        "followers": {
          "type": "number"
        },
        "following": {
          "type": "number"
        },
        "id": {
          "type": "number"
        },
        "login": {
          "type": "string"
        },
        "name": {
          "type": "string"
        },
        "public_repos": {
          "type": "number"
        },
        "site_admin": {
          "type": "boolean"
        },
        "type": {
          "type": "string"
        }
      },
      "type": "object"
    }
  },
  "gitlab-api": {
    "current_user.json": {
      "keys": {
        "avatar_url": {
          "type": "string"
        },
        "bio": {
          "type": "string"
        },
        "created_at": {
          "type": "string"
        },
        "email": {
          "type": "string"
        },
        "id": {
          "type": "number"
        },
        "is_admin": {
          "type": "boolean"
        },
        "name": {
          "type": "string"
        },
        "state": {
          "type": "string"
        },
        "username": {
          "type": "string"
        },
        "web_url": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "issues.json": {
      "items": {
        "keys": {
          "assignee": {
            "type": "string"
          },
          "author": {
            "type": "string"
          },
          "closed_at": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "iid": {
            "type": "string"
          },
          "labels": {
            "type": "string"
          },
          "project_id": {
            "type": "string"
          },
          "state": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "updated_at": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "merge_requests.json": {
      "items": {
        "keys": {
          "assignee": {
            "type": "string"
          },
          "author": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "draft": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "iid": {
            "type": "string"
          },
          "merge_status": {
            "type": "string"
          },
          "merged_at": {
            "type": "string"
          },
          "project_id": {
            "type": "string"
          },
          "source_branch": {
            "type": "string"
          },
          "state": {
            "type": "string"
          },
          "target_branch": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "updated_at": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "pipelines.json": {
      "items": {
        "keys": {
          "created_at": {
            "type": "string"
          },
          "duration": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "project_id": {
            "type": "string"
          },
          "ref": {
            "type": "string"
          },
          "sha": {
            "type": "string"
          },
          "source": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "updated_at": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "projects.json": {
      "items": {
        "keys": {
          "created_at": {
            "type": "string"
          },
          "default_branch": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "forks_count": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "last_activity_at": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "namespace": {
            "type": "string"
          },
          "open_issues_count": {
            "type": "string"
          },
          "path": {
            "type": "string"
          },
          "path_with_namespace": {
            "type": "string"
          },
          "star_count": {
            "type": "string"
          },
          "visibility": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "users.json": {
      "items": {
        "keys": {
          "created_at": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "is_admin": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "state": {
            "type": "string"
          },
          "username": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "gmail-api": {
    "drafts.json": {
      "items": {
        "keys": {
          "body": {
            "type": "string"
          },
          "cc_addr": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "subject": {
            "type": "string"
          },
          "thread_id": {
            "type": "string"
          },
          "to_addr": {
            "type": "string"
          },
          "updated_at": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "labels.json": {
      "items": {
        "keys": {
          "id": {
            "type": "string"
          },
          "messages_total": {
            "type": "string"
          },
          "messages_unread": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "threads_total": {
            "type": "string"
          },
          "threads_unread": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "messages.json": {
      "items": {
        "keys": {
          "body": {
            "type": "string"
          },
          "cc_addr": {
            "type": "string"
          },
          "date": {
            "type": "string"
          },
          "from_addr": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "internal_date": {
            "type": "string"
          },
          "is_starred": {
            "type": "string"
          },
          "is_unread": {
            "type": "string"
          },
          "labels": {
            "type": "string"
          },
          "size_estimate": {
            "type": "string"
          },
          "snippet": {
            "type": "string"
          },
          "subject": {
            "type": "string"
          },
          "thread_id": {
            "type": "string"
          },
          "to_addr": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "profile.json": {
      "keys": {
        "emailAddress": {
          "type": "string"
        },
        "historyId": {
          "type": "string"
        },
        "messagesTotal": {
          "type": "number"
        },
        "threadsTotal": {
          "type": "number"
        }
      },
      "type": "object"
    }
  },
  "google-analytics-api": {
    "events.json": {
      "items": {
        "keys": {
          "activeUsers": {
            "type": "string"
          },
          "country": {
            "type": "string"
          },
          "date": {
            "type": "string"
          },
          "deviceCategory": {
            "type": "string"
          },
          "eventCount": {
            "type": "string"
          },
          "pagePath": {
            "type": "string"
          },
          "screenPageViews": {
            "type": "string"
          },
          "sessions": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "property.json": {
      "keys": {
        "create_time": {
          "type": "string"
        },
        "currency_code": {
          "type": "string"
        },
        "industry_category": {
          "type": "string"
        },
        "name": {
          "type": "string"
        },
        "property_id": {
          "type": "string"
        },
        "time_zone": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "realtime.json": {
      "items": {
        "keys": {
          "activeUsers": {
            "type": "string"
          },
          "country": {
            "type": "string"
          },
          "deviceCategory": {
            "type": "string"
          },
          "eventCount": {
            "type": "string"
          },
          "unifiedScreenName": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "google-calendar-api": {
    "calendars.json": {
      "items": {
        "keys": {
          "access_role": {
            "type": "string"
          },
          "color_id": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "primary": {
            "type": "string"
          },
          "summary": {
            "type": "string"
          },
          "time_zone": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "event_attendees.json": {
      "items": {
        "keys": {
          "display_name": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "event_id": {
            "type": "string"
          },
          "optional": {
            "type": "string"
          },
          "organizer": {
            "type": "string"
          },
          "response_status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "events.json": {
      "items": {
        "keys": {
          "all_day": {
            "type": "string"
          },
          "calendar_id": {
            "type": "string"
          },
          "creator": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "end": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "location": {
            "type": "string"
          },
          "organizer": {
            "type": "string"
          },
          "recurrence": {
            "type": "string"
          },
          "start": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "summary": {
            "type": "string"
          },
          "visibility": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "google-classroom-api": {
    "announcements.json": {
      "items": {
        "keys": {
          "alternateLink": {
            "type": "string"
          },
          "courseId": {
            "type": "string"
          },
          "creationTime": {
            "type": "string"
          },
          "creatorUserId": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "state": {
            "type": "string"
          },
          "text": {
            "type": "string"
          },
          "updateTime": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "courses.json": {
      "items": {
        "keys": {
          "alternateLink": {
            "type": "string"
          },
          "calendarId": {
            "type": "string"
          },
          "courseState": {
            "type": "string"
          },
          "creationTime": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "descriptionHeading": {
            "type": "string"
          },
          "enrollmentCode": {
            "type": "string"
          },
          "guardiansEnabled": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "ownerId": {
            "type": "string"
          },
          "room": {
            "type": "string"
          },
          "section": {
            "type": "string"
          },
          "updateTime": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "coursework.json": {
      "items": {
        "keys": {
          "alternateLink": {
            "type": "string"
          },
          "courseId": {
            "type": "string"
          },
          "creationTime": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "dueDate_day": {
            "type": "string"
          },
          "dueDate_month": {
            "type": "string"
          },
          "dueDate_year": {
            "type": "string"
          },
          "dueTime_hours": {
            "type": "string"
          },
          "dueTime_minutes": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "maxPoints": {
            "type": "string"
          },
          "state": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "topicId": {
            "type": "string"
          },
          "updateTime": {
            "type": "string"
          },
          "workType": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "materials.json": {
      "items": {
        "keys": {
          "alternateLink": {
            "type": "string"
          },
          "courseId": {
            "type": "string"
          },
          "creationTime": {
            "type": "string"
          },
          "creatorUserId": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "materialType": {
            "type": "string"
          },
          "materialUrl": {
            "type": "string"
          },
          "state": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "topicId": {
            "type": "string"
          },
          "updateTime": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "students.json": {
      "items": {
        "keys": {
          "courseId": {
            "type": "string"
          },
          "emailAddress": {
            "type": "string"
          },
          "fullName": {
            "type": "string"
          },
          "photoUrl": {
            "type": "string"
          },
          "userId": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "submissions.json": {
      "items": {
        "keys": {
          "alternateLink": {
            "type": "string"
          },
          "assignedGrade": {
            "type": "string"
          },
          "courseId": {
            "type": "string"
          },
          "courseWorkId": {
            "type": "string"
          },
          "creationTime": {
            "type": "string"
          },
          "draftGrade": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "late": {
            "type": "string"
          },
          "state": {
            "type": "string"
          },
          "updateTime": {
            "type": "string"
          },
          "userId": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "teachers.json": {
      "items": {
        "keys": {
          "courseId": {
            "type": "string"
          },
          "emailAddress": {
            "type": "string"
          },
          "fullName": {
            "type": "string"
          },
          "photoUrl": {
            "type": "string"
          },
          "userId": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "topics.json": {
      "items": {
        "keys": {
          "courseId": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "topicId": {
            "type": "string"
          },
          "updateTime": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "google-drive-api": {
    "about.json": {
      "keys": {
        "maxUploadSize": {
          "type": "string"
        },
        "storageQuota": {
          "keys": {
            "limit": {
              "type": "string"
            },
            "usage": {
              "type": "string"
            },
            "usageInDrive": {
              "type": "string"
            },
            "usageInDriveTrash": {
              "type": "string"
            }
          },
          "type": "object"
        },
        "user": {
          "keys": {
            "displayName": {
              "type": "string"
            },
            "emailAddress": {
              "type": "string"
            },
            "permissionId": {
              "type": "string"
            }
          },
          "type": "object"
        }
      },
      "type": "object"
    },
    "files.json": {
      "items": {
        "keys": {
          "created_time": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "mime_type": {
            "type": "string"
          },
          "modified_time": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "owner_email": {
            "type": "string"
          },
          "parent_id": {
            "type": "string"
          },
          "size": {
            "type": "string"
          },
          "starred": {
            "type": "string"
          },
          "trashed": {
            "type": "string"
          },
          "web_view_link": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "permissions.json": {
      "items": {
        "keys": {
          "display_name": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "file_id": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "role": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "google-maps-api": {
    "geocodes.json": {
      "items": {
        "keys": {
          "formatted_address": {
            "type": "string"
          },
          "lat": {
            "type": "string"
          },
          "lng": {
            "type": "string"
          },
          "location_type": {
            "type": "string"
          },
          "place_id": {
            "type": "string"
          },
          "query": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "places.json": {
      "items": {
        "keys": {
          "business_status": {
            "type": "string"
          },
          "formatted_address": {
            "type": "string"
          },
          "lat": {
            "type": "string"
          },
          "lng": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "place_id": {
            "type": "string"
          },
          "price_level": {
            "type": "string"
          },
          "rating": {
            "type": "string"
          },
          "types": {
            "type": "string"
          },
          "user_ratings_total": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "greenhouse-api": {
    "applications.json": {
      "items": {
        "keys": {
          "applied_at": {
            "type": "string"
          },
          "candidate_id": {
            "type": "string"
          },
          "current_stage": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "job_id": {
            "type": "string"
          },
          "last_activity_at": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "candidates.json": {
      "items": {
        "keys": {
          "company": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "first_name": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "last_name": {
            "type": "string"
          },
          "phone": {
            "type": "string"
          },
          "source": {
            "type": "string"
          },
          "title": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "jobs.json": {
      "items": {
        "keys": {
          "closed_at": {
            "type": "string"
          },
          "department": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "location": {
            "type": "string"
          },
          "opened_at": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "title": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "scorecards.json": {
      "items": {
        "keys": {
          "application_id": {
            "type": "string"
          },
          "candidate_id": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "interviewer": {
            "type": "string"
          },
          "notes": {
            "type": "string"
          },
          "overall_recommendation": {
            "type": "string"
          },
          "rating": {
            "type": "string"
          },
          "stage": {
            "type": "string"
          },
          "submitted_at": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "gusto-api": {
    "company.json": {
      "keys": {
        "company_status": {
          "type": "string"
        },
        "currency": {
          "type": "string"
        },
        "ein": {
          "type": "string"
        },
        "entity_type": {
          "type": "string"
        },
        "id": {
          "type": "string"
        },
        "name": {
          "type": "string"
        },
        "pay_schedule": {
          "type": "string"
        },
        "primary_address": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "compensations.json": {
      "items": {
        "keys": {
          "effective_date": {
            "type": "string"
          },
          "employee_id": {
            "type": "string"
          },
          "flsa_status": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "job_title": {
            "type": "string"
          },
          "payment_unit": {
            "type": "string"
          },
          "rate": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "contractors.json": {
      "items": {
        "keys": {
          "business_name": {
            "type": "string"
          },
          "company_id": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "first_name": {
            "type": "string"
          },
          "hourly_rate": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "last_name": {
            "type": "string"
          },
          "start_date": {
            "type": "string"
          },
          "type": {
            "type": "string"
          },
          "wage_type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "employees.json": {
      "items": {
        "keys": {
          "company_id": {
            "type": "string"
          },
          "department": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "first_name": {
            "type": "string"
          },
          "flsa_status": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "job_title": {
            "type": "string"
          },
          "last_name": {
            "type": "string"
          },
          "payment_unit": {
            "type": "string"
          },
          "rate": {
            "type": "string"
          },
          "start_date": {
            "type": "string"
          },
          "terminated": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "payrolls.json": {
      "items": {
        "keys": {
          "check_date": {
            "type": "string"
          },
          "company_id": {
            "type": "string"
          },
          "employee_count": {
            "type": "string"
          },
          "gross_pay": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "net_pay": {
            "type": "string"
          },
          "pay_period_end": {
            "type": "string"
          },
          "pay_period_start": {
            "type": "string"
          },
          "processed": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "hubspot-api": {
    "companies.json": {
      "items": {
        "keys": {
          "annualrevenue": {
            "type": "string"
          },
          "city": {
            "type": "string"
          },
          "createdate": {
            "type": "string"
          },
          "domain": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "industry": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "numberofemployees": {
            "type": "string"
          },
          "state": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "contacts.json": {
      "items": {
        "keys": {
          "company": {
            "type": "string"
          },
          "createdate": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "firstname": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "jobtitle": {
            "type": "string"
          },
          "lastmodifieddate": {
            "type": "string"
          },
          "lastname": {
            "type": "string"
          },
          "lifecyclestage": {
            "type": "string"
          },
          "phone": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "deals.json": {
      "items": {
        "keys": {
          "amount": {
            "type": "string"
          },
          "associated_company": {
            "type": "string"
          },
          "associated_contact": {
            "type": "string"
          },
          "closedate": {
            "type": "string"
          },
          "createdate": {
            "type": "string"
          },
          "dealname": {
            "type": "string"
          },
          "dealstage": {
            "type": "string"
          },
          "dealtype": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "lastmodifieddate": {
            "type": "string"
          },
          "pipeline": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "pipeline_stages.json": {
      "items": {
        "keys": {
          "closed": {
            "type": "string"
          },
          "display_order": {
            "type": "string"
          },
          "pipeline_id": {
            "type": "string"
          },
          "pipeline_label": {
            "type": "string"
          },
          "probability": {
            "type": "string"
          },
          "stage_id": {
            "type": "string"
          },
          "stage_label": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "instacart-api": {
    "order_items.json": {
      "items": {
        "keys": {
          "line_total": {
            "type": "string"
          },
          "order_id": {
            "type": "string"
          },
          "product_id": {
            "type": "string"
          },
          "quantity": {
            "type": "string"
          },
          "replacement_for": {
            "type": "string"
          },
          "unit_price": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "orders.json": {
      "items": {
        "keys": {
          "delivery_fee": {
            "type": "string"
          },
          "delivery_window_end": {
            "type": "string"
          },
          "delivery_window_start": {
            "type": "string"
          },
          "order_id": {
            "type": "string"
          },
          "placed_at": {
            "type": "string"
          },
          "retailer_id": {
            "type": "string"
          },
          "service_fee": {
            "type": "string"
          },
          "shopper_id": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "subtotal": {
            "type": "string"
          },
          "tip": {
            "type": "string"
          },
          "total": {
            "type": "string"
          },
          "user_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "products.json": {
      "items": {
        "keys": {
          "brand": {
            "type": "string"
          },
          "category": {
            "type": "string"
          },
          "image_url": {
            "type": "string"
          },
          "in_stock": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "price": {
            "type": "string"
          },
          "product_id": {
            "type": "string"
          },
          "retailer_id": {
            "type": "string"
          },
          "sale_price": {
            "type": "string"
          },
          "unit_size": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "retailers.json": {
      "items": {
        "keys": {
          "delivers_to_zips": {
            "type": "string"
          },
          "delivery_fee": {
            "type": "string"
          },
          "eta_minutes": {
            "type": "string"
          },
          "logo_url": {
            "type": "string"
          },
          "min_basket": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "retailer_id": {
            "type": "string"
          },
          "service_fee_pct": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "user.json": {
      "keys": {
        "default_address": {
          "keys": {
            "city": {
              "type": "string"
            },
            "line1": {
              "type": "string"
            },
            "line2": {
              "type": "string"
            },
            "state": {
              "type": "string"
            },
            "zip": {
              "type": "string"
            }
          },
          "type": "object"
        },
        "default_payment_method_id": {
          "type": "string"
        },
        "default_zip": {
          "type": "string"
        },
        "email": {
          "type": "string"
        },
        "membership": {
          "type": "string"
        },
        "name": {
          "type": "string"
        },
        "user_id": {
          "type": "string"
        }
      },
      "type": "object"
    }
  },
  "instagram-api": {
    "carousel_children.json": {
      "items": {
        "keys": {
          "id": {
            "type": "string"
          },
          "media_id": {
            "type": "string"
          },
          "media_type": {
            "type": "string"
          },
          "media_url": {
            "type": "string"
          },
          "timestamp": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "comments.json": {
      "items": {
        "keys": {
          "hidden": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "like_count": {
            "type": "string"
          },
          "media_id": {
            "type": "string"
          },
          "parent_id": {
            "type": "string"
          },
          "text": {
            "type": "string"
          },
          "timestamp": {
            "type": "string"
          },
          "user_id": {
            "type": "string"
          },
          "username": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "hashtags.json": {
      "items": {
        "keys": {
          "id": {
            "type": "string"
          },
          "media_count": {
            "type": "string"
          },
          "name": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "media.json": {
      "items": {
        "keys": {
          "caption": {
            "type": "string"
          },
          "comments_count": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "is_comment_enabled": {
            "type": "string"
          },
          "like_count": {
            "type": "string"
          },
          "media_type": {
            "type": "string"
          },
          "media_url": {
            "type": "string"
          },
          "permalink": {
            "type": "string"
          },
          "thumbnail_url": {
            "type": "string"
          },
          "timestamp": {
            "type": "string"
          },
          "user_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "media_insights.json": {
      "items": {
        "keys": {
          "engagement": {
            "type": "string"
          },
          "follows": {
            "type": "string"
          },
          "impressions": {
            "type": "string"
          },
          "media_id": {
            "type": "string"
          },
          "profile_visits": {
            "type": "string"
          },
          "reach": {
            "type": "string"
          },
          "saves": {
            "type": "string"
          },
          "shares": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "mentions.json": {
      "items": {
        "keys": {
          "caption": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "media_id": {
            "type": "string"
          },
          "media_url": {
            "type": "string"
          },
          "mentioned_by_user_id": {
            "type": "string"
          },
          "mentioned_by_username": {
            "type": "string"
          },
          "timestamp": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "stories.json": {
      "items": {
        "keys": {
          "caption": {
            "type": "string"
          },
          "expiring_at": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "link": {
            "type": "string"
          },
          "media_type": {
            "type": "string"
          },
          "media_url": {
            "type": "string"
          },
          "poll_options": {
            "type": "string"
          },
          "poll_question": {
            "type": "string"
          },
          "timestamp": {
            "type": "string"
          },
          "user_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "user.json": {
      "items": {
        "keys": {
          "account_type": {
            "type": "string"
          },
          "biography": {
            "type": "string"
          },
          "category": {
            "type": "string|null"
          },
          "followers_count": {
            "type": "number"
          },
          "follows_count": {
            "type": "number"
          },
          "id": {
            "type": "string"
          },
          "ig_id": {
            "type": "number"
          },
          "media_count": {
            "type": "number"
          },
          "name": {
            "type": "string"
          },
          "profile_picture_url": {
            "type": "string"
          },
          "username": {
            "type": "string"
          },
          "website": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "intercom-api": {
    "companies.json": {
      "items": {
        "keys": {
          "company_id": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "industry": {
            "type": "string"
          },
          "monthly_spend": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "plan": {
            "type": "string"
          },
          "user_count": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "contacts.json": {
      "items": {
        "keys": {
          "company_id": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "last_seen_at": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "phone": {
            "type": "string"
          },
          "role": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "conversation_parts.json": {
      "items": {
        "keys": {
          "author_id": {
            "type": "string"
          },
          "author_type": {
            "type": "string"
          },
          "body": {
            "type": "string"
          },
          "conversation_id": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "part_type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "conversations.json": {
      "items": {
        "keys": {
          "assignee_id": {
            "type": "string"
          },
          "contact_id": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "open": {
            "type": "string"
          },
          "state": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "updated_at": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "jira-api": {
    "boards.json": {
      "items": {
        "keys": {
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "project_key": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "issues.json": {
      "items": {
        "keys": {
          "assignee": {
            "type": "string"
          },
          "created": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "issue_type": {
            "type": "string"
          },
          "key": {
            "type": "string"
          },
          "priority": {
            "type": "string"
          },
          "project_key": {
            "type": "string"
          },
          "reporter": {
            "type": "string"
          },
          "sprint_id": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "story_points": {
            "type": "string"
          },
          "summary": {
            "type": "string"
          },
          "updated": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "projects.json": {
      "items": {
        "keys": {
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "key": {
            "type": "string"
          },
          "lead": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "project_type_key": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "sprints.json": {
      "items": {
        "keys": {
          "board_id": {
            "type": "string"
          },
          "end_date": {
            "type": "string"
          },
          "goal": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "start_date": {
            "type": "string"
          },
          "state": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "users.json": {
      "items": {
        "keys": {
          "account_id": {
            "type": "string"
          },
          "active": {
            "type": "string"
          },
          "display_name": {
            "type": "string"
          },
          "email": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "klaviyo-api": {
    "campaigns.json": {
      "items": {
        "keys": {
          "channel": {
            "type": "string"
          },
          "created": {
            "type": "string"
          },
          "from_email": {
            "type": "string"
          },
          "from_label": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "list_id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "send_time": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "subject": {
            "type": "string"
          },
          "updated": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "lists.json": {
      "items": {
        "keys": {
          "created": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "profile_count": {
            "type": "string"
          },
          "updated": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "profiles.json": {
      "items": {
        "keys": {
          "city": {
            "type": "string"
          },
          "country": {
            "type": "string"
          },
          "created": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "first_name": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "last_name": {
            "type": "string"
          },
          "organization": {
            "type": "string"
          },
          "phone_number": {
            "type": "string"
          },
          "region": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "updated": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "kraken-api": {
    "assets.json": {
      "items": {
        "keys": {
          "aclass": {
            "type": "string"
          },
          "altname": {
            "type": "string"
          },
          "asset": {
            "type": "string"
          },
          "decimals": {
            "type": "string"
          },
          "display_decimals": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "balances.json": {
      "items": {
        "keys": {
          "asset": {
            "type": "string"
          },
          "balance": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "ohlc.json": {
      "items": {
        "keys": {
          "close": {
            "type": "string"
          },
          "count": {
            "type": "string"
          },
          "high": {
            "type": "string"
          },
          "low": {
            "type": "string"
          },
          "open": {
            "type": "string"
          },
          "pair": {
            "type": "string"
          },
          "time": {
            "type": "string"
          },
          "volume": {
            "type": "string"
          },
          "vwap": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "pairs.json": {
      "items": {
        "keys": {
          "altname": {
            "type": "string"
          },
          "base": {
            "type": "string"
          },
          "lot_decimals": {
            "type": "string"
          },
          "ordermin": {
            "type": "string"
          },
          "pair": {
            "type": "string"
          },
          "pair_decimals": {
            "type": "string"
          },
          "quote": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "wsname": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "tickers.json": {
      "items": {
        "keys": {
          "altname": {
            "type": "string"
          },
          "ask": {
            "type": "string"
          },
          "bid": {
            "type": "string"
          },
          "high": {
            "type": "string"
          },
          "last": {
            "type": "string"
          },
          "low": {
            "type": "string"
          },
          "open": {
            "type": "string"
          },
          "pair": {
            "type": "string"
          },
          "volume": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "kubernetes-api": {
    "deployments.json": {
      "items": {
        "keys": {
          "available_replicas": {
            "type": "string"
          },
          "created_time": {
            "type": "string"
          },
          "image": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "namespace": {
            "type": "string"
          },
          "ready_replicas": {
            "type": "string"
          },
          "replicas": {
            "type": "string"
          },
          "strategy": {
            "type": "string"
          },
          "updated_replicas": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "namespaces.json": {
      "items": {
        "keys": {
          "created_time": {
            "type": "string"
          },
          "labels": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "nodes.json": {
      "items": {
        "keys": {
          "cpu_capacity": {
            "type": "string"
          },
          "created_time": {
            "type": "string"
          },
          "internal_ip": {
            "type": "string"
          },
          "kubelet_version": {
            "type": "string"
          },
          "memory_capacity": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "os_image": {
            "type": "string"
          },
          "role": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "pods.json": {
      "items": {
        "keys": {
          "container_name": {
            "type": "string"
          },
          "created_time": {
            "type": "string"
          },
          "image": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "namespace": {
            "type": "string"
          },
          "node": {
            "type": "string"
          },
          "phase": {
            "type": "string"
          },
          "pod_ip": {
            "type": "string"
          },
          "ready": {
            "type": "string"
          },
          "restart_count": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "services.json": {
      "items": {
        "keys": {
          "cluster_ip": {
            "type": "string"
          },
          "created_time": {
            "type": "string"
          },
          "external_ip": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "namespace": {
            "type": "string"
          },
          "port": {
            "type": "string"
          },
          "protocol": {
            "type": "string"
          },
          "selector": {
            "type": "string"
          },
          "target_port": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "linear-api": {
    "comments.json": {
      "items": {
        "keys": {
          "body": {
            "type": "string"
          },
          "createdAt": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "issueId": {
            "type": "string"
          },
          "updatedAt": {
            "type": "string"
          },
          "userId": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "cycles.json": {
      "items": {
        "keys": {
          "completedAt": {
            "type": "string"
          },
          "createdAt": {
            "type": "string"
          },
          "endsAt": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "number": {
            "type": "string"
          },
          "startsAt": {
            "type": "string"
          },
          "teamId": {
            "type": "string"
          },
          "updatedAt": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "issues.json": {
      "items": {
        "keys": {
          "assigneeId": {
            "type": "string"
          },
          "branchName": {
            "type": "string"
          },
          "canceledAt": {
            "type": "string"
          },
          "completedAt": {
            "type": "string"
          },
          "createdAt": {
            "type": "string"
          },
          "cycleId": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "dueDate": {
            "type": "string"
          },
          "estimate": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "identifier": {
            "type": "string"
          },
          "labelIds": {
            "type": "string"
          },
          "number": {
            "type": "string"
          },
          "priority": {
            "type": "string"
          },
          "projectId": {
            "type": "string"
          },
          "sortOrder": {
            "type": "string"
          },
          "startedAt": {
            "type": "string"
          },
          "stateId": {
            "type": "string"
          },
          "teamId": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "updatedAt": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "labels.json": {
      "items": {
        "keys": {
          "color": {
            "type": "string"
          },
          "createdAt": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "teamId": {
            "type": "string"
          },
          "updatedAt": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "projects.json": {
      "items": {
        "keys": {
          "createdAt": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "leadId": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "startDate": {
            "type": "string"
          },
          "state": {
            "type": "string"
          },
          "targetDate": {
            "type": "string"
          },
          "teamIds": {
            "type": "string"
          },
          "updatedAt": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "teams.json": {
      "items": {
        "keys": {
          "color": {
            "type": "string"
          },
          "createdAt": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "key": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "updatedAt": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "users.json": {
      "items": {
        "keys": {
          "active": {
            "type": "string"
          },
          "admin": {
            "type": "string"
          },
          "avatarUrl": {
            "type": "string"
          },
          "createdAt": {
            "type": "string"
          },
          "displayName": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "teamId": {
            "type": "string"
          },
          "updatedAt": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "workflow_states.json": {
      "items": {
        "keys": {
          "color": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "position": {
            "type": "string"
          },
          "teamId": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "workspace.json": {
      "keys": {
        "createdAt": {
          "type": "string"
        },
        "id": {
          "type": "string"
        },
        "name": {
          "type": "string"
        },
        "updatedAt": {
          "type": "string"
        },
        "urlKey": {
          "type": "string"
        }
      },
      "type": "object"
    }
  },
  "linkedin-api": {
    "connections.json": {
      "items": {
        "keys": {
          "connectedAt": {
            "type": "string"
          },
          "firstName": {
            "type": "string"
          },
          "headline": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "industry": {
            "type": "string"
          },
          "lastName": {
            "type": "string"
          },
          "location": {
            "type": "string"
          },
          "organizationId": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "jobs.json": {
      "items": {
        "keys": {
          "applicants": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "employmentType": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "keywords": {
            "type": "string"
          },
          "location": {
            "type": "string"
          },
          "organizationId": {
            "type": "string"
          },
          "postedAt": {
            "type": "string"
          },
          "seniority": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "workplaceType": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "organizations.json": {
      "items": {
        "keys": {
          "description": {
            "type": "string"
          },
          "followerCount": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "industry": {
            "type": "string"
          },
          "location": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "staffCountRange": {
            "type": "string"
          },
          "vanityName": {
            "type": "string"
          },
          "website": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "posts.json": {
      "items": {
        "keys": {
          "author_id": {
            "type": "string"
          },
          "comment_count": {
            "type": "string"
          },
          "commentary": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "like_count": {
            "type": "string"
          },
          "share_count": {
            "type": "string"
          },
          "visibility": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "profile.json": {
      "keys": {
        "currentOrganizationId": {
          "type": "string"
        },
        "headline": {
          "type": "string"
        },
        "id": {
          "type": "string"
        },
        "industry": {
          "type": "string"
        },
        "localizedFirstName": {
          "type": "string"
        },
        "localizedLastName": {
          "type": "string"
        },
        "location": {
          "type": "string"
        },
        "numConnections": {
          "type": "number"
        },
        "profilePicture": {
          "type": "string"
        },
        "publicProfileUrl": {
          "type": "string"
        },
        "summary": {
          "type": "string"
        },
        "vanityName": {
          "type": "string"
        }
      },
      "type": "object"
    }
  },
  "mailchimp-api": {
    "campaigns.json": {
      "items": {
        "keys": {
          "create_time": {
            "type": "string"
          },
          "emails_sent": {
            "type": "string"
          },
          "from_name": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "list_id": {
            "type": "string"
          },
          "reply_to": {
            "type": "string"
          },
          "send_time": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "subject_line": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "lists.json": {
      "items": {
        "keys": {
          "company": {
            "type": "string"
          },
          "date_created": {
            "type": "string"
          },
          "from_email": {
            "type": "string"
          },
          "from_name": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "member_count": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "subject": {
            "type": "string"
          },
          "unsubscribe_count": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "members.json": {
      "items": {
        "keys": {
          "email_address": {
            "type": "string"
          },
          "full_name": {
            "type": "string"
          },
          "list_id": {
            "type": "string"
          },
          "member_rating": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "timestamp_signup": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "reports.json": {
      "items": {
        "keys": {
          "bounces": {
            "type": "string"
          },
          "campaign_id": {
            "type": "string"
          },
          "click_rate": {
            "type": "string"
          },
          "clicks_total": {
            "type": "string"
          },
          "emails_sent": {
            "type": "string"
          },
          "open_rate": {
            "type": "string"
          },
          "opens_total": {
            "type": "string"
          },
          "unique_clicks": {
            "type": "string"
          },
          "unique_opens": {
            "type": "string"
          },
          "unsubscribed": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "mailgun-api": {
    "events.json": {
      "items": {
        "keys": {
          "domain": {
            "type": "string"
          },
          "event": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "message_id": {
            "type": "string"
          },
          "reason": {
            "type": "string"
          },
          "recipient": {
            "type": "string"
          },
          "timestamp": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "list_members.json": {
      "items": {
        "keys": {
          "address": {
            "type": "string"
          },
          "list_address": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "subscribed": {
            "type": "string"
          },
          "vars": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "messages.json": {
      "items": {
        "keys": {
          "body": {
            "type": "string"
          },
          "domain": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "recipient": {
            "type": "string"
          },
          "sender": {
            "type": "string"
          },
          "subject": {
            "type": "string"
          },
          "timestamp": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "microsoft-teams-api": {
    "channels.json": {
      "items": {
        "keys": {
          "created_date": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "display_name": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "membership_type": {
            "type": "string"
          },
          "team_id": {
            "type": "string"
          },
          "web_url": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "messages.json": {
      "items": {
        "keys": {
          "channel_id": {
            "type": "string"
          },
          "content": {
            "type": "string"
          },
          "content_type": {
            "type": "string"
          },
          "created_date": {
            "type": "string"
          },
          "from_display_name": {
            "type": "string"
          },
          "from_user_id": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "importance": {
            "type": "string"
          },
          "team_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "teams.json": {
      "items": {
        "keys": {
          "description": {
            "type": "string"
          },
          "display_name": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "is_archived": {
            "type": "string"
          },
          "member_ids": {
            "type": "string"
          },
          "visibility": {
            "type": "string"
          },
          "web_url": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "mixpanel-api": {
    "events.json": {
      "items": {
        "keys": {
          "country": {
            "type": "string"
          },
          "distinct_id": {
            "type": "string"
          },
          "event": {
            "type": "string"
          },
          "event_id": {
            "type": "string"
          },
          "plan": {
            "type": "string"
          },
          "platform": {
            "type": "string"
          },
          "time": {
            "type": "string"
          },
          "utm_source": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "funnels.json": {
      "items": {
        "keys": {
          "count": {
            "type": "string"
          },
          "funnel_id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "step_event": {
            "type": "string"
          },
          "step_order": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "profiles.json": {
      "items": {
        "keys": {
          "country": {
            "type": "string"
          },
          "distinct_id": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "last_seen": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "plan": {
            "type": "string"
          },
          "total_events": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "monday-api": {
    "boards.json": {
      "items": {
        "keys": {
          "board_id": {
            "type": "string"
          },
          "board_kind": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "state": {
            "type": "string"
          },
          "workspace_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "column_values.json": {
      "items": {
        "keys": {
          "column_id": {
            "type": "string"
          },
          "item_id": {
            "type": "string"
          },
          "text": {
            "type": "string"
          },
          "value": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "columns.json": {
      "items": {
        "keys": {
          "board_id": {
            "type": "string"
          },
          "column_id": {
            "type": "string"
          },
          "position": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "groups.json": {
      "items": {
        "keys": {
          "board_id": {
            "type": "string"
          },
          "color": {
            "type": "string"
          },
          "group_id": {
            "type": "string"
          },
          "position": {
            "type": "string"
          },
          "title": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "items.json": {
      "items": {
        "keys": {
          "board_id": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "group_id": {
            "type": "string"
          },
          "item_id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "users.json": {
      "items": {
        "keys": {
          "email": {
            "type": "string"
          },
          "is_admin": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "user_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "workspaces.json": {
      "items": {
        "keys": {
          "description": {
            "type": "string"
          },
          "kind": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "workspace_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "myfitnesspal-api": {
    "diary_entries.json": {
      "items": {
        "keys": {
          "brand": {
            "type": "string"
          },
          "calories": {
            "type": "string"
          },
          "cholesterol_mg": {
            "type": "string"
          },
          "date": {
            "type": "string"
          },
          "dietary_fiber_g": {
            "type": "string"
          },
          "entry_id": {
            "type": "string"
          },
          "food_id": {
            "type": "string"
          },
          "food_name": {
            "type": "string"
          },
          "meal": {
            "type": "string"
          },
          "protein_g": {
            "type": "string"
          },
          "saturated_fat_g": {
            "type": "string"
          },
          "serving_size": {
            "type": "string"
          },
          "serving_unit": {
            "type": "string"
          },
          "servings": {
            "type": "string"
          },
          "sodium_mg": {
            "type": "string"
          },
          "sugars_g": {
            "type": "string"
          },
          "total_carbs_g": {
            "type": "string"
          },
          "total_fat_g": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "exercise_log.json": {
      "items": {
        "keys": {
          "calories_burned": {
            "type": "string"
          },
          "date": {
            "type": "string"
          },
          "duration_minutes": {
            "type": "string"
          },
          "exercise_id": {
            "type": "string"
          },
          "exercise_name": {
            "type": "string"
          },
          "exercise_type_id": {
            "type": "string"
          },
          "notes": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "exercise_types.json": {
      "items": {
        "keys": {
          "calories_per_minute_high": {
            "type": "string"
          },
          "calories_per_minute_low": {
            "type": "string"
          },
          "category": {
            "type": "string"
          },
          "exercise_name": {
            "type": "string"
          },
          "exercise_type_id": {
            "type": "string"
          },
          "met_value": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "foods.json": {
      "items": {
        "keys": {
          "brand": {
            "type": "string"
          },
          "calories": {
            "type": "string"
          },
          "cholesterol_mg": {
            "type": "string"
          },
          "dietary_fiber_g": {
            "type": "string"
          },
          "food_id": {
            "type": "string"
          },
          "food_name": {
            "type": "string"
          },
          "is_verified": {
            "type": "string"
          },
          "potassium_mg": {
            "type": "string"
          },
          "protein_g": {
            "type": "string"
          },
          "saturated_fat_g": {
            "type": "string"
          },
          "serving_size": {
            "type": "string"
          },
          "serving_unit": {
            "type": "string"
          },
          "sodium_mg": {
            "type": "string"
          },
          "sugars_g": {
            "type": "string"
          },
          "total_carbs_g": {
            "type": "string"
          },
          "total_fat_g": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "myfitnesspal_user_profile.json": {
      "keys": {
        "user_profile": {
          "keys": {
            "current_day_total_carbs": {
              "type": "number"
            },
            "daily_carb_limit_g": {
              "type": "number"
            },
            "last_a1c": {
              "type": "number"
            },
            "time_zone": {
              "type": "string"
            },
            "user_id": {
              "type": "string"
            }
          },
          "type": "object"
        }
      },
      "type": "object"
    },
    "user_profile.json": {
      "keys": {
        "activity_level": {
          "type": "string"
        },
        "current_weight_lbs": {
          "type": "number"
        },
        "daily_calorie_goal": {
          "type": "number"
        },
        "date_of_birth": {
          "type": "string"
        },
        "display_name": {
          "type": "string"
        },
        "email": {
          "type": "string"
        },
        "goal_weight_lbs": {
          "type": "number"
        },
        "height_cm": {
          "type": "number"
        },
        "joined_date": {
          "type": "string"
        },
        "location": {
          "type": "string"
        },
        "macro_goals": {
          "keys": {
            "carbs_pct": {
              "type": "number"
            },
            "fat_pct": {
              "type": "number"
            },
            "protein_pct": {
              "type": "number"
            }
          },
          "type": "object"
        },
        "nutrient_goals": {
          "keys": {
            "calcium_pct": {
              "type": "number"
            },
            "calories": {
              "type": "number"
            },
            "cholesterol_mg": {
              "type": "number"
            },
            "dietary_fiber_g": {
              "type": "number"
            },
            "iron_pct": {
              "type": "number"
            },
            "potassium_mg": {
              "type": "number"
            },
            "protein_g": {
              "type": "number"
            },
            "saturated_fat_g": {
              "type": "number"
            },
            "sodium_mg": {
              "type": "number"
            },
            "sugars_g": {
              "type": "number"
            },
            "total_carbs_g": {
              "type": "number"
            },
            "total_fat_g": {
              "type": "number"
            },
            "vitamin_a_pct": {
              "type": "number"
            },
            "vitamin_c_pct": {
              "type": "number"
            }
          },
          "type": "object"
        },
        "profile_image_url": {
          "type": "string"
        },
        "sex": {
          "type": "string"
        },
        "units": {
          "keys": {
            "energy": {
              "type": "string"
            },
            "height": {
              "type": "string"
            },
            "water": {
              "type": "string"
            },
            "weight": {
              "type": "string"
            }
          },
          "type": "object"
        },
        "user_id": {
          "type": "number"
        },
        "username": {
          "type": "string"
        },
        "weekly_weight_goal_lbs": {
          "type": "number"
        }
      },
      "type": "object"
    },
    "water_log.json": {
      "items": {
        "keys": {
          "cups": {
            "type": "string"
          },
          "date": {
            "type": "string"
          },
          "notes": {
            "type": "string"
          },
          "water_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "weight_log.json": {
      "items": {
        "keys": {
          "date": {
            "type": "string"
          },
          "notes": {
            "type": "string"
          },
          "weight_id": {
            "type": "string"
          },
          "weight_lbs": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "nasa-api": {
    "apod.json": {
      "items": {
        "keys": {
          "copyright": {
            "type": "string"
          },
          "date": {
            "type": "string"
          },
          "explanation": {
            "type": "string"
          },
          "hdurl": {
            "type": "string"
          },
          "media_type": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "url": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "epic.json": {
      "items": {
        "keys": {
          "caption": {
            "type": "string"
          },
          "centroid_lat": {
            "type": "string"
          },
          "centroid_lon": {
            "type": "string"
          },
          "date": {
            "type": "string"
          },
          "identifier": {
            "type": "string"
          },
          "image": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "neos.json": {
      "items": {
        "keys": {
          "absolute_magnitude_h": {
            "type": "string"
          },
          "close_approach_date": {
            "type": "string"
          },
          "est_diameter_max_km": {
            "type": "string"
          },
          "est_diameter_min_km": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "is_potentially_hazardous": {
            "type": "string"
          },
          "miss_distance_km": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "orbiting_body": {
            "type": "string"
          },
          "relative_velocity_kph": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "rover_photos.json": {
      "items": {
        "keys": {
          "camera": {
            "type": "string"
          },
          "camera_full_name": {
            "type": "string"
          },
          "earth_date": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "img_src": {
            "type": "string"
          },
          "rover": {
            "type": "string"
          },
          "sol": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "rovers.json": {
      "items": {
        "keys": {
          "landing_date": {
            "type": "string"
          },
          "launch_date": {
            "type": "string"
          },
          "max_date": {
            "type": "string"
          },
          "max_sol": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "total_photos": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "notion-api": {
    "blocks.json": {
      "items": {
        "keys": {
          "checked": {
            "type": "string"
          },
          "created_time": {
            "type": "string"
          },
          "has_children": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "last_edited_time": {
            "type": "string"
          },
          "order": {
            "type": "string"
          },
          "page_id": {
            "type": "string"
          },
          "parent_block_id": {
            "type": "string"
          },
          "text": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "comments.json": {
      "items": {
        "keys": {
          "author_id": {
            "type": "string"
          },
          "created_time": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "parent_block_id": {
            "type": "string"
          },
          "parent_page_id": {
            "type": "string"
          },
          "resolved": {
            "type": "string"
          },
          "text": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "databases.json": {
      "items": {
        "keys": {
          "archived": {
            "type": "string"
          },
          "created_by": {
            "type": "string"
          },
          "created_time": {
            "type": "string"
          },
          "icon": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "last_edited_time": {
            "type": "string"
          },
          "parent_page_id": {
            "type": "string"
          },
          "title": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "page_properties.json": {
      "items": {
        "keys": {
          "page_id": {
            "type": "string"
          },
          "property_name": {
            "type": "string"
          },
          "property_type": {
            "type": "string"
          },
          "value": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "pages.json": {
      "items": {
        "keys": {
          "archived": {
            "type": "string"
          },
          "cover_url": {
            "type": "string"
          },
          "created_by": {
            "type": "string"
          },
          "created_time": {
            "type": "string"
          },
          "icon": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "last_edited_time": {
            "type": "string"
          },
          "parent_id": {
            "type": "string"
          },
          "parent_type": {
            "type": "string"
          },
          "title": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "users.json": {
      "items": {
        "keys": {
          "avatar_url": {
            "type": "string"
          },
          "bot": {
            "type": "string"
          },
          "created_time": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "owner_workspace": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "workspace.json": {
      "keys": {
        "created_time": {
          "type": "string"
        },
        "domain": {
          "type": "string"
        },
        "icon": {
          "type": "string"
        },
        "id": {
          "type": "string"
        },
        "name": {
          "type": "string"
        },
        "owner_user_id": {
          "type": "string"
        },
        "plan": {
          "type": "string"
        },
        "settings": {
          "keys": {
            "ai_blocks_enabled": {
              "type": "boolean"
            },
            "default_page_size": {
              "type": "number"
            },
            "public_sharing_enabled": {
              "type": "boolean"
            }
          },
          "type": "object"
        }
      },
      "type": "object"
    }
  },
  "obsidian-api": {
    "note_contents.json": {
      "items": {
        "keys": {
          "content": {
            "type": "string"
          },
          "path": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "notes.json": {
      "items": {
        "keys": {
          "modified_at": {
            "type": "string"
          },
          "path": {
            "type": "string"
          },
          "size_bytes": {
            "type": "string"
          },
          "tags": {
            "type": "string"
          },
          "title": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "vault.json": {
      "keys": {
        "created_at": {
          "type": "string"
        },
        "name": {
          "type": "string"
        },
        "owner": {
          "type": "string"
        },
        "path": {
          "type": "string"
        }
      },
      "type": "object"
    }
  },
  "okta-api": {
    "app_assignments.json": {
      "items": {
        "keys": {
          "app_id": {
            "type": "string"
          },
          "scope": {
            "type": "string"
          },
          "user_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "apps.json": {
      "items": {
        "keys": {
          "created": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "label": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "sign_on_mode": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "group_memberships.json": {
      "items": {
        "keys": {
          "group_id": {
            "type": "string"
          },
          "user_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "groups.json": {
      "items": {
        "keys": {
          "created": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "users.json": {
      "items": {
        "keys": {
          "activated": {
            "type": "string"
          },
          "created": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "first_name": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "last_login": {
            "type": "string"
          },
          "last_name": {
            "type": "string"
          },
          "login": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "openlibrary-api": {
    "authors.json": {
      "items": {
        "keys": {
          "author_id": {
            "type": "string"
          },
          "bio": {
            "type": "string"
          },
          "birth_date": {
            "type": "string"
          },
          "death_date": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "top_work": {
            "type": "string"
          },
          "work_count": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "editions.json": {
      "items": {
        "keys": {
          "edition_id": {
            "type": "string"
          },
          "isbn_10": {
            "type": "string"
          },
          "isbn_13": {
            "type": "string"
          },
          "language": {
            "type": "string"
          },
          "number_of_pages": {
            "type": "string"
          },
          "publish_date": {
            "type": "string"
          },
          "publisher": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "work_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "subjects.json": {
      "items": {
        "keys": {
          "name": {
            "type": "string"
          },
          "subject": {
            "type": "string"
          },
          "subject_type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "works.json": {
      "items": {
        "keys": {
          "author_id": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "edition_count": {
            "type": "string"
          },
          "first_publish_year": {
            "type": "string"
          },
          "subjects": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "work_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "openweather-api": {
    "cities.json": {
      "items": {
        "keys": {
          "country": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "lat": {
            "type": "string"
          },
          "lon": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "state": {
            "type": "string"
          },
          "timezone": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "current_weather.json": {
      "items": {
        "keys": {
          "city_id": {
            "type": "string"
          },
          "clouds": {
            "type": "string"
          },
          "dt": {
            "type": "string"
          },
          "feels_like": {
            "type": "string"
          },
          "humidity": {
            "type": "string"
          },
          "pressure": {
            "type": "string"
          },
          "temp": {
            "type": "string"
          },
          "temp_max": {
            "type": "string"
          },
          "temp_min": {
            "type": "string"
          },
          "visibility": {
            "type": "string"
          },
          "weather_description": {
            "type": "string"
          },
          "weather_icon": {
            "type": "string"
          },
          "weather_id": {
            "type": "string"
          },
          "weather_main": {
            "type": "string"
          },
          "wind_deg": {
            "type": "string"
          },
          "wind_speed": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "forecast.json": {
      "items": {
        "keys": {
          "city_id": {
            "type": "string"
          },
          "clouds": {
            "type": "string"
          },
          "dt": {
            "type": "string"
          },
          "dt_txt": {
            "type": "string"
          },
          "feels_like": {
            "type": "string"
          },
          "humidity": {
            "type": "string"
          },
          "pop": {
            "type": "string"
          },
          "pressure": {
            "type": "string"
          },
          "temp": {
            "type": "string"
          },
          "temp_max": {
            "type": "string"
          },
          "temp_min": {
            "type": "string"
          },
          "weather_description": {
            "type": "string"
          },
          "weather_icon": {
            "type": "string"
          },
          "weather_id": {
            "type": "string"
          },
          "weather_main": {
            "type": "string"
          },
          "wind_deg": {
            "type": "string"
          },
          "wind_speed": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "outlook-api": {
    "contacts.json": {
      "items": {
        "keys": {
          "company": {
            "type": "string"
          },
          "display_name": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "given_name": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "job_title": {
            "type": "string"
          },
          "mobile_phone": {
            "type": "string"
          },
          "surname": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "events.json": {
      "items": {
        "keys": {
          "attendees": {
            "type": "string"
          },
          "end_date": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "is_all_day": {
            "type": "string"
          },
          "is_online": {
            "type": "string"
          },
          "location": {
            "type": "string"
          },
          "organizer_address": {
            "type": "string"
          },
          "organizer_name": {
            "type": "string"
          },
          "start_date": {
            "type": "string"
          },
          "subject": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "messages.json": {
      "items": {
        "keys": {
          "body_preview": {
            "type": "string"
          },
          "content_type": {
            "type": "string"
          },
          "from_address": {
            "type": "string"
          },
          "from_name": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "importance": {
            "type": "string"
          },
          "is_read": {
            "type": "string"
          },
          "received_date": {
            "type": "string"
          },
          "subject": {
            "type": "string"
          },
          "to_address": {
            "type": "string"
          },
          "to_name": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "pagerduty-api": {
    "escalation_policies.json": {
      "items": {
        "keys": {
          "escalation_policy_id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "num_loops": {
            "type": "string"
          },
          "tier1_user_id": {
            "type": "string"
          },
          "tier2_user_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "incidents.json": {
      "items": {
        "keys": {
          "assigned_to": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "escalation_policy_id": {
            "type": "string"
          },
          "incident_id": {
            "type": "string"
          },
          "incident_number": {
            "type": "string"
          },
          "resolved_at": {
            "type": "string"
          },
          "service_id": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "urgency": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "schedules.json": {
      "items": {
        "keys": {
          "current_oncall_user_id": {
            "type": "string"
          },
          "escalation_policy_id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "oncall_end": {
            "type": "string"
          },
          "oncall_start": {
            "type": "string"
          },
          "schedule_id": {
            "type": "string"
          },
          "time_zone": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "services.json": {
      "items": {
        "keys": {
          "auto_resolve_timeout": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "escalation_policy_id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "service_id": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "users.json": {
      "items": {
        "keys": {
          "email": {
            "type": "string"
          },
          "job_title": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "role": {
            "type": "string"
          },
          "time_zone": {
            "type": "string"
          },
          "user_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "paypal-api": {
    "captures.json": {
      "items": {
        "keys": {
          "amount_value": {
            "type": "string"
          },
          "create_time": {
            "type": "string"
          },
          "currency_code": {
            "type": "string"
          },
          "final_capture": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "order_id": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "invoices.json": {
      "items": {
        "keys": {
          "amount_value": {
            "type": "string"
          },
          "currency_code": {
            "type": "string"
          },
          "due_date": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "invoice_number": {
            "type": "string"
          },
          "note": {
            "type": "string"
          },
          "recipient_email": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "orders.json": {
      "items": {
        "keys": {
          "amount_value": {
            "type": "string"
          },
          "create_time": {
            "type": "string"
          },
          "currency_code": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "intent": {
            "type": "string"
          },
          "payee_email": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "payouts.json": {
      "items": {
        "keys": {
          "amount_value": {
            "type": "string"
          },
          "create_time": {
            "type": "string"
          },
          "currency_code": {
            "type": "string"
          },
          "payout_batch_id": {
            "type": "string"
          },
          "recipient_email": {
            "type": "string"
          },
          "sender_batch_id": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "refunds.json": {
      "items": {
        "keys": {
          "amount_value": {
            "type": "string"
          },
          "capture_id": {
            "type": "string"
          },
          "create_time": {
            "type": "string"
          },
          "currency_code": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "note_to_payer": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "pinterest-api": {
    "ad_accounts.json": {
      "items": {
        "keys": {
          "ad_account_id": {
            "type": "string"
          },
          "country": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "currency": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "board_sections.json": {
      "items": {
        "keys": {
          "board_id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "pin_count": {
            "type": "string"
          },
          "section_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "boards.json": {
      "items": {
        "keys": {
          "board_id": {
            "type": "string"
          },
          "collaborator_count": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "follower_count": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "pin_count": {
            "type": "string"
          },
          "privacy": {
            "type": "string"
          },
          "updated_at": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "campaigns.json": {
      "items": {
        "keys": {
          "ad_account_id": {
            "type": "string"
          },
          "campaign_id": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "daily_spend_cap_micro": {
            "type": "string"
          },
          "end_time": {
            "type": "string"
          },
          "lifetime_spend_cap_micro": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "objective_type": {
            "type": "string"
          },
          "start_time": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "updated_at": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "pin_analytics.json": {
      "items": {
        "keys": {
          "date": {
            "type": "string"
          },
          "impressions": {
            "type": "string"
          },
          "outbound_clicks": {
            "type": "string"
          },
          "pin_clicks": {
            "type": "string"
          },
          "pin_id": {
            "type": "string"
          },
          "saves": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "pins.json": {
      "items": {
        "keys": {
          "alt_text": {
            "type": "string"
          },
          "board_id": {
            "type": "string"
          },
          "board_section_id": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "dominant_color": {
            "type": "string"
          },
          "is_promoted": {
            "type": "string"
          },
          "link": {
            "type": "string"
          },
          "media_type": {
            "type": "string"
          },
          "pin_id": {
            "type": "string"
          },
          "pin_metrics_clicks": {
            "type": "string"
          },
          "pin_metrics_impressions": {
            "type": "string"
          },
          "pin_metrics_saves": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "updated_at": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "user_account.json": {
      "items": {
        "keys": {
          "account_type": {
            "type": "string"
          },
          "board_count": {
            "type": "number"
          },
          "business_name": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "follower_count": {
            "type": "number"
          },
          "following_count": {
            "type": "number"
          },
          "monthly_views": {
            "type": "number"
          },
          "pin_count": {
            "type": "number"
          },
          "profile_image": {
            "type": "string"
          },
          "username": {
            "type": "string"
          },
          "website_url": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "user_analytics.json": {
      "items": {
        "keys": {
          "date": {
            "type": "string"
          },
          "follows": {
            "type": "string"
          },
          "impressions": {
            "type": "string"
          },
          "outbound_clicks": {
            "type": "string"
          },
          "pin_clicks": {
            "type": "string"
          },
          "profile_visits": {
            "type": "string"
          },
          "saves": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "plaid-api": {
    "accounts.json": {
      "items": {
        "keys": {
          "account_id": {
            "type": "string"
          },
          "available": {
            "type": "string"
          },
          "current": {
            "type": "string"
          },
          "iso_currency_code": {
            "type": "string"
          },
          "limit": {
            "type": "string"
          },
          "mask": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "official_name": {
            "type": "string"
          },
          "subtype": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "identity.json": {
      "keys": {
        "owners": {
          "keys": {
            "acc_chk_001": {
              "items": {
                "keys": {
                  "addresses": {
                    "items": {
                      "keys": {
                        "data": {
                          "keys": {
                            "city": {
                              "type": "string"
                            },
                            "country": {
                              "type": "string"
                            },
                            "postal_code": {
                              "type": "string"
                            },
                            "region": {
                              "type": "string"
                            },
                            "street": {
                              "type": "string"
                            }
                          },
                          "type": "object"
                        },
                        "primary": {
                          "type": "boolean"
                        }
                      },
                      "type": "object"
                    },
                    "type": "array"
                  },
                  "emails": {
                    "items": {
                      "keys": {
                        "data": {
                          "type": "string"
                        },
                        "primary": {
                          "type": "boolean"
                        },
                        "type": {
                          "type": "string"
                        }
                      },
                      "type": "object"
                    },
                    "type": "array"
                  },
                  "names": {
                    "items": {
                      "type": "string"
                    },
                    "type": "array"
                  },
                  "phone_numbers": {
                    "items": {
                      "keys": {
                        "data": {
                          "type": "string"
                        },
                        "primary": {
                          "type": "boolean"
                        },
                        "type": {
                          "type": "string"
                        }
                      },
                      "type": "object"
                    },
                    "type": "array"
                  }
                },
                "type": "object"
              },
              "type": "array"
            },
            "acc_sav_002": {
              "items": {
                "keys": {
                  "addresses": {
                    "items": {
                      "keys": {
                        "data": {
                          "keys": {
                            "city": {
                              "type": "string"
                            },
                            "country": {
                              "type": "string"
                            },
                            "postal_code": {
                              "type": "string"
                            },
                            "region": {
                              "type": "string"
                            },
                            "street": {
                              "type": "string"
                            }
                          },
                          "type": "object"
                        },
                        "primary": {
                          "type": "boolean"
                        }
                      },
                      "type": "object"
                    },
                    "type": "array"
                  },
                  "emails": {
                    "items": {
                      "keys": {
                        "data": {
                          "type": "string"
                        },
                        "primary": {
                          "type": "boolean"
                        },
                        "type": {
                          "type": "string"
                        }
                      },
                      "type": "object"
                    },
                    "type": "array"
                  },
                  "names": {
                    "items": {
                      "type": "string"
                    },
                    "type": "array"
                  },
                  "phone_numbers": {
                    "items": {
                      "keys": {
                        "data": {
                          "type": "string"
                        },
                        "primary": {
                          "type": "boolean"
                        },
                        "type": {
                          "type": "string"
                        }
                      },
                      "type": "object"
                    },
                    "type": "array"
                  }
                },
                "type": "object"
              },
              "type": "array"
            }
          },
          "type": "object"
        }
      },
      "type": "object"
    },
    "item.json": {
      "keys": {
        "institution": {
          "keys": {
            "country_codes": {
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            "institution_id": {
              "type": "string"
            },
            "name": {
              "type": "string"
            },
            "primary_color": {
              "type": "string"
            },
            "products": {
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            "routing_numbers": {
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            "url": {
              "type": "string"
            }
          },
          "type": "object"
        },
        "item": {
          "keys": {
            "available_products": {
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            "billed_products": {
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            "consent_expiration_time": {
              "type": "null"
            },
            "institution_id": {
              "type": "string"
            },
            "item_id": {
              "type": "string"
            },
            "update_type": {
              "type": "string"
            },
            "webhook": {
              "type": "string"
            }
          },
          "type": "object"
        }
      },
      "type": "object"
    },
    "transactions.json": {
      "items": {
        "keys": {
          "account_id": {
            "type": "string"
          },
          "amount": {
            "type": "string"
          },
          "category": {
            "type": "string"
          },
          "date": {
            "type": "string"
          },
          "iso_currency_code": {
            "type": "string"
          },
          "merchant_name": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "payment_channel": {
            "type": "string"
          },
          "pending": {
            "type": "string"
          },
          "transaction_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "posthog-api": {
    "events.json": {
      "items": {
        "keys": {
          "distinct_id": {
            "type": "string"
          },
          "event": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "project_id": {
            "type": "string"
          },
          "properties": {
            "type": "string"
          },
          "timestamp": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "feature_flags.json": {
      "items": {
        "keys": {
          "active": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "key": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "project_id": {
            "type": "string"
          },
          "rollout_percentage": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "persons.json": {
      "items": {
        "keys": {
          "created_at": {
            "type": "string"
          },
          "distinct_id": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "project_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "quickbooks-api": {
    "Corporate_Expense_Ledger.json": {
      "keys": {
        "account_id": {
          "type": "number"
        },
        "document_name": {
          "type": "string"
        },
        "entries": {
          "items": {
            "keys": {
              "amount": {
                "type": "number"
              },
              "date": {
                "type": "string"
              },
              "employee": {
                "type": "string"
              },
              "merchant": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "type": "array"
        }
      },
      "type": "object"
    },
    "Reimbursement_Policy.json": {
      "keys": {
        "context": {
          "type": "string"
        },
        "policy_name": {
          "type": "string"
        },
        "validation_rules": {
          "items": {
            "keys": {
              "action": {
                "type": "string"
              },
              "notes": {
                "type": "string"
              },
              "requirement": {
                "type": "string"
              },
              "rule": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "type": "array"
        },
        "version": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "accounts.json": {
      "items": {
        "keys": {
          "AccountSubType": {
            "type": "string"
          },
          "AccountType": {
            "type": "string"
          },
          "Active": {
            "type": "string"
          },
          "Classification": {
            "type": "string"
          },
          "CurrentBalance": {
            "type": "string"
          },
          "Description": {
            "type": "string"
          },
          "Id": {
            "type": "string"
          },
          "Name": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "bill-payments.json": {
      "keys": {
        "QueryResponse": {
          "keys": {
            "BillPayment": {
              "items": {
                "keys": {
                  "CheckPayment": {
                    "keys": {
                      "BankAccountRef": {
                        "keys": {
                          "name": {
                            "type": "string"
                          }
                        },
                        "type": "object"
                      }
                    },
                    "type": "object"
                  },
                  "Id": {
                    "type": "string"
                  },
                  "Line": {
                    "items": {
                      "keys": {
                        "Amount": {
                          "type": "number"
                        },
                        "LinkedTxn": {
                          "items": {
                            "keys": {
                              "TxnId": {
                                "type": "string"
                              },
                              "TxnType": {
                                "type": "string"
                              }
                            },
                            "type": "object"
                          },
                          "type": "array"
                        }
                      },
                      "type": "object"
                    },
                    "type": "array"
                  },
                  "PayType": {
                    "type": "string"
                  },
                  "PrivateNote": {
                    "type": "string"
                  },
                  "TotalAmt": {
                    "type": "number"
                  },
                  "TxnDate": {
                    "type": "string"
                  },
                  "VendorRef": {
                    "keys": {
                      "name": {
                        "type": "string"
                      },
                      "value": {
                        "type": "string"
                      }
                    },
                    "type": "object"
                  }
                },
                "type": "object"
              },
              "type": "array"
            },
            "maxResults": {
              "type": "number"
            },
            "startPosition": {
              "type": "number"
            },
            "totalCount": {
              "type": "number"
            }
          },
          "type": "object"
        }
      },
      "type": "object"
    },
    "bills.json": {
      "items": {
        "keys": {
          "Balance": {
            "type": "number"
          },
          "DocNumber": {
            "type": "string"
          },
          "DueDate": {
            "type": "string"
          },
          "Id": {
            "type": "string"
          },
          "Line": {
            "items": {
              "keys": {
                "AccountBasedExpenseLineDetail": {
                  "keys": {
                    "AccountRef": {
                      "keys": {
                        "name": {
                          "type": "string"
                        },
                        "value": {
                          "type": "string"
                        }
                      },
                      "type": "object"
                    }
                  },
                  "type": "object"
                },
                "Amount": {
                  "type": "number"
                },
                "Description": {
                  "type": "string"
                },
                "DetailType": {
                  "type": "string"
                },
                "Id": {
                  "type": "string"
                },
                "LineNum": {
                  "type": "number"
                },
                "Quantity": {
                  "type": "number"
                },
                "UnitPrice": {
                  "type": "number"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "MetaData": {
            "keys": {
              "CreateTime": {
                "type": "string"
              },
              "LastUpdatedTime": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "PrivateNote": {
            "type": "string"
          },
          "Status": {
            "type": "string"
          },
          "SyncToken": {
            "type": "string"
          },
          "TotalAmt": {
            "type": "number"
          },
          "TxnDate": {
            "type": "string"
          },
          "VendorRef": {
            "keys": {
              "name": {
                "type": "string"
              },
              "value": {
                "type": "string"
              }
            },
            "type": "object"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "break-even-analysis.json": {
      "keys": {
        "BreakEvenAnalysis": {
          "keys": {
            "ActionItems": {
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            "Context": {
              "type": "string"
            },
            "CurrentState": {
              "keys": {
                "AaronDrawFromNet": {
                  "type": "number"
                },
                "MonthlyExpenses": {
                  "keys": {
                    "Cleaning": {
                      "keys": {
                        "BiWeekly": {
                          "type": "number"
                        },
                        "Monthly": {
                          "type": "number"
                        }
                      },
                      "type": "object"
                    },
                    "InstructorPay_Raj": {
                      "type": "number"
                    },
                    "Insurance": {
                      "keys": {
                        "Monthly": {
                          "type": "number"
                        },
                        "Quarterly": {
                          "type": "number"
                        }
                      },
                      "type": "object"
                    },
                    "Marketing": {
                      "keys": {
                        "AvgMonthly": {
                          "type": "number"
                        }
                      },
                      "type": "object"
                    },
                    "Rent": {
                      "type": "number"
                    },
                    "Supplies": {
                      "keys": {
                        "AvgMonthly": {
                          "type": "number"
                        }
                      },
                      "type": "object"
                    },
                    "TotalMonthlyExpenses": {
                      "type": "number"
                    },
                    "Utilities": {
                      "keys": {
                        "Electric": {
                          "type": "number"
                        },
                        "Total": {
                          "type": "number"
                        },
                        "Water": {
                          "type": "number"
                        }
                      },
                      "type": "object"
                    }
                  },
                  "type": "object"
                },
                "MonthlyNetIncome": {
                  "type": "number"
                },
                "MonthlyRevenue": {
                  "keys": {
                    "DropIns": {
                      "keys": {
                        "AvgMonthly": {
                          "type": "number"
                        }
                      },
                      "type": "object"
                    },
                    "EquipmentSales": {
                      "keys": {
                        "AvgMonthly": {
                          "type": "number"
                        }
                      },
                      "type": "object"
                    },
                    "MembershipDues": {
                      "keys": {
                        "Members": {
                          "type": "number"
                        },
                        "Rate": {
                          "type": "number"
                        },
                        "Total": {
                          "type": "number"
                        }
                      },
                      "type": "object"
                    },
                    "TotalMonthlyRevenue": {
                      "type": "number"
                    }
                  },
                  "type": "object"
                },
                "Note": {
                  "type": "string"
                },
                "RetainedForReserves": {
                  "type": "number"
                }
              },
              "type": "object"
            },
            "KeyInsight": {
              "type": "string"
            },
            "PreparedBy": {
              "type": "string"
            },
            "PreparedDate": {
              "type": "string"
            },
            "Scenarios": {
              "keys": {
                "Scenario_A_RentTo750": {
                  "keys": {
                    "BreakEvenCalculation": {
                      "type": "string"
                    },
                    "BreakEvenMembers": {
                      "type": "number"
                    },
                    "Impact": {
                      "type": "string"
                    },
                    "Label": {
                      "type": "string"
                    },
                    "NewNetIncome": {
                      "type": "number"
                    },
                    "NewRent": {
                      "type": "number"
                    },
                    "NewTotalExpenses": {
                      "type": "number"
                    },
                    "RentIncrease": {
                      "type": "number"
                    }
                  },
                  "type": "object"
                },
                "Scenario_B_RentTo850": {
                  "keys": {
                    "BreakEvenMembers": {
                      "type": "number"
                    },
                    "Impact": {
                      "type": "string"
                    },
                    "Label": {
                      "type": "string"
                    },
                    "NewNetIncome": {
                      "type": "number"
                    },
                    "NewRent": {
                      "type": "number"
                    },
                    "NewTotalExpenses": {
                      "type": "number"
                    },
                    "RentIncrease": {
                      "type": "number"
                    }
                  },
                  "type": "object"
                }
              },
              "type": "object"
            }
          },
          "type": "object"
        }
      },
      "type": "object"
    },
    "company.json": {
      "keys": {
        "CompanyInfo": {
          "keys": {
            "CompanyAddr": {
              "keys": {
                "City": {
                  "type": "string"
                },
                "CountrySubDivisionCode": {
                  "type": "string"
                },
                "Line1": {
                  "type": "string"
                },
                "PostalCode": {
                  "type": "string"
                }
              },
              "type": "object"
            },
            "CompanyName": {
              "type": "string"
            },
            "Country": {
              "type": "string"
            },
            "Email": {
              "keys": {
                "Address": {
                  "type": "string"
                }
              },
              "type": "object"
            },
            "FiscalYearStartMonth": {
              "type": "string"
            },
            "IndustryType": {
              "type": "string"
            },
            "LegalName": {
              "type": "string"
            },
            "MetaData": {
              "keys": {
                "CreateTime": {
                  "type": "string"
                },
                "LastUpdatedTime": {
                  "type": "string"
                }
              },
              "type": "object"
            },
            "NameValue": {
              "items": {
                "keys": {
                  "Name": {
                    "type": "string"
                  },
                  "Value": {
                    "type": "string"
                  }
                },
                "type": "object"
              },
              "type": "array"
            },
            "PrimaryPhone": {
              "keys": {
                "FreeFormNumber": {
                  "type": "string"
                }
              },
              "type": "object"
            }
          },
          "type": "object"
        }
      },
      "type": "object"
    },
    "company_info.json": {
      "keys": {
        "CompanyAddr": {
          "keys": {
            "City": {
              "type": "string"
            },
            "CountrySubDivisionCode": {
              "type": "string"
            },
            "Line1": {
              "type": "string"
            },
            "PostalCode": {
              "type": "string"
            }
          },
          "type": "object"
        },
        "CompanyName": {
          "type": "string"
        },
        "Country": {
          "type": "string"
        },
        "Email": {
          "keys": {
            "Address": {
              "type": "string"
            }
          },
          "type": "object"
        },
        "FiscalYearStartMonth": {
          "type": "string"
        },
        "IndustryType": {
          "type": "string"
        },
        "LegalName": {
          "type": "string"
        },
        "MetaData": {
          "keys": {
            "CreateTime": {
              "type": "string"
            },
            "LastUpdatedTime": {
              "type": "string"
            }
          },
          "type": "object"
        },
        "NameValue": {
          "items": {
            "keys": {
              "Name": {
                "type": "string"
              },
              "Value": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "type": "array"
        },
        "PrimaryPhone": {
          "keys": {
            "FreeFormNumber": {
              "type": "string"
            }
          },
          "type": "object"
        }
      },
      "type": "object"
    },
    "customers.json": {
      "items": {
        "keys": {
          "Active": {
            "type": "string"
          },
          "Balance": {
            "type": "string"
          },
          "BillAddr_City": {
            "type": "string"
          },
          "BillAddr_CountrySubDivisionCode": {
            "type": "string"
          },
          "BillAddr_Line1": {
            "type": "string"
          },
          "BillAddr_PostalCode": {
            "type": "string"
          },
          "CompanyName": {
            "type": "string"
          },
          "DisplayName": {
            "type": "string"
          },
          "FamilyName": {
            "type": "string"
          },
          "GivenName": {
            "type": "string"
          },
          "Id": {
            "type": "string"
          },
          "Job": {
            "type": "string"
          },
          "Notes": {
            "type": "string"
          },
          "PrimaryEmailAddr": {
            "type": "string"
          },
          "PrimaryPhone": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "estimates.json": {
      "items": {
        "keys": {
          "AcceptedDate": {
            "type": "string|null|null|null|null"
          },
          "CustomerRef": {
            "keys": {
              "name": {
                "type": "string"
              },
              "value": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "DocNumber": {
            "type": "string"
          },
          "ExpirationDate": {
            "type": "string"
          },
          "Id": {
            "type": "string"
          },
          "Line": {
            "items": {
              "keys": {
                "Amount": {
                  "type": "number"
                },
                "Description": {
                  "type": "string"
                },
                "DetailType": {
                  "type": "string"
                },
                "Id": {
                  "type": "string"
                },
                "LineNum": {
                  "type": "number"
                },
                "SalesItemLineDetail": {
                  "keys": {
                    "ItemRef": {
                      "keys": {
                        "name": {
                          "type": "string"
                        },
                        "value": {
                          "type": "string"
                        }
                      },
                      "type": "object"
                    },
                    "Qty": {
                      "type": "number"
                    },
                    "UnitPrice": {
                      "type": "number"
                    }
                  },
                  "type": "object"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "LinkedTxn": {
            "items": {
              "keys": {
                "TxnId": {
                  "type": "string"
                },
                "TxnType": {
                  "type": "string"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "MetaData": {
            "keys": {
              "CreateTime": {
                "type": "string"
              },
              "LastUpdatedTime": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "SyncToken": {
            "type": "string"
          },
          "TotalAmt": {
            "type": "number"
          },
          "TxnDate": {
            "type": "string"
          },
          "TxnStatus": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "expenses.json": {
      "items": {
        "keys": {
          "Id": {
            "type": "string"
          },
          "Line": {
            "items": {
              "keys": {
                "Amount": {
                  "type": "number"
                },
                "Description": {
                  "type": "string"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "MetaData": {
            "keys": {
              "CreateTime": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "PrivateNote": {
            "type": "string"
          },
          "TotalAmt": {
            "type": "number"
          },
          "TxnDate": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "invoices.json": {
      "items": {
        "keys": {
          "Balance": {
            "type": "number"
          },
          "BillEmail": {
            "keys": {
              "Address": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "CustomerRef": {
            "keys": {
              "name": {
                "type": "string"
              },
              "value": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "DocNumber": {
            "type": "string"
          },
          "DueDate": {
            "type": "string"
          },
          "EmailStatus": {
            "type": "string"
          },
          "Id": {
            "type": "string"
          },
          "Line": {
            "items": {
              "keys": {
                "Amount": {
                  "type": "number"
                },
                "Description": {
                  "type": "string"
                },
                "DetailType": {
                  "type": "string"
                },
                "Id": {
                  "type": "string"
                },
                "LineNum": {
                  "type": "number"
                },
                "SalesItemLineDetail": {
                  "keys": {
                    "ItemRef": {
                      "keys": {
                        "name": {
                          "type": "string"
                        },
                        "value": {
                          "type": "string"
                        }
                      },
                      "type": "object"
                    },
                    "Qty": {
                      "type": "number"
                    },
                    "UnitPrice": {
                      "type": "number"
                    }
                  },
                  "type": "object"
                },
                "SubTotalLineDetail": {
                  "keys": {},
                  "type": "object"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "MetaData": {
            "keys": {
              "CreateTime": {
                "type": "string"
              },
              "LastUpdatedTime": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "PrintStatus": {
            "type": "string"
          },
          "PrivateNote": {
            "type": "string"
          },
          "Status": {
            "type": "string"
          },
          "SyncToken": {
            "type": "string"
          },
          "TotalAmt": {
            "type": "number"
          },
          "TxnDate": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "items.json": {
      "items": {
        "keys": {
          "Active": {
            "type": "string"
          },
          "Description": {
            "type": "string"
          },
          "Id": {
            "type": "string"
          },
          "IncomeAccountRef_name": {
            "type": "string"
          },
          "IncomeAccountRef_value": {
            "type": "string"
          },
          "Name": {
            "type": "string"
          },
          "Taxable": {
            "type": "string"
          },
          "Type": {
            "type": "string"
          },
          "UnitPrice": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "payments.json": {
      "items": {
        "keys": {
          "CustomerRef": {
            "keys": {
              "name": {
                "type": "string"
              },
              "value": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "Id": {
            "type": "string"
          },
          "Line": {
            "items": {
              "keys": {
                "Amount": {
                  "type": "number"
                },
                "LinkedTxn": {
                  "items": {
                    "keys": {
                      "TxnId": {
                        "type": "string"
                      },
                      "TxnType": {
                        "type": "string"
                      }
                    },
                    "type": "object"
                  },
                  "type": "array"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "PrivateNote": {
            "type": "string"
          },
          "TotalAmt": {
            "type": "number"
          },
          "TxnDate": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "vendors.json": {
      "items": {
        "keys": {
          "AcctNum": {
            "type": "string"
          },
          "Active": {
            "type": "string"
          },
          "Balance": {
            "type": "string"
          },
          "BillAddr_City": {
            "type": "string"
          },
          "BillAddr_CountrySubDivisionCode": {
            "type": "string"
          },
          "BillAddr_Line1": {
            "type": "string"
          },
          "BillAddr_PostalCode": {
            "type": "string"
          },
          "CompanyName": {
            "type": "string"
          },
          "DisplayName": {
            "type": "string"
          },
          "Id": {
            "type": "string"
          },
          "PrimaryEmailAddr": {
            "type": "string"
          },
          "PrimaryPhone": {
            "type": "string"
          },
          "Vendor1099": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "reddit-api": {
    "comments.json": {
      "items": {
        "keys": {
          "author": {
            "type": "string"
          },
          "body": {
            "type": "string"
          },
          "created_utc": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "parent_id": {
            "type": "string"
          },
          "post_id": {
            "type": "string"
          },
          "score": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "posts.json": {
      "items": {
        "keys": {
          "author": {
            "type": "string"
          },
          "created_utc": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "is_self": {
            "type": "string"
          },
          "num_comments": {
            "type": "string"
          },
          "score": {
            "type": "string"
          },
          "selftext": {
            "type": "string"
          },
          "subreddit": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "url": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "subreddits.json": {
      "items": {
        "keys": {
          "created_utc": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "over18": {
            "type": "string"
          },
          "public_description": {
            "type": "string"
          },
          "subscribers": {
            "type": "string"
          },
          "title": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "users.json": {
      "items": {
        "keys": {
          "comment_karma": {
            "type": "string"
          },
          "created_utc": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "is_gold": {
            "type": "string"
          },
          "is_mod": {
            "type": "string"
          },
          "link_karma": {
            "type": "string"
          },
          "name": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "ring-api": {
    "active_dings.json": {
      "items": {
        "keys": {
          "device_kind": {
            "type": "string"
          },
          "doorbot_description": {
            "type": "string"
          },
          "doorbot_id": {
            "type": "number"
          },
          "expires_in": {
            "type": "number"
          },
          "id": {
            "type": "number"
          },
          "id_str": {
            "type": "string"
          },
          "is_sharing": {
            "type": "boolean"
          },
          "kind": {
            "type": "string"
          },
          "motion": {
            "type": "boolean"
          },
          "now": {
            "type": "number"
          },
          "optimization_level": {
            "type": "number"
          },
          "protocol": {
            "type": "string"
          },
          "sip_ding_id": {
            "type": "string"
          },
          "sip_endpoints": {
            "items": null,
            "type": "array"
          },
          "sip_from": {
            "type": "string"
          },
          "sip_server_ip": {
            "type": "string"
          },
          "sip_server_port": {
            "type": "number"
          },
          "sip_server_tls": {
            "type": "boolean"
          },
          "sip_session_id": {
            "type": "string"
          },
          "sip_to": {
            "type": "string"
          },
          "snapshot_url": {
            "type": "string"
          },
          "state": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "devices.json": {
      "keys": {
        "chimes": {
          "items": {
            "keys": {
              "address": {
                "type": "string"
              },
              "alerts": {
                "keys": {
                  "connection": {
                    "type": "string"
                  }
                },
                "type": "object"
              },
              "created_at": {
                "type": "string"
              },
              "description": {
                "type": "string"
              },
              "device_id": {
                "type": "string"
              },
              "features": {
                "keys": {
                  "ringtones_enabled": {
                    "type": "boolean"
                  },
                  "wifi_extender_enabled": {
                    "type": "boolean"
                  }
                },
                "type": "object"
              },
              "firmware_version": {
                "type": "string"
              },
              "id": {
                "type": "number"
              },
              "kind": {
                "type": "string"
              },
              "latitude": {
                "type": "number"
              },
              "location_id": {
                "type": "string"
              },
              "longitude": {
                "type": "number"
              },
              "owned": {
                "type": "boolean"
              },
              "owner": {
                "keys": {
                  "first_name": {
                    "type": "string"
                  },
                  "id": {
                    "type": "number"
                  },
                  "last_name": {
                    "type": "string"
                  }
                },
                "type": "object"
              },
              "settings": {
                "keys": {
                  "ding_audio_id": {
                    "type": "string"
                  },
                  "ding_audio_user_id": {
                    "type": "null"
                  },
                  "linked_doorbots": {
                    "items": {
                      "type": "number"
                    },
                    "type": "array"
                  },
                  "motion_audio_id": {
                    "type": "null"
                  },
                  "motion_audio_user_id": {
                    "type": "null"
                  },
                  "volume": {
                    "type": "number"
                  }
                },
                "type": "object"
              },
              "time_zone": {
                "type": "string"
              },
              "wifi_signal_category": {
                "type": "string"
              },
              "wifi_signal_strength": {
                "type": "number"
              }
            },
            "type": "object"
          },
          "type": "array"
        },
        "doorbots": {
          "items": {
            "keys": {
              "address": {
                "type": "string"
              },
              "alerts": {
                "keys": {
                  "connection": {
                    "type": "string"
                  }
                },
                "type": "object"
              },
              "battery_life": {
                "type": "number"
              },
              "created_at": {
                "type": "string"
              },
              "description": {
                "type": "string"
              },
              "device_id": {
                "type": "string"
              },
              "external_connection": {
                "type": "boolean"
              },
              "features": {
                "keys": {
                  "advanced_motion_enabled": {
                    "type": "boolean"
                  },
                  "motion_message_enabled": {
                    "type": "boolean"
                  },
                  "motions_enabled": {
                    "type": "boolean"
                  },
                  "people_only_enabled": {
                    "type": "boolean"
                  },
                  "shadow_correction_enabled": {
                    "type": "boolean"
                  },
                  "show_recordings": {
                    "type": "boolean"
                  }
                },
                "type": "object"
              },
              "firmware_version": {
                "type": "string"
              },
              "id": {
                "type": "number"
              },
              "kind": {
                "type": "string"
              },
              "latitude": {
                "type": "number"
              },
              "led_status": {
                "type": "string"
              },
              "location_id": {
                "type": "string"
              },
              "longitude": {
                "type": "number"
              },
              "motion_snooze": {
                "type": "null"
              },
              "night_mode_status": {
                "type": "string"
              },
              "owned": {
                "type": "boolean"
              },
              "owner": {
                "keys": {
                  "first_name": {
                    "type": "string"
                  },
                  "id": {
                    "type": "number"
                  },
                  "last_name": {
                    "type": "string"
                  }
                },
                "type": "object"
              },
              "ring_snooze": {
                "type": "null"
              },
              "settings": {
                "keys": {
                  "chime_settings": {
                    "keys": {
                      "duration": {
                        "type": "number"
                      },
                      "enabled": {
                        "type": "boolean"
                      },
                      "type": {
                        "type": "string"
                      }
                    },
                    "type": "object"
                  },
                  "doorbell_volume": {
                    "type": "number"
                  },
                  "motion_detection_enabled": {
                    "type": "boolean"
                  },
                  "motion_sensitivity": {
                    "type": "number"
                  },
                  "package_detection_enabled": {
                    "type": "boolean"
                  },
                  "people_detection_enabled": {
                    "type": "boolean"
                  }
                },
                "type": "object"
              },
              "time_zone": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "type": "array"
        },
        "stickup_cams": {
          "items": {
            "keys": {
              "address": {
                "type": "string"
              },
              "alerts": {
                "keys": {
                  "connection": {
                    "type": "string"
                  }
                },
                "type": "object"
              },
              "battery_life": {
                "type": "number|null|null|number"
              },
              "created_at": {
                "type": "string"
              },
              "description": {
                "type": "string"
              },
              "device_id": {
                "type": "string"
              },
              "external_connection": {
                "type": "boolean"
              },
              "features": {
                "keys": {
                  "advanced_motion_enabled": {
                    "type": "boolean"
                  },
                  "motion_message_enabled": {
                    "type": "boolean"
                  },
                  "motions_enabled": {
                    "type": "boolean"
                  },
                  "night_vision_enabled": {
                    "type": "boolean"
                  },
                  "people_only_enabled": {
                    "type": "boolean"
                  },
                  "shadow_correction_enabled": {
                    "type": "boolean"
                  },
                  "show_recordings": {
                    "type": "boolean"
                  }
                },
                "type": "object"
              },
              "firmware_version": {
                "type": "string"
              },
              "floodlight_status": {
                "keys": {
                  "on": {
                    "type": "boolean"
                  }
                },
                "type": "object"
              },
              "id": {
                "type": "number"
              },
              "kind": {
                "type": "string"
              },
              "latitude": {
                "type": "number"
              },
              "led_status": {
                "type": "string"
              },
              "location_id": {
                "type": "string"
              },
              "longitude": {
                "type": "number"
              },
              "motion_snooze": {
                "type": "null"
              },
              "night_mode_status": {
                "type": "string"
              },
              "owned": {
                "type": "boolean"
              },
              "owner": {
                "keys": {
                  "first_name": {
                    "type": "string"
                  },
                  "id": {
                    "type": "number"
                  },
                  "last_name": {
                    "type": "string"
                  }
                },
                "type": "object"
              },
              "settings": {
                "keys": {
                  "light_on_duration_seconds": {
                    "type": "number"
                  },
                  "light_schedule_enabled": {
                    "type": "boolean"
                  },
                  "motion_detection_enabled": {
                    "type": "boolean"
                  },
                  "motion_sensitivity": {
                    "type": "number"
                  },
                  "package_detection_enabled": {
                    "type": "boolean"
                  },
                  "people_detection_enabled": {
                    "type": "boolean"
                  }
                },
                "type": "object"
              },
              "siren_status": {
                "keys": {
                  "seconds_remaining": {
                    "type": "number"
                  }
                },
                "type": "object"
              },
              "time_zone": {
                "type": "string"
              },
              "wifi_signal_category": {
                "type": "string"
              },
              "wifi_signal_strength": {
                "type": "number"
              }
            },
            "type": "object"
          },
          "type": "array"
        }
      },
      "type": "object"
    },
    "events.json": {
      "items": {
        "keys": {
          "answered": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "cv_properties": {
            "type": "string"
          },
          "device_id": {
            "type": "string"
          },
          "doorbot_id": {
            "type": "string"
          },
          "duration_seconds": {
            "type": "string"
          },
          "favorite": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "kind": {
            "type": "string"
          },
          "recording_status": {
            "type": "string"
          },
          "snapshot_url": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "location.json": {
      "keys": {
        "address": {
          "keys": {
            "city": {
              "type": "string"
            },
            "country": {
              "type": "string"
            },
            "state": {
              "type": "string"
            },
            "street1": {
              "type": "string"
            },
            "street2": {
              "type": "string"
            },
            "zip": {
              "type": "string"
            }
          },
          "type": "object"
        },
        "created_at": {
          "type": "string"
        },
        "latitude": {
          "type": "number"
        },
        "location_id": {
          "type": "string"
        },
        "longitude": {
          "type": "number"
        },
        "mode": {
          "type": "string"
        },
        "name": {
          "type": "string"
        },
        "owner": {
          "keys": {
            "email": {
              "type": "string"
            },
            "first_name": {
              "type": "string"
            },
            "id": {
              "type": "number"
            },
            "last_name": {
              "type": "string"
            }
          },
          "type": "object"
        },
        "subscription": {
          "keys": {
            "plan": {
              "type": "string"
            },
            "status": {
              "type": "string"
            },
            "video_history_days": {
              "type": "number"
            }
          },
          "type": "object"
        },
        "time_zone": {
          "type": "string"
        },
        "updated_at": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "motion_zones.json": {
      "items": {
        "keys": {
          "coordinates": {
            "type": "string"
          },
          "device_id": {
            "type": "string"
          },
          "enabled": {
            "type": "string"
          },
          "sensitivity": {
            "type": "string"
          },
          "zone_id": {
            "type": "string"
          },
          "zone_name": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "notification_prefs.json": {
      "items": {
        "keys": {
          "device_id": {
            "type": "string"
          },
          "ding_alerts": {
            "type": "string"
          },
          "motion_alerts": {
            "type": "string"
          },
          "package_alerts": {
            "type": "string"
          },
          "person_alerts": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "shared_users.json": {
      "items": {
        "keys": {
          "device_access": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "first_name": {
            "type": "string"
          },
          "last_name": {
            "type": "string"
          },
          "role": {
            "type": "string"
          },
          "shared_at": {
            "type": "string"
          },
          "user_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "salesforce-api": {
    "accounts.json": {
      "items": {
        "keys": {
          "AnnualRevenue": {
            "type": "string"
          },
          "BillingCity": {
            "type": "string"
          },
          "BillingState": {
            "type": "string"
          },
          "Id": {
            "type": "string"
          },
          "Industry": {
            "type": "string"
          },
          "Name": {
            "type": "string"
          },
          "NumberOfEmployees": {
            "type": "string"
          },
          "Phone": {
            "type": "string"
          },
          "Website": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "contacts.json": {
      "items": {
        "keys": {
          "AccountId": {
            "type": "string"
          },
          "Email": {
            "type": "string"
          },
          "FirstName": {
            "type": "string"
          },
          "Id": {
            "type": "string"
          },
          "LastName": {
            "type": "string"
          },
          "MailingCity": {
            "type": "string"
          },
          "Phone": {
            "type": "string"
          },
          "Title": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "leads.json": {
      "items": {
        "keys": {
          "Company": {
            "type": "string"
          },
          "Email": {
            "type": "string"
          },
          "FirstName": {
            "type": "string"
          },
          "Id": {
            "type": "string"
          },
          "Industry": {
            "type": "string"
          },
          "LastName": {
            "type": "string"
          },
          "LeadSource": {
            "type": "string"
          },
          "Phone": {
            "type": "string"
          },
          "Rating": {
            "type": "string"
          },
          "Status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "opportunities.json": {
      "items": {
        "keys": {
          "AccountId": {
            "type": "string"
          },
          "Amount": {
            "type": "string"
          },
          "CloseDate": {
            "type": "string"
          },
          "Id": {
            "type": "string"
          },
          "Name": {
            "type": "string"
          },
          "Probability": {
            "type": "string"
          },
          "StageName": {
            "type": "string"
          },
          "Type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "segment-api": {
    "destinations.json": {
      "items": {
        "keys": {
          "created_at": {
            "type": "string"
          },
          "enabled": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "slug": {
            "type": "string"
          },
          "source_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "events.json": {
      "items": {
        "keys": {
          "event": {
            "type": "string"
          },
          "messageId": {
            "type": "string"
          },
          "properties": {
            "type": "string"
          },
          "timestamp": {
            "type": "string"
          },
          "type": {
            "type": "string"
          },
          "userId": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "sources.json": {
      "items": {
        "keys": {
          "created_at": {
            "type": "string"
          },
          "enabled": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "slug": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "sendgrid-api": {
    "contacts.json": {
      "items": {
        "keys": {
          "country": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "first_name": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "last_name": {
            "type": "string"
          },
          "list_ids": {
            "type": "string"
          },
          "updated_at": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "lists.json": {
      "items": {
        "keys": {
          "contact_count": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "sent_log.json": {
      "items": {
        "keys": {
          "clicks": {
            "type": "string"
          },
          "from_email": {
            "type": "string"
          },
          "message_id": {
            "type": "string"
          },
          "opens": {
            "type": "string"
          },
          "sent_at": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "subject": {
            "type": "string"
          },
          "template_id": {
            "type": "string"
          },
          "to_email": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "stats.json": {
      "items": {
        "keys": {
          "bounces": {
            "type": "string"
          },
          "clicks": {
            "type": "string"
          },
          "date": {
            "type": "string"
          },
          "delivered": {
            "type": "string"
          },
          "opens": {
            "type": "string"
          },
          "requests": {
            "type": "string"
          },
          "spam_reports": {
            "type": "string"
          },
          "unique_clicks": {
            "type": "string"
          },
          "unique_opens": {
            "type": "string"
          },
          "unsubscribes": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "templates.json": {
      "items": {
        "keys": {
          "active": {
            "type": "string"
          },
          "generation": {
            "type": "string"
          },
          "html_content": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "subject": {
            "type": "string"
          },
          "updated_at": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "sentry-api": {
    "events.json": {
      "items": {
        "keys": {
          "date_created": {
            "type": "string"
          },
          "environment": {
            "type": "string"
          },
          "event_id": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "issue_id": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "platform": {
            "type": "string"
          },
          "release": {
            "type": "string"
          },
          "user_email": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "issues.json": {
      "items": {
        "keys": {
          "count": {
            "type": "string"
          },
          "culprit": {
            "type": "string"
          },
          "first_seen": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "last_seen": {
            "type": "string"
          },
          "level": {
            "type": "string"
          },
          "org_slug": {
            "type": "string"
          },
          "project_slug": {
            "type": "string"
          },
          "short_id": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "user_count": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "organizations.json": {
      "items": {
        "keys": {
          "date_created": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "slug": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "projects.json": {
      "items": {
        "keys": {
          "date_created": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "org_slug": {
            "type": "string"
          },
          "platform": {
            "type": "string"
          },
          "slug": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "releases.json": {
      "items": {
        "keys": {
          "date_created": {
            "type": "string"
          },
          "date_released": {
            "type": "string"
          },
          "new_groups": {
            "type": "string"
          },
          "org_slug": {
            "type": "string"
          },
          "project_slug": {
            "type": "string"
          },
          "ref": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "version": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "servicenow-api": {
    "change_request.json": {
      "items": {
        "keys": {
          "assigned_to": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "end_date": {
            "type": "string"
          },
          "number": {
            "type": "string"
          },
          "priority": {
            "type": "string"
          },
          "requested_by": {
            "type": "string"
          },
          "risk": {
            "type": "string"
          },
          "short_description": {
            "type": "string"
          },
          "start_date": {
            "type": "string"
          },
          "state": {
            "type": "string"
          },
          "sys_id": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "incident.json": {
      "items": {
        "keys": {
          "assigned_to": {
            "type": "string"
          },
          "category": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "impact": {
            "type": "string"
          },
          "number": {
            "type": "string"
          },
          "opened_at": {
            "type": "string"
          },
          "opened_by": {
            "type": "string"
          },
          "priority": {
            "type": "string"
          },
          "short_description": {
            "type": "string"
          },
          "state": {
            "type": "string"
          },
          "sys_id": {
            "type": "string"
          },
          "updated_at": {
            "type": "string"
          },
          "urgency": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "problem.json": {
      "items": {
        "keys": {
          "assigned_to": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "number": {
            "type": "string"
          },
          "opened_at": {
            "type": "string"
          },
          "opened_by": {
            "type": "string"
          },
          "priority": {
            "type": "string"
          },
          "related_incident": {
            "type": "string"
          },
          "short_description": {
            "type": "string"
          },
          "state": {
            "type": "string"
          },
          "sys_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "sys_user.json": {
      "items": {
        "keys": {
          "active": {
            "type": "string"
          },
          "department": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "sys_id": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "user_name": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "shippo-api": {
    "addresses.json": {
      "items": {
        "keys": {
          "city": {
            "type": "string"
          },
          "company": {
            "type": "string"
          },
          "country": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "is_residential": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "object_id": {
            "type": "string"
          },
          "phone": {
            "type": "string"
          },
          "state": {
            "type": "string"
          },
          "street1": {
            "type": "string"
          },
          "street2": {
            "type": "string"
          },
          "validated": {
            "type": "string"
          },
          "zip": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "parcels.json": {
      "items": {
        "keys": {
          "distance_unit": {
            "type": "string"
          },
          "height": {
            "type": "string"
          },
          "length": {
            "type": "string"
          },
          "mass_unit": {
            "type": "string"
          },
          "object_id": {
            "type": "string"
          },
          "template": {
            "type": "string"
          },
          "weight": {
            "type": "string"
          },
          "width": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "rates.json": {
      "items": {
        "keys": {
          "amount": {
            "type": "string"
          },
          "currency": {
            "type": "string"
          },
          "estimated_days": {
            "type": "string"
          },
          "object_id": {
            "type": "string"
          },
          "provider": {
            "type": "string"
          },
          "servicelevel_name": {
            "type": "string"
          },
          "servicelevel_token": {
            "type": "string"
          },
          "shipment": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "shipments.json": {
      "items": {
        "keys": {
          "address_from": {
            "type": "string"
          },
          "address_to": {
            "type": "string"
          },
          "created_time": {
            "type": "string"
          },
          "object_id": {
            "type": "string"
          },
          "parcel": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "tracking.json": {
      "items": {
        "keys": {
          "carrier": {
            "type": "string"
          },
          "location_city": {
            "type": "string"
          },
          "location_state": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "status_detail": {
            "type": "string"
          },
          "status_time": {
            "type": "string"
          },
          "tracking_number": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "transactions.json": {
      "items": {
        "keys": {
          "carrier": {
            "type": "string"
          },
          "created_time": {
            "type": "string"
          },
          "label_url": {
            "type": "string"
          },
          "object_id": {
            "type": "string"
          },
          "rate": {
            "type": "string"
          },
          "shipment": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "tracking_number": {
            "type": "string"
          },
          "tracking_status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "slack-api": {
    "channel_members.json": {
      "items": {
        "keys": {
          "channel_id": {
            "type": "string"
          },
          "user_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "channels.json": {
      "items": {
        "keys": {
          "created": {
            "type": "string"
          },
          "creator": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "is_archived": {
            "type": "string"
          },
          "is_private": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "num_members": {
            "type": "string"
          },
          "purpose": {
            "type": "string"
          },
          "topic": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "messages.json": {
      "items": {
        "keys": {
          "channel_id": {
            "type": "string"
          },
          "reactions": {
            "type": "string"
          },
          "reply_count": {
            "type": "string"
          },
          "text": {
            "type": "string"
          },
          "thread_ts": {
            "type": "string"
          },
          "ts": {
            "type": "string"
          },
          "user_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "team.json": {
      "keys": {
        "domain": {
          "type": "string"
        },
        "email_domain": {
          "type": "string"
        },
        "icon": {
          "keys": {
            "image_132": {
              "type": "string"
            }
          },
          "type": "object"
        },
        "id": {
          "type": "string"
        },
        "name": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "users.json": {
      "items": {
        "keys": {
          "email": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "is_admin": {
            "type": "string"
          },
          "is_bot": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "presence": {
            "type": "string"
          },
          "real_name": {
            "type": "string"
          },
          "status_text": {
            "type": "string"
          },
          "tz": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "spotify-api": {
    "albums.json": {
      "items": {
        "keys": {
          "album_id": {
            "type": "string"
          },
          "album_type": {
            "type": "string"
          },
          "artist_id": {
            "type": "string"
          },
          "label": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "release_date": {
            "type": "string"
          },
          "total_tracks": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "artists.json": {
      "items": {
        "keys": {
          "artist_id": {
            "type": "string"
          },
          "followers": {
            "type": "string"
          },
          "genres": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "popularity": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "playlist_tracks.json": {
      "items": {
        "keys": {
          "added_at": {
            "type": "string"
          },
          "playlist_id": {
            "type": "string"
          },
          "position": {
            "type": "string"
          },
          "track_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "playlists.json": {
      "items": {
        "keys": {
          "collaborative": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "owner_id": {
            "type": "string"
          },
          "playlist_id": {
            "type": "string"
          },
          "public": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "tracks.json": {
      "items": {
        "keys": {
          "album_id": {
            "type": "string"
          },
          "artist_id": {
            "type": "string"
          },
          "duration_ms": {
            "type": "string"
          },
          "explicit": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "popularity": {
            "type": "string"
          },
          "track_id": {
            "type": "string"
          },
          "track_number": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "user.json": {
      "keys": {
        "country": {
          "type": "string"
        },
        "display_name": {
          "type": "string"
        },
        "email": {
          "type": "string"
        },
        "followers": {
          "type": "number"
        },
        "id": {
          "type": "string"
        },
        "images": {
          "items": {
            "keys": {
              "height": {
                "type": "number"
              },
              "url": {
                "type": "string"
              },
              "width": {
                "type": "number"
              }
            },
            "type": "object"
          },
          "type": "array"
        },
        "product": {
          "type": "string"
        }
      },
      "type": "object"
    }
  },
  "square-api": {
    "catalog_items.json": {
      "items": {
        "keys": {
          "category": {
            "type": "string"
          },
          "currency": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "price_amount": {
            "type": "string"
          },
          "type": {
            "type": "string"
          },
          "variation_id": {
            "type": "string"
          },
          "variation_name": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "customers.json": {
      "items": {
        "keys": {
          "company_name": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "email_address": {
            "type": "string"
          },
          "family_name": {
            "type": "string"
          },
          "given_name": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "phone_number": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "inventory.json": {
      "items": {
        "keys": {
          "catalog_object_id": {
            "type": "string"
          },
          "location_id": {
            "type": "string"
          },
          "quantity": {
            "type": "string"
          },
          "state": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "merchant.json": {
      "keys": {
        "business_name": {
          "type": "string"
        },
        "country": {
          "type": "string"
        },
        "created_at": {
          "type": "string"
        },
        "currency": {
          "type": "string"
        },
        "id": {
          "type": "string"
        },
        "language_code": {
          "type": "string"
        },
        "main_location_id": {
          "type": "string"
        },
        "status": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "orders.json": {
      "items": {
        "keys": {
          "created_at": {
            "type": "string"
          },
          "currency": {
            "type": "string"
          },
          "customer_id": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "line_items": {
            "type": "string"
          },
          "location_id": {
            "type": "string"
          },
          "state": {
            "type": "string"
          },
          "total_amount": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "payments.json": {
      "items": {
        "keys": {
          "amount": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "currency": {
            "type": "string"
          },
          "customer_id": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "location_id": {
            "type": "string"
          },
          "order_id": {
            "type": "string"
          },
          "receipt_number": {
            "type": "string"
          },
          "source_type": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "strava-api": {
    "activities.json": {
      "items": {
        "keys": {
          "average_speed": {
            "type": "string"
          },
          "distance": {
            "type": "string"
          },
          "elapsed_time": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "kudos_count": {
            "type": "string"
          },
          "moving_time": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "segment_id": {
            "type": "string"
          },
          "start_date": {
            "type": "string"
          },
          "total_elevation_gain": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "athlete.json": {
      "keys": {
        "city": {
          "type": "string"
        },
        "country": {
          "type": "string"
        },
        "created_at": {
          "type": "string"
        },
        "firstname": {
          "type": "string"
        },
        "follower_count": {
          "type": "number"
        },
        "friend_count": {
          "type": "number"
        },
        "ftp": {
          "type": "number"
        },
        "id": {
          "type": "number"
        },
        "lastname": {
          "type": "string"
        },
        "premium": {
          "type": "boolean"
        },
        "sex": {
          "type": "string"
        },
        "state": {
          "type": "string"
        },
        "username": {
          "type": "string"
        },
        "weight": {
          "type": "number"
        }
      },
      "type": "object"
    },
    "kudoers.json": {
      "items": {
        "keys": {
          "activity_id": {
            "type": "string"
          },
          "athlete_id": {
            "type": "string"
          },
          "firstname": {
            "type": "string"
          },
          "lastname": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "segments.json": {
      "items": {
        "keys": {
          "activity_type": {
            "type": "string"
          },
          "average_grade": {
            "type": "string"
          },
          "city": {
            "type": "string"
          },
          "climb_category": {
            "type": "string"
          },
          "distance": {
            "type": "string"
          },
          "elevation_high": {
            "type": "string"
          },
          "elevation_low": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "maximum_grade": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "state": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "stripe-api": {
    "balance.json": {
      "keys": {
        "available": {
          "items": {
            "keys": {
              "amount": {
                "type": "number"
              },
              "currency": {
                "type": "string"
              },
              "source_types": {
                "keys": {
                  "card": {
                    "type": "number"
                  }
                },
                "type": "object"
              }
            },
            "type": "object"
          },
          "type": "array"
        },
        "connect_reserved": {
          "items": {
            "keys": {
              "amount": {
                "type": "number"
              },
              "currency": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "type": "array"
        },
        "livemode": {
          "type": "boolean"
        },
        "object": {
          "type": "string"
        },
        "pending": {
          "items": {
            "keys": {
              "amount": {
                "type": "number"
              },
              "currency": {
                "type": "string"
              },
              "source_types": {
                "keys": {
                  "card": {
                    "type": "number"
                  }
                },
                "type": "object"
              }
            },
            "type": "object"
          },
          "type": "array"
        }
      },
      "type": "object"
    },
    "charges.json": {
      "items": {
        "keys": {
          "amount": {
            "type": "string"
          },
          "amount_refunded": {
            "type": "string"
          },
          "created": {
            "type": "string"
          },
          "currency": {
            "type": "string"
          },
          "customer": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "paid": {
            "type": "string"
          },
          "payment_intent": {
            "type": "string"
          },
          "refunded": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "customers.json": {
      "items": {
        "keys": {
          "balance": {
            "type": "string"
          },
          "created": {
            "type": "string"
          },
          "currency": {
            "type": "string"
          },
          "delinquent": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "phone": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "invoices.json": {
      "items": {
        "keys": {
          "amount_due": {
            "type": "string"
          },
          "amount_paid": {
            "type": "string"
          },
          "charge": {
            "type": "string"
          },
          "created": {
            "type": "string"
          },
          "currency": {
            "type": "string"
          },
          "customer": {
            "type": "string"
          },
          "due_date": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "number": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "subscription": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "prices.json": {
      "items": {
        "keys": {
          "active": {
            "type": "string"
          },
          "currency": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "nickname": {
            "type": "string"
          },
          "product": {
            "type": "string"
          },
          "recurring_interval": {
            "type": "string"
          },
          "unit_amount": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "products.json": {
      "items": {
        "keys": {
          "active": {
            "type": "string"
          },
          "created": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "subscriptions.json": {
      "items": {
        "keys": {
          "cancel_at_period_end": {
            "type": "string"
          },
          "created": {
            "type": "string"
          },
          "current_period_end": {
            "type": "string"
          },
          "current_period_start": {
            "type": "string"
          },
          "customer": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "price": {
            "type": "string"
          },
          "quantity": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "telegram-api": {
    "bot.json": {
      "keys": {
        "can_join_groups": {
          "type": "boolean"
        },
        "can_read_all_group_messages": {
          "type": "boolean"
        },
        "first_name": {
          "type": "string"
        },
        "id": {
          "type": "number"
        },
        "is_bot": {
          "type": "boolean"
        },
        "supports_inline_queries": {
          "type": "boolean"
        },
        "username": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "chat_members.json": {
      "items": {
        "keys": {
          "chat_id": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "user_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "chats.json": {
      "items": {
        "keys": {
          "description": {
            "type": "string"
          },
          "first_name": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "last_name": {
            "type": "string"
          },
          "member_count": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "type": {
            "type": "string"
          },
          "username": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "messages.json": {
      "items": {
        "keys": {
          "chat_id": {
            "type": "string"
          },
          "date": {
            "type": "string"
          },
          "from_id": {
            "type": "string"
          },
          "message_id": {
            "type": "string"
          },
          "reply_to_message_id": {
            "type": "string"
          },
          "text": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "users.json": {
      "items": {
        "keys": {
          "first_name": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "is_bot": {
            "type": "string"
          },
          "language_code": {
            "type": "string"
          },
          "last_name": {
            "type": "string"
          },
          "username": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "ticketmaster-api": {
    "attractions.json": {
      "items": {
        "keys": {
          "genre": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "segment": {
            "type": "string"
          },
          "type": {
            "type": "string"
          },
          "upcoming_events": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "classifications.json": {
      "items": {
        "keys": {
          "genre": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "segment": {
            "type": "string"
          },
          "subgenre": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "events.json": {
      "items": {
        "keys": {
          "attraction_id": {
            "type": "string"
          },
          "classification_id": {
            "type": "string"
          },
          "currency": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "price_max": {
            "type": "string"
          },
          "price_min": {
            "type": "string"
          },
          "start_datetime": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "venue_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "venues.json": {
      "items": {
        "keys": {
          "address": {
            "type": "string"
          },
          "city": {
            "type": "string"
          },
          "country": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "latitude": {
            "type": "string"
          },
          "longitude": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "postal_code": {
            "type": "string"
          },
          "state": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "tmdb-api": {
    "credits.json": {
      "items": {
        "keys": {
          "character": {
            "type": "string"
          },
          "credit_type": {
            "type": "string"
          },
          "job": {
            "type": "string"
          },
          "movie_id": {
            "type": "string"
          },
          "order": {
            "type": "string"
          },
          "person_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "genres.json": {
      "items": {
        "keys": {
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "movies.json": {
      "items": {
        "keys": {
          "genre_ids": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "original_language": {
            "type": "string"
          },
          "overview": {
            "type": "string"
          },
          "popularity": {
            "type": "string"
          },
          "release_date": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "vote_average": {
            "type": "string"
          },
          "vote_count": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "people.json": {
      "items": {
        "keys": {
          "gender": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "known_for_department": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "popularity": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "tv.json": {
      "items": {
        "keys": {
          "first_air_date": {
            "type": "string"
          },
          "genre_ids": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "number_of_episodes": {
            "type": "string"
          },
          "number_of_seasons": {
            "type": "string"
          },
          "overview": {
            "type": "string"
          },
          "popularity": {
            "type": "string"
          },
          "vote_average": {
            "type": "string"
          },
          "vote_count": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "trello-api": {
    "boards.json": {
      "items": {
        "keys": {
          "closed": {
            "type": "string"
          },
          "desc": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "id_organization": {
            "type": "string"
          },
          "member_ids": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "url": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "cards.json": {
      "items": {
        "keys": {
          "closed": {
            "type": "string"
          },
          "desc": {
            "type": "string"
          },
          "due": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "id_board": {
            "type": "string"
          },
          "id_list": {
            "type": "string"
          },
          "labels": {
            "type": "string"
          },
          "member_ids": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "pos": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "checklists.json": {
      "items": {
        "keys": {
          "id": {
            "type": "string"
          },
          "id_board": {
            "type": "string"
          },
          "id_card": {
            "type": "string"
          },
          "items": {
            "type": "string"
          },
          "name": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "lists.json": {
      "items": {
        "keys": {
          "closed": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "id_board": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "pos": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "members.json": {
      "items": {
        "keys": {
          "email": {
            "type": "string"
          },
          "full_name": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "initials": {
            "type": "string"
          },
          "username": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "twilio-api": {
    "account.json": {
      "keys": {
        "auth_token": {
          "type": "string"
        },
        "date_created": {
          "type": "string"
        },
        "date_updated": {
          "type": "string"
        },
        "friendly_name": {
          "type": "string"
        },
        "owner_account_sid": {
          "type": "string"
        },
        "sid": {
          "type": "string"
        },
        "status": {
          "type": "string"
        },
        "type": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "calls.json": {
      "items": {
        "keys": {
          "answered_by": {
            "type": "string"
          },
          "date_created": {
            "type": "string"
          },
          "direction": {
            "type": "string"
          },
          "duration": {
            "type": "string"
          },
          "end_time": {
            "type": "string"
          },
          "from_number": {
            "type": "string"
          },
          "price": {
            "type": "string"
          },
          "price_unit": {
            "type": "string"
          },
          "sid": {
            "type": "string"
          },
          "start_time": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "to_number": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "messages.json": {
      "items": {
        "keys": {
          "body": {
            "type": "string"
          },
          "date_created": {
            "type": "string"
          },
          "date_sent": {
            "type": "string"
          },
          "direction": {
            "type": "string"
          },
          "error_code": {
            "type": "string"
          },
          "from_number": {
            "type": "string"
          },
          "num_segments": {
            "type": "string"
          },
          "price": {
            "type": "string"
          },
          "price_unit": {
            "type": "string"
          },
          "sid": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "to_number": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "phone_numbers.json": {
      "items": {
        "keys": {
          "capabilities_fax": {
            "type": "string"
          },
          "date_created": {
            "type": "string"
          },
          "friendly_name": {
            "type": "string"
          },
          "iso_country": {
            "type": "string"
          },
          "mms_enabled": {
            "type": "string"
          },
          "phone_number": {
            "type": "string"
          },
          "sid": {
            "type": "string"
          },
          "sms_enabled": {
            "type": "string"
          },
          "voice_enabled": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "twitch-api": {
    "channels.json": {
      "items": {
        "keys": {
          "broadcaster_id": {
            "type": "string"
          },
          "broadcaster_language": {
            "type": "string"
          },
          "broadcaster_login": {
            "type": "string"
          },
          "broadcaster_name": {
            "type": "string"
          },
          "follower_count": {
            "type": "string"
          },
          "game_id": {
            "type": "string"
          },
          "game_name": {
            "type": "string"
          },
          "tags": {
            "type": "string"
          },
          "title": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "clips.json": {
      "items": {
        "keys": {
          "broadcaster_id": {
            "type": "string"
          },
          "broadcaster_name": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "creator_id": {
            "type": "string"
          },
          "creator_name": {
            "type": "string"
          },
          "duration": {
            "type": "string"
          },
          "game_id": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "url": {
            "type": "string"
          },
          "view_count": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "games.json": {
      "items": {
        "keys": {
          "box_art_url": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "rank": {
            "type": "string"
          },
          "viewer_count": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "streams.json": {
      "items": {
        "keys": {
          "game_id": {
            "type": "string"
          },
          "game_name": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "is_live": {
            "type": "string"
          },
          "language": {
            "type": "string"
          },
          "started_at": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "type": {
            "type": "string"
          },
          "user_id": {
            "type": "string"
          },
          "user_login": {
            "type": "string"
          },
          "user_name": {
            "type": "string"
          },
          "viewer_count": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "users.json": {
      "items": {
        "keys": {
          "broadcaster_type": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "display_name": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "login": {
            "type": "string"
          },
          "profile_image_url": {
            "type": "string"
          },
          "type": {
            "type": "string"
          },
          "view_count": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "twitter-api": {
    "follows.json": {
      "items": {
        "keys": {
          "follower_id": {
            "type": "string"
          },
          "following_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "likes.json": {
      "items": {
        "keys": {
          "tweet_id": {
            "type": "string"
          },
          "user_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "retweets.json": {
      "items": {
        "keys": {
          "tweet_id": {
            "type": "string"
          },
          "user_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "tweets.json": {
      "items": {
        "keys": {
          "author_id": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "lang": {
            "type": "string"
          },
          "like_count": {
            "type": "string"
          },
          "quote_count": {
            "type": "string"
          },
          "reply_count": {
            "type": "string"
          },
          "reply_to_tweet_id": {
            "type": "string"
          },
          "retweet_count": {
            "type": "string"
          },
          "text": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "users.json": {
      "items": {
        "keys": {
          "created_at": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "followers_count": {
            "type": "string"
          },
          "following_count": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "location": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "profile_image_url": {
            "type": "string"
          },
          "protected": {
            "type": "string"
          },
          "tweet_count": {
            "type": "string"
          },
          "username": {
            "type": "string"
          },
          "verified": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "typeform-api": {
    "answers.json": {
      "items": {
        "keys": {
          "answer": {
            "type": "string"
          },
          "field_id": {
            "type": "string"
          },
          "field_type": {
            "type": "string"
          },
          "ref": {
            "type": "string"
          },
          "response_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "fields.json": {
      "items": {
        "keys": {
          "choices": {
            "type": "string"
          },
          "field_id": {
            "type": "string"
          },
          "field_type": {
            "type": "string"
          },
          "form_id": {
            "type": "string"
          },
          "order": {
            "type": "string"
          },
          "ref": {
            "type": "string"
          },
          "required": {
            "type": "string"
          },
          "title": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "forms.json": {
      "items": {
        "keys": {
          "created_time": {
            "type": "string"
          },
          "form_id": {
            "type": "string"
          },
          "is_public": {
            "type": "string"
          },
          "language": {
            "type": "string"
          },
          "last_updated_time": {
            "type": "string"
          },
          "response_count": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "workspace": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "responses.json": {
      "items": {
        "keys": {
          "completed": {
            "type": "string"
          },
          "form_id": {
            "type": "string"
          },
          "landed_time": {
            "type": "string"
          },
          "response_id": {
            "type": "string"
          },
          "submitted_time": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "uber-api": {
    "products.json": {
      "items": {
        "keys": {
          "base_fare": {
            "type": "string"
          },
          "booking_fee": {
            "type": "string"
          },
          "capacity": {
            "type": "string"
          },
          "cost_per_mile": {
            "type": "string"
          },
          "cost_per_minute": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "display_name": {
            "type": "string"
          },
          "image_url": {
            "type": "string"
          },
          "minimum_fare": {
            "type": "string"
          },
          "product_id": {
            "type": "string"
          },
          "shared": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "rider.json": {
      "keys": {
        "email": {
          "type": "string"
        },
        "first_name": {
          "type": "string"
        },
        "home_address": {
          "type": "string"
        },
        "last_name": {
          "type": "string"
        },
        "member_since": {
          "type": "string"
        },
        "payment_methods": {
          "items": {
            "keys": {
              "balance": {
                "type": "number"
              },
              "brand": {
                "type": "string"
              },
              "default": {
                "type": "boolean"
              },
              "last_four": {
                "type": "string"
              },
              "payment_method_id": {
                "type": "string"
              },
              "type": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "type": "array"
        },
        "phone_number": {
          "type": "string"
        },
        "promo_code": {
          "type": "string"
        },
        "rating": {
          "type": "number"
        },
        "rider_id": {
          "type": "string"
        },
        "work_address": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "trips.json": {
      "items": {
        "keys": {
          "completed_at": {
            "type": "string"
          },
          "distance_miles": {
            "type": "string"
          },
          "driver_name": {
            "type": "string"
          },
          "duration_minutes": {
            "type": "string"
          },
          "end_address": {
            "type": "string"
          },
          "end_latitude": {
            "type": "string"
          },
          "end_longitude": {
            "type": "string"
          },
          "fare": {
            "type": "string"
          },
          "license_plate": {
            "type": "string"
          },
          "product_id": {
            "type": "string"
          },
          "request_id": {
            "type": "string"
          },
          "requested_at": {
            "type": "string"
          },
          "rider_id": {
            "type": "string"
          },
          "start_address": {
            "type": "string"
          },
          "start_latitude": {
            "type": "string"
          },
          "start_longitude": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "surge_multiplier": {
            "type": "string"
          },
          "vehicle": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "ups-api": {
    "rates.json": {
      "items": {
        "keys": {
          "currency": {
            "type": "string"
          },
          "delivery_date": {
            "type": "string"
          },
          "dest_zip": {
            "type": "string"
          },
          "origin_zip": {
            "type": "string"
          },
          "service_code": {
            "type": "string"
          },
          "service_name": {
            "type": "string"
          },
          "total_charge": {
            "type": "string"
          },
          "transit_days": {
            "type": "string"
          },
          "weight_lb": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "shipments.json": {
      "items": {
        "keys": {
          "currency": {
            "type": "string"
          },
          "dest_zip": {
            "type": "string"
          },
          "label_url": {
            "type": "string"
          },
          "origin_zip": {
            "type": "string"
          },
          "service_code": {
            "type": "string"
          },
          "service_name": {
            "type": "string"
          },
          "ship_date": {
            "type": "string"
          },
          "total_charge": {
            "type": "string"
          },
          "tracking_number": {
            "type": "string"
          },
          "weight_lb": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "tracking.json": {
      "items": {
        "keys": {
          "latest_activity": {
            "type": "string"
          },
          "latest_activity_location": {
            "type": "string"
          },
          "latest_activity_time": {
            "type": "string"
          },
          "scheduled_delivery": {
            "type": "string"
          },
          "service_name": {
            "type": "string"
          },
          "ship_date": {
            "type": "string"
          },
          "status_code": {
            "type": "string"
          },
          "status_description": {
            "type": "string"
          },
          "status_type": {
            "type": "string"
          },
          "tracking_number": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "vimeo-api": {
    "users.json": {
      "items": {
        "keys": {
          "account": {
            "type": "string"
          },
          "bio": {
            "type": "string"
          },
          "created_time": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "link": {
            "type": "string"
          },
          "location": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "websites": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "videos.json": {
      "items": {
        "keys": {
          "created_time": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "duration": {
            "type": "string"
          },
          "height": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "likes": {
            "type": "string"
          },
          "link": {
            "type": "string"
          },
          "modified_time": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "plays": {
            "type": "string"
          },
          "privacy": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "user_id": {
            "type": "string"
          },
          "width": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "webflow-api": {
    "collections.json": {
      "items": {
        "keys": {
          "created_on": {
            "type": "string"
          },
          "display_name": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "last_updated": {
            "type": "string"
          },
          "singular_name": {
            "type": "string"
          },
          "site_id": {
            "type": "string"
          },
          "slug": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "items.json": {
      "items": {
        "keys": {
          "collection_id": {
            "type": "string"
          },
          "created_on": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "is_archived": {
            "type": "string"
          },
          "is_draft": {
            "type": "string"
          },
          "last_updated": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "slug": {
            "type": "string"
          },
          "summary": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "sites.json": {
      "items": {
        "keys": {
          "created_on": {
            "type": "string"
          },
          "custom_domains": {
            "type": "string"
          },
          "display_name": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "last_published": {
            "type": "string"
          },
          "preview_url": {
            "type": "string"
          },
          "short_name": {
            "type": "string"
          },
          "time_zone": {
            "type": "string"
          },
          "workspace_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "whatsapp-api": {
    "business.json": {
      "keys": {
        "business_account_id": {
          "type": "string"
        },
        "display_phone_number": {
          "type": "string"
        },
        "messaging_limit_tier": {
          "type": "string"
        },
        "name": {
          "type": "string"
        },
        "phone_number_id": {
          "type": "string"
        },
        "verified_name": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "contacts.json": {
      "items": {
        "keys": {
          "last_seen": {
            "type": "string"
          },
          "opted_in": {
            "type": "string"
          },
          "phone_number": {
            "type": "string"
          },
          "profile_name": {
            "type": "string"
          },
          "wa_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "conversations.json": {
      "items": {
        "keys": {
          "conversation_id": {
            "type": "string"
          },
          "last_message_at": {
            "type": "string"
          },
          "origin": {
            "type": "string"
          },
          "started_at": {
            "type": "string"
          },
          "wa_id": {
            "type": "string"
          },
          "within_24h_window": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "messages.json": {
      "items": {
        "keys": {
          "conversation_id": {
            "type": "string"
          },
          "direction": {
            "type": "string"
          },
          "from_wa_id": {
            "type": "string"
          },
          "message_id": {
            "type": "string"
          },
          "sent_at": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "template_name": {
            "type": "string"
          },
          "text": {
            "type": "string"
          },
          "to_wa_id": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "templates.json": {
      "items": {
        "keys": {
          "body_text": {
            "type": "string"
          },
          "category": {
            "type": "string"
          },
          "header_text": {
            "type": "string"
          },
          "language": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "woocommerce-api": {
    "customers.json": {
      "items": {
        "keys": {
          "billing_city": {
            "type": "string"
          },
          "billing_country": {
            "type": "string"
          },
          "date_created": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "first_name": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "is_paying_customer": {
            "type": "string"
          },
          "last_name": {
            "type": "string"
          },
          "role": {
            "type": "string"
          },
          "username": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "orders.json": {
      "items": {
        "keys": {
          "billing_email": {
            "type": "string"
          },
          "billing_first_name": {
            "type": "string"
          },
          "billing_last_name": {
            "type": "string"
          },
          "currency": {
            "type": "string"
          },
          "customer_id": {
            "type": "string"
          },
          "date_created": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "number": {
            "type": "string"
          },
          "payment_method": {
            "type": "string"
          },
          "payment_method_title": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "subtotal": {
            "type": "string"
          },
          "total": {
            "type": "string"
          },
          "total_tax": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "products.json": {
      "items": {
        "keys": {
          "categories": {
            "type": "string"
          },
          "date_created": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "manage_stock": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "on_sale": {
            "type": "string"
          },
          "price": {
            "type": "string"
          },
          "regular_price": {
            "type": "string"
          },
          "sale_price": {
            "type": "string"
          },
          "sku": {
            "type": "string"
          },
          "slug": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "stock_quantity": {
            "type": "string"
          },
          "stock_status": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "wordpress-api": {
    "categories.json": {
      "items": {
        "keys": {
          "count": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "parent": {
            "type": "string"
          },
          "slug": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "comments.json": {
      "items": {
        "keys": {
          "author_email": {
            "type": "string"
          },
          "author_name": {
            "type": "string"
          },
          "content": {
            "type": "string"
          },
          "date": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "parent": {
            "type": "string"
          },
          "post": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "media.json": {
      "items": {
        "keys": {
          "alt_text": {
            "type": "string"
          },
          "author": {
            "type": "string"
          },
          "date": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "media_type": {
            "type": "string"
          },
          "mime_type": {
            "type": "string"
          },
          "post": {
            "type": "string"
          },
          "slug": {
            "type": "string"
          },
          "source_url": {
            "type": "string"
          },
          "title": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "pages.json": {
      "items": {
        "keys": {
          "author": {
            "type": "string"
          },
          "content": {
            "type": "string"
          },
          "date": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "modified": {
            "type": "string"
          },
          "parent": {
            "type": "string"
          },
          "slug": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "title": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "posts.json": {
      "items": {
        "keys": {
          "author": {
            "type": "string"
          },
          "category_ids": {
            "type": "string"
          },
          "comment_status": {
            "type": "string"
          },
          "content": {
            "type": "string"
          },
          "date": {
            "type": "string"
          },
          "excerpt": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "modified": {
            "type": "string"
          },
          "slug": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "tag_ids": {
            "type": "string"
          },
          "title": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "tags.json": {
      "items": {
        "keys": {
          "count": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "slug": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "users.json": {
      "items": {
        "keys": {
          "avatar_url": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "roles": {
            "type": "string"
          },
          "slug": {
            "type": "string"
          },
          "url": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "xero-api": {
    "accounts.json": {
      "items": {
        "keys": {
          "account_id": {
            "type": "string"
          },
          "code": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "enable_payments_to_account": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "tax_type": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "contacts.json": {
      "items": {
        "keys": {
          "account_number": {
            "type": "string"
          },
          "contact_id": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "first_name": {
            "type": "string"
          },
          "is_customer": {
            "type": "string"
          },
          "is_supplier": {
            "type": "string"
          },
          "last_name": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "invoices.json": {
      "items": {
        "keys": {
          "amount_due": {
            "type": "string"
          },
          "amount_paid": {
            "type": "string"
          },
          "contact_id": {
            "type": "string"
          },
          "contact_name": {
            "type": "string"
          },
          "currency_code": {
            "type": "string"
          },
          "date": {
            "type": "string"
          },
          "due_date": {
            "type": "string"
          },
          "invoice_id": {
            "type": "string"
          },
          "invoice_number": {
            "type": "string"
          },
          "line_amount_types": {
            "type": "string"
          },
          "reference": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "sub_total": {
            "type": "string"
          },
          "total": {
            "type": "string"
          },
          "total_tax": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "yelp-api": {
    "businesses.json": {
      "items": {
        "keys": {
          "address": {
            "type": "string"
          },
          "category": {
            "type": "string"
          },
          "category_title": {
            "type": "string"
          },
          "city": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "image_url": {
            "type": "string"
          },
          "is_closed": {
            "type": "string"
          },
          "latitude": {
            "type": "string"
          },
          "longitude": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "phone": {
            "type": "string"
          },
          "price": {
            "type": "string"
          },
          "rating": {
            "type": "string"
          },
          "review_count": {
            "type": "string"
          },
          "state": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "categories.json": {
      "items": {
        "keys": {
          "alias": {
            "type": "string"
          },
          "parent": {
            "type": "string"
          },
          "title": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "reviews.json": {
      "items": {
        "keys": {
          "business_id": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "rating": {
            "type": "string"
          },
          "text": {
            "type": "string"
          },
          "time_created": {
            "type": "string"
          },
          "user_name": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "youtube-api": {
    "analytics.json": {
      "keys": {
        "channel": {
          "keys": {
            "averageViewDuration": {
              "type": "number"
            },
            "comments": {
              "type": "number"
            },
            "dislikes": {
              "type": "number"
            },
            "estimatedMinutesWatched": {
              "type": "number"
            },
            "likes": {
              "type": "number"
            },
            "period": {
              "type": "string"
            },
            "shares": {
              "type": "number"
            },
            "subscribersGained": {
              "type": "number"
            },
            "subscribersLost": {
              "type": "number"
            },
            "views": {
              "type": "number"
            }
          },
          "type": "object"
        },
        "videos": {
          "items": {
            "keys": {
              "averageViewDuration": {
                "type": "number"
              },
              "averageViewPercentage": {
                "type": "number"
              },
              "comments": {
                "type": "number"
              },
              "dislikes": {
                "type": "number"
              },
              "estimatedMinutesWatched": {
                "type": "number"
              },
              "likes": {
                "type": "number"
              },
              "shares": {
                "type": "number"
              },
              "videoId": {
                "type": "string"
              },
              "views": {
                "type": "number"
              }
            },
            "type": "object"
          },
          "type": "array"
        }
      },
      "type": "object"
    },
    "captions.json": {
      "items": {
        "keys": {
          "caption_id": {
            "type": "string"
          },
          "isDraft": {
            "type": "string"
          },
          "language": {
            "type": "string"
          },
          "lastUpdated": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "trackKind": {
            "type": "string"
          },
          "videoId": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "channel.json": {
      "keys": {
        "brandingSettings": {
          "keys": {
            "channel": {
              "keys": {
                "country": {
                  "type": "string"
                },
                "description": {
                  "type": "string"
                },
                "keywords": {
                  "type": "string"
                },
                "title": {
                  "type": "string"
                },
                "unsubscribedTrailer": {
                  "type": "string"
                }
              },
              "type": "object"
            },
            "image": {
              "keys": {
                "bannerExternalUrl": {
                  "type": "string"
                }
              },
              "type": "object"
            }
          },
          "type": "object"
        },
        "contentDetails": {
          "keys": {
            "relatedPlaylists": {
              "keys": {
                "likes": {
                  "type": "string"
                },
                "uploads": {
                  "type": "string"
                }
              },
              "type": "object"
            }
          },
          "type": "object"
        },
        "id": {
          "type": "string"
        },
        "snippet": {
          "keys": {
            "country": {
              "type": "string"
            },
            "customUrl": {
              "type": "string"
            },
            "description": {
              "type": "string"
            },
            "publishedAt": {
              "type": "string"
            },
            "thumbnails": {
              "keys": {
                "default": {
                  "keys": {
                    "height": {
                      "type": "number"
                    },
                    "url": {
                      "type": "string"
                    },
                    "width": {
                      "type": "number"
                    }
                  },
                  "type": "object"
                },
                "high": {
                  "keys": {
                    "height": {
                      "type": "number"
                    },
                    "url": {
                      "type": "string"
                    },
                    "width": {
                      "type": "number"
                    }
                  },
                  "type": "object"
                },
                "medium": {
                  "keys": {
                    "height": {
                      "type": "number"
                    },
                    "url": {
                      "type": "string"
                    },
                    "width": {
                      "type": "number"
                    }
                  },
                  "type": "object"
                }
              },
              "type": "object"
            },
            "title": {
              "type": "string"
            }
          },
          "type": "object"
        },
        "statistics": {
          "keys": {
            "hiddenSubscriberCount": {
              "type": "boolean"
            },
            "subscriberCount": {
              "type": "string"
            },
            "videoCount": {
              "type": "string"
            },
            "viewCount": {
              "type": "string"
            }
          },
          "type": "object"
        }
      },
      "type": "object"
    },
    "channel_sections.json": {
      "items": {
        "keys": {
          "contentDetails": {
            "keys": {
              "playlists": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              }
            },
            "type": "object"
          },
          "id": {
            "type": "string"
          },
          "snippet": {
            "keys": {
              "channelId": {
                "type": "string"
              },
              "position": {
                "type": "number"
              },
              "title": {
                "type": "string"
              },
              "type": {
                "type": "string"
              }
            },
            "type": "object"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "comments.json": {
      "items": {
        "keys": {
          "authorChannelId": {
            "type": "string"
          },
          "authorDisplayName": {
            "type": "string"
          },
          "channelId": {
            "type": "string"
          },
          "comment_id": {
            "type": "string"
          },
          "likeCount": {
            "type": "string"
          },
          "moderationStatus": {
            "type": "string"
          },
          "parentId": {
            "type": "string"
          },
          "publishedAt": {
            "type": "string"
          },
          "textDisplay": {
            "type": "string"
          },
          "updatedAt": {
            "type": "string"
          },
          "videoId": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "playlist_items.json": {
      "items": {
        "keys": {
          "channelId": {
            "type": "string"
          },
          "playlistId": {
            "type": "string"
          },
          "playlist_item_id": {
            "type": "string"
          },
          "position": {
            "type": "string"
          },
          "publishedAt": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "videoId": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "playlists.json": {
      "items": {
        "keys": {
          "channelId": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "itemCount": {
            "type": "string"
          },
          "playlist_id": {
            "type": "string"
          },
          "privacyStatus": {
            "type": "string"
          },
          "publishedAt": {
            "type": "string"
          },
          "title": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "video_categories.json": {
      "items": {
        "keys": {
          "id": {
            "type": "string"
          },
          "snippet": {
            "keys": {
              "assignable": {
                "type": "boolean"
              },
              "channelId": {
                "type": "string"
              },
              "title": {
                "type": "string"
              }
            },
            "type": "object"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "videos.json": {
      "items": {
        "keys": {
          "categoryId": {
            "type": "string"
          },
          "channelId": {
            "type": "string"
          },
          "commentCount": {
            "type": "string"
          },
          "defaultAudioLanguage": {
            "type": "string"
          },
          "defaultLanguage": {
            "type": "string"
          },
          "definition": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "dimension": {
            "type": "string"
          },
          "dislikeCount": {
            "type": "string"
          },
          "duration": {
            "type": "string"
          },
          "embeddable": {
            "type": "string"
          },
          "likeCount": {
            "type": "string"
          },
          "liveBroadcastContent": {
            "type": "string"
          },
          "privacyStatus": {
            "type": "string"
          },
          "publishAt": {
            "type": "string"
          },
          "publishedAt": {
            "type": "string"
          },
          "tags": {
            "type": "string"
          },
          "thumbnailUrl": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "video_id": {
            "type": "string"
          },
          "viewCount": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "zendesk-api": {
    "comments.json": {
      "items": {
        "keys": {
          "author_id": {
            "type": "string"
          },
          "body": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "public": {
            "type": "string"
          },
          "ticket_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "organizations.json": {
      "items": {
        "keys": {
          "created_at": {
            "type": "string"
          },
          "domain_names": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "tickets.json": {
      "items": {
        "keys": {
          "assignee_id": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "organization_id": {
            "type": "string"
          },
          "priority": {
            "type": "string"
          },
          "requester_id": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "subject": {
            "type": "string"
          },
          "tags": {
            "type": "string"
          },
          "type": {
            "type": "string"
          },
          "updated_at": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "users.json": {
      "items": {
        "keys": {
          "active": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "organization_id": {
            "type": "string"
          },
          "role": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "zillow-api": {
    "agents.json": {
      "items": {
        "keys": {
          "active_listings": {
            "type": "string"
          },
          "agent_id": {
            "type": "string"
          },
          "brokerage": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "license_number": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "phone": {
            "type": "string"
          },
          "rating": {
            "type": "string"
          },
          "reviews": {
            "type": "string"
          },
          "sold_last_12mo": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "price_history.json": {
      "items": {
        "keys": {
          "event": {
            "type": "string"
          },
          "event_date": {
            "type": "string"
          },
          "price": {
            "type": "string"
          },
          "price_per_sqft": {
            "type": "string"
          },
          "source": {
            "type": "string"
          },
          "zpid": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "properties.json": {
      "items": {
        "keys": {
          "address": {
            "type": "string"
          },
          "bathrooms": {
            "type": "string"
          },
          "bedrooms": {
            "type": "string"
          },
          "city": {
            "type": "string"
          },
          "days_on_zillow": {
            "type": "string"
          },
          "home_type": {
            "type": "string"
          },
          "latitude": {
            "type": "string"
          },
          "list_price": {
            "type": "string"
          },
          "listing_agent_id": {
            "type": "string"
          },
          "living_area_sqft": {
            "type": "string"
          },
          "longitude": {
            "type": "string"
          },
          "lot_size_sqft": {
            "type": "string"
          },
          "rent_zestimate": {
            "type": "string"
          },
          "state": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "year_built": {
            "type": "string"
          },
          "zestimate": {
            "type": "string"
          },
          "zipcode": {
            "type": "string"
          },
          "zpid": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "saved_searches.json": {
      "items": {
        "keys": {
          "city": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "home_type": {
            "type": "string"
          },
          "max_price": {
            "type": "string"
          },
          "min_baths": {
            "type": "string"
          },
          "min_beds": {
            "type": "string"
          },
          "min_price": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "search_id": {
            "type": "string"
          },
          "state": {
            "type": "string"
          },
          "user_id": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "zoom-api": {
    "meetings.json": {
      "items": {
        "keys": {
          "agenda": {
            "type": "string"
          },
          "created_at": {
            "type": "string"
          },
          "duration": {
            "type": "string"
          },
          "host_id": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "join_url": {
            "type": "string"
          },
          "start_time": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "timezone": {
            "type": "string"
          },
          "topic": {
            "type": "string"
          },
          "type": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "recordings.json": {
      "items": {
        "keys": {
          "file_size": {
            "type": "string"
          },
          "file_type": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "meeting_id": {
            "type": "string"
          },
          "play_url": {
            "type": "string"
          },
          "recording_end": {
            "type": "string"
          },
          "recording_start": {
            "type": "string"
          },
          "recording_type": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "registrants.json": {
      "items": {
        "keys": {
          "create_time": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "first_name": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "join_time": {
            "type": "string"
          },
          "last_name": {
            "type": "string"
          },
          "meeting_id": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "user.json": {
      "keys": {
        "account_id": {
          "type": "string"
        },
        "created_at": {
          "type": "string"
        },
        "dept": {
          "type": "string"
        },
        "email": {
          "type": "string"
        },
        "first_name": {
          "type": "string"
        },
        "id": {
          "type": "string"
        },
        "last_name": {
          "type": "string"
        },
        "pmi": {
          "type": "number"
        },
        "role_name": {
          "type": "string"
        },
        "status": {
          "type": "string"
        },
        "timezone": {
          "type": "string"
        },
        "type": {
          "type": "number"
        },
        "verified": {
          "type": "number"
        }
      },
      "type": "object"
    }
  }
}
""")
# === END BASELINE ===


if __name__ == "__main__":
    sys.exit(main())
