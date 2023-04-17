import os
import importlib
import logging
from http import HTTPStatus

import requests
import simplejson
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("prefix", help="Snippets prefix to process. Like 'minimal_api', 'relationship_', etc")
parser.add_argument("-v", "--verbose", help="set logging level to DEBUG", action="store_true")

log = logging.getLogger(__name__)

SNIPPETS_DIR = "snippets"
SORT_KEYS_ON_DUMP = True
SNIPPET_RESULT_POSTFIX = "_result"
REMOVE_PYTHON_SNIPPET = True


SORTING_ORDER = [
    "create",
    "get",
    "patch",
    "update",  # like patch
    "delete",
]

ORDER_POS = {
    i: v for i, v in enumerate(SORTING_ORDER)
}


class StrOrderCRUD:
    def __init__(self, inner):
        self.inner = inner

    def __lt__(self, other):
        index_1 = -1
        index_2 = -1
        for index, name in ORDER_POS.items():
            substring = f"__{name}_"
            if substring in self.inner:
                index_1 = index
            if substring in other.inner:
                index_2 = index

        if index_1 != index_2:
            return index_1 < index_2

        return self.inner < other.inner


def run_request_for_module(module_name: str):
    log.info("Start processing %r", module_name)

    module_full_name = ".".join((SNIPPETS_DIR, module_name))
    log.debug("import module %s", module_full_name)
    module = importlib.import_module(module_full_name)

    log.info("Process module %s", module)
    response: requests.Response = module.response
    log.info("Response %s", response)

    http_response_text = []

    response_reason = (response.reason or "")
    if response.status_code != HTTPStatus.OK:
        response_reason = response_reason.title()

    http_response_text.append(
        # "HTTP/1.1 201 Created"
        "{} {} {}".format(
            "HTTP/1.1",
            response.status_code,
            response_reason,
        )
    )

    http_response_text.append(
        "{}: {}".format(
            "Content-Type",
            response.headers.get('content-type'),
        )
    )
    http_response_text.append("")

    http_response_text.append(
        simplejson.dumps(
            response.json(),
            sort_keys=SORT_KEYS_ON_DUMP,
            indent=2,
        ),
    )

    http_response_text.append("")

    result_text = "\n".join(http_response_text)
    log.debug("Result text:\n%s", result_text)

    result_file_name = "/".join((SNIPPETS_DIR, module_name + SNIPPET_RESULT_POSTFIX))
    with open(result_file_name, "w") as f:
        res = f.write(result_text)
        log.info("Wrote text (%s) to %r", res, result_file_name)

    log.info("Processed %r", module_name)


def add_help_lines(lines: list, module_name: str) -> None:
    """

    Append help lines to create smth like this:

    '''

    Request:

    .. literalinclude:: ./http_snippets/snippets/minimal_api__create_person
      :language: HTTP

    Response:

    .. literalinclude:: ./http_snippets/snippets/minimal_api__create_person_result
      :language: HTTP

    '''

    """
    literalinclude_file =  ".. literalinclude:: ./http_snippets/snippets/" + module_name
    rst_language_http    = "  :language: HTTP"

    lines.append("")
    lines.append("Request:")
    lines.append("")
    lines.append(literalinclude_file)
    lines.append(rst_language_http)
    lines.append("")
    lines.append("Response:")
    lines.append("")
    lines.append(literalinclude_file + SNIPPET_RESULT_POSTFIX)
    lines.append(rst_language_http)
    lines.append("")


def main():
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    log.warning("Starting")

    available_modules = os.listdir(SNIPPETS_DIR)
    log.debug("all available snippets: %s", available_modules)
    modules_to_process = list(
        filter(lambda name: name.startswith(args.prefix), available_modules)
    )
    modules_to_process.sort(key=StrOrderCRUD)
    log.warning("modules to process (with order): %s", modules_to_process)

    result_help_text = []
    result_help_text.append("=" * 30)

    for module_file in modules_to_process:
        if module_file.endswith(".py"):
            module_name = module_file[:-3]
            try:
                run_request_for_module(module_name)
            except Exception:
                log.exception("Could not process module %r, skipping", module_file)
            else:
                if REMOVE_PYTHON_SNIPPET:
                    os.unlink("/".join((SNIPPETS_DIR, module_file)))
                add_help_lines(result_help_text, module_name)

    result_help_text.append("=" * 30)
    result_help_text.append("")

    print("\n".join(result_help_text))

    log.warning("Done")


if __name__ == "__main__":
    main()
