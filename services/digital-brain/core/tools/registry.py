from typing import Dict, Type, List
from .base import BaseTool
from .definitions import OrderStatusTool
from .crm_status import CrmCustomerStatusTool, CrmQuotationStatusTool
from .web_search import WebSearchTool
from .rpa_browser import RPABrowserTool
from .ppt_generator import PPTGeneratorTool

class ToolRegistry:
    _tools: Dict[str, BaseTool] = {}
    
    @classmethod
    def register_defaults(cls):
        cls.register(OrderStatusTool())
        # Unbound prototypes only expose schemas; run() fails without trusted
        # server-side actor+session context, never supplied by tool arguments.
        cls.register(CrmCustomerStatusTool())
        cls.register(CrmQuotationStatusTool())
        cls.register(WebSearchTool())
        cls.register(RPABrowserTool())
        cls.register(PPTGeneratorTool())
        
    @classmethod
    def register(cls, tool: BaseTool):
        cls._tools[tool.name] = tool
        
    @classmethod
    def get_tool(cls, name: str) -> BaseTool:
        if not cls._tools:
            cls.register_defaults()
        return cls._tools.get(name)
        
    @classmethod
    def get_all_schemas(cls, filter_names: List[str] = None) -> List[Dict]:
        if not cls._tools:
            cls.register_defaults()
            
        schemas = []
        for name, tool in cls._tools.items():
            if filter_names is None or name in filter_names:
                schemas.append(tool.schema)
        return schemas

# Auto init
ToolRegistry.register_defaults()
