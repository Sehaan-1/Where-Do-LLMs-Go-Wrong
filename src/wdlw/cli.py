"""Command-line entry point for preparation, annotation exchange, and analysis."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from .agreement import build_agreement_report
from .analysis import build_analysis_report
from .io import (
    DataFormatError,
    read_json,
    read_jsonl,
    refuse_existing,
    serialize_json,
    serialize_jsonl,
    write_text_atomic,
)
from .label_studio import build_label_studio_tasks, normalize_label_studio_export
from .models import (
    SOURCE_REPOSITORY,
    SOURCE_REVISION,
    AnnotationRecord,
    ResponseRecord,
)
from .observability import emit_event, new_run_id
from .prepare import prepare_dataset
from .validation import index_response_batch, validate_annotation_file


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wdlw",
        description="Prepare and analyze step-level reasoning annotations.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="emit structured JSON run events to stderr",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    prepare = commands.add_parser("prepare", help="build a deterministic GSM8K response batch")
    prepare.add_argument("--test-jsonl", type=Path, required=True)
    prepare.add_argument("--solutions-jsonl", type=Path, required=True)
    prepare.add_argument("--output", type=Path, default=Path("data/annotation_batch.jsonl"))
    prepare.add_argument("--manifest", type=Path, default=Path("data/manifest.json"))
    prepare.add_argument("--sample-size", type=int, default=150)
    prepare.add_argument("--seed", type=int, default=2026)
    prepare.add_argument("--source-revision", default=SOURCE_REVISION)
    prepare.add_argument("--source-repository", default=SOURCE_REPOSITORY)
    prepare.add_argument("--force", action="store_true", help="replace existing output files")

    validate = commands.add_parser("validate", help="validate a response batch")
    validate.add_argument("--batch", type=Path, required=True)

    export = commands.add_parser("export-label-studio", help="export blinded step tasks as JSON")
    export.add_argument("--batch", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    export.add_argument(
        "--sample-problems",
        type=int,
        help="optionally sample whole paired problem groups (useful for double annotation)",
    )
    export.add_argument("--seed", type=int, default=2026)
    export.add_argument("--force", action="store_true", help="replace an existing task file")

    import_export = commands.add_parser(
        "import-label-studio", help="normalize one annotator's Label Studio JSON export"
    )
    import_export.add_argument("--batch", type=Path, required=True)
    import_export.add_argument("--input", type=Path, required=True)
    import_export.add_argument("--annotator-id", required=True)
    import_export.add_argument("--guideline-version", default="1.0")
    import_export.add_argument(
        "--label-studio-user-id",
        type=int,
        help="filter a shared export by annotations.completed_by",
    )
    import_export.add_argument("--output", type=Path, required=True)
    import_export.add_argument(
        "--force", action="store_true", help="replace an existing label file"
    )

    agreement = commands.add_parser("agreement", help="compare two annotation files")
    agreement.add_argument("--batch", type=Path, required=True)
    agreement.add_argument("--annotator-a", type=Path, required=True)
    agreement.add_argument("--annotator-b", type=Path, required=True)
    agreement.add_argument("--output", type=Path)
    agreement.add_argument("--force", action="store_true", help="replace an existing report")

    analyze = commands.add_parser("analyze", help="summarize one annotator's labels")
    analyze.add_argument("--batch", type=Path, required=True)
    analyze.add_argument("--annotations", type=Path, required=True)
    analyze.add_argument("--output", type=Path)
    analyze.add_argument("--force", action="store_true", help="replace an existing report")
    return parser


def _load_batch(path: Path) -> list[ResponseRecord]:
    records = read_jsonl(path, ResponseRecord)
    index_response_batch(records)
    return records


def _load_annotations(path: Path, batch: Sequence[ResponseRecord]) -> list[AnnotationRecord]:
    annotations = read_jsonl(path, AnnotationRecord)
    validate_annotation_file(annotations, index_response_batch(batch))
    return annotations


def _ensure_output_distinct(output: Path, protected_paths: Sequence[Path]) -> None:
    resolved_output = output.resolve()
    conflicts = [path for path in protected_paths if resolved_output == path.resolve()]
    if conflicts:
        joined = ", ".join(str(path) for path in conflicts)
        raise DataFormatError(f"output path {output} must not overwrite input file(s): {joined}")


def _write_report(
    report: dict[str, object],
    output: Path | None,
    force: bool,
    protected_paths: Sequence[Path] = (),
) -> None:
    if output is None:
        sys.stdout.write(serialize_json(report))
        return
    _ensure_output_distinct(output, protected_paths)
    refuse_existing([output], force)
    write_text_atomic(output, serialize_json(report))
    print(f"Wrote report to {output}")


def _emit(args: argparse.Namespace, event: str, details: dict[str, object] | None = None) -> None:
    if getattr(args, "verbose", False):
        emit_event(args._run_id, args.command, event, details)


def _run(args: argparse.Namespace) -> int:
    if args.command == "prepare":
        output: Path = args.output
        manifest_path: Path = args.manifest
        if output.resolve() == manifest_path.resolve():
            raise DataFormatError("batch output and manifest must use different paths")
        source_paths = [args.test_jsonl, args.solutions_jsonl]
        _ensure_output_distinct(output, [*source_paths, manifest_path])
        _ensure_output_distinct(manifest_path, [*source_paths, output])
        refuse_existing([output, manifest_path], args.force)
        records, manifest = prepare_dataset(
            args.test_jsonl,
            args.solutions_jsonl,
            sample_size=args.sample_size,
            seed=args.seed,
            source_revision=args.source_revision,
            source_repository=args.source_repository,
        )
        write_text_atomic(output, serialize_jsonl(records))
        write_text_atomic(manifest_path, serialize_json(manifest))
        _emit(
            args,
            "prepare.outputs_written",
            {
                "problems": manifest.counts.problems,
                "responses": manifest.counts.responses,
                "steps": manifest.counts.steps,
                "model_final_answers_missing": manifest.counts.model_final_answers_missing,
            },
        )
        print(
            f"Prepared {manifest.counts.responses} responses across "
            f"{manifest.counts.problems} problems and {manifest.counts.steps} steps."
        )
        print(f"Batch: {output}\nManifest: {manifest_path}")
        return 0

    if args.command == "validate":
        records = _load_batch(args.batch)
        result = {
            "valid": True,
            "responses": len(records),
            "problems": len({record.problem_id for record in records}),
            "steps": sum(len(record.steps) for record in records),
            "model_final_answers_missing": sum(
                record.model_final_answer is None for record in records
            ),
            "models": sorted({record.model_id for record in records}),
        }
        sys.stdout.write(serialize_json(result))
        _emit(
            args,
            "batch.validated",
            {"responses": len(records), "problems": result["problems"], "steps": result["steps"]},
        )
        return 0

    if args.command == "export-label-studio":
        records = _load_batch(args.batch)
        _ensure_output_distinct(args.output, [args.batch])
        tasks = build_label_studio_tasks(
            records,
            sample_problems=args.sample_problems,
            seed=args.seed,
        )
        refuse_existing([args.output], args.force)
        write_text_atomic(args.output, serialize_json(tasks))
        _emit(
            args,
            "label_studio.tasks_written",
            {"responses": len({task.data.response_id for task in tasks}), "step_tasks": len(tasks)},
        )
        print(f"Wrote {len(tasks)} step tasks to {args.output}")
        return 0

    if args.command == "import-label-studio":
        records = _load_batch(args.batch)
        _ensure_output_distinct(args.output, [args.batch, args.input])
        export_value = read_json(args.input)
        annotations = normalize_label_studio_export(
            export_value,
            records,
            annotator_id=args.annotator_id,
            guideline_version=args.guideline_version,
            label_studio_user_id=args.label_studio_user_id,
        )
        refuse_existing([args.output], args.force)
        write_text_atomic(args.output, serialize_jsonl(annotations))
        _emit(
            args,
            "annotations.imported",
            {
                "responses": len(annotations),
                "steps": sum(len(annotation.step_annotations) for annotation in annotations),
            },
        )
        print(f"Wrote {len(annotations)} response annotations to {args.output}")
        return 0

    if args.command == "agreement":
        records = _load_batch(args.batch)
        annotator_a = _load_annotations(args.annotator_a, records)
        annotator_b = _load_annotations(args.annotator_b, records)
        report = build_agreement_report(records, annotator_a, annotator_b)
        _emit(args, "agreement.report_ready", {"report_generated": True})
        _write_report(
            report,
            args.output,
            args.force,
            [args.batch, args.annotator_a, args.annotator_b],
        )
        return 0

    if args.command == "analyze":
        records = _load_batch(args.batch)
        annotations = _load_annotations(args.annotations, records)
        report = build_analysis_report(records, annotations)
        _emit(args, "analysis.report_ready", {"report_generated": True})
        _write_report(report, args.output, args.force, [args.batch, args.annotations])
        return 0

    raise DataFormatError(f"unsupported command: {args.command}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    run_id = new_run_id()
    args._run_id = run_id
    command = str(args.command)
    if args.verbose:
        emit_event(run_id, command, "command.started")
    try:
        exit_code = _run(args)
    except (DataFormatError, OSError, ValueError) as error:
        if args.verbose:
            emit_event(
                run_id,
                command,
                "command.failed",
                {"error_type": type(error).__name__, "message": str(error)},
            )
        print(f"wdlw: error: {error}", file=sys.stderr)
        return 2
    if args.verbose:
        emit_event(run_id, command, "command.completed", {"exit_code": exit_code})
    return exit_code
