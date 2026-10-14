"""Reference and attribute closure after the pinned ReqIF schema gate."""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from xml.etree.ElementTree import Element

import xmlschema
from returns.result import Failure, Result, Success

from reqif_mcp.source_validation import (
    MAX_VALIDATION_ISSUES,
    ReqIFSourceIssue,
    ReqIFSourceValidationError,
    ValidatedReqIFSource,
    validate_reqif_source,
)

NS = "{http://www.omg.org/spec/ReqIF/20110401/reqif.xsd}"
ATTRIBUTE_KINDS = (
    "BOOLEAN",
    "DATE",
    "ENUMERATION",
    "INTEGER",
    "REAL",
    "STRING",
    "XHTML",
)
TYPE_KINDS = (
    "SPEC-OBJECT-TYPE",
    "SPEC-RELATION-TYPE",
    "SPECIFICATION-TYPE",
    "RELATION-GROUP-TYPE",
)
REF_KINDS = {
    name + "-REF": name
    for name in (
        *TYPE_KINDS,
        "SPEC-OBJECT",
        "SPEC-RELATION",
        "SPECIFICATION",
        "ENUM-VALUE",
        *("DATATYPE-DEFINITION-" + kind for kind in ATTRIBUTE_KINDS),
        *("ATTRIBUTE-DEFINITION-" + kind for kind in ATTRIBUTE_KINDS),
    )
}


def _name(element: Element) -> str:
    return element.tag.removeprefix(NS)


def _reference(element: Element, path: str) -> str:
    target = element.find(path, {"r": NS[1:-1]})
    return "" if target is None else (target.text or "").strip()


def validate_reqif_semantics(
    content: bytes,
) -> Result[ValidatedReqIFSource, ReqIFSourceValidationError]:
    """Validate category-aware closure without asserting a model mapping.

    Global references outside this document are unsupported until an explicit
    external document resolver supplies their identities. Hierarchy occurrences
    stay distinct; repeated references to one object are legal.
    """
    preflight = validate_reqif_source(content)
    if isinstance(preflight, Failure):
        return preflight
    resource = xmlschema.XMLResource(BytesIO(content), allow="none", defuse="always")
    core = resource.root.find(f"{NS}CORE-CONTENT/{NS}REQ-IF-CONTENT")
    if core is None:
        return preflight
    nodes: list[Element] = []
    paths: dict[Element, str] = {core: "/REQ-IF/CORE-CONTENT/REQ-IF-CONTENT"}
    stack = [core]
    while stack:
        node = stack.pop()
        if not node.tag.startswith(NS):
            continue
        nodes.append(node)
        counts: dict[str, int] = {}
        for child in node:
            name = _name(child)
            counts[name] = counts.get(name, 0) + 1
            paths[child] = f"{paths[node]}/{name}[{counts[name]}]"
            stack.append(child)
    identities = {
        node.attrib["IDENTIFIER"]: node for node in nodes if "IDENTIFIER" in node.attrib
    }
    issues: list[ReqIFSourceIssue] = []

    def reject(node: Element, reason: str, unsupported: bool = False) -> None:
        if len(issues) < MAX_VALIDATION_ISSUES:
            issues.append(
                ReqIFSourceIssue(
                    "unsupported" if unsupported else "invalid", paths[node], reason
                )
            )

    def attributes(type_id: str) -> set[str]:
        type_node = identities.get(type_id)
        return (
            set()
            if type_node is None
            else {
                child.attrib["IDENTIFIER"]
                for child in type_node.findall("r:SPEC-ATTRIBUTES/*", {"r": NS[1:-1]})
            }
        )

    for node in nodes:
        expected = REF_KINDS.get(_name(node))
        if expected is None:
            continue
        identity = (node.text or "").strip()
        target = identities.get(identity)
        if target is None:
            reject(
                node, f"Unresolved {expected} reference: {identity}", unsupported=True
            )
        elif _name(target) != expected:
            reject(
                node,
                f"Reference requires {expected}, found {_name(target)}: {identity}",
            )

    for owner in nodes:
        owner_kind = _name(owner)
        if owner_kind in ("DATATYPE-DEFINITION-INTEGER", "DATATYPE-DEFINITION-REAL"):
            minimum, maximum = (
                Decimal(owner.attrib["MIN"]),
                Decimal(owner.attrib["MAX"]),
            )
            if not minimum.is_finite() or not maximum.is_finite():
                reject(
                    owner,
                    "Non-finite numeric bounds require an explicit mapping policy",
                    unsupported=True,
                )
            elif minimum > maximum:
                reject(owner, "Datatype minimum exceeds maximum")
        if (
            owner_kind == "DATATYPE-DEFINITION-STRING"
            and Decimal(owner.attrib["MAX-LENGTH"]) < 0
        ):
            reject(owner, "Datatype maximum length must be nonnegative")
        if owner_kind in (
            "SPEC-OBJECT",
            "SPEC-RELATION",
            "SPECIFICATION",
            "RELATION-GROUP",
        ):
            type_id = _reference(owner, "r:TYPE/*")
            allowed = attributes(type_id)
            seen: set[str] = set()
            for value in owner.findall("r:VALUES/*", {"r": NS[1:-1]}):
                definition_id = _reference(value, "r:DEFINITION/*")
                if definition_id not in allowed:
                    reject(
                        value,
                        f"Attribute definition does not belong to owner type {type_id}: {definition_id}",
                    )
                if definition_id in seen:
                    reject(
                        value,
                        f"Duplicate attribute value for definition: {definition_id}",
                    )
                seen.add(definition_id)
        if owner_kind == "SPEC-HIERARCHY":
            object_node = identities.get(_reference(owner, "r:OBJECT/*"))
            type_id = "" if object_node is None else _reference(object_node, "r:TYPE/*")
            for reference in owner.findall("r:EDITABLE-ATTS/*", {"r": NS[1:-1]}):
                if (reference.text or "").strip() not in attributes(type_id):
                    reject(
                        reference,
                        "Editable attribute does not belong to hierarchy object's type",
                    )
        if owner_kind.startswith("ATTRIBUTE-DEFINITION-"):
            for value in owner.findall("r:DEFAULT-VALUE/*", {"r": NS[1:-1]}):
                if _reference(value, "r:DEFINITION/*") != owner.attrib["IDENTIFIER"]:
                    reject(
                        value,
                        "Default value must reference its enclosing attribute definition",
                    )
        if not owner_kind.startswith("ATTRIBUTE-VALUE-"):
            continue
        definition = identities.get(_reference(owner, "r:DEFINITION/*"))
        datatype = (
            None
            if definition is None
            else identities.get(_reference(definition, "r:TYPE/*"))
        )
        expected_datatype = owner_kind.replace(
            "ATTRIBUTE-VALUE-", "DATATYPE-DEFINITION-"
        )
        if datatype is not None and _name(datatype) != expected_datatype:
            reject(owner, "Attribute value kind does not match its definition datatype")
            continue
        if datatype is not None and owner_kind in (
            "ATTRIBUTE-VALUE-INTEGER",
            "ATTRIBUTE-VALUE-REAL",
        ):
            numeric_value = Decimal(owner.attrib["THE-VALUE"])
            minimum, maximum = (
                Decimal(datatype.attrib["MIN"]),
                Decimal(datatype.attrib["MAX"]),
            )
            if not all(
                number.is_finite() for number in (numeric_value, minimum, maximum)
            ):
                reject(
                    owner,
                    "Non-finite numeric value requires an explicit mapping policy",
                    unsupported=True,
                )
            elif not minimum <= numeric_value <= maximum:
                reject(owner, "Numeric attribute value is outside datatype bounds")
        if datatype is not None and owner_kind == "ATTRIBUTE-VALUE-STRING":
            if Decimal(len(owner.attrib["THE-VALUE"])) > Decimal(
                datatype.attrib["MAX-LENGTH"]
            ):
                reject(owner, "String attribute value exceeds datatype maximum length")
        if owner_kind != "ATTRIBUTE-VALUE-ENUMERATION":
            continue
        allowed_values = (
            set()
            if datatype is None
            else {
                child.attrib["IDENTIFIER"]
                for child in datatype.findall("r:SPECIFIED-VALUES/*", {"r": NS[1:-1]})
            }
        )
        values = owner.findall("r:VALUES/*", {"r": NS[1:-1]})
        selected = [(value.text or "").strip() for value in values]
        for value, identity in zip(values, selected, strict=True):
            if identity not in allowed_values:
                reject(
                    value,
                    f"Enumeration value does not belong to the attribute datatype: {identity}",
                )
        if len(set(selected)) != len(selected):
            reject(owner, "Duplicate enumeration selection")
        if (
            definition is not None
            and definition.attrib.get("MULTI-VALUED") in ("false", "0")
            and len(selected) > 1
        ):
            reject(owner, "Single-valued enumeration has multiple selections")
    if issues:
        return Failure(ReqIFSourceValidationError(tuple(issues)))
    return Success(preflight.unwrap())
