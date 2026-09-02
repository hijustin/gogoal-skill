"""GoGoal 安全错误类型。"""


class GoGoalError(Exception):
    """可安全显示给用户的业务错误。"""


class ValidationFailure(GoGoalError):
    """一致性校验失败。"""
