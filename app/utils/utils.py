import asyncio
import os
import re
import threading
from collections.abc import Mapping
from io import BytesIO
from pathlib import Path
from typing import Optional

import pandas as pd
import yaml
from pandas import ExcelWriter, MultiIndex, DataFrame
from pandas.core.dtypes.common import is_datetime64_any_dtype

path_matcher = re.compile(r"\$\{([^}^{]+)\}")

def path_constructor(loader, node):
    value = node.value
    match = path_matcher.match(value)
    env_var = match.group()[2:-1]
    return f"{os.environ.get(env_var)}{value[match.end():]}"


def read_yaml(path: Path) -> Mapping:
    yaml.add_implicit_resolver("!path", path_matcher, None, yaml.SafeLoader)
    yaml.add_constructor("!path", path_constructor, yaml.SafeLoader)

    with open(path, encoding="utf-8") as file:
        return yaml.safe_load(file)


def merge(left: Mapping, right: Mapping) -> Mapping:
    """
    Merge two mappings objects together, combining overlapping Mappings,
    and favoring right-values
    left: The left Mapping object.
    right: The right (favored) Mapping object.
    NOTE: This is not commutative (merge(a,b) != merge(b,a)).
    """
    merged = {}

    left_keys = frozenset(left)
    right_keys = frozenset(right)

    # Items only in the left Mapping
    for key in left_keys - right_keys:
        merged[key] = left[key]

    # Items only in the right Mapping
    for key in right_keys - left_keys:
        merged[key] = right[key]

    # in both
    for key in left_keys & right_keys:
        left_value = left[key]
        right_value = right[key]

        if isinstance(left_value, Mapping) and isinstance(
                right_value, Mapping
        ):  # recursive merge
            merged[key] = merge(left_value, right_value)
        else:  # overwrite with right value
            merged[key] = right_value

    return merged


class RunThread(threading.Thread):
    def __init__(self, func, args, kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.result = None
        super().__init__()

    def run(self):
        self.result = asyncio.run(self.func(*self.args, **self.kwargs))


def run_async(func, *args, **kwargs):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        thread = RunThread(func, args, kwargs)
        thread.start()
        thread.join()
        return thread.result
    else:
        return asyncio.run(func(*args, **kwargs))


def clean_html(raw_html: str) -> str:
    CLEANR = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')
    clean_text = re.sub(CLEANR, '', raw_html)
    return clean_text


def table_writer(dataframes: dict[Optional[str], DataFrame], param: Optional = "xlsx") -> BytesIO:
    def excellent_header():
        # Get the xlsxwriter workbook and worksheet objects.
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]
        # Add a header format.
        header_format = workbook.add_format(
            {"text_v_align": 2, "align": "center", "text_wrap": True, "bold": True, "fg_color": "#ffcccc", "border": 1}
        )
        if isinstance(dataframe.columns, MultiIndex):
            # multilevel header
            for row_num, value in enumerate(dataframe.columns.names):
                worksheet.write(row_num, 0, value, header_format)
        for col_num, value in enumerate(dataframe.columns.values):
            if isinstance(value, tuple):
                # multilevel header
                for level in range(len(value)):
                    worksheet.write(level, col_num + 1, value[level], header_format)
            else:
                worksheet.write(0, col_num, value, header_format)
            column_len = dataframe.iloc[:, col_num].astype(str).str.len().max()
            # Setting the length if the column header is larger than the max column value length (<= 30)
            column_len = min(max(column_len, len(value) // 2 + 1) + 3, 30)
            # set the column length
            worksheet.set_column(col_num, col_num, column_len)

    output = BytesIO()
    if param == "xlsx":
        max_row = 1000000
        writer = ExcelWriter(output, engine="xlsxwriter")
        for count, (name, dataframe) in enumerate(dataframes.items()):
            sheet_name_begin = name if name else f"sheet {count}"
            sheet_count = int((dataframe.shape[0] - 1) / max_row + 1)
            # replace dot with comma for Decimal
            dataframe = df_convert_number_to_number(dataframe)
            # dataframe = dataframe.copy().apply(pd.to_numeric, errors="ignore")
            for index in range(sheet_count):
                if sheet_count > 1:
                    sheet_name = f"{sheet_name_begin} ({index})"
                    df = dataframe.loc[index * max_row : (index + 1) * max_row - 1]
                else:
                    sheet_name = sheet_name_begin
                    df = dataframe
                if isinstance(df.columns, MultiIndex):
                    # multilevel header
                    df.to_excel(writer, sheet_name=sheet_name, index=True, freeze_panes=(2, 0))
                else:
                    df.to_excel(writer, sheet_name=sheet_name, index=False, freeze_panes=(1, 0))
                excellent_header()
            # writer.save()
        writer.close()
    elif param == "csv":
        for name, dataframe in dataframes.items():
            dataframe.to_csv(output, index=False)
            # output.seek(0)
    return output



def df_convert_number_to_number(df: DataFrame) -> DataFrame:
    # replace dot with comma for Decimal
    if df.shape[0] > 0:
        df = df.copy()
        # non-date format columns
        for column in [column for column in df.columns if not is_datetime64_any_dtype(df[column])]:
            # df[column] = df[column].apply(pd.to_numeric, errors="ignore")
            try:
                df[column] = pd.to_numeric(df[column], errors="raise")
            except (ValueError, TypeError):
                # Same logic as errors='ignore' in pd.to_numeric
                pass

    # return df.apply(pd.to_numeric, errors="ignore")
    return df