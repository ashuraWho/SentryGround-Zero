# Contributing

Thanks for helping improve Sentry-Sat. Small, focused changes are easier to review than large refactors mixed with new features.

## Workflow

1. Fork or branch from `main` (or `master`).
2. Run **C++ checks** locally:

   ```bash
   sudo apt-get install build-essential cmake libssl-dev   # Linux example
   cmake -S core_engine -B core_engine/build
   cmake --build core_engine/build --parallel
   ctest --test-dir core_engine/build --output-on-failure   # JSON self-test + simulator + telemetry JSON parser
   ```

3. Run **Python** training/export only when your change touches `ai_training/` (requires your own TensorFlow-capable environment).
4. Open a pull request describing **what** changed and **why** in full sentences.

## Style

- Match existing comment density and language (**English** in source).
- Prefer extending `config.default.json` and documenting keys in `README.md` over magic numbers in code.
- Do not commit large binary artifacts (`*.h5`, `*.tflite`, private datasets); use `.gitignore` defaults.

## Licensing

By contributing, you agree your contributions are licensed under the same terms as the repository (**MIT**; see `LICENSE`).
