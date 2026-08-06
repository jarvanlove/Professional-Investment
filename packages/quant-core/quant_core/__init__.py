"""纯算法库：方案 PDF 规则的代码化。禁止 import Web/DB/网络框架。"""
from .engine import (  # noqa: F401
    AccountState, FundDecision, SignalReport, build_decisions, build_signal_report,
    compute_metrics,
)
