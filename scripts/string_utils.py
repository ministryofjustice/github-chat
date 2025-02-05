import datetime as dt
import re
import warnings

from scripts.constants import RESP_EVALUATION_PROMPT, RESPONSE_TEMPLATE


def format_results(
    db_result:dict,
    template:str=RESPONSE_TEMPLATE
    ) -> str:
    return template.format(
        org_nm = db_result.get("org_nm"),
        repo_nm=db_result.get("repo_nm"),
        repo_desc=db_result.get("repo_desc"),
        url=db_result.get("html_url"),
        is_private=db_result.get("is_private"),
        is_archived=db_result.get("is_archived"),
        updated_at=db_result.get("updated_at"),
        programming_language=db_result.get("programming_language"),
        distance=db_result.get("distance"),
        model_summary=db_result.get("model_summary"),
        )

def format_evaluation_response(
    usr_prompt:str,
    res:str,
    template:str=RESP_EVALUATION_PROMPT
    ) -> str:
    return template.format(results=res, user_prompt=usr_prompt)


def remove_invisible_unicode(some_str:str, debug:bool = False) -> str:
    warnings.simplefilter("always", UserWarning)
    hidden_pattern = re.compile(r"[\U000E0000-\U000E007F]")
    hits = hidden_pattern.findall(some_str)
    if hits:
        decoded_message = "".join(
            chr(ord(char) - 0xE0000 + 0x20) for char in hits)
        warnings.warn(
            f" Hidden message was removed: {decoded_message}", UserWarning)
        cleaned = hidden_pattern.sub("", some_str)
        return cleaned
    else:
        if debug:
            print("No hidden unicode tags detected")
        return some_str


def escape_tags(some_str:str) -> str:
    return some_str.replace("<", r"/<").replace(">", r"/>")


def sanitise_string(s:str) -> str:
    s = remove_invisible_unicode(s)
    s = escape_tags(s)
    return s


def get_vintage_from_str(s:str) -> str:
    date_pat = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}_\d{2}_\d{2}.\d{6}")
    match = date_pat.search(s)
    vintage = match[0].replace("_", ":")
    _dt = dt.datetime.fromisoformat(vintage)
    return _dt.strftime("%A, %d %B, %Y at %H:%M")
    
