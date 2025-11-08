# This file is part of HOMEctlx. Copyright (C) 2024 Christian Rauch.
# Distributed under terms of the GPL3 license.

"""
View-model for markdown.
"""

import logging
import re
import services.meta as m
import services.fileaccess as fa
from flask import session

from typing import Generator

def for_str(content: str, recess: bool = True) -> m.markdown:
    """ Convert a markdown string to a uielement. """

    sectionsx = [s for s in re.split(r'(?m)(?=^# )', content.strip()) if s.strip()]
    sections = list()

    for s in sectionsx:

        fields = []
        lines = s.strip().split("\n")

        for l in lines:

            if l.startswith("#"):
                order = 0
                for char in l:
                    if char == '#': order += 1
                    else: break
                fields.append(m.title(l[order:].strip(), order))
            else:
                links = re.findall(r'\[(.*?)\]\((.*?)\)', l)
                prev_idx = 0
                for link in links:
                    replace = f"[{link[0]}]({link[1]})"
                    index = l.find(replace, prev_idx)
                    if index != -1:
                        if prev_idx != index:
                            fields.append(m.label(l[prev_idx:index]))
                        src = link[1].strip()
                        if src.startswith('embed:'):
                            fields.append(m.embed(src[6:], link[0].strip()))
                        else:
                            fields.append(m.link(src, link[0].strip()))
                        prev_idx = index + len(replace)
                
                if prev_idx < len(l):
                    fields.append(m.label(l[prev_idx:]))

            fields.append(m.space(1))
        fields.append(m.space(1))

        sections.append(m.section(fields))
    
    return m.markdown(sections, recess)


def for_file(dir:str, file:str, recess:bool=True) -> m.uielement:
    """ Markdown fields from a file. """
    try:
        content = fa.read_file([dir, file])
        return for_str(content, recess)
    
    except Exception as e:
        logging.warning(f"File '{file}' in '{dir}' cannot be interpreted: {e}")
        return m.space(1)
