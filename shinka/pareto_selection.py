"""Project Pareto selection hooks for pinned native ShinkaEvolve.

Call ``install_native_pareto()`` before constructing the native runner. This
module does not generate/evaluate candidates or run an evolution loop. Native
SQLite rows, generation accounting, executable lineage and MOVE migration are
retained. Hooks are class-level so native thread-local read-only databases use
the same rule. Only configurations explicitly selecting ``pareto`` are changed.

Scientific policy: maximize J1/J2/J3; exact dominance; crowding and distances in
z=(J1,J2,J3/10). Fixed objective ranges are [-1,1] in z. Equal coordinate values
receive equal crowding contributions, including boundary ties. Canonical
duplicates have one earliest valid representative per island. All rank-zero
representatives survive; archive_size/num_islands is a SOFT per-island target.
No scalar score, code complexity, embedding or runtime enters selection.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from functools import wraps
import json
import logging
import math
import random
import re
from typing import Any, Iterable

PROTOCOL = "multiobjective-v1"
YEARS = ("2006", "2007", "2008", "2009")
OBJECTIVES = ("J1", "J2", "J3")
MEAN_TOLERANCE = 1e-12
logger = logging.getLogger("shinka.project.pareto")
_INSTALLED = False


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_metrics(metrics: Any, combined_score: Any) -> str | None:
    """Return an actionable admission error; never manufacture an objective."""
    if not isinstance(metrics, dict) or metrics.get("protocol") != PROTOCOL:
        return "public_metrics.protocol must be multiobjective-v1"
    if metrics.get("valid") is not True:
        return "all four development years must be scientifically valid"
    canonical = metrics.get("canonical_sha256")
    if not isinstance(canonical, str) or re.fullmatch(r"[0-9a-f]{64}", canonical) is None:
        return "canonical_sha256 must be a lowercase SHA256 of the validated specification"
    complexity = metrics.get("complexity")
    if not isinstance(complexity, int) or isinstance(complexity, bool) or complexity < 0:
        return "complexity must be the nonnegative integer count of free structural coefficients"
    years = metrics.get("years")
    if not isinstance(years, dict) or set(years) != set(YEARS):
        return "years must contain exactly 2006, 2007, 2008, 2009"
    for year in YEARS:
        annual = years[year]
        if not isinstance(annual, dict) or annual.get("valid") is not True:
            return f"development year {year} is not valid"
        for key, bound in zip(OBJECTIVES, (1.0, 1.0, 10.0)):
            if not _finite(annual.get(key)) or abs(annual[key]) > bound + MEAN_TOLERANCE:
                return f"year {year} requires a finite, physically bounded {key}"
    for key in OBJECTIVES:
        value = metrics.get(key)
        if not _finite(value):
            return f"public {key} must be finite"
        mean = math.fsum(years[year][key] for year in YEARS) / len(YEARS)
        if abs(value - mean) > MEAN_TOLERANCE:
            return f"public {key} does not equal the four equally weighted annual values"
    auxiliary = 2.0 + (metrics["J1"] + metrics["J2"] + metrics["J3"] / 10.0) / 3.0
    if not _finite(combined_score) or abs(combined_score - auxiliary) > MEAN_TOLERANCE:
        return "combined_score must equal the declared auxiliary 2+(J1+J2+J3/10)/3"
    return None


@dataclass(frozen=True)
class Entry:
    id: str
    canonical: str
    island: int
    generation: int
    timestamp: float
    objectives: tuple[float, float, float]

    @property
    def z(self) -> tuple[float, float, float]:
        return (self.objectives[0], self.objectives[1], self.objectives[2] / 10.0)


def _origin(entry: Entry) -> tuple[int, float, str]:
    return (entry.generation, entry.timestamp, entry.id)


def _enabled(config: Any) -> bool:
    parent = getattr(config, "parent_selection_strategy", None) == "pareto"
    archive = getattr(config, "archive_selection_strategy", None) == "pareto"
    if parent != archive:
        raise ValueError("Pareto requires BOTH parent_selection_strategy and archive_selection_strategy='pareto'")
    if parent:
        islands = getattr(config, "num_islands", 0)
        size = getattr(config, "archive_size", 0)
        if not isinstance(islands, int) or islands < 1 or size < islands or size % islands:
            raise ValueError("archive_size must be a positive multiple of num_islands (equal soft quotas)")
        if not getattr(config, "enforce_island_separation", True):
            raise ValueError("Pareto executable inspirations require enforce_island_separation=true")
        if getattr(config, "enable_dynamic_islands", False):
            raise ValueError("Dynamic island spawning is outside this fixed-island Pareto policy")
        if getattr(config, "island_selection_strategy", None) != "equal":
            raise ValueError("Pareto campaign uses native equal island selection")
    return parent


def read_entries(cursor: Any, config: Any) -> tuple[list[Entry], dict[str, str]]:
    """Read scientific admission from native rows, without touching outcomes."""
    cursor.execute("SELECT id, correct, public_metrics, combined_score, island_idx, generation, timestamp FROM programs")
    entries, excluded = [], {}
    for raw in cursor.fetchall():
        row = dict(raw)
        pid = row["id"]
        if row["correct"] != 1:
            excluded[pid] = "native_correct_false"
            continue
        try:
            metrics = json.loads(row["public_metrics"] or "{}")
        except (TypeError, json.JSONDecodeError):
            excluded[pid] = "malformed_public_metrics"
            continue
        error = validate_metrics(metrics, row["combined_score"])
        if error:
            excluded[pid] = error
            continue
        island = row["island_idx"]
        if not isinstance(island, int) or not 0 <= island < config.num_islands:
            excluded[pid] = "invalid_island"
            continue
        entries.append(Entry(pid, metrics["canonical_sha256"], island,
                             int(row["generation"]), float(row["timestamp"]),
                             tuple(float(metrics[key]) for key in OBJECTIVES)))
    return entries, excluded


def representatives(entries: Iterable[Entry]) -> list[Entry]:
    """Earliest valid canonical model wins representation, never its best score."""
    first: dict[str, Entry] = {}
    for entry in sorted(entries, key=_origin):
        first.setdefault(entry.canonical, entry)
    return list(first.values())


def dominates(a: Entry, b: Entry) -> bool:
    return all(x >= y for x, y in zip(a.objectives, b.objectives)) and any(
        x > y for x, y in zip(a.objectives, b.objectives))


def rank_and_crowding(entries: list[Entry]) -> tuple[dict[str, int], dict[str, float]]:
    """Nondominated sorting; no tolerance or scalarization in dominance."""
    ranks: dict[str, int] = {}
    crowding: dict[str, float] = {}
    dominated: dict[str, list[Entry]] = {entry.id: [] for entry in entries}
    counts = {entry.id: 0 for entry in entries}
    for i, left in enumerate(entries):
        for right in entries[i + 1:]:
            if dominates(left, right):
                dominated[left.id].append(right)
                counts[right.id] += 1
            elif dominates(right, left):
                dominated[right.id].append(left)
                counts[left.id] += 1
    front = [entry for entry in entries if counts[entry.id] == 0]
    rank = 0
    while front:
        for entry in front:
            ranks[entry.id] = rank
            crowding[entry.id] = 0.0
        for axis in range(3):
            groups: dict[float, list[Entry]] = defaultdict(list)
            for entry in front:
                groups[entry.z[axis]].append(entry)
            values = sorted(groups)
            if len(values) < 2:
                continue  # A constant objective confers no artificial boundary reward.
            for index, value in enumerate(values):
                distance = math.inf if index in (0, len(values) - 1) else (
                    values[index + 1] - values[index - 1]) / 2.0
                for entry in groups[value]:
                    crowding[entry.id] += distance
        following = []
        for entry in front:
            for other in dominated[entry.id]:
                counts[other.id] -= 1
                if counts[other.id] == 0:
                    following.append(other)
        front, rank = following, rank + 1
    return ranks, crowding


def retained(entries: list[Entry], soft_target: int) -> tuple[list[Entry], dict[str, int], dict[str, float]]:
    unique = representatives(entries)
    ranks, crowding = rank_and_crowding(unique)
    ordered = sorted(unique, key=lambda entry: (ranks[entry.id], -crowding[entry.id], _origin(entry)))
    front_size = sum(rank == 0 for rank in ranks.values())
    return ordered[:max(front_size, soft_target)], ranks, crowding


def _distance(a: Entry, b: Entry) -> float:
    return math.sqrt(math.fsum((x - y) ** 2 for x, y in zip(a.z, b.z)))


def _choose_max(options: list[Any], key: Any) -> Any:
    best = max(key(option) for option in options)
    return random.choice([option for option in options if key(option) == best])


def diverse_front(entries: list[Entry], anchors: list[Entry], count: int) -> list[Entry]:
    unique = representatives(entries)
    ranks, crowding = rank_and_crowding(unique)
    excluded = {entry.canonical for entry in anchors}
    available = [entry for entry in unique if ranks[entry.id] == 0 and entry.canonical not in excluded]
    selected: list[Entry] = []
    while available and len(selected) < count:
        context = anchors + selected
        choice = _choose_max(available, lambda entry: (
            min((_distance(entry, other) for other in context), default=0.0), crowding[entry.id]))
        selected.append(choice)
        available.remove(choice)
    return selected


def refresh_archive(cursor: Any, conn: Any, config: Any, event: dict | None = None) -> None:
    """Atomically rebuild native archive membership; never delete lineage rows."""
    entries, excluded = read_entries(cursor, config)
    selected: list[Entry] = []
    islands = {}
    for island in range(config.num_islands):
        local = [entry for entry in entries if entry.island == island]
        keep, ranks, crowding = retained(local, config.archive_size // config.num_islands)
        selected.extend(keep)
        representatives_ids = set(ranks)
        islands[str(island)] = {
            "valid_rows": len(local), "canonical_models": len(ranks),
            "canonical_duplicates": [entry.id for entry in local if entry.id not in representatives_ids],
            "rank_zero_count": sum(rank == 0 for rank in ranks.values()),
            "retained": [{"id": entry.id, "canonical_sha256": entry.canonical,
                          "J": list(entry.objectives), "rank": ranks[entry.id],
                          "crowding": crowding[entry.id] if math.isfinite(crowding[entry.id]) else None,
                          "boundary": math.isinf(crowding[entry.id])} for entry in keep],
        }
    global_unique = representatives(entries)
    global_ranks, _ = rank_and_crowding(global_unique)
    snapshot = {"protocol": PROTOCOL, "rule": "rank_then_fixed_range_objective_crowding",
                "soft_archive_size": config.archive_size, "all_rank_zero_preserved": True,
                "global_nondominated_canonical_sha256": [entry.canonical for entry in global_unique if global_ranks[entry.id] == 0],
                "islands": islands, "excluded": excluded, "event": event}
    with conn:
        cursor.execute("DELETE FROM archive")
        cursor.executemany("INSERT INTO archive (program_id) VALUES (?)", [(entry.id,) for entry in selected])
        cursor.execute("INSERT OR REPLACE INTO metadata_store (key, value) VALUES (?, ?)",
                       ("project_pareto_selection", json.dumps(snapshot, sort_keys=True, allow_nan=False)))
    logger.info("PARETO_ARCHIVE %s", json.dumps({"retained": len(selected), "excluded": len(excluded),
                                              "event": event}, sort_keys=True))


def _sample_parent(selector: Any, island_idx: int | None) -> Any:
    entries, _ = read_entries(selector.cursor, selector.config)
    local = [entry for entry in entries if island_idx is None or entry.island == island_idx]
    pool, ranks, crowding = retained(local, selector.config.archive_size // selector.config.num_islands)
    if not pool:
        raise ValueError(f"No valid {PROTOCOL} parent on island {island_idx}; restore a valid four-year seed")
    contestants = random.sample(pool, min(2, len(pool)))
    winner = _choose_max(contestants, lambda entry: (-ranks[entry.id], crowding[entry.id]))
    logger.info("PARETO_PARENT %s", json.dumps({"island": island_idx, "id": winner.id,
                "canonical_sha256": winner.canonical, "rank": ranks[winner.id],
                "J": list(winner.objectives), "tournament": [entry.id for entry in contestants]}))
    parent = selector.get_program(winner.id)
    if parent is None:
        raise RuntimeError("Selected Pareto parent disappeared from native SQLite")
    return parent


def _sample_context(selector: Any, parent: Any, num_archive: int, num_topk: int) -> tuple[list[Any], list[Any]]:
    context = selector.archive_selector
    entries, _ = read_entries(context.cursor, context.config)
    local = [entry for entry in entries if entry.island == parent.island_idx]
    matching = [entry for entry in local if entry.id == parent.id]
    if not matching:
        raise ValueError("Cannot build scientific inspirations for an invalid parent")
    selected = diverse_front(local, matching, max(0, num_archive) + max(0, num_topk))
    programs = [context.get_program(entry.id) for entry in selected]
    if any(program is None for program in programs):
        raise RuntimeError("Selected Pareto inspiration disappeared from native SQLite")
    logger.info("PARETO_INSPIRATIONS %s", json.dumps({"parent": parent.id,
                "ids": [entry.id for entry in selected], "canonical_sha256": [entry.canonical for entry in selected]}))
    return programs[:num_archive], programs[num_archive:]


def _perform_migration(strategy: Any, current_generation: int) -> bool:
    config = strategy.config
    rate = config.migration_rate
    if config.num_islands < 2 or rate <= 0:
        return False
    entries, _ = read_entries(strategy.cursor, config)
    # Plan on canonical populations; native rows still retain every duplicate.
    populations = {island: representatives(entry for entry in entries if entry.island == island)
                   for island in range(config.num_islands)}
    migrated_canonical: set[str] = set()
    moves: list[dict] = []
    source_order = list(range(config.num_islands))
    random.shuffle(source_order)
    for source in source_order:
        local = populations[source]
        ranks, crowding = rank_and_crowding(local)
        front = [entry for entry in local if ranks[entry.id] == 0]
        if len(front) < 2:
            continue  # Keep at least one original source-front anchor.
        seed_anchors = [entry for entry in front if entry.generation == 0]
        anchor = min(seed_anchors, key=_origin) if seed_anchors else _choose_max(front, lambda entry: crowding[entry.id])
        available = [entry for entry in front if entry.id != anchor.id and entry.generation > 0
                     and entry.canonical not in migrated_canonical]
        quota = min(len(available), max(1, math.floor(len(local) * rate)))
        for _ in range(quota):
            options = []
            for entry in available:
                for destination, others in populations.items():
                    if destination == source or any(other.canonical == entry.canonical for other in others):
                        continue
                    # Move a source-front trade-off only if it survives at its destination.
                    if any(dominates(other, entry) for other in others):
                        continue
                    gap = min((_distance(entry, other) for other in others), default=math.sqrt(12.0))
                    if gap == 0:
                        continue  # No new objective-space trade-off at this destination.
                    options.append((entry, destination, gap))
            if not options:
                break
            entry, destination, gap = _choose_max(options, lambda option: (option[2], crowding[option[0].id]))
            strategy._migrate_program(entry.id, source, destination, current_generation)
            populations[source].remove(entry)
            moved = Entry(entry.id, entry.canonical, destination, entry.generation, entry.timestamp, entry.objectives)
            populations[destination].append(moved)
            migrated_canonical.add(entry.canonical)
            available.remove(entry)
            moves.append({"id": entry.id, "canonical_sha256": entry.canonical, "from": source,
                          "to": destination, "J": list(entry.objectives), "objective_gap": gap,
                          "source_anchor_id": anchor.id})
    refresh_archive(strategy.cursor, strategy.conn, config,
                    {"kind": "pareto_move_migration", "generation": current_generation, "moves": moves})
    logger.info("PARETO_MIGRATION %s", json.dumps({"generation": current_generation, "moves": moves}, sort_keys=True))
    return bool(moves)


def install_native_pareto() -> None:
    """Install once per process; the launcher must also set inspiration_sort_order='none'."""
    global _INSTALLED
    if _INSTALLED:
        return
    from shinka.database.dbase import ProgramDatabase
    from shinka.database.parents import CombinedParentSelector
    from shinka.database.inspirations import CombinedContextSelector
    from shinka.database.islands import ElitistMigrationStrategy
    from shinka.database.island_sampler import IslandSampler
    from shinka.core.async_runner import ShinkaEvolveRunner

    original_ready = ShinkaEvolveRunner._verify_database_ready
    @wraps(original_ready)
    async def require_scientific_seed(runner):
        await original_ready(runner)
        if _enabled(runner.db_config):
            if runner.evo_config.inspiration_sort_order != "none":
                raise ValueError("Pareto inspirations require inspiration_sort_order='none'")
            entries, _ = read_entries(runner.db.cursor, runner.db_config)
            if {entry.island for entry in entries} != set(range(runner.db_config.num_islands)):
                raise ValueError("Native evolution needs a valid four-year multiobjective seed on every island")
    ShinkaEvolveRunner._verify_database_ready = require_scientific_seed

    original_counts = IslandSampler._get_island_program_counts
    @wraps(original_counts)
    def canonical_island_counts(sampler, island_indices):
        if _enabled(sampler.config):
            entries, _ = read_entries(sampler.cursor, sampler.config)
            return {island: len(representatives(entry for entry in entries if entry.island == island))
                    for island in island_indices}
        return original_counts(sampler, island_indices)
    IslandSampler._get_island_program_counts = canonical_island_counts

    original_add = ProgramDatabase.add
    @wraps(original_add)
    def add(database, program, *args, **kwargs):
        if _enabled(database.config) and not program.correct:
            # Upstream's missing-result fallback uses numeric zero. Scientific
            # failures have no objective vector or auxiliary predictive score.
            program.combined_score = None
            program.public_metrics = {**(program.public_metrics or {}),
                                      "protocol": PROTOCOL, "valid": False,
                                      "J1": None, "J2": None, "J3": None}
        if _enabled(database.config) and program.correct:
            error = validate_metrics(program.public_metrics, program.combined_score)
            if error:
                # Preserve native lineage and reported diagnostics, but exclude malformed
                # success reports from all scientific/auxiliary successful-program paths.
                program.metadata = dict(program.metadata or {})
                program.metadata["pareto_admission_error"] = error
                program.metadata["reported_combined_score"] = program.combined_score
                program.metadata["reported_correct"] = program.correct
                program.correct = False
                program.combined_score = None
                program.text_feedback = f"Invalid multiobjective evaluation: {error}.\n" + (program.text_feedback or "")
        return original_add(database, program, *args, **kwargs)
    ProgramDatabase.add = add

    original_archive = ProgramDatabase._update_archive
    @wraps(original_archive)
    def update_archive(database, program):
        if _enabled(database.config):
            return refresh_archive(database.cursor, database.conn, database.config,
                                   {"kind": "program_maintenance", "program_id": program.id})
        return original_archive(database, program)
    ProgramDatabase._update_archive = update_archive

    original_maintenance = ProgramDatabase.run_post_add_maintenance_batch
    @wraps(original_maintenance)
    def maintenance(database, *args, **kwargs):
        result = original_maintenance(database, *args, **kwargs)
        if _enabled(database.config):
            # Native generation-zero island copies insert archive rows directly.
            refresh_archive(database.cursor, database.conn, database.config, {"kind": "post_maintenance"})
        return result
    ProgramDatabase.run_post_add_maintenance_batch = maintenance

    original_parent = CombinedParentSelector.sample_parent
    @wraps(original_parent)
    def sample_parent(selector, island_idx=None):
        if _enabled(selector.config):
            return _sample_parent(selector, island_idx)
        return original_parent(selector, island_idx)
    CombinedParentSelector.sample_parent = sample_parent

    original_has_correct = CombinedParentSelector.has_correct_programs
    @wraps(original_has_correct)
    def has_correct(selector, island_idx=None):
        if _enabled(selector.config):
            entries, _ = read_entries(selector.cursor, selector.config)
            return any(island_idx is None or entry.island == island_idx for entry in entries)
        return original_has_correct(selector, island_idx)
    CombinedParentSelector.has_correct_programs = has_correct

    original_fix_parent = CombinedParentSelector.sample_parent_with_fix_mode
    @wraps(original_fix_parent)
    def sample_fix_parent(selector, island_idx=None):
        if _enabled(selector.config):
            return _sample_parent(selector, island_idx), False
        return original_fix_parent(selector, island_idx)
    CombinedParentSelector.sample_parent_with_fix_mode = sample_fix_parent

    # Native pre-initialization fallbacks bypass CombinedParentSelector. Refuse
    # those branches unless every island contains an admitted scientific seed.
    def guard_sampling(original):
        @wraps(original)
        def sample(database, *args, **kwargs):
            if _enabled(database.config):
                entries, _ = read_entries(database.cursor, database.config)
                if {entry.island for entry in entries} != set(range(database.config.num_islands)):
                    raise ValueError("Every native island needs a valid multiobjective-v1 seed before Pareto sampling")
            return original(database, *args, **kwargs)
        return sample
    ProgramDatabase.sample = guard_sampling(ProgramDatabase.sample)
    ProgramDatabase.sample_with_fix_mode = guard_sampling(ProgramDatabase.sample_with_fix_mode)

    original_context = CombinedContextSelector.sample_context
    @wraps(original_context)
    def sample_context(selector, parent, num_archive, num_topk):
        if _enabled(selector.archive_selector.config):
            return _sample_context(selector, parent, num_archive, num_topk)
        return original_context(selector, parent, num_archive, num_topk)
    CombinedContextSelector.sample_context = sample_context

    original_migration = ElitistMigrationStrategy.perform_migration
    @wraps(original_migration)
    def migrate(strategy, current_generation):
        if _enabled(strategy.config):
            return _perform_migration(strategy, current_generation)
        return original_migration(strategy, current_generation)
    ElitistMigrationStrategy.perform_migration = migrate
    _INSTALLED = True
