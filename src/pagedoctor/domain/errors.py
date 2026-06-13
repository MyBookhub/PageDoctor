class PageDoctorError(Exception):
    pass


class ConfigError(PageDoctorError):
    pass


class ManuscriptTooLargeError(PageDoctorError):
    pass


class SpanNotLocatableError(PageDoctorError):
    pass


class DocumentAccessDeniedError(PageDoctorError):
    pass


class RunNotFoundError(PageDoctorError):
    pass


class CommentPostingError(PageDoctorError):
    pass


class LlmResponseInvalidError(PageDoctorError):
    pass


class TokenBudgetExceededError(PageDoctorError):
    pass
