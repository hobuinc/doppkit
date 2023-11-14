
# header parse code inherited from werkzeug
# https://github.com/pallets/werkzeug/blob/76b049dd45fd072fb62a54bccc0e8d513b03f4d8/src/werkzeug/http.py
# SPDX-License-Identifier: BSD-3-Clause

import re
from typing import Optional
from urllib.parse import unquote

# https://httpwg.org/specs/rfc9110.html#parameter
_parameter_re = re.compile(
    r"""
    # don't match multiple empty parts, that causes backtracking
    \s*;\s*  # find the part delimiter
    (?:
        ([\w!#$%&'*+\-.^`|~]+)  # key, one or more token chars
        =  # equals, with no space on either side
        (  # value, token or quoted string
            [\w!#$%&'*+\-.^`|~]+  # one or more token chars
        |
            "(?:\\\\|\\"|.)*?"  # quoted string, consuming slash escapes
        )
    )?  # optionally match key=value, to account for empty parts
    """,
    re.ASCII | re.VERBOSE,
)
# https://www.rfc-editor.org/rfc/rfc2231#section-4
_charset_value_re = re.compile(
    r"""
    ([\w!#$%&*+\-.^`|~]*)'  # charset part, could be empty
    [\w!#$%&*+\-.^`|~]*'  # don't care about language part, usually empty
    ([\w!#$%&'*+\-.^`|~]+)  # one or more token chars with percent encoding
    """,
    re.ASCII | re.VERBOSE,
)
# https://www.rfc-editor.org/rfc/rfc2231#section-3
_continuation_re = re.compile(r"\*(\d+)$", re.ASCII)

def parse_options_header(value: Optional[str]) -> tuple[str, dict[str, str]]:
    """Parse a header that consists of a value with ``key=value`` parameters separated
    by semicolons ``;``. For example, the ``Content-Type`` header.

    .. code-block:: python

        parse_options_header("text/html; charset=UTF-8")
        ('text/html', {'charset': 'UTF-8'})

        parse_options_header("")
        ("", {})

    This is the reverse of :func:`dump_options_header`.

    This parses valid parameter parts as described in
    `RFC 9110 <https://httpwg.org/specs/rfc9110.html#parameter>`__. Invalid parts are
    skipped.

    This handles continuations and charsets as described in
    `RFC 2231 <https://www.rfc-editor.org/rfc/rfc2231#section-3>`__, although not as
    strictly as the RFC. Only ASCII, UTF-8, and ISO-8859-1 charsets are accepted,
    otherwise the value remains quoted.

    Clients may not be consistent in how they handle a quote character within a quoted
    value. The `HTML Standard <https://html.spec.whatwg.org/#multipart-form-data>`__
    replaces it with ``%22`` in multipart form data.
    `RFC 9110 <https://httpwg.org/specs/rfc9110.html#quoted.strings>`__ uses backslash
    escapes in HTTP headers. Both are decoded to the ``"`` character.

    Clients may not be consistent in how they handle non-ASCII characters. HTML
    documents must declare ``<meta charset=UTF-8>``, otherwise browsers may replace with
    HTML character references, which can be decoded using :func:`html.unescape`.

    :param value: The header value to parse.
    :return: ``(value, options)``, where ``options`` is a dict

    .. versionchanged:: 2.3
        Invalid parts, such as keys with no value, quoted keys, and incorrectly quoted
        values, are discarded instead of treating as ``None``.

    .. versionchanged:: 2.3
        Only ASCII, UTF-8, and ISO-8859-1 are accepted for charset values.

    .. versionchanged:: 2.3
        Escaped quotes in quoted values, like ``%22`` and ``\\"``, are handled.

    .. versionchanged:: 2.2
        Option names are always converted to lowercase.

    .. versionchanged:: 2.2
        The ``multiple`` parameter was removed.

    .. versionchanged:: 0.15
        :rfc:`2231` parameter continuations are handled.

    .. versionadded:: 0.5
    """
    if value is None:
        return "", {}

    value, _, rest = value.partition(";")
    value = value.strip()
    rest = rest.strip()

    if not value or not rest:
        # empty (invalid) value, or value without options
        return value, {}

    rest = f";{rest}"
    options: dict[str, str] = {}
    encoding: Optional[str] = None
    continued_encoding: Optional[str] = None

    for pk, pv in _parameter_re.findall(rest):
        if not pk:
            # empty or invalid part
            continue

        pk = pk.lower()

        if pk[-1] == "*":
            # key*=charset''value becomes key=value, where value is percent encoded
            pk = pk[:-1]
            match = _charset_value_re.match(pv)

            if match:
                # If there is a valid charset marker in the value, split it off.
                encoding, pv = match.groups()
                # This might be the empty string, handled next.
                encoding = encoding.lower()

            # No charset marker, or marker with empty charset value.
            if not encoding:
                encoding = continued_encoding

            # A safe list of encodings. Modern clients should only send ASCII or UTF-8.
            # This list will not be extended further. An invalid encoding will leave the
            # value quoted.
            if encoding in {"ascii", "us-ascii", "utf-8", "iso-8859-1"}:
                # Continuation parts don't require their own charset marker. This is
                # looser than the RFC, it will persist across different keys and allows
                # changing the charset during a continuation. But this implementation is
                # much simpler than tracking the full state.
                continued_encoding = encoding
                # invalid bytes are replaced during unquoting
                pv = unquote(pv, encoding=encoding)

        # Remove quotes. At this point the value cannot be empty or a single quote.
        if pv[0] == pv[-1] == '"':
            # HTTP headers use slash, multipart form data uses percent
            pv = pv[1:-1].replace("\\\\", "\\").replace('\\"', '"').replace("%22", '"')

        match = _continuation_re.search(pk)

        if match:
            # key*0=a; key*1=b becomes key=ab
            pk = pk[: match.start()]
            options[pk] = options.get(pk, "") + pv
        else:
            options[pk] = pv

    return value, options
