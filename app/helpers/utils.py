import json
import logging
import traceback
import concurrent.futures
from typing import Callable, Iterable, List, Literal, Tuple, Any

def dump_json(x):
    try:
        return json.dumps(x)
    except Exception:
        return x

def get_trace(e: Exception, n: int = 5):
    return "".join(traceback.format_exception(e)[-n:])

def run_parallel_exec(exec_func: Callable, iterable: Iterable, *func_args, **kwargs):
    """
    Runs a function in parallel using ThreadPoolExecutor.

    Args:
        exec_func (Callable): A function to run concurrently.
        iterable (Iterable): An iterable to run the function on.
        *func_args: Any additional arguments to pass to the function.
        **kwargs: Any additional keyword arguments to pass to the function.

    Returns:
        List[Tuple[Any, Any]]: A list of tuples containing the input element and the result of the function.

    Notes:
        The `max_workers` argument can be passed as a keyword argument to set the maximum number of worker threads in the thread pool executor.
        The `quiet` argument can be passed as a keyword argument to suppress the traceback logging for exceptions.
    """
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
    """
    Runs a function in parallel using ThreadPoolExecutor and returns the results in the same order as the input iterable.

    Args:
        exec_func (Callable): A function to run concurrently.
        iterable (Iterable): An iterable to run the function on.
        *func_args: Any additional arguments to pass to the function.
        **kwargs: Any additional keyword arguments to pass to the function.

    Returns:
        List[Any]: A list of results of the function, in the same order as the input iterable.

    Notes:
        The `max_workers` argument can be passed as a keyword argument to set the maximum number of worker threads in the thread pool executor.
        The `quiet` argument can be passed as a keyword argument to suppress the traceback logging for exceptions.
    """
    result = run_parallel_exec(
        exec_func, iterable := list(iterable), *func_args, **kwargs
    )
    result.sort(key=lambda x: iterable.index(x[0]))
    return [x[-1] for x in result]

def run_functions_in_parallel(
    functions: List[Callable],
    max_workers: int = 100,
    parallelism: Literal["thread", "process"] = "thread",
    prefix: str = "unknown",
    quiet: bool = False,
):
    """
    Runs a list of functions in parallel using ThreadPoolExecutor.

    Args:
        functions (List[Callable]): A list of functions to run concurrently.
        max_workers (int, optional): The maximum number of worker threads in the thread pool executor. Defaults to 100.
        parallelism ("thread", "process"): The type of parallelism to use. Defaults to "thread".
        prefix (str, optional): The prefix to use for the thread name. Defaults to "unknown". Only used if parallelism is "thread".
        quiet (bool, optional): If True, suppresses the traceback logging for exceptions. Defaults to False.

    Returns:
        List[Tuple[str, Any]]: A list of tuples containing the function name and the result of the function.
    """
    results: List[Tuple[str, Any]] = []
    max_workers = min(max_workers, len(functions))
    def pool_executor():
        if parallelism == "process":
            return concurrent.futures.ProcessPoolExecutor(max_workers=max_workers)
        elif parallelism == "thread":
            return concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers, thread_name_prefix=f"{prefix} | parallel_func | "
            )
    with pool_executor() as executor:
        # Map the functions to the executor and run them in parallel
        futures = {executor.submit(func): getattr(func, "__name__", None) for func in functions}
        for future in concurrent.futures.as_completed(futures):
            func_name = futures[future]
            try:
                results.append((func_name, future.result()))
            except Exception as exc:
                log_trace = exc if quiet else get_trace(exc, 3)
                logging.error(f"Got error while running parallel_exec: {func_name}: \n{log_trace}")
                results.append((func_name, exc))
    return results


def chunkify(lst: list, chunk_size: int = 40):
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size] 

def clean_name(
    name: str,
    replacements: dict[str, str] = {},
    replace_dot_with_next_capital: bool = True,
):
    for k, v in replacements.items():
        name = name.replace(k, v)

    col_name_parts = []
    
    for i, x in enumerate(name.split(".")):
        if i == 0:
            col_name_parts.append(x)
            continue
        if replace_dot_with_next_capital:
            col_name_parts.append(x[0].upper() + x[1:])
        
    return "".join(col_name_parts)
