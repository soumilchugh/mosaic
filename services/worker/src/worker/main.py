from harness_core import FakeHarnessAdapter, HarnessAdapter


def main(adapter: HarnessAdapter | None = None) -> int:
    adapter = adapter or FakeHarnessAdapter()
    _ = adapter
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
