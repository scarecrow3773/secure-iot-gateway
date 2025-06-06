import logging

_logger = logging.getLogger(__name__)

class Feedback:
    # TODO: Add more attributes to feedback
    def __init__(self, text):
        self.text = text

class FeedbackSystem:
    # TODO: Finalize the feedback system
    def __init__(self):
        self.feedback_log = []

    def submit_feedback(self, feedback):
        self.feedback_log.append(feedback)
        _logger.warning(f"Feedback: {feedback}")
