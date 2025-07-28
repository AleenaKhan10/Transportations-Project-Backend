import json
from enum import Enum
from collections import Counter

import pandas as pd

from helpers.utils import clean_name, dump_json


class JsonType(Enum):
    LIST = 'list'
    TUPLE = 'tuple'
    DICT = 'dict'
    STRING = 'string'
    INT = 'int'
    FLOAT = 'float'
    BOOL = 'bool'
    NULL = 'null'
    OTHER = 'other'
    
    def __str__(self):
        return self.value

    @property
    def pytype(self):
        """
        Return the Python type associated with this JsonType.
        
        Returns:
            type: The Python type associated with this JsonType
        """
        return {
            self.LIST: list,
            self.TUPLE: tuple,
            self.DICT: dict,
            self.STRING: str,
            self.INT: int,
            self.FLOAT: float,
            self.BOOL: bool,
            self.NULL: None,
            self.OTHER: str,
        }[self]
    
    @property
    def bqtype(self):
        """
        Return the BigQuery type associated with this JsonType.
        
        Returns:
            str: The BigQuery type associated with this JsonType
        """
        return {
            self.LIST: 'JSON',
            self.TUPLE: 'JSON',
            self.DICT: 'JSON',
            self.STRING: 'STRING',
            self.INT: 'INT64',
            self.FLOAT: 'FLOAT64',
            self.BOOL: 'BOOL',
            self.NULL: 'STRING',
            self.OTHER: 'STRING',
        }[self]
    
    @property
    def bqtype_convertor(self):
        """
        Return a function that takes a value and converts it to a BigQuery type.
        
        The function returned maps the JsonType to a BigQuery type by returning
        a function that takes a value and converts it to the corresponding BigQuery type.
        The conversion is as follows:
            list: str (JSON string of list)
            tuple: str (JSON string of tuple)
            dict: str (JSON string of dict)
            str: str
            int: int
            float: float
            bool: bool
            null: None
            other: str (string of the value)
        
        Returns:
            function(value): The function that takes a value and converts it to the corresponding BigQuery type
        """
        def apply_if_not_none(x, fn):
            return fn(x) if x is not None else None
        
        return {
            self.LIST: lambda x: apply_if_not_none(x, dump_json),
            self.TUPLE: lambda x: apply_if_not_none(dump_json(x, list)),
            self.DICT: lambda x: apply_if_not_none(x, dump_json),
            self.STRING: lambda x: apply_if_not_none(x, str),
            self.INT: lambda x: apply_if_not_none(x, int),
            self.FLOAT: lambda x: apply_if_not_none(x, float),
            self.BOOL: lambda x: apply_if_not_none(x, bool),
            self.NULL: lambda x: None,
            self.OTHER: lambda x: apply_if_not_none(x, str),
        }[self]

# Shorter alias
J = JsonType

class TypeCounter(Counter):
    @property
    def most_common_type(self) -> JsonType:
        return super().most_common(1)[0][0]


def find_python_types(df: pd.DataFrame) -> dict[str, TypeCounter[J]]:
    """
    Analyze a DataFrame and return the Python types found in each column.
    Focuses on JSON-serializable types that might come from APIs.
    
    Returns a dictionary where keys are column names and values are lists
    of unique types found in that column.
    """
    column_types = {}
    
    # Iterate through each column
    for col in df.columns:
        types_in_column: list[J] = []
        
        for value in df[col]:
            # Handle NaN/None values - use try/except for arrays
            try:
                if pd.isna(value):
                    types_in_column.append(J.NULL)
                    continue
            except (ValueError, TypeError):
                # For arrays or other objects where pd.isna() fails
                if value is None:
                    types_in_column.append(J.NULL)
                    continue
                
            # Handle special cases for JSON-compatible types
            if isinstance(value, (list, tuple)):
                # Try to serialize to check if it's JSON-compatible
                try:
                    json.dumps(value)
                    types_in_column.append(J.LIST if isinstance(value, list) else J.TUPLE)
                except (TypeError, ValueError):
                    types_in_column.append(J.OTHER)
            elif isinstance(value, dict):
                try:
                    json.dumps(value)
                    types_in_column.append(J.DICT)
                except (TypeError, ValueError):
                    types_in_column.append(J.OTHER)
            elif isinstance(value, str):
                types_in_column.append(J.STRING)
            elif isinstance(value, bool):
                types_in_column.append(J.BOOL)
            elif isinstance(value, int):
                types_in_column.append(J.INT) 
            elif isinstance(value, float):
                types_in_column.append(J.FLOAT)
            else:
                # For other types, use the class name
                types_in_column.append(J.OTHER)
        
        # Remove NULL type if there are other types
        if J.NULL in types_in_column and len(types_in_column) > 1:
            types_in_column.remove(J.NULL)
        
        # Convert set to sorted list for consistent output
        column_types[col] = TypeCounter(types_in_column)
    
    return column_types

def clean_column_names(
    df: pd.DataFrame,
    replacements: dict[str, str] = {},
    replace_dot_with_next_capital: bool = True,
) -> pd.DataFrame:
    """
    Clean column names in a DataFrame by replacing special characters and applying case rules.

    Args:
        df: DataFrame to clean column names of
        replacements: Optional dictionary of replacement strings
        replace_dot_with_next_capital: If True, replace dots with the next character capitalized

    Returns:
        DataFrame with cleaned column names
    """
    _df = df.copy(deep=True)
    _df.columns = [
        clean_name(col, 
            replacements=replacements, 
            replace_dot_with_next_capital=replace_dot_with_next_capital, 
        )
        for col in _df.columns
    ]
    return _df
