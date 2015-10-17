#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   PyNAM -- Python Neural Associative Memory Simulator and Evaluator
#   Copyright (C) 2015 Andreas Stöckel
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Contains various utility methods used in various places of the program.
"""

import re
import json
import numpy as np
import pynnless.pynnless_utils

def initialize_seed(seed, seq=1):
    """
    Initializes the numpy random number generator seed with the given seed
    value. The seed value may be None, in which case no changes the the numpy
    seed are made. Returns the old random generator state or None if no change
    was made.
    """
    if seed is None:
        return None
    old_state = np.random.get_state()
    np.random.seed(long(seed * (seq + 1)) % long(1 << 30))
    return old_state

def finalize_seed(old_state):
    """
    Restores the numpy random seed to its old value, or does nothin if the given
    value is "None".
    """
    if (old_state != None):
        np.random.set_state(old_state)

# Regular expression for comments
# See http://www.lifl.fr/~damien.riquet/parse-a-json-file-with-comments.html
JSON_COMMENT_RE = re.compile(
    '(^)?[^\S\n]*/(?:\*(.*?)\*/[^\S\n]*|/[^\n]*)($)?',
    re.DOTALL | re.MULTILINE
)

def parse_json_with_comments(stream):
    """
    Parse a JSON stream, allow JavaScript like comments. Adapted from
    http://www.lifl.fr/~damien.riquet/parse-a-json-file-with-comments.html
    """
    content = ''.join(stream.readlines())
    match = JSON_COMMENT_RE.search(content)
    while match:
        content = content[:match.start()] + content[match.end():]
        match = JSON_COMMENT_RE.search(content)
    return json.loads(content)

# Forward the "init_key" method
init_key = pynnless.pynnless_utils.init_key
