import re
import json
import logging
import traceback
import concurrent.futures
from typing import Callable, Iterable

def dump_json(x):
    try:
        return json.dumps(x)
    except Exception:
        return x

def is_trip_id(trip_id: str):
    return re.match(r"[A-Z]{2}-\d{10}-\d{2}", trip_id)

def is_trailer_id(trailer_id: str):
    return re.match(r"RX\d{5}E", trailer_id)

def get_trace(e: Exception, n: int = 5):
    return "".join(traceback.format_exception(e)[-n:])

def run_parallel_exec(exec_func: Callable, iterable: Iterable, *func_args, **kwargs):
    func_name = (
        f"{exec_func.__name__} | parallel_exec | "
        if hasattr(exec_func, "__name__")
        else "unknown | parallel_exec | "
    )
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=kwargs.pop("max_workers", 100), thread_name_prefix=func_name
    ) as executor:
        future_element_map = {
            executor.submit(exec_func, element, *func_args): element
            for element in iterable
        }
        result: list[tuple] = []
        for future in concurrent.futures.as_completed(future_element_map):
            element = future_element_map[future]
            try:
                result.append((element, future.result()))
            except Exception as exc:
                log_trace = exc if kwargs.pop("quiet", False) else get_trace(exc, 3)
                logging.error(
                    f"Got error while running parallel_exec: {element}: \n{log_trace}"
                )
                result.append((element, exc))
        return result

def run_parallel_exec_but_return_in_order(
    exec_func: Callable, iterable: Iterable, *func_args, **kwargs
):
    result = run_parallel_exec(
        exec_func, iterable := list(iterable), *func_args, **kwargs
    )
    result.sort(key=lambda x: iterable.index(x[0]))
    return [x[-1] for x in result]

def chunkify(lst: list, chunk_size: int = 40):
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size] 