import json
import logging
import os
import re
from typing import Optional

from utils.cache.timed import timed_lru_cache
from versions.v2 import overrides
from versions.v2.schema import TGroup, Teacher, TTeacher, Subject, Classroom


def canonicalize(x): return x.replace("_", " ").lower()


@timed_lru_cache(60*60)
def get_overrides(name: str):
    path = os.path.join("versions/v2/overrides/", name + ".json")
    if not os.path.exists(path): return {}
    with open(path, "r") as fh:
        return json.load(fh)


def prep_subject(x: Subject, ctx):
    if not x:
        return ""
    if x.name in (ovr := get_overrides("subject")):
        return ovr[x.name]
    return canonicalize(x.name)


def prep_subject_short(x: Subject, ctx):
    if not x:
        return ""
    if x.short in (ovr := get_overrides("subject_short")):
        return ovr[x.short]
    return canonicalize(x.short)


def prep_classroom(x: Classroom, ctx):
    if not x:
        return ""
    ovr = get_overrides("classroom")
    if x.short in ovr:
        return ovr[x.short]
    return x.short


def prep_group(x: str) -> Optional[TGroup]:
    if not x:
        return None
    if x in (ovr := get_overrides("group")):
        return TGroup(name=ovr[x], short=ovr[x], raw=x)

    if reg := re.match(r"([1-4])([a-zA-Z]|DSD)([1-4])?kl([1-4])?-(\d+)", x):
        cnt, tok, class1, class2, idx = reg.groups()
        # TODO: Use proper group code instead of idx
        cnt, idx, class_ = int(cnt), int(idx), int(class1 or class2)
        if tok.lower() == "dsd":
            return TGroup(name=f"DSD ({idx}) - kl. {class_}", short=f"{class_}DSD ({idx})", raw=x)
        name = {
            "a": "angielski",
            "n": "niemiecki",
            "f": "francuski",
            "h": "hiszpański",
            "r": "rosyjski",
            "w": "włoski"
        }[tok.lower()]
        type_ = ["mały", "duży"][tok.isupper()]
        return TGroup(
            name=f"{name} {type_} ({idx}) - kl. {class_}",
            short=f"{class_}{tok} ({idx})",
            raw=x
        )
    name = canonicalize(x)
    return TGroup(name=name, short=name, raw=x)


def prep_teacher(x: Teacher) -> TTeacher:
    if not x:
        return TTeacher(name="", short="")
    ovr = overrides.parse()
    if (key := x.short.lower()) in ovr:
        return ovr[key]
    logging.info(f"No name expansion for teacher with key \"{x.short}\"")
    return TTeacher(name=x.short, short=x.short)  # Don't canonicalize
