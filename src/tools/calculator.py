"""Calculator Tool Implementation.
Allows the AI Agent to perform safe mathematical calculations.
"""

import ast 
import operator
from typing import Any 
from src.agent.interfaces import ToolInterface


class CalculatorTool(ToolInterface):

    _SAFE_OPERATORS = {
        ast.Add: operator.add,      # addition (+)
        ast.Sub: operator.sub,      # subtraction (-)
        ast.Mult: operator.mul,     # multiplication (*)
        ast.Div: operator.truediv,  # division (/)
        ast.Pow: operator.pow,      # exponent (**)
        ast.USub: operator.neg,     # negative numbers (-x)
        ast.UAdd: operator.pos,    
    }

    @property
    def name(self) -> str:
        """Unique tool name passed to the LLM."""
        return "calculator"

    @property
    def description(self) -> str:
        """Description telling the LLM when and how to use this tool."""
        return (
            "Perform mathematical calculations and statistical computations accurately. "
            "Argument: 'expression' (str) - math string like '(55 - 45) / 10' or '12 * 3.5'."
        )
    def run(self, arguments: dict[str, Any]) -> Any:
        expression = arguments.get("expression")
        if not expression or not isinstance(expression, str):
            raise ValueError("calculator tool requires a non-empty string 'expression' arguments.   ")
        

        try:
            # Parse math string into a safe Abstract Syntax Tree (AST) node
            node = ast.parse(expression.strip(), mode="eval").body
            return self._eval_node(node)
        except Exception as e:
            raise ValueError(f"Invalid math expression '{expression}': {e}")

    
    def _eval_node(self, node: ast.AST) -> float | int:
        """Recursively evaluate safe AST math nodes without using unsafe eval()."""
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op_type = type(node.op)
            if op_type in self._SAFE_OPERATORS:
                return self._SAFE_OPERATORS[op_type](left, right)
        if isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            op_type = type(node.op)
            if op_type in self._SAFE_OPERATORS:
                return self._SAFE_OPERATORS[op_type](operand)
        raise ValueError("Unsupported or unsafe math operation.")    