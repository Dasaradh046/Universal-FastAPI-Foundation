# Integrations Guide

Universal FastAPI Foundation uses the **Adapter pattern** for all third-party integrations. Business code depends on stable interfaces (contracts), while concrete adapters implement provider-specific logic.

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Business Services                          │
│  (EmailService, StorageService, AIService, NotificationService) │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Integration Contracts                       │
│  (EmailSender, ObjectStorage, TextGenerator, NotificationSender) │
└────────────────────────────────┬────────────────────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
       ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
       │  Adapter A  │    │  Adapter B  │    │  Adapter C  │
       │  (Provider) │    │  (Provider) │    │  (Provider) │
       └─────────────┘    └─────────────┘    └─────────────┘
```

## Email Integration

### Contract (`app/integrations/email/contracts.py`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class EmailMessage:
    to: list[str]
    subject: str
    text_body: str | None = None
    html_body: str | None = None
    from_email: str | None = None
    from_name: str | None = None
    reply_to: str | None = None
    headers: dict[str, str] | None = None
    attachments: list["EmailAttachment"] | None = None


@dataclass
class EmailAttachment:
    filename: str
    content: bytes
    mimetype: str


@dataclass
class EmailResult:
    success: bool
    message_id: str | None = None
    error: str | None = None
    provider: str | None = None


class EmailSender(ABC):
    @abstractmethod
    async def send(self, message: EmailMessage) -> EmailResult:
        """Send an email message."""
        pass

    @abstractmethod
    async def send_batch(self, messages: list[EmailMessage]) -> list[EmailResult]:
        """Send multiple emails efficiently."""
        pass
```

### Factory (`app/integrations/email/factory.py`)

```python
from app.core.config import settings
from app.integrations.email.contracts import EmailSender
from app.integrations.email.providers.smtp import SMTPProvider
from app.integrations.email.providers.brevo import BrevoProvider
from app.integrations.email.providers.sendgrid import SendGridProvider
from app.integrations.email.providers.ses import SESProvider
from app.integrations.email.providers.log import LogProvider


def create_email_sender() -> EmailSender:
    provider = settings.EMAIL_PROVIDER.lower()

    if provider == "smtp":
        return SMTPProvider(
            host=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            use_tls=settings.SMTP_TLS,
            use_ssl=settings.SMTP_SSL,
        )
    elif provider == "brevo":
        return BrevoProvider(api_key=settings.BREVO_API_KEY)
    elif provider == "sendgrid":
        return SendGridProvider(api_key=settings.SENDGRID_API_KEY)
    elif provider == "ses":
        return SESProvider(
            region=settings.AWS_REGION,
            access_key=settings.AWS_ACCESS_KEY_ID,
            secret_key=settings.AWS_SECRET_ACCESS_KEY,
        )
    elif provider == "log":
        return LogProvider()
    else:
        raise ValueError(f"Unknown email provider: {provider}")
```

### Service (`app/integrations/email/service.py`)

```python
from app.integrations.email.contracts import EmailSender, EmailMessage, EmailResult
from app.integrations.email.factory import create_email_sender


class EmailService:
    def __init__(self, sender: EmailSender | None = None):
        self._sender = sender or create_email_sender()

    async def send(
        self,
        to: str | list[str],
        subject: str,
        text_body: str | None = None,
        html_body: str | None = None,
        **kwargs,
    ) -> EmailResult:
        message = EmailMessage(
            to=[to] if isinstance(to, str) else to,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            **kwargs,
        )
        return await self._sender.send(message)

    async def send_template(
        self,
        to: str | list[str],
        template: str,
        context: dict,
        subject: str,
        **kwargs,
    ) -> EmailResult:
        # Render template (Jinja2)
        from app.integrations.email.service import render_template
        text_body = render_template(f"{template}.txt", context)
        html_body = render_template(f"{template}.html", context)
        return await self.send(to, subject, text_body, html_body, **kwargs)
```

### Usage in Business Code

```python
from app.integrations.email.service import EmailService

class WelcomeService:
    def __init__(self, email_service: EmailService):
        self.email_service = email_service

    async def send_welcome(self, email: str, name: str):
        await self.email_service.send_template(
            to=email,
            template="welcome",
            context={"name": name},
            subject="Welcome to Our Platform!",
        )
```

### Configuration

```env
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASSWORD=secret
SMTP_TLS=true
NOTIFICATIONS_FROM_EMAIL=noreply@example.com
NOTIFICATIONS_FROM_NAME="My App"
```

## Storage Integration

### Contract (`app/integrations/storage/contracts.py`)

```python
from abc import ABC, abstractmethod
from typing import BinaryIO, Optional
from dataclasses import dataclass


@dataclass
class ObjectMetadata:
    key: str
    size: int
    content_type: str
    etag: str
    last_modified: datetime
    metadata: dict[str, str]


class ObjectStorage(ABC):
    @abstractmethod
    async def put_object(
        self,
        key: str,
        data: BinaryIO | bytes,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> ObjectMetadata:
        pass

    @abstractmethod
    async def get_object(self, key: str) -> tuple[BinaryIO, ObjectMetadata]:
        pass

    @abstractmethod
    async def delete_object(self, key: str) -> bool:
        pass

    @abstractmethod
    async def object_exists(self, key: str) -> bool:
        pass

    @abstractmethod
    async def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        method: str = "GET",
    ) -> str:
        pass

    @abstractmethod
    async def list_objects(
        self,
        prefix: str = "",
        max_keys: int = 1000,
    ) -> list[ObjectMetadata]:
        pass
```

### Adapters

- **Local** (`local.py`) - Filesystem storage for development
- **MinIO** (`minio.py`) - S3-compatible self-hosted
- **S3** (`s3.py`) - AWS S3
- **GCS** (`gcs.py`) - Google Cloud Storage
- **Azure** (`azure.py`) - Azure Blob Storage

### Configuration

```env
STORAGE_PROVIDER=minio
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
MINIO_BUCKET=my-bucket
```

## AI/LLM Integration

### Contract (`app/integrations/ai/contracts.py`)

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional
from dataclasses import dataclass


@dataclass
class ChatMessage:
    role: str  # system, user, assistant
    content: str


@dataclass
class ChatCompletionRequest:
    messages: list[ChatMessage]
    model: str
    temperature: float = 0.7
    max_tokens: int | None = None
    stream: bool = False
    tools: list[dict] | None = None


@dataclass
class ChatCompletionResponse:
    content: str
    model: str
    usage: dict | None = None
    finish_reason: str | None = None


@dataclass
class EmbeddingRequest:
    texts: list[str]
    model: str


@dataclass
class EmbeddingResponse:
    embeddings: list[list[float]]
    model: str
    usage: dict | None = None


class TextGenerator(ABC):
    @abstractmethod
    async def chat_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        pass

    @abstractmethod
    async def chat_completion_stream(
        self, request: ChatCompletionRequest
    ) -> AsyncIterator[str]:
        pass

    @abstractmethod
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        pass
```

### Provider Adapters

- **OpenAI** (`openai.py`)
- **Anthropic** (`anthropic.py`)
- **Google** (`google.py`)
- **Groq** (`groq.py`)
- **Mistral** (`mistral.py`)
- **LiteLLM** (`litellm.py`) - Unified gateway

### Configuration

```env
AI_PROVIDER=groq
GROQ_API_KEY=gsk_xxx
AI_MODEL=llama-3.1-70b-versatile
```

## SMS/OTP Integration

### Contract (`app/integrations/sms/contracts.py`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SMSMessage:
    to: str
    body: str
    from_number: str | None = None


@dataclass
class SMSResult:
    success: bool
    message_id: str | None = None
    error: str | None = None


class SMSSender(ABC):
    @abstractmethod
    async def send(self, message: SMSMessage) -> SMSResult:
        pass


class OTPProvider(ABC):
    @abstractmethod
    async def generate_otp(self, identifier: str, length: int = 6) -> str:
        pass

    @abstractmethod
    async def verify_otp(self, identifier: str, code: str) -> bool:
        pass

    @abstractmethod
    async def send_otp(self, phone: str, code: str) -> SMSResult:
        pass
```

### Adapters

- **Twilio** (`twilio.py`)
- **AWS SNS** (`sns.py`)
- **Vonage** (`vonage.py`)

## Notification Orchestration

### Service (`app/shared/notifications/service.py`)

```python
from app.integrations.email.contracts import EmailSender
from app.integrations.sms.contracts import SMSSender
from app.integrations.push.contracts import PushSender


class NotificationService:
    def __init__(
        self,
        email_sender: EmailSender,
        sms_sender: SMSSender | None = None,
        push_sender: PushSender | None = None,
    ):
        self.email = email_sender
        self.sms = sms_sender
        self.push = push_sender

    async def notify_user(
        self,
        user_id: str,
        channels: list[str],
        template: str,
        context: dict,
    ):
        # Resolve user preferences and contact info
        # Send via appropriate channels
        pass
```

## External HTTP Client

### Contract (`app/integrations/external_http/contracts.py`)

```python
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass


@dataclass
class HTTPRequest:
    method: str
    url: str
    headers: dict[str, str] | None = None
    params: dict[str, str] | None = None
    json: dict | None = None
    data: bytes | None = None
    timeout: float = 30.0


@dataclass
class HTTPResponse:
    status_code: int
    headers: dict[str, str]
    content: bytes
    text: str


class HTTPClient(ABC):
    @abstractmethod
    async def request(self, request: HTTPRequest) -> HTTPResponse:
        pass

    @abstractmethod
    async def get(self, url: str, **kwargs) -> HTTPResponse:
        pass

    @abstractmethod
    async def post(self, url: str, **kwargs) -> HTTPResponse:
        pass
```

### Implementation (`app/integrations/external_http/client.py`)

- Connection pooling
- Retry policies with exponential backoff
- Rate limiting
- Correlation ID propagation
- Mock transport for tests

## Adding New Integrations

1. Create contract in `app/integrations/<name>/contracts.py`
2. Implement adapters in `app/integrations/<name>/providers/`
3. Create factory in `app/integrations/<name>/factory.py`
4. Create service in `app/integrations/<name>/service.py`
5. Add configuration to `app/core/config.py`
6. Register in dependency injection container
7. Add tests with fake/mock adapters

## Testing Integrations

Each integration provides fake implementations:

```python
# tests/unit/test_email.py
from app.integrations.email.providers.fake import FakeEmailProvider

@pytest.fixture
def email_sender():
    return FakeEmailProvider()

async def test_send_welcome(email_sender):
    result = await email_sender.send(...)
    assert result.success
    assert len(email_sender.sent_messages) == 1
```

## Reliability Requirements

All integrations must implement:

| Concern | Requirement |
|---------|-------------|
| **Timeouts** | Explicit connection/operation timeouts |
| **Retries** | Bounded retries with backoff + jitter |
| **Rate Limits** | Respect provider quotas, retry-after |
| **Idempotency** | Prevent duplicate side effects |
| **Circuit Breakers** | Optional protection against failures |
| **Error Mapping** | Translate to stable internal errors |
| **Observability** | Latency, success rate, error category metrics |
| **Testing** | Unit, contract, sandbox integration tests |