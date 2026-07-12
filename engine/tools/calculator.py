"""Deterministic arithmetic, statistics, percentages, and unit conversion."""
from __future__ import annotations

import ast
import math
import operator
import re
import statistics

from .base import ToolBase, ToolResult

_BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCTIONS = {
    "abs": abs, "round": round, "sqrt": math.sqrt,
    "mean": statistics.mean, "median": statistics.median,
    "stdev": statistics.stdev, "variance": statistics.variance,
    "sum": sum, "min": min, "max": max,
}
_UNITS = {
    "m": ("length", 1.0), "km": ("length", 1000.0), "cm": ("length", 0.01),
    "mm": ("length", 0.001), "mi": ("length", 1609.344), "ft": ("length", 0.3048),
    "in": ("length", 0.0254), "kg": ("mass", 1.0), "g": ("mass", 0.001),
    "lb": ("mass", 0.45359237), "oz": ("mass", 0.028349523125),
}


def _evaluate(node: ast.AST):
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_evaluate(item) for item in node.elts]
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        left, right = _evaluate(node.left), _evaluate(node.right)
        if isinstance(node.op, ast.Pow) and (abs(right) > 1_000 or abs(left) > 1e100):
            raise ValueError("Exponentiation exceeds the calculator safety limit")
        result = _BINARY[type(node.op)](left, right)
        if isinstance(result, (int, float)) and abs(result) > 1e300:
            raise ValueError("Result exceeds the calculator magnitude limit")
        return result
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_evaluate(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCTIONS:
        args = [_evaluate(argument) for argument in node.args]
        return _FUNCTIONS[node.func.id](*args)
    raise ValueError("Expression contains an unsupported operation")


def _convert(value: float, source: str, target: str) -> float:
    source, target = source.lower(), target.lower()
    if source in {"c", "f", "k"} and target in {"c", "f", "k"}:
        celsius = value if source == "c" else (value - 32) * 5 / 9 if source == "f" else value - 273.15
        return celsius if target == "c" else celsius * 9 / 5 + 32 if target == "f" else celsius + 273.15
    if source not in _UNITS or target not in _UNITS or _UNITS[source][0] != _UNITS[target][0]:
        raise ValueError("Unsupported or incompatible unit conversion")
    return value * _UNITS[source][1] / _UNITS[target][1]


def calculate(expression: str):
    percent = re.fullmatch(r"\s*([-+]?\d+(?:\.\d+)?)\s*%\s+of\s+([-+]?\d+(?:\.\d+)?)\s*", expression, re.I)
    if percent:
        return float(percent.group(1)) / 100 * float(percent.group(2))
    conversion = re.fullmatch(r"\s*(?:convert\s+)?([-+]?\d+(?:\.\d+)?)\s*([A-Za-z]+)\s+(?:to|in)\s+([A-Za-z]+)\s*", expression, re.I)
    if conversion:
        return _convert(float(conversion.group(1)), conversion.group(2), conversion.group(3))
    if len(expression) > 1_000:
        raise ValueError("Expression is too long")
    tree = ast.parse(expression, mode="eval")
    if sum(1 for _ in ast.walk(tree)) > 200:
        raise ValueError("Expression is too complex")
    return _evaluate(tree)


class CalculatorTool(ToolBase):
    name = "calculator"
    description = "Perform deterministic arithmetic, percentages, unit conversions, and basic statistics."
    skill_ids = ("quantitative_analysis",)

    async def call(self, query: str, precision: int = 6, **kwargs) -> ToolResult:
        result = calculate(query)
        if isinstance(result, float):
            result = round(result, precision)
        content = str(result)
        return ToolResult(content=content, sources=[], credibility_base=1.0, raw={"result": result})
