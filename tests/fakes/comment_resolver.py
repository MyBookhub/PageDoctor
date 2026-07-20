class FakeCommentResolver:
    def __init__(self) -> None:
        self.resolved: list[tuple[str, str]] = []

    def resolve_comment(self, doc_id: str, comment_id: str) -> None:
        self.resolved.append((doc_id, comment_id))
