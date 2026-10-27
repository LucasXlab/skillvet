# README demonstration

The image is a rendered excerpt of actual installed CLI stdout on bundled synthetic input. It is not an illustration of invented output. Only line wrapping and presentation styling are applied; the adjacent [text excerpt](../assets/readme-demo.txt) preserves the selected output. The excerpt may not be a complete JSON document.

Reproduce from the source checkout after the README installation steps:

```sh
.venv/bin/skillvet examples/malicious-skill --strict --json
```

The selected violation fixture intentionally exits 1. Installation may need public dependencies; the captured run used existing public-package caches with runtime networking disabled. These are functional demonstrations, not accuracy, performance, profitability, or security benchmarks.
