class PaperCIError(Exception):
    """Base error for expected, user-facing PaperCI failures."""


class ProjectNotFoundError(PaperCIError):
    """Raised when a project cannot be resolved."""


class ProjectLoadError(PaperCIError):
    """Raised when a project file cannot be parsed."""


class SchemaNotFoundError(PaperCIError):
    """Raised when the installed schema cannot be located."""


class ProposalError(PaperCIError):
    """Raised when story proposals cannot be generated safely."""


class HypothesisError(PaperCIError):
    """Raised when frontier hypotheses cannot be generated safely."""
