from __future__ import annotations

import zipfile
from pathlib import Path

from letterforge.models import ALL_CHARS, Character, ExtractionResult


def assemble_zip(
    output_files: dict[str, bytes],
    output_zip: Path,
) -> tuple[Path, list[ExtractionResult]]:
    expected = {c.filename: c for c in ALL_CHARS}
    found = set(output_files.keys())
    missing_names = set(expected.keys()) - found
    unexpected_names = found - set(expected.keys())

    results: list[ExtractionResult] = []

    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for filename, data in output_files.items():
            zf.writestr(filename, data)
            char = expected.get(filename)
            if char:
                results.append(
                    ExtractionResult(
                        character=char,
                        png_path=output_zip.parent / filename,
                        success=True,
                    )
                )

        for name in missing_names:
            char = expected[name]
            results.append(
                ExtractionResult(
                    character=char,
                    png_path=output_zip.parent / name,
                    success=False,
                    error="not produced by extraction code",
                )
            )

        manifest_lines = [
            "letterforge output manifest",
            f"total files: {len(output_files)}",
            f"expected: {len(expected)}",
            f"missing ({len(missing_names)}): {', '.join(sorted(missing_names)) or 'none'}",
            f"unexpected ({len(unexpected_names)}): "
            f"{', '.join(sorted(unexpected_names)) or 'none'}",
        ]
        zf.writestr("manifest.txt", "\n".join(manifest_lines))

    return output_zip, results
