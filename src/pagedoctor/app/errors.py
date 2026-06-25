class InvalidReviewForm(Exception):
    # Carries a German, user-facing message for an invalid submission; the route catches
    # it and re-renders an inline error rather than letting it become a 500.
    pass
