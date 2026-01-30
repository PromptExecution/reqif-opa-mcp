"""ReqIF MCP Server - Requirements validation and policy evaluation system."""

__version__ = "0.1.0"

from reqif_mcp.decision_logger import (
    DecisionLogEntry,
    append_decision_log,
    create_decision_log_entry,
    log_evaluation,
)
from reqif_mcp.normalization import normalize_reqif
from reqif_mcp.opa_evaluator import (
    compose_opa_input,
    evaluate_requirement,
    evaluate_with_opa,
    load_bundle_manifest,
    validate_opa_output,
)
from reqif_mcp.sarif_producer import (
    create_sarif_result,
    create_sarif_rule,
    generate_sarif_report,
    write_sarif_file,
)
from reqif_mcp.sarif_validator import (
    SARIFValidationErrorDetail,
    SARIFValidationResult,
    load_sarif_schema,
    validate_sarif,
    validate_sarif_file,
    validate_sarif_from_schema_file,
)
from reqif_mcp.server import (
    clear_baseline_store,
    create_error_response,
    get_baseline_by_handle,
    mcp,
    run_server,
    store_baseline,
)
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
    "mcp",
    "run_server",
    "get_baseline_by_handle",
    "store_baseline",
    "clear_baseline_store",
    "create_error_response",
    "load_bundle_manifest",
    "compose_opa_input",
    "evaluate_with_opa",
    "evaluate_requirement",
    "validate_opa_output",
    "create_decision_log_entry",
    "append_decision_log",
    "log_evaluation",
    "DecisionLogEntry",
    "create_sarif_rule",
    "create_sarif_result",
    "generate_sarif_report",
    "write_sarif_file",
    "load_sarif_schema",
    "validate_sarif",
    "validate_sarif_file",
    "validate_sarif_from_schema_file",
    "SARIFValidationResult",
    "SARIFValidationErrorDetail",
]
