# This file is part of HOMEctlx. Copyright (C) 2024 Christian Rauch.
# Distributed under terms of the GPL3 license.

"""
View-model for files.
"""

import base64
from copy import deepcopy
import re
import services.meta as m
import services.fileaccess as fa
from flask import session
from viewmodels import markdown


def ctl(dir:str=None, 
        file:str=None, 
        content:bool=None, 
        edit:bool=None,
        show:bool=False) -> list[m.view]:
    """ Starting point."""
    if show != False: return showx(0)
    if file != None:  return filex(file, dir, content, edit)
    else:             return directory(dir, content, edit)


def set_defaults():
    for kv in ({
        'dir': '/',
        'edit': False,
        'content': False,
        'st_idx': False}).items():
        if kv[0] not in session: session[kv[0]] = kv[1]


def directory(
        dir:str=None,
        content:bool=None,
        edit:bool=None,
        st_idx:int=None) -> list[m.view]:
    """ Directory related actions."""

    if dir != None:
        session['dir'] = fa.sanitize([dir])
        session['st_idx'] = 0
    if edit != None:    session['edit'] = edit in [True, "True"]
    if content != None: session['content'] = content in [True, "True"]
    if st_idx != None:  session['st_idx'] = max(int(st_idx), 0)
    set_defaults()

    files, dirs  = fa.list_files([session['dir']])

    forms = []

    form_dir = m.form(None, None, [], True, False, "small flex")

    # menu
    show_menu = m.execute_params("files/directory", 
        f"{'hide' if session['edit'] else 'show'} menu",
        { "content": session['content'] })
    show_menu.params['edit'] = not session['edit']
    form_dir.fields.append(show_menu)
        
    # content
    if len(files) > 0:
        show_media = m.execute_params("files/directory", 
        f"{'hide' if session['content'] else 'show'} media",
        { "edit": session['edit'] })
        show_media.params['content'] = not session['content']
        form_dir.fields.append(show_media)
        if session['content']:
            form_dir.fields.append(m.execute_params(
                "files/ctl", "presentation", { "show": True }))
        
    # add edit menu
    if len(form_dir.fields) > 0: 
        forms.append(form_dir)
    
    if session['edit']: forms += directory_edit_fields(files)

    # list sub directories
    if len(dirs) > 0 or session['dir'] != '/':
        dirs_content = []
        if session['dir'] != '/':
            dirs_content.append(m.dir("files/directory",
                fa.sanitize([session['dir'], '..']), "..", False, 0))
        for d in dirs:
            if session['edit']:
                meta = fa.read_directory_meta_data([session['dir'], d])
                locked = meta['readonly']
                cnt =  meta['files']
            else:
                locked = False
                cnt = 0
            dirs_content.append(m.dir("files/directory",
                session['dir'], d, locked, cnt))
        forms.append(m.form("d", "directories", dirs_content, True))

    # list files
    forms += directory_files(session['st_idx'])

    #if session['edit']:
    #    forms[0].fields.append(
    #        m.label(f"directory: share{session['dir']}".strip('/')))
        
    return [m.view("_body", f"share", forms),
            m.header([_path_triggers(session['dir'])])]


def directory_files(st_idx:int):
    """ Directory files."""
    files, dirs  = fa.list_files([session['dir']])
    session['st_idx'] = max(int(st_idx), 0)
    page_sz = 10
    files_sz = len(files)
    files = files[session['st_idx']:session['st_idx']+page_sz]
    forms = list()
    if len(files) > 0:
        pager_top = m.pager("files/directory_files", "st_idx", 
            session['st_idx'], page_sz, files_sz, "f", False)
        files_content = []
        if session['edit'] or session['content']:
            files_content.append(pager_top)
            files_content.append(m.label(f"{files_sz} files"))
        for f in files: 
            files_content += file_fields(f)
        pager_bottom = deepcopy(pager_top)
        pager_bottom.focus = session['edit'] or session['content']
        files_content.append(pager_bottom)
        forms.append(m.form("f", "files", files_content, True))
    return forms


def directory_edit_fields(files:list):
    """ Edit fields."""

    forms = list()
    files_choices = m.choice.makelist(files)

    # upload file
    form_ulfile = m.form(None, "upload file", [
            m.upload("upload", "select local files:"),
            m.text("rename", "", "rename (optional):"),
            m.execute("files/upload_file", "upload files")
        ], style='small')
    forms.append(form_ulfile)

    # create file
    form_mkfile = m.form(None, "create file", [
            m.text("file", "new", "name:"),
            m.text_big("content", "", "content:"),
            m.execute("files/create_file", "create text file")
        ], style='small')
    forms.append(form_mkfile)

    if len(files_choices) > 0:
        # delete file
        form_mvfile = m.form(None, "delete file", [
                m.select("file", files_choices, None, "file:"),
                m.execute("files/delete_file", "delete file",
                    confirm="Do you want to delete this file?")
            ], style='small')
        forms.append(form_mvfile)

        # edit file
        form_mkfile = m.form(None, "edit file", [
            m.select("file", files_choices, None, "file:"),
            m.execute("files/edit", "edit file")
        ], style='small')
        forms.append(form_mkfile)

        # move file
        form_mvfile = m.form(None, "move file", [
                m.select("file", files_choices, None, "old:"),
                m.text("file_new", "", "new:"),
                m.execute("files/move_file", "move file",
                    confirm="Do you want to move this file?")
            ], style='small')
        forms.append(form_mvfile)

    # create directory
    form_mkdir = m.form(None, "create directory", [
            m.text("dir_new", "new", "name:"),
            m.execute("files/create_directory", "create sub directory")
        ], style='small')
    forms.append(form_mkdir)

    # delete directory
    form_rmdir = m.form(None, "delete directory", [
        m.execute("files/delete_directory", "delete current directory", 
            confirm="Do you want to delete this directory?")
    ], style='small')
    forms.append(form_rmdir)

    # move directory
    form_mvdir = m.form(None, "move directory", [
            m.text("dir_new", session['dir'], "new:"),
            m.execute("files/move_directory", "move directory",
                confirm="Do you want to move this directory?")
        ], style='small')
    forms.append(form_mvdir)
    
    forms.append(m.form("", "", fields=[m.space(1)], table=False, style='small'))

    return forms


def filex(file:str, dir:str=None, content:bool=None, editx:bool=None):
    """ File related actions."""
    if editx != None:   session['edit'] = editx in ['True', True]
    if content != None: session['content'] = content in ['True', True]
    if dir != None:     session['dir'] = dir
    set_defaults()
    return [*edit(file), m.header([_path_triggers(session['dir'])])]


def file_fields(file:str):
    """ Content fields."""
    fields = []
    link = fa.sanitize([session['dir'], file])
    if session['edit'] or session['content']:
        meta = fa.read_file_meta_data([session['dir'], file])
    locked = session['edit'] and meta["readonly"]
    fields.append(m.file("files/edit",
        session['dir'], file, locked, link))
    if session['content']:
        _file_content(link, meta, fields, file)
        fields.append(m.space(1))
    return fields


def edit(file) -> list[m.form]:
    """ File edit commands."""
    forms = [m.form(None, None, [m.dir("files/directory", 
        fa.sanitize([session['dir']]), "..", False, 0)], True, False)] 

    file_hidden = m.hidden("file", file)

    files, _ = fa.list_files([session['dir']])
    link = fa.sanitize([session['dir'], file])
    download = m.download(link)

    meta = fa.read_file_meta_data([session['dir'], file])
    meta_info = m.label(
        f"last change: {meta['changed']} / bytes: {meta['size']}", "small")

    if not meta["is_text"] and not meta["is_markdown"]:

        fields = []
        if   meta["is_image"]:    fields.append(m.media(link, "image"))
        elif meta["is_video"]:    fields.append(m.media(link, "video"))
        elif meta["is_pdf"]:      fields.append(m.media(link, "pdf"))

        fields.append(download)
        fields.append(meta_info)
        forms.append(m.form("vf", "view content", fields, True))

    else:

        content = fa.read_file([session['dir'], file])
        
        forms.append(
            m.form("uf", "edit content", [
                file_hidden,
                m.text_big("content", content),
                meta_info,
                m.execute("files/update_file", "overwrite"),
            ], True))
        
        has_remove_and_import = not meta["is_markdown"] \
            and not fa.is_essential([session['dir'], file])

        if has_remove_and_import:

            lines   = fa.clean_lines(content)

            forms.append(
                m.form("rl", "remove entries", [
                    file_hidden,
                    m.select_many("remove", m.choice.makelist(lines), []),
                    m.execute("files/remove_entries", "remove")
                ]))
            
            files, _       = fa.list_files([session['dir']], True)
            files          = [f for f in files \
                if f != file and fa.read_file_meta_data([session['dir'], f])["is_text"]]
            files_template = [f for f in files if f.startswith("template/")]
            files_rest     = [f for f in files if f not in files_template]
            files          = [*files_template, * files_rest]

            if len(files) > 0:
                forms.append(
                    m.form("t", "import entries", [
                        file_hidden,
                        m.select_many("templates", m.choice.makelist(files), []),
                        m.execute("files/template"),
                    ]))
            
    if not fa.is_essential([session['dir'], file]):
        forms.append(
            m.form("mf", "move file", [
                file_hidden,
                m.text("file_new", file),
                m.execute("files/move_file", "move")
            ]))
        forms.append(
            m.form("df", "delete file", [
                file_hidden,
                m.execute("files/delete_file", "delete",
                    confirm="Do you want to delete this file?")
            ]))
    
    path = f"share/{session['dir'].strip('/')}/{file}"
    forms[0].fields.append(m.label(f"file: {path}", 'small'))
    return [m.view("_body", f"share", forms)]


def _file_content(link:str, meta:dict, fields:list, file:str):
    """ File content."""
    if not meta["is_text"]:
        if   meta["is_image"]:    fields.append(m.media(link, "image"))
        elif meta["is_video"]:    fields.append(m.media(link, "video"))
        elif meta["is_pdf"]:      fields.append(m.media(link, "pdf"))
        elif meta["is_markdown"]: fields.append(markdown.for_file(session['dir'], file))
    else:
        text = fa.read_file([session['dir'], file])
        fields.append(m.text_big_ro('', text))


def showx(file_idx:str):
    """ Show."""
    file_idx = int(file_idx)
    fields = []
    files = fa.list_files([session['dir']])
    if file_idx >= len(files[0]): file_idx = 0
    elif file_idx < 0: file_idx = len(files[0]) -1
    file = files[0][file_idx]
    link = fa.sanitize([session['dir'], file])
    meta = fa.read_file_meta_data([session['dir'], file])
    _file_content(link, meta, fields, file)
    if len(fields) == 0: fields.append(m.label(file))
    else: fields[0].style = "fill"
    forms = [m.form(None, "", fields, True, False)]
    fields_header = [m.show("files/showx", "file_idx", 
        file_idx, len(files[0]), file, "files/ctl", link)]
    return [m.view("_body", None, forms), m.header(fields_header, style="flex")]


def template(file:str, templates:list[str]):
    """ Fills the file with the lines contained in other files."""
    lines = [l for f in templates for l in \
             fa.clean_lines(fa.read_file([session['dir'], f]))]
    lines = m.choice.makelist(lines)
    forms = [
        m.form(
            "ae", "add entries", [
                m.hidden("file", file),
                m.select_many("lines", lines, []),
                m.execute("files/add_entries", "append")
            ], True)
    ]

    return [m.view("_body", "share", forms)]


def add_entries(file:str, lines:list=[]):
    """ Add lines."""
    if len(lines) > 0: 
        content = "\n".join(lines)
        if not fa.read_file([session['dir'], file]).endswith("\n"):
            content = f"\n{content}"
        fa.update_file([session['dir'], file], content, False)
    return ctl(session['dir'], file)


def remove_entries(file:str, remove:list[str]):
    """ Remove entries."""
    if len(remove) > 0:
        fa.clean_file([session['dir'], file], lambda line: line in remove)
    return ctl(session['dir'], file)


def update_file(file:str, content:list):
    """ Edit file."""
    fa.update_file([session['dir'], file], content, True)
    return ctl(session['dir'], file)


def create_file(file:str, content:str):
    """ Create file."""
    if file == "": return [m.error("No file name specified.")]
    fa.create_file([session['dir'], file], content)
    return ctl(session['dir'], file)


def create_directory(dir_new:str=None):
    """ Create directory."""
    fa.create_directory([session['dir'], dir_new])
    return directory(fa.sanitize([session['dir'], dir_new]))


def delete_file(file:str):
    """ Delete file."""
    fa.delete_file([session['dir'], file])
    return directory()


def delete_directory():
    """ Delete file."""
    fa.delete_directory([session['dir']])
    return directory("/".join(session['dir'].split("/")[:-1]))


def move_file(file:str, file_new:str):
    """ Move file."""
    if file_new == "": return [m.error("No file name specified.")]
    fa.move_file([session['dir'], file], [session['dir'], file_new])
    return directory()


def move_directory(dir_new:str):
    """ Move directory."""
    if dir_new == "": return [m.error("No file name specified.")]
    fa.move_directory([session['dir']], [dir_new])
    return directory(dir_new)


def upload_file(rename:str, upload):
    """ Saves an uploaded file."""
    names  = upload["names"]
    for i, dataurl in enumerate(upload["bytes"]):
        bytes = base64.b64decode(dataurl.split(",")[1])
        if rename.strip() != "":
            name = rename
            if len(upload["bytes"]) > 1:
                name = f"{name}-{i+1}"
            if name.find(".") < 0 and names[i].find(".") > 0:
                name += "." + names[i].split(".")[-1]
        else:
            name = names[i]
        fa.create_file([session['dir'], name], bytes)
    return directory()


def _path_triggers(path:str) -> m.path:
    """ Returns the path parts as triggers for navigation."""
    parts = [p for p in path.split("/") if p != ""]
    link = ''
    choices = list[m.choice]()
    choices.append(m.choice('/', 'share', True))
    for p in parts:
        link = fa.sanitize([link, p])
        choice = m.choice(link, f'/ {p}')
        choices.append(choice)
    return m.path("files/directory", "dir", choices)
