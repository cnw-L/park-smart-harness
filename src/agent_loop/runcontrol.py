from __future__ import annotations


class RunControl:
    """统一的中断信号源。

    替代散落在 BudgetTracker 上的 interrupted 标志:中断是「运行控制」关注点,
    不是预算关注点。服务端可在任意时刻 request_interrupt()(如用户发新消息、
    连接断开),引擎在每个迭代边界检查 interrupted —— 若置位则不提交在途迭代
    (事务回滚),返回 interrupted 退出原因。
    """

    def __init__(self) -> None:
        self._interrupted = False

    def request_interrupt(self) -> None:
        self._interrupted = True

    @property
    def interrupted(self) -> bool:
        return self._interrupted
