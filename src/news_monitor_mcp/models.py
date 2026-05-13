"""Pydantic-Input-Modelle fuer alle 15 MCP-Tools.

Werden von den `@mcp.tool`-Funktionen in `tools/` verwendet. Saemtliche Modelle
sind mit `extra="forbid"` konfiguriert, damit unbekannte Felder im LLM-Aufruf
einen klaren Validation-Fehler erzeugen statt stillschweigend ignoriert zu werden.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from news_monitor_mcp.api_client import DEFAULT_RESULTS, MAX_RESULTS
from news_monitor_mcp.formatting import AlertConditionType, ResponseFormat, SortOrder


class SearchNewsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    query: str = Field(..., description="Suchbegriff(e)", min_length=1, max_length=500)
    language: Optional[str] = Field(default=None, max_length=10)
    source_country: Optional[str] = Field(default=None, max_length=100)
    earliest_date: Optional[str] = Field(default=None, description="Format YYYY-MM-DD")
    latest_date: Optional[str] = Field(default=None)
    sort: SortOrder = Field(default=SortOrder.RELEVANCE)
    number: int = Field(default=DEFAULT_RESULTS, ge=1, le=MAX_RESULTS)
    include_full_text: bool = Field(default=False)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
    use_cache: bool = Field(default=True, description="Cache verwenden (Standard: True)")

    @field_validator("earliest_date", "latest_date")
    @classmethod
    def validate_date(cls, v: Optional[str]) -> Optional[str]:
        if v is None: return v
        try: datetime.strptime(v, "%Y-%m-%d")
        except ValueError as e: raise ValueError("Format YYYY-MM-DD erforderlich") from e
        return v


class TopNewsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    source_country: str = Field(default="ch", min_length=2, max_length=5)
    language: str = Field(default="de", min_length=2, max_length=5)
    date: Optional[str] = Field(default=None)
    number: int = Field(default=10, ge=1, le=100)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
    use_cache: bool = Field(default=True)

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: Optional[str]) -> Optional[str]:
        if v is None: return v
        try: datetime.strptime(v, "%Y-%m-%d")
        except ValueError as e: raise ValueError("Format YYYY-MM-DD erforderlich") from e
        return v


class SentimentMonitorInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    entity: str = Field(..., description="Institution, Person oder Thema", min_length=2, max_length=300)
    language: str = Field(default="de")
    days_back: int = Field(default=30, ge=1, le=365)
    source_country: Optional[str] = Field(default="ch,de,at")
    number: int = Field(default=20, ge=1, le=100)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
    use_cache: bool = Field(default=True)

    @field_validator("language")
    @classmethod
    def validate_lang(cls, v: str) -> str:
        if v not in ("de", "en"): raise ValueError("Sentiment nur fuer de und en.")
        return v


class RetrieveArticleInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    article_id: int = Field(..., gt=0)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
    use_cache: bool = Field(default=True)


class SearchSourcesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    name: Optional[str] = Field(default=None, max_length=200)
    country: Optional[str] = Field(default=None, max_length=5)
    language: Optional[str] = Field(default=None, max_length=5)
    number: int = Field(default=20, ge=1, le=100)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
    use_cache: bool = Field(default=True)


class MediaBriefingInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    topics: list[str] = Field(..., min_length=1, max_length=5)
    language: str = Field(default="de")
    days_back: int = Field(default=7, ge=1, le=31)
    source_country: str = Field(default="ch,de,at")
    use_cache: bool = Field(default=True)

    @field_validator("language")
    @classmethod
    def validate_lang(cls, v: str) -> str:
        if v not in ("de", "en"): raise ValueError("Fuer Sentiment: de oder en.")
        return v

    @field_validator("topics")
    @classmethod
    def validate_topics(cls, v: list[str]) -> list[str]:
        if len(v) > 5: raise ValueError("Max. 5 Themen")
        return v


class FrontPagesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    source_country: str = Field(default="ch", min_length=2, max_length=5)
    source_name: Optional[str] = Field(default=None, max_length=200)
    date: Optional[str] = Field(default=None)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
    use_cache: bool = Field(default=True)

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: Optional[str]) -> Optional[str]:
        if v is None: return v
        try: datetime.strptime(v, "%Y-%m-%d")
        except ValueError as e: raise ValueError("Format YYYY-MM-DD erforderlich") from e
        return v


class TrendRadarInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    category: str = Field(..., description="z.B. politics, technology, education", min_length=2, max_length=50)
    source_country: str = Field(default="ch")
    language: str = Field(default="de")
    days_back: int = Field(default=7, ge=1, le=30)
    number: int = Field(default=15, ge=1, le=50)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
    use_cache: bool = Field(default=True)


class GeoNewsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    location: str = Field(..., description="Ortsname, z.B. Zuerich, Bern, Kanton Zuerich", min_length=2, max_length=200)
    query: Optional[str] = Field(default=None, max_length=300)
    language: str = Field(default="de")
    days_back: int = Field(default=14, ge=1, le=90)
    number: int = Field(default=10, ge=1, le=50)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
    use_cache: bool = Field(default=True)


class CreateAlertInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    name: str = Field(..., description="Name des Alerts, z.B. Schulamt Zuerich Negativalert", min_length=2, max_length=200)
    entity: str = Field(..., description="Suchbegriff / Entitaet, z.B. Schulamt Zuerich", min_length=2, max_length=300)
    language: str = Field(default="de")
    source_country: Optional[str] = Field(default="ch,de,at")
    days_back: int = Field(default=7, ge=1, le=90)
    condition_type: AlertConditionType = Field(..., description="sentiment_below | sentiment_above | volume_above | keyword_found")
    threshold: Optional[float] = Field(default=None, description="Schwellenwert fuer sentiment/volume conditions")
    keyword: Optional[str] = Field(default=None, max_length=200, description="Schluesselwort fuer keyword_found")

    @field_validator("language")
    @classmethod
    def validate_lang(cls, v: str) -> str:
        if v not in ("de", "en"): raise ValueError("Nur de und en.")
        return v


class CheckAlertsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    alert_id: Optional[str] = Field(default=None, description="Spezifische Alert-ID (leer = alle)")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class DeleteAlertInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    alert_id: str = Field(..., description="Alert-ID aus news_alert_list", min_length=10)
    confirm: bool = Field(default=False,
        description="Muss explizit True sein, um den Alert zu loeschen. Erstaufruf "
                    "mit confirm=False liefert eine Bestaetigungs-Aufforderung.")


class CacheClearInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    tool_type: Optional[str] = Field(default=None, description="Cache-Typ leeren: search|headlines|sentiment|briefing|article|sources|front_pages|trend|geo. Leer = alles.")
    confirm: bool = Field(default=False,
        description="Muss explizit True sein, um den Cache zu leeren. Erstaufruf "
                    "mit confirm=False liefert eine Bestaetigungs-Aufforderung.")
