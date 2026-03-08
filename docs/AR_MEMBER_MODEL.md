# AR Member Model Draft

Status: draft
Purpose: define the architectural member model before AR feature logic begins

The lesson from structure is clear:
- do not start with summary formulas
- do not start with generic area calculators
- define the domain objects first

## Core Rule

Every AR member must carry:
- `source_ref`
- `basis_status`

No AR quantity may bypass that rule.

## Member Types

### WallMember

Required fields:
- `wall_id`
- `level`
- `location_tag`
- `wall_type`
- `length`
- `height`
- `gross_area`
- `basis_status`
- `source_ref`

Purpose:
- base geometry for paint, render, cladding, tiling, skirting dependency

### OpeningMember

Required fields:
- `opening_id`
- `parent_wall_id`
- `opening_type`
- `width`
- `height`
- `area`
- `count`
- `basis_status`
- `source_ref`

Purpose:
- explicit deductions from wall gross area
- optional trigger for trim, lintel, frame, hardware items

### FinishLayer

Required fields:
- `finish_id`
- `parent_member_type`
- `parent_member_id`
- `finish_type`
- `coverage_basis`
- `thickness` optional
- `net_area`
- `basis_status`
- `source_ref`

Purpose:
- separate geometry from finish mapping
- allow one wall to carry multiple finish systems

### EdgeOrAccessory

Required fields:
- `accessory_id`
- `parent_member_id`
- `accessory_type`
- `length_or_count`
- `unit`
- `basis_status`
- `source_ref`

Purpose:
- skirting
- cornice
- sealant
- trims
- edge angles

### AreaBlock

Required fields:
- `area_block_id`
- `zone_type`
- `level`
- `gross_area`
- `deductions`
- `net_area`
- `basis_status`
- `source_ref`

Purpose:
- floors
- ceilings
- roofs
- facade zones

## Deduction Rule Model

AR logic must not silently deduct openings.

Define explicit deduction rows:
- `deduction_id`
- `owner_member_id`
- `deducted_member_id`
- `rule_type`
- `deducted_qty`
- `formula_text`
- `source_ref`

Examples:
- wall net area = wall gross area - opening areas
- tile finish net area = wall net area

## Accuracy Hierarchy

AR should use the same hierarchy as structure:
- `VERIFIED_DETAIL`
- `ADOPTED_DETAIL`
- `EST_GRID`
- `DENSITY_FALLBACK`
- `MANUAL_ALLOWANCE`
- `NEGOTIATED_COMMERCIAL` only if commercial override is explicitly involved

## First AR Acceptance Case

Before any broad AR module is claimed, one real project must prove:
- wall gross area capture
- opening deductions
- finish mapping
- workbook traceability from AR member to summary

That first project will define the real AR acceptance gate.
