"""
WCP v1.0-rc1 conformance suite runner.

Speaks JSON-RPC over WebSocket to a target implementation; runs the test
bundles defined in `conformance/test-suite/levelN.json`; produces a
structured report.

Target-agnostic: the runner does not assume any specific implementation. It
runs equally against the reference coordinator at wcp_coordinator/ and
against any third-party WCP-conformant implementation.
"""

__version__ = "1.0.0rc1"
__schema_version__ = "wcp/1.0-rc1"
