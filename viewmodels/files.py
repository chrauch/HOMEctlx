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
import services.state as state
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
    for key, default in {
        'files.dir': '/',
        'files.edit': False,
        'files.content': False,
        'files.st_idx': 0}.items():
        if state.get(key) is None:
            state.set(key, default)


def directory(
        dir:str=None,
        content:bool=None,
        edit:bool=None,
        st_idx:int=None) -> list[m.view]:
    """ Directory related actions."""

    if dir != None:
        state.set('files.dir', fa.sanitize([dir]))
        state.set('files.st_idx', 0)
    if edit != None:    state.set('files.edit', edit in [True, "True"])
    if content != None: state.set('files.content', content in [True, "True"])
    if st_idx != None:  state.set('files.st_idx', max(int(st_idx), 0))
    set_defaults()

    curr_dir = state.get('files.dir', '/')
    
    # Check if directory exists, if not go to root
    try:
        files, dirs  = fa.list_files([curr_dir])
    except:
        # Directory doesn't exist, reset to root
        curr_dir = '/'
        state.set('files.dir', curr_dir)
        state.set('files.st_idx', 0)
        files, dirs  = fa.list_files([curr_dir])

    curr_edit = state.get('files.edit', False) in [True, "True"]
    curr_content = state.get('files.content', False) in [True, "True"]
    curr_st_idx = int(state.get('files.st_idx', 0))
    
    # Validate st_idx is within bounds
    if curr_st_idx < 0 or curr_st_idx >= len(files):
        curr_st_idx = 0
        state.set('files.st_idx', 0)
    
    forms = []

    form_dir = m.form(None, None, [], True, False, "small flex")

    # menu
    show_menu = m.execute_params("files/directory", 
        f"{'hide' if curr_edit else 'show'} menu",
        { "content": curr_content })
    show_menu.params['edit'] = not curr_edit
    form_dir.fields.append(show_menu)
        
    # content
    if len(files) > 0:
        show_media = m.execute_params("files/directory", 
        f"{'hide' if curr_content else 'show'} media",
        { "edit": curr_edit })
        show_media.params['content'] = not curr_content
        form_dir.fields.append(show_media)
        if curr_content:
            form_dir.fields.append(m.execute_params(
                "files/ctl", "presentation", { "show": True }))
        
    # add edit menu
    if len(form_dir.fields) > 0: 
        forms.append(form_dir)
    
    if curr_edit: forms += directory_edit_fields(files)

    # list sub directories
    if len(dirs) > 0 or curr_dir != '/':
        dirs_content = []
        if curr_dir != '/':
            dirs_content.append(m.dir("files/directory",
                fa.sanitize([curr_dir, '..']), "..", False, 0))
        for d in dirs:
            if curr_edit:
                meta = fa.read_directory_meta_data([curr_dir, d])
                locked = meta['readonly']
                cnt =  meta['files']
            else:
                locked = False
                cnt = 0
            dirs_content.append(m.dir("files/directory",
                curr_dir, d, locked, cnt))
        forms.append(m.form("d", "directories", dirs_content, True))

    # list files
    forms += directory_files(curr_st_idx)

    #if curr_edit:
    #    forms[0].fields.append(
    #        m.label(f"directory: share{curr_dir}".strip('/')))
        
    return [m.view("_body", f"share", forms),
            m.header([_path_triggers(curr_dir)])]


def directory_files(st_idx:int):
    """ Directory files."""
    curr_dir = state.get('files.dir', '/')
    files, dirs  = fa.list_files([curr_dir])
    
    # Validate and set st_idx
    st_idx = max(int(st_idx), 0)
    files_sz = len(files)
    page_sz = 10
    
    # Ensure st_idx is within valid range
    if st_idx >= files_sz and files_sz > 0:
        st_idx = 0
    
    state.set('files.st_idx', st_idx)
    curr_st_idx = st_idx
    files = files[curr_st_idx:curr_st_idx+page_sz]
    forms = list()
    if len(files) > 0:
        curr_edit = state.get('files.edit', False) in [True, "True"]
        curr_content = state.get('files.content', False) in [True, "True"]
        pager_top = m.pager("files/directory_files", "st_idx", 
            curr_st_idx, page_sz, files_sz, "f", False)
        files_content = []
        if curr_edit or curr_content:
            files_content.append(pager_top)
            files_content.append(m.label(f"{files_sz} files"))
        for f in files: 
            files_content += file_fields(f)
        pager_bottom = deepcopy(pager_top)
        pager_bottom.focus = curr_edit or curr_content
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
    curr_dir = state.get('files.dir', '/')
    form_mvdir = m.form(None, "move directory", [
            m.text("dir_new", curr_dir, "new:"),
            m.execute("files/move_directory", "move directory",
                confirm="Do you want to move this directory?")
        ], style='small')
    forms.append(form_mvdir)
    
    forms.append(m.form("", "", fields=[m.space(1)], table=False, style='small'))

    return forms


def filex(file:str, dir:str=None, content:bool=None, editx:bool=None):
    """ File related actions."""
    if editx != None:   state.set('files.edit', editx in ['True', True])
    if content != None: state.set('files.content', content in ['True', True])
    if dir != None:     state.set('files.dir', dir)
    set_defaults()
    curr_dir = state.get('files.dir', '/')
    return [*edit(file), m.header([_path_triggers(curr_dir)])]


def file_fields(file:str):
    """ Content fields."""
    curr_dir = state.get('files.dir', '/')
    curr_edit = state.get('files.edit', False) in [True, "True"]
    curr_content = state.get('files.content', False) in [True, "True"]
    fields = []
    link = fa.sanitize([curr_dir, file])
    if curr_edit or curr_content:
        meta = fa.read_file_meta_data([curr_dir, file])
    locked = curr_edit and meta["readonly"]
    fields.append(m.file("files/edit",
        curr_dir, file, locked, link))
    if curr_content:
        _file_content(link, meta, fields, file)
        fields.append(m.space(1))
    return fields


def edit(file) -> list[m.form]:
    """ File edit commands."""
    curr_dir = state.get('files.dir', '/')
    forms = [m.form(None, None, [m.dir("files/directory", 
        fa.sanitize([curr_dir]), "..", False, 0)], True, False)] 

    file_hidden = m.hidden("file", file)

    files, _ = fa.list_files([curr_dir])
    link = fa.sanitize([curr_dir, file])
    download = m.download(link)

    meta = fa.read_file_meta_data([curr_dir, file])
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

        content = fa.read_file([curr_dir, file])
        
        forms.append(
            m.form("uf", "edit content", [
                file_hidden,
                m.text_big("content", content),
                meta_info,
                m.execute("files/update_file", "overwrite"),
            ], True))
        
        has_remove_and_import = not meta["is_markdown"] \
            and not fa.is_essential([curr_dir, file])

        if has_remove_and_import:

            lines   = fa.clean_lines(content)

            forms.append(
                m.form("rl", "remove entries", [
                    file_hidden,
                    m.select_many("remove", m.choice.makelist(lines), []),
                    m.execute("files/remove_entries", "remove")
                ]))
            
            files, _       = fa.list_files([curr_dir], True)
            files          = [f for f in files \
                if f != file and fa.read_file_meta_data([curr_dir, f])["is_text"]]
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
            
    if not fa.is_essential([curr_dir, file]):
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
    
    path = f"share/{curr_dir.strip('/')}/{file}"
    forms[0].fields.append(m.label(f"file: {path}", 'small'))
    return [m.view("_body", f"share", forms)]


def _file_content(link:str, meta:dict, fields:list, file:str):
    """ File content."""
    curr_dir = state.get('files.dir', '/')
    if not meta["is_text"]:
        if   meta["is_image"]:    fields.append(m.media(link, "image"))
        elif meta["is_video"]:    fields.append(m.media(link, "video"))
        elif meta["is_pdf"]:      fields.append(m.media(link, "pdf"))
        elif meta["is_markdown"]: fields.append(markdown.for_file(curr_dir, file))
    else:
        text = fa.read_file([curr_dir, file])
        fields.append(m.text_big_ro('', text))


def showx(file_idx:str):
    """ Show."""
    curr_dir = state.get('files.dir', '/')
    file_idx = int(file_idx)
    fields = []
    files = fa.list_files([curr_dir])
    if file_idx >= len(files[0]): file_idx = 0
    elif file_idx < 0: file_idx = len(files[0]) -1
    file = files[0][file_idx]
    link = fa.sanitize([curr_dir, file])
    meta = fa.read_file_meta_data([curr_dir, file])
    _file_content(link, meta, fields, file)
    if len(fields) == 0: fields.append(m.label(file))
    else: fields[0].style = "fill"
    forms = [m.form(None, "", fields, True, False)]
    fields_header = [m.show("files/showx", "file_idx", 
        file_idx, len(files[0]), file, "files/ctl", link)]
    return [m.view("_body", None, forms), m.header(fields_header, style="flex")]


def template(file:str, templates:list[str]):
    """ Fills the file with the lines contained in other files."""
    curr_dir = state.get('files.dir', '/')
    lines = [l for f in templates for l in \
             fa.clean_lines(fa.read_file([curr_dir, f]))]
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
    curr_dir = state.get('files.dir', '/')
    if len(lines) > 0: 
        content = "\n".join(lines)
        if not fa.read_file([curr_dir, file]).endswith("\n"):
            content = f"\n{content}"
        fa.update_file([curr_dir, file], content, False)
    return ctl(curr_dir, file)


def remove_entries(file:str, remove:list[str]):
    """ Remove entries."""
    curr_dir = state.get('files.dir', '/')
    if len(remove) > 0:
        fa.clean_file([curr_dir, file], lambda line: line in remove)
    return ctl(curr_dir, file)


def update_file(file:str, content:list):
    """ Edit file."""
    curr_dir = state.get('files.dir', '/')
    fa.update_file([curr_dir, file], content, True)
    return [*ctl(curr_dir, file), m.notification(f"File {file} saved.")]


def create_file(file:str, content:str):
    """ Create file."""
    curr_dir = state.get('files.dir', '/')
    if file == "": return [m.error("No file name specified.")]
    fa.create_file([curr_dir, file], content)
    return ctl(curr_dir, file)


def create_directory(dir_new:str=None):
    """ Create directory."""
    curr_dir = state.get('files.dir', '/')
    fa.create_directory([curr_dir, dir_new])
    return directory(fa.sanitize([curr_dir, dir_new]))


def delete_file(file:str):
    """ Delete file."""
    curr_dir = state.get('files.dir', '/')
    fa.delete_file([curr_dir, file])
    return directory()


def delete_directory():
    """ Delete file."""
    curr_dir = state.get('files.dir', '/')
    fa.delete_directory([curr_dir])
    return directory("/".join(curr_dir.split("/")[:-1]))


def move_file(file:str, file_new:str):
    """ Move file."""
    curr_dir = state.get('files.dir', '/')
    if file_new == "": return [m.error("No file name specified.")]
    fa.move_file([curr_dir, file], [curr_dir, file_new])
    return directory()


def move_directory(dir_new:str):
    """ Move directory."""
    curr_dir = state.get('files.dir', '/')
    if dir_new == "": return [m.error("No file name specified.")]
    fa.move_directory([curr_dir], [dir_new])
    return directory(dir_new)


def upload_file(rename:str, upload):
    """ Saves an uploaded file."""
    curr_dir = state.get('files.dir', '/')
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
        fa.create_file([curr_dir, name], bytes)
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
