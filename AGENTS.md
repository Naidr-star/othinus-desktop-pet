# Development Guidelines

## Read first

Before changing the project, read only the minimum relevant context:

1. `docs/DESIGN_RULES.md`
2. `docs/ARCHITECTURE.md`
3. `CHANGELOG.md`
4. The source, script, or asset directly involved in the task

Do not recursively scan build output, release packages, caches, executables, reference collections, or every animation frame.

## Asset rules

- The selected master model is `assets_v2/othinus_master_v2_transparent.png`.
- Do not regenerate the discarded candidate models or repeat completed color, proportion, outline, and sprite-sheet normalization without a new art requirement.
- Do not restore deprecated portrait icons, first-generation action sprites, or separate minigame windows.
- Character and motion changes must follow `docs/DESIGN_RULES.md`.
- Preserve user files and unidentified art intermediates.

## Code and verification

- Check the current version, relevant file state, and running process before changing behavior.
- Movement, scaling, edge interaction, and transparency changes must run the corresponding `verify_v25.py` regressions.
- Code changes require at least syntax validation and focused regression tests.
- Release changes must update `APP_VERSION`, `pyproject.toml`, `version_info.txt`, `README.txt`, `CHANGELOG.md`, and `RELEASE_NOTES.md` together.

## Build safety

- Do not build or replace the desktop EXE unless explicitly requested.
- Confirm that the running desktop pet has exited before packaging.
- Build into a new versioned output directory and verify it before replacing an existing EXE.
- Do not overwrite files whose purpose is unclear.
- A release package must include the EXE and the user-facing `README.txt`.
