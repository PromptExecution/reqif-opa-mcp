"""ReqIF MCP Server - Requirements validation and policy evaluation system."""

__version__ = "0.1.0"

from reqif_mcp.normalization import normalize_reqif
from reqif_mcp.validation import (
    IntegrityErrorDetail,
    IntegrityValidationResult,
    ValidationErrorDetail,
    ValidationResult,
    validate_requirement_integrity,
    validate_requirement_record,
    validate_requirement_record_from_schema_file,
)

__all__ = [
    "normalize_reqif",
    "validate_requirement_record",
    "validate_requirement_record_from_schema_file",
    "validate_requirement_integrity",
    "ValidationResult",
    "ValidationErrorDetail",
    "IntegrityValidationResult",
    "IntegrityErrorDetail",
]
