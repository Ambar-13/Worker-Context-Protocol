"""
wcp CLI: scaffold and operate Worker Context Protocol (WCP) projects.

Commands:
    wcp init worker <name> --class <C> --domain <D>
    wcp init agent <name> --llm <L>
    wcp init coordinator <name>
    wcp dev
    wcp test --conformance [--level N]
    wcp inspect
    wcp register --coordinator <wss-url>
    wcp doctor

The CLI is vendor-neutral. Templates use abstract operator names
(operator-a, example-coordinator, coordinator-alpha). The 14 domain
templates cover institutional and industrial coordination contexts.
"""

__version__ = "0.95.0"
__schema_version__ = "wcp/0.2"
