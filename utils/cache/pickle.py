from datetime import datetime as dt
import json
import os
from pathlib import Path
import pickle
from typing import Callable, Union
from functools import partial

sentinel = object()

def arg_stringify(*args, **kwargs) -> str:
	key = (*args, "$", *sorted(kwargs.items()))
	if len(args) == 0 and len(kwargs) == 0:
		return ""
	kw = "#".join(json.dumps(x, default=str, separators=("",""))[1:-1] for x in sorted(kwargs.items()))
	if kw: kw = "$" + kw
	return json.dumps(args, default=str, separators=("",""))[1:-1] + kw

def pickle_cache(timeout: Union[int, None] = 900,
	             arg_transform_fn: Callable[..., str] = arg_stringify,
	             cache_directory: Path = Path("./cache/"),
				 timeout_rule: Union[Callable[..., bool], None] = None,
				 timeout_env: Union[str, None] = "PKLCACHE_NO_TIMEOUT"):
	timeout = timeout or 1e18
	os.makedirs(cache_directory, exist_ok=True)
	def transformer(fn: Callable[..., str], *args, **kwargs):
		ret = fn(*args, **kwargs)
		if ret == "":
			return ""
		else:
			return "@" + ret
	arg_transform_fn = partial(transformer, arg_transform_fn)

	def outer(func):
		def inner(*args, **kwargs):
			arghash = arg_transform_fn(*args, **kwargs)
			fname = cache_directory / ("%s%s.pkl" % (func.__name__, arghash))
			os.makedirs(cache_directory, exist_ok=True)
			if fname.exists():
				if os.getenv(timeout_env):
					n_timeout = 0
				elif timeout_rule is not None:
					n_timeout = timeout_rule(*args, **kwargs)
				else:
					n_timeout = timeout
				now = dt.now()
				mtime = dt.fromtimestamp(fname.stat().st_mtime)
				is_timeout = (now - mtime).seconds <= n_timeout
				if is_timeout:
					with fname.open("rb") as f:
						ret = pickle.load(f)
					return ret
			
			ret = func(*args, **kwargs)
			f = open(fname, "wb")
			pickle.dump(ret, f)
			f.close()
			return ret
		return inner
	return outer
