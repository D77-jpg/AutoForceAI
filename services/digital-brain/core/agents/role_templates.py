"""Conservative H-06 role catalog. Templates are descriptions, not tool grants.

No execution adapter has been verified for these five workflows. Until a scoped,
authorization-aware adapter is implemented, the executable tool whitelist is empty.
"""
from copy import deepcopy

VERSION = "1.0.0"
SCOPE = {"organization": "authenticated user's current organization", "project": "owned project only", "cross_project": False}

_DEFINITIONS = (
    ("lead_researcher", "线索研究员", "archivist", "研究并去重线索，生成待人工审核的线索草稿。", ["不得自动联系潜在客户", "不得直接写入外部 CRM"], ["search", "lead_deduplication", "lead_write"]),
    ("sales_development", "销售开发助手", "strategist", "生成销售开发信草稿，由人审核后另行发送。", ["不得发送邮件", "不得对外联系客户"], ["email_draft", "send_email"]),
    ("followup_coordinator", "跟进协调员", "strategist", "生成跟进建议与排期草稿。", ["不得自动写入日程或 CRM", "不得自动发信"], ["followup_scheduling", "crm_write"]),
    ("quote_assistant", "报价助手", "strategist", "依据已核实的报价流程提供建议与报价草稿。", ["不得发送报价", "不得擅自承诺价格或修改订单"], ["quote_suggestion", "quote_draft"]),
    ("customer_support", "客服助手", "customer_service", "依据知识库回答问题，并在获授权时查看报价状态。", ["不得修改订单", "不得对外发送信息"], ["knowledge_base_lookup", "quote_status_lookup"]),
)


def list_role_templates():
    result = []
    for key, name, role, goal, prohibitions, unavailable in _DEFINITIONS:
        result.append({
            "key": key, "name": name, "role": role, "description": goal,
            "goal": goal, "prohibitions": prohibitions,
            "allowed_tools": [], "unavailable_capabilities": unavailable,
            "data_scope": deepcopy(SCOPE), "max_steps": 5,
            "timeout_seconds": 120, "max_cost_usd": 0.25,
            "requires_human_approval_for_external_actions": True,
            "template_version": VERSION, "prompt_version": VERSION,
            "system_prompt": (
                f"角色：{name}。目标：{goal} 禁止：{'；'.join(prohibitions)}。"
                "只能在当前用户所属组织及其拥有的项目内处理数据。"
                "当前无已验证可执行工具；不得声称已搜索、查询、写入、发送或执行。"
                "所有外部写入和发送必须先经人工审批，且由独立安全执行器处理。"
                "输出仅是计划或草稿，不是执行结果。"
            ),
        })
    return result


def get_role_template(key):
    return next((t for t in list_role_templates() if t["key"] == key), None)


# Explicit deny-by-default registry. A new backend tool is not automatically approved.
TRUSTED_EXECUTABLE_TOOLS = frozenset()
FORBIDDEN_ACTIONS = frozenset({"send_email", "rpa_action"})
