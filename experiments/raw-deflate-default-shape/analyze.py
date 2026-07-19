#!/usr/bin/env python3
"""Validate and analyze one complete raw-DEFLATE scoring campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


sys.dont_write_bytecode = True
PYTHON = Path(
    "/Applications/Xcode.app/Contents/Developer/Library/Frameworks/"
    "Python3.framework/Versions/3.9/bin/python3.9"
)
MASK64 = (1 << 64) - 1
ORDER_SEED = 0x5244464C41544531
BOOTSTRAP_SEED = 0x5244424F4F543031
BOOTSTRAP_RESAMPLES = 10_000
LOWER_INDEX = 249
UPPER_INDEX = 9_749
MEMBER_COUNT = 12
PASSES = 4
DECODED_BYTES = 847_754_320
CALL_COUNT = 48
VARIANTS = ("F", "N", "Z")
ORDER_STRATA = (
    "F,N,Z",
    "F,Z,N",
    "N,F,Z",
    "N,Z,F",
    "Z,F,N",
    "Z,N,F",
)
EXPECTED_SCORE_HOST = {
    "machine_model": "Mac16,12",
    "chip_type": "Apple M4",
    "processor_description": "proc 10:4:6:0",
    "processor_core_count": 10,
    "physical_memory": "16 GB",
    "architecture": "arm64",
    "macos_product_version": "26.5.1",
    "macos_build_version": "25F80",
    "platform": "macOS-26.5.1-arm64-arm-64bit",
}


class AnalysisFailure(ValueError):
    """The campaign is incomplete, inconsistent, or non-scoring."""


class XorShift64Star:
    def __init__(self, seed: int) -> None:
        if not 0 < seed <= MASK64:
            raise ValueError("xorshift seed must be a nonzero u64")
        self.state = seed

    def next(self) -> int:
        self.state ^= self.state >> 12
        self.state ^= (self.state << 25) & MASK64
        self.state ^= self.state >> 27
        self.state &= MASK64
        return (self.state * 2_685_821_657_736_338_717) & MASK64


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json_object(path: Path, label: str) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AnalysisFailure("could not read %s: %s" % (label, error))
    if not isinstance(value, dict):
        raise AnalysisFailure("%s is not a JSON object" % label)
    return value


def read_raw(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as source:
            for line_number, line in enumerate(source, 1):
                if not line.strip():
                    raise AnalysisFailure("blank raw row at line %d" % line_number)
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise AnalysisFailure("raw row %d is not an object" % line_number)
                records.append(value)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AnalysisFailure("could not read raw sample rows: %s" % error)
    return records


def require_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(byte not in "0123456789abcdef" for byte in value)
    ):
        raise AnalysisFailure("%s is not a lowercase SHA-256" % label)
    return value


def median(values: Iterable[float]) -> float:
    ordered = sorted(values)
    if not ordered:
        raise AnalysisFailure("median of empty data")
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def mad_over_median(values: Sequence[float]) -> float:
    center = median(values)
    if center <= 0:
        raise AnalysisFailure("nonpositive throughput median")
    return median(abs(value - center) for value in values) / center


def expected_schedule() -> List[str]:
    orders = list(ORDER_STRATA) * 5
    rng = XorShift64Star(ORDER_SEED)
    for index in range(len(orders) - 1, 0, -1):
        swap = rng.next() % (index + 1)
        orders[index], orders[swap] = orders[swap], orders[index]
    return orders


def validate_sample(
    sample: Any,
    variant: str,
    ordinal: int,
    expected_output_sha: str,
    block_index: int,
) -> Dict[str, Any]:
    if not isinstance(sample, dict):
        raise AnalysisFailure("block %d sample is not an object" % block_index)
    if (
        sample.get("variant") != variant
        or sample.get("ordinal") != ordinal
        or sample.get("decoded_bytes") != DECODED_BYTES
        or sample.get("passes") != PASSES
        or sample.get("member_count") != MEMBER_COUNT
        or sample.get("call_count") != CALL_COUNT
        or type(sample.get("elapsed_ns")) is not int
        or sample["elapsed_ns"] <= 0
        or sample.get("output_sha256") != expected_output_sha
    ):
        raise AnalysisFailure("block %d has a malformed %s sample" % (block_index, variant))
    return sample


def validate_campaign(
    campaign: Path,
) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]]]:
    metadata_path = campaign / "metadata.json"
    schedule_path = campaign / "schedule.json"
    raw_path = campaign / "raw.jsonl"
    metadata = read_json_object(metadata_path, "campaign metadata")
    schedule = read_json_object(schedule_path, "campaign schedule")
    records = read_raw(raw_path)
    if (
        metadata.get("kind") != "raw-deflate-campaign"
        or metadata.get("mode") != "score"
        or metadata.get("not_a_score") is not False
    ):
        raise AnalysisFailure("analysis refuses non-scoring campaign metadata")
    if metadata.get("status") != "complete":
        raise AnalysisFailure("analysis requires a complete campaign")
    if metadata.get("blocks_expected") != 30 or metadata.get("blocks_completed") != 30:
        raise AnalysisFailure("campaign metadata does not bind exactly 30 blocks")
    if metadata.get("fresh_child_process_per_block") is not True:
        raise AnalysisFailure("campaign does not attest one fresh process per block")
    if metadata.get("passes_per_sample") != PASSES:
        raise AnalysisFailure("campaign pass count changed")
    if metadata.get("decoded_bytes_per_variant") != DECODED_BYTES:
        raise AnalysisFailure("campaign aggregate byte count changed")
    if metadata.get("calls_per_variant") != CALL_COUNT:
        raise AnalysisFailure("campaign aggregate call count changed")
    host = metadata.get("host")
    if (
        not isinstance(host, dict)
        or {key: host.get(key) for key in EXPECTED_SCORE_HOST} != EXPECTED_SCORE_HOST
        or host.get("matches_frozen_score_host") is not True
    ):
        raise AnalysisFailure("campaign did not run on the frozen score host")
    for label in (
        "power_before_preparation",
        "power_before_measurement",
        "power_after_measurement",
    ):
        power = metadata.get(label)
        if (
            not isinstance(power, dict)
            or power.get("power_source") != "AC Power"
            or power.get("power_source_available") is not True
            or power.get("ac_low_power_mode") != 0
            or power.get("ac_low_power_mode_available") is not True
        ):
            raise AnalysisFailure("%s does not bind AC Power with lowpowermode=0" % label)
    thermal = metadata.get("thermal_monitoring")
    if (
        not isinstance(thermal, dict)
        or thermal.get("available") is not False
        or thermal.get("enforced") is not False
        or "No thermal-stability claim" not in thermal.get("limitation", "")
    ):
        raise AnalysisFailure("campaign overclaims unavailable thermal monitoring")
    if metadata.get("warmup_policy") != {
        "candidate_warmup_calls_per_worker": 0,
        "comparator_warmup_calls_per_worker": 0,
        "reference_status_contract_exercised_only_in_parent_before_workers": True,
    }:
        raise AnalysisFailure("campaign warmup policy changed")
    if metadata.get("raw_sha256") != sha256_file(raw_path):
        raise AnalysisFailure("raw sample SHA-256 does not match metadata")
    if metadata.get("schedule_sha256") != sha256_file(schedule_path):
        raise AnalysisFailure("schedule SHA-256 does not match metadata")
    expected_output_sha = require_sha256(
        metadata.get("expected_output_sequence_sha256"), "expected output sequence"
    )
    scoring = metadata.get("scoring")
    if (
        not isinstance(scoring, dict)
        or scoring.get("aggregate")
        != {
            "member_count": MEMBER_COUNT,
            "raw_deflate_bytes": 68_220_415,
            "source_bytes": 211_938_580,
        }
    ):
        raise AnalysisFailure("campaign scoring aggregate changed")
    if not isinstance(metadata.get("generation_freeze"), dict):
        raise AnalysisFailure("campaign lacks a verified generation freeze")
    frozen_source = metadata.get("frozen_source")
    if not isinstance(frozen_source, dict):
        raise AnalysisFailure("campaign lacks a frozen source identity")
    require_sha256(frozen_source.get("sha256"), "frozen source")
    build = metadata.get("build")
    if not isinstance(build, dict) or not isinstance(build.get("proof_reports"), dict):
        raise AnalysisFailure("campaign lacks post-freeze proof reports")
    for variant in ("F", "N"):
        proof = build["proof_reports"].get(variant)
        if (
            not isinstance(proof, dict)
            or proof.get("ir_byte_identical_with_and_without_report") is not True
            or proof.get("collected_post_freeze") is not True
        ):
            raise AnalysisFailure("%s proof-report identity is incomplete" % variant)

    if (
        schedule.get("mode") != "score"
        or schedule.get("not_a_score") is not False
        or schedule.get("variants") != list(VARIANTS)
        or schedule.get("strata_order") != list(ORDER_STRATA)
        or schedule.get("repetitions_per_stratum") != 5
        or schedule.get("seed_hex") != "0x%016x" % ORDER_SEED
        or schedule.get("shuffle")
        != "descending Fisher-Yates; i=n-1..1, j=next()%(i+1)"
    ):
        raise AnalysisFailure("schedule metadata differs from the frozen method")
    scheduled = schedule.get("orders")
    if not isinstance(scheduled, list) or len(scheduled) != 30 or len(records) != 30:
        raise AnalysisFailure("score requires exactly 30 scheduled and recorded rows")
    scheduled_orders = [
        row.get("order") for row in scheduled if isinstance(row, dict)
    ]
    if scheduled_orders != expected_schedule():
        raise AnalysisFailure("schedule differs from the seeded Fisher-Yates vector")

    counts = {stratum: 0 for stratum in ORDER_STRATA}
    positions = {
        variant: {ordinal: 0 for ordinal in range(3)} for variant in VARIANTS
    }
    for block_index, (scheduled_row, record) in enumerate(zip(scheduled, records)):
        if not isinstance(scheduled_row, dict):
            raise AnalysisFailure("schedule row %d is malformed" % block_index)
        order = scheduled_row.get("order")
        if scheduled_row.get("block_index") != block_index or order not in counts:
            raise AnalysisFailure("schedule row %d has the wrong identity" % block_index)
        if (
            record.get("kind") != "raw-deflate-benchmark-block"
            or record.get("mode") != "score"
            or record.get("not_a_score") is not False
            or record.get("block_index") != block_index
            or record.get("order") != order
            or record.get("order_stratum") != order
            or record.get("passes") != PASSES
            or record.get("member_count") != MEMBER_COUNT
            or record.get("decoded_bytes_per_variant") != DECODED_BYTES
            or record.get("expected_output_sha256") != expected_output_sha
        ):
            raise AnalysisFailure("raw block %d does not match its schedule" % block_index)
        if record.get("power_policy_transition") is not None:
            raise AnalysisFailure("raw block %d recorded a power-policy transition" % block_index)
        if type(record.get("worker_pid")) is not int or record["worker_pid"] <= 0:
            raise AnalysisFailure("raw block %d lacks its child-process identity" % block_index)
        command = record.get("process_command")
        if not isinstance(command, list) or "_worker" not in command:
            raise AnalysisFailure("raw block %d lacks a worker process command" % block_index)
        identities = record.get("identities")
        candidate = metadata.get("candidate")
        reference = scoring.get("reference_adapter")
        manifest_binding = scoring.get("manifest")
        if (
            not isinstance(identities, dict)
            or not isinstance(candidate, dict)
            or not isinstance(reference, dict)
            or not isinstance(manifest_binding, dict)
            or identities.get("candidate_sha256") != candidate.get("sha256")
            or identities.get("reference_adapter_sha256") != reference.get("sha256")
            or identities.get("scoring_manifest_sha256") != manifest_binding.get("sha256")
        ):
            raise AnalysisFailure("raw block %d has stale build identities" % block_index)
        alignment = record.get("alignment")
        state_alignment = (
            alignment.get("comparator_state_alignment")
            if isinstance(alignment, dict)
            else None
        )
        if (
            not isinstance(alignment, dict)
            or alignment.get("bytes") != 64
            or alignment.get("all_input_modulo") != [0]
            or alignment.get("output_modulo") != 0
            or alignment.get("same_input_pointer_for_all_variants") is not True
            or alignment.get("same_output_pointer_for_all_variants") is not True
            or alignment.get("same_result_pointer_for_F_and_N") is not True
            or type(alignment.get("comparator_state_size")) is not int
            or alignment["comparator_state_size"] <= 0
            or type(state_alignment) is not int
            or state_alignment <= 0
            or state_alignment & (state_alignment - 1)
            or alignment.get("all_comparator_state_modulo") != [0]
            or alignment.get("fresh_comparator_state_per_call") is not True
        ):
            raise AnalysisFailure("raw block %d has inconsistent pointer alignment" % block_index)
        if record.get("timing_boundary") != {
            "F_and_N": "perf_counter_ns immediately around exactly one Whitefoot decoder call",
            "Z": "perf_counter_ns immediately around exactly one wf_zng_raw_inflate_prepared call",
        }:
            raise AnalysisFailure("raw block %d has the wrong timing boundary" % block_index)
        if record.get("comparator_lifecycle") != {
            "prepare": "wf_zng_raw_prepare outside timing; status checked",
            "decode": "wf_zng_raw_inflate_prepared inside timing; status and output checked",
            "end": "wf_zng_raw_end outside timing; status checked",
            "one_shot_used_for_measurement": False,
        }:
            raise AnalysisFailure("raw block %d has the wrong comparator lifecycle" % block_index)
        if record.get("warmup_policy") != {
            "candidate_decoder_calls_before_samples": 0,
            "comparator_decoder_calls_before_samples": 0,
            "reference_validation_in_worker": "hash/provenance/load-only",
        }:
            raise AnalysisFailure("raw block %d performed an asymmetric warmup" % block_index)
        samples = record.get("samples")
        if not isinstance(samples, list) or len(samples) != 3:
            raise AnalysisFailure("raw block %d lacks exactly three samples" % block_index)
        sample_map: Dict[str, Dict[str, Any]] = {}
        for ordinal, variant in enumerate(order.split(",")):
            sample = validate_sample(
                samples[ordinal], variant, ordinal, expected_output_sha, block_index
            )
            sample_map[variant] = sample
            positions[variant][ordinal] += 1
        if set(sample_map) != set(VARIANTS):
            raise AnalysisFailure("raw block %d does not contain F, N, and Z" % block_index)
        counts[order] += 1
        record["_sample_map"] = sample_map
    if any(count != 5 for count in counts.values()):
        raise AnalysisFailure("order strata are not repeated exactly five times")
    for variant in VARIANTS:
        if any(positions[variant][ordinal] != 10 for ordinal in range(3)):
            raise AnalysisFailure("ordinal positions are not balanced for %s" % variant)
    return metadata, schedule, records


def throughput(sample: Dict[str, Any]) -> float:
    return sample["decoded_bytes"] * 1_000_000_000.0 / sample["elapsed_ns"]


def bootstrap(
    records: Sequence[Dict[str, Any]],
) -> Tuple[List[float], List[float]]:
    groups = {
        stratum: [record for record in records if record["order_stratum"] == stratum]
        for stratum in ORDER_STRATA
    }
    if any(len(group) != 5 for group in groups.values()):
        raise AnalysisFailure("bootstrap order strata do not each have five rows")
    rng = XorShift64Star(BOOTSTRAP_SEED)
    primary: List[float] = []
    attribution: List[float] = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        primary_draw: List[float] = []
        attribution_draw: List[float] = []
        # The same selected row feeds F/Z and F/N, preserving their pairing.
        for stratum in ORDER_STRATA:
            group = groups[stratum]
            for _draw in range(5):
                record = group[rng.next() % 5]
                samples = record["_sample_map"]
                facts_ns = samples["F"]["elapsed_ns"]
                nofacts_ns = samples["N"]["elapsed_ns"]
                zlib_ns = samples["Z"]["elapsed_ns"]
                primary_draw.append(zlib_ns / facts_ns)
                attribution_draw.append(nofacts_ns / facts_ns)
        primary.append(median(primary_draw))
        attribution.append(median(attribution_draw))
    return primary, attribution


def verdict(interval: Sequence[float], winner: str, loser: str) -> str:
    lower, upper = interval
    if lower > 1.02:
        return "meaningful %s win" % winner
    if lower >= 0.98 and upper <= 1.02:
        return "practical parity"
    if upper < 0.98:
        return "meaningful %s win" % loser
    return "inconclusive against the 2% band"


def summarize(campaign: Path) -> Dict[str, Any]:
    metadata, schedule, records = validate_campaign(campaign)
    per_variant: Dict[str, List[float]] = {variant: [] for variant in VARIANTS}
    primary_ratios: List[float] = []
    attribution_ratios: List[float] = []
    retained_samples: List[Dict[str, Any]] = []
    for record in records:
        samples = record["_sample_map"]
        measured = {variant: throughput(samples[variant]) for variant in VARIANTS}
        primary_ratios.append(samples["Z"]["elapsed_ns"] / samples["F"]["elapsed_ns"])
        attribution_ratios.append(samples["N"]["elapsed_ns"] / samples["F"]["elapsed_ns"])
        for variant in VARIANTS:
            per_variant[variant].append(measured[variant])
            retained = dict(samples[variant])
            retained.update(
                {
                    "block_index": record["block_index"],
                    "order_stratum": record["order_stratum"],
                    "throughput_bytes_per_second": measured[variant],
                }
            )
            retained_samples.append(retained)

    boot_primary, boot_attribution = bootstrap(records)
    boot_primary.sort()
    boot_attribution.sort()
    primary_interval = [boot_primary[LOWER_INDEX], boot_primary[UPPER_INDEX]]
    attribution_interval = [
        boot_attribution[LOWER_INDEX],
        boot_attribution[UPPER_INDEX],
    ]
    variant_summary: Dict[str, Any] = {}
    position_summary: Dict[str, Any] = {}
    stratum_summary: Dict[str, Any] = {}
    for variant in VARIANTS:
        values = per_variant[variant]
        variant_summary[variant] = {
            "sample_count": len(values),
            "median_bytes_per_second": median(values),
            "median_mib_per_second": median(values) / (1024.0 * 1024.0),
            "mad_over_median": mad_over_median(values),
        }
        position_summary[variant] = {}
        for ordinal in range(3):
            position_values = [
                throughput(record["_sample_map"][variant])
                for record in records
                if record["_sample_map"][variant]["ordinal"] == ordinal
            ]
            position_summary[variant][str(ordinal)] = {
                "sample_count": len(position_values),
                "median_bytes_per_second": median(position_values),
            }
        stratum_summary[variant] = {}
        for stratum in ORDER_STRATA:
            stratum_values = [
                throughput(record["_sample_map"][variant])
                for record in records
                if record["order_stratum"] == stratum
            ]
            stratum_summary[variant][stratum] = {
                "sample_count": len(stratum_values),
                "median_bytes_per_second": median(stratum_values),
            }

    result = {
        "schema_version": 1,
        "kind": "raw-deflate-score-analysis",
        "campaign": str(campaign.resolve()),
        "protocol_sha256": metadata["protocol_sha256"],
        "frozen_source": metadata["frozen_source"],
        "scoring_manifest": metadata["scoring"]["manifest"],
        "candidate": metadata["candidate"],
        "reference_adapter": metadata["scoring"]["reference_adapter"],
        "raw_sha256": metadata["raw_sha256"],
        "schedule_sha256": metadata["schedule_sha256"],
        "decoded_bytes_per_variant_per_row": DECODED_BYTES,
        "rows": 30,
        "schedule": {
            "strata_order": list(ORDER_STRATA),
            "repetitions_per_stratum": 5,
            "order_seed_hex": "0x%016x" % ORDER_SEED,
        },
        "statistics": {
            "median_definition": "odd: middle; even: arithmetic mean of two middle values",
            "bootstrap": {
                "resamples": BOOTSTRAP_RESAMPLES,
                "seed_hex": "0x%016x" % BOOTSTRAP_SEED,
                "strata_visit_order": list(ORDER_STRATA),
                "within_stratum_source_order": "ascending campaign block_index",
                "draws_per_stratum": 5,
                "draw_rule": "next()%5 with replacement",
                "shared_primary_attribution_indices": True,
                "interval": "empirical nearest-rank 95% percentile",
                "sorted_zero_based_indices": [LOWER_INDEX, UPPER_INDEX],
            },
        },
        "variants": variant_summary,
        "order_position_medians": position_summary,
        "order_stratum_medians": stratum_summary,
        "primary": {
            "ratio": "throughput(F)/throughput(Z)",
            "point_estimate_median": median(primary_ratios),
            "bootstrap_95_percent_interval": primary_interval,
            "practical_band": [0.98, 1.02],
            "verdict": verdict(primary_interval, "Whitefoot", "zlib-ng"),
            "paired_row_ratios": primary_ratios,
        },
        "facts_attribution": {
            "ratio": "throughput(F)/throughput(N)",
            "point_estimate_median": median(attribution_ratios),
            "bootstrap_95_percent_interval": attribution_interval,
            "practical_band": [0.98, 1.02],
            "verdict": verdict(attribution_interval, "facts-on", "facts-off"),
            "paired_row_ratios": attribution_ratios,
            "cannot_change_primary_verdict": True,
        },
        "retained_samples": retained_samples,
        "scope": (
            "This result applies only to this frozen implementation, corpus, "
            "comparator build, machine, and campaign."
        ),
    }
    numeric = (
        primary_ratios
        + attribution_ratios
        + primary_interval
        + attribution_interval
        + [
            value
            for summary in variant_summary.values()
            for value in (
                summary["median_bytes_per_second"],
                summary["median_mib_per_second"],
                summary["mad_over_median"],
            )
        ]
    )
    if any(not math.isfinite(value) for value in numeric):
        raise AnalysisFailure("analysis produced a non-finite statistic")
    return result


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    if Path(sys.executable).resolve() != PYTHON.resolve():
        raise AnalysisFailure("analysis must run under locked Python %s" % PYTHON)
    args = parse_args(argv)
    campaign = args.campaign.resolve()
    result = summarize(campaign)
    output = campaign / "analysis.json"
    atomic_json(output, result)
    print(
        json.dumps(
            {
                "analysis": str(output),
                "facts_over_zlib_ng": result["primary"]["point_estimate_median"],
                "interval": result["primary"]["bootstrap_95_percent_interval"],
                "verdict": result["primary"]["verdict"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AnalysisFailure, OSError, UnicodeError, KeyError, ValueError) as error:
        print("analysis failed: %s" % error, file=sys.stderr)
        raise SystemExit(2)
