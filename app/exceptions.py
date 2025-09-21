class TelegramParsingError(Exception):
    def __init__(self, error: str):
        super().__init__(f"telegram error: {error}")


class KafkaException(Exception):
    def __init__(self, error: str):
        super().__init__(f"kafka error: {error}")


class ValidationKafkaError(KafkaException):
    def __init__(self, error: str):
        super().__init__(f"kafka message validation  error: {error}")

