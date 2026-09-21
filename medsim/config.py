"""Settings loaded from the environment and ``.env``."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from medsim.errors import ConfigError
from medsim.models import SourceName

DEFAULT_MODEL = "deepseek/deepseek-v4-flash-0731"


def _default_sources() -> list[SourceName]:
    return ["europe_pmc", "litsense"]


class EuropePMCSettings(BaseModel):
    enabled: bool = True
    base_url: str = "https://www.ebi.ac.uk/europepmc/webservices/rest"
    page_size: int = Field(default=25, ge=1, le=1000)  # candidate pool before reranking
    result_type: Literal["idlist", "lite", "core"] = "core"
    open_access_only: bool = False
    full_text_only: bool = False
    sort: str | None = None  # e.g. "CITED desc"; None = relevance order
    synonym: bool = False  # MeSH expansion; made title/abstract queries slightly worse in probes
    timeout_s: float = 20.0
    max_retries: int = Field(default=3, ge=0)
    backoff_base_s: float = 1.0
    min_interval_s: float = 0.0  # no rate limit found in accessible docs


class LitSenseSettings(BaseModel):
    enabled: bool = True
    base_url: str = "https://www.ncbi.nlm.nih.gov/research/litsense2-api/api"
    mode: Literal["sentences", "passages"] = "passages"
    rerank: bool = True
    max_results: int = Field(default=30, ge=1, le=100)  # candidate pool; API returns at most 100
    # "natural": "serum albumin in patients with biloma" instead of "serum albumin biloma"
    query_style: Literal["keywords", "natural"] = "keywords"
    timeout_s: float = 30.0
    max_retries: int = Field(default=3, ge=0)
    backoff_base_s: float = 1.0
    min_interval_s: float = 1.0  # documented: one request per user per second


# Biomedical literature databases plus two clinical references; the search engine only returns
# pages from these sites. Override with MEDSIM_OPENROUTER_SEARCH__ALLOWED_DOMAINS='[...]'.
MEDICAL_DOMAINS = ("ncbi.nlm.nih.gov", "europepmc.org", "msdmanuals.com", "medscape.com")


class OpenRouterSearchSettings(BaseModel):
    """OpenRouter's ``openrouter:web_search`` server tool used as a document retriever.

    Not in the default ``enabled_sources``; add "openrouter_search" to use it. Each search is
    billed by the engine (Exa: $0.007 per request with up to 10 results) plus the tokens of the
    model that issues the search call.
    """

    enabled: bool = True
    model: str | None = None  # model that issues the search call; None = default_model
    engine: Literal["auto", "native", "exa", "parallel", "perplexity", "firecrawl"] = "exa"
    mode: str | None = None  # engine-specific, e.g. Exa "fast" or "deep"; None = engine default
    max_results: int = Field(default=8, ge=1, le=25)
    max_characters: int | None = Field(default=1500, ge=1, le=100_000)  # per-result excerpt cap
    allowed_domains: list[str] = Field(default_factory=lambda: list(MEDICAL_DOMAINS))
    excluded_domains: list[str] = Field(default_factory=list)
    max_tokens: int = Field(default=2000, ge=1)
    timeout_s: float = 120.0
    max_retries: int = Field(default=2, ge=0)
    backoff_base_s: float = 1.0


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MEDSIM_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # OpenRouter
    openrouter_api_key: SecretStr = Field(
        validation_alias=AliasChoices("OPENROUTER_API_KEY", "MEDSIM_OPENROUTER_API_KEY")
    )
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_http_referer: str | None = None
    openrouter_app_title: str = "medsim"
    verify_models_on_startup: bool = True

    # Models and sampling
    default_model: str = DEFAULT_MODEL
    resolver_model: str | None = None
    query_builder_model: str | None = None
    synthesizer_model: str | None = None
    synthesizer_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    seed: int | None = 7
    # Completion budgets include reasoning tokens. A cut-off reply is retried once with double
    # the budget (see llm/structured.py).
    resolver_max_tokens: int = Field(default=4000, ge=1)
    query_builder_max_tokens: int = Field(default=4000, ge=1)
    synthesizer_max_tokens: int = Field(default=6000, ge=1)
    json_mode: Literal["json_schema", "json_object", "none"] = "json_schema"
    llm_timeout_s: float = 120.0
    llm_max_retries: int = Field(default=2, ge=0)
    llm_backoff_base_s: float = 1.0
    llm_extra_body: dict[str, Any] = Field(default_factory=dict)

    # Retrieval
    enabled_sources: list[SourceName] = Field(default_factory=_default_sources)
    europe_pmc: EuropePMCSettings = Field(default_factory=EuropePMCSettings)
    litsense: LitSenseSettings = Field(default_factory=LitSenseSettings)
    openrouter_search: OpenRouterSearchSettings = Field(default_factory=OpenRouterSearchSettings)
    max_documents: int = Field(default=8, ge=1)
    max_doc_chars: int = Field(default=1500, ge=100)
    near_duplicate_threshold: float = Field(default=0.9, gt=0.0, le=1.0)
    rerank_documents: bool = True  # lexical term rerank within each source before merging
    relax_min_relevant: int = Field(default=3, ge=0)  # broaden a source's query below this
    # Retrieval changes measured in results/README.md; all off by default (the original method).
    rank_for_values: bool = False  # 1: documents stating a value for the variable rank first
    merge_strategy: Literal["round_robin", "global"] = "round_robin"  # 1: one list, all sources
    population_filter: bool = False  # 2: drop animal studies; rank other age groups lower
    ladder_version: Literal["v1", "v2"] = "v1"  # 3+4: article-body search, value-based broadening
    fulltext_excerpts: bool = False  # 3: text around the variable instead of the first N chars
    fulltext_max_docs: int = Field(default=10, ge=0)  # open-access full texts fetched per search
    llm_rerank: bool = False  # 6: an LLM picks the documents that state a value for this patient
    reranker_model: str | None = None
    reranker_max_tokens: int = Field(default=4000, ge=1)
    rerank_candidates: int = Field(default=20, ge=1)
    cache_enabled: bool = False
    cache_dir: Path = Path(".medsim_cache")
    contact_email: str | None = None

    log_level: str = "WARNING"

    def model_for(self, stage: str) -> str:
        override: str | None = getattr(self, f"{stage}_model", None)
        return override or self.default_model

    def stage_models(self) -> list[str]:
        return list(
            dict.fromkeys(self.model_for(s) for s in ("resolver", "query_builder", "synthesizer"))
        )

    def user_agent(self) -> str:
        from medsim import __version__

        contact = f" (mailto:{self.contact_email})" if self.contact_email else ""
        return f"medsim/{__version__} research-simulator{contact}"


def load_settings(**overrides: Any) -> Settings:
    """Build ``Settings``; convert validation failures into an actionable ``ConfigError``."""
    try:
        return Settings(**overrides)
    except ValidationError as exc:
        missing_key = any(
            (err["type"] == "missing" and "openrouter_api_key" in str(err["loc"]))
            or err["loc"] == ("OPENROUTER_API_KEY",)
            for err in exc.errors()
        )
        if missing_key:
            raise ConfigError(
                "OPENROUTER_API_KEY is not set. Copy .env.example to .env and add your key "
                "(https://openrouter.ai/keys), or export OPENROUTER_API_KEY in your shell."
            ) from None
        details = "; ".join(
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()
        )
        raise ConfigError(f"Invalid medsim configuration: {details}") from None
