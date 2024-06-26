from curses.textpad import rectangle
from enum import Enum
from math import ceil
from pathlib import Path, PosixPath
import curses
import json
import os

from pygit2 import Repository, GitError
from pygit2.enums import ObjectType
from pypager.source import StringSource
from pypager.pager import Pager
import click


class Quit(Exception):
    pass


class Back(Exception):
    pass


class Style(Enum):
    normal = 'normal'
    selected = 'selected'


STYLES = {}


def display_blob_content(content):
    p = Pager()
    p.add_source(StringSource(content))
    p.run()


def browse_refs(stdscr, repo):
    return browse_objects(
        stdscr,
        list(repo.references),
        name=repo.path,
        display=display_object,
    )


def display_object(obj):
    if isinstance(obj, str):
        type = 'ref'
    else:
        type = obj.type

    binary = None
    if type == ObjectType.BLOB:
        binary = obj.is_binary

    normal = STYLES.get((type, Style.normal, binary), curses.A_NORMAL)
    selected = STYLES.get((type, Style.selected, binary))
    if selected is None:
        selected = STYLES[(None, Style.selected, None)]

    match type:
        case ObjectType.TREE:
            label = 'tree'
            display = f'{obj.name}/'
        case 'ref':
            label = 'ref'
            display = f'{obj}'
        case ObjectType.BLOB:
            label = 'binary' if obj.is_binary else 'text'
            display = f'{obj.name}'
        case _:
            label = ''
            display = obj.name
    return (normal, selected, label, display)


def define_style(key, foreground, background, flags=None):
    global STYLES
    pair = len(STYLES) + 1
    curses.init_pair(pair, foreground, background)
    style = curses.color_pair(pair)
    if flags:
        style = style | flags
    STYLES[key] = style


def define_styles():
    global STYLES
    STYLES = {}
    define_style(
        (None, Style.selected, None),
        curses.COLOR_BLACK, curses.COLOR_CYAN,
        flags=curses.A_BOLD | curses.A_DIM,
    )
    define_style(
        (ObjectType.TREE, Style.normal, None),
        curses.COLOR_BLUE, curses.COLOR_BLACK,
        flags=curses.A_BOLD,
    )
    define_style(
        (ObjectType.TREE, Style.selected, None),
        curses.COLOR_BLUE, curses.COLOR_CYAN,
        flags=curses.A_BOLD | curses.A_DIM,
    )

    define_style(
        (ObjectType.BLOB, Style.normal, True),
        curses.COLOR_RED, curses.COLOR_BLACK,
        flags=curses.A_BOLD
    )
    define_style(
        (ObjectType.BLOB, Style.selected, True),
        curses.COLOR_RED, curses.COLOR_CYAN,
        flags=curses.A_BOLD | curses.A_DIM
    )


def browse_tree(stdscr, tree, previous, name):
    return browse_objects(
        stdscr,
        list(tree),
        name=name,
        display=display_object,
        previous=previous,
    )


def pagination(item_count, visible_item_count, selected_ix):
    page_start_ix = selected_ix - (selected_ix % visible_item_count)
    pages = int(ceil(item_count / visible_item_count))
    page = int(ceil(float(page_start_ix) / visible_item_count))
    return page, pages, page_start_ix


def browse_objects(stdscr, items, *, name, display, previous=None):
    if previous:
        selected = items.index(previous)
    else:
        selected = 0
    item_count = len(items)
    while True:
        stdscr.clear()
        uly, ulx = stdscr.getbegyx()
        lry, lrx = stdscr.getmaxyx()

        # one header line
        # four footer lines
        height = curses.LINES - 5
        # Two cols padding on each side
        width = curses.COLS - 4

        page, pages, page_start_ix = pagination(item_count, height, selected)

        rectangle(stdscr, uly, ulx, lry - 4, lrx - 1)
        stdscr.addstr(uly, ulx + 2, name)

        stdscr.addstr(curses.LINES - 2, ulx + 2, '^X Exit | ^G Back/Refresh')

        display_items = items[page_start_ix:page_start_ix + height]
        items_win = curses.newwin(height, width, uly + 1, ulx + 2)
        for index, item in enumerate(display_items):
            normal_style, selected_style, label, formatted = display(item)
            style = normal_style
            if index + page_start_ix == selected:
                style = selected_style
            items_win.addstr(index, 0, label, curses.A_NORMAL | curses.A_DIM)
            items_win.addstr(index, 10, formatted, style)

        stdscr.refresh()
        items_win.refresh()

        key = stdscr.getch()

        keyname = curses.keyname(key)
        if keyname == b'KEY_UP':
            selected = (selected - 1) % len(items)
        elif keyname == b'KEY_DOWN':
            selected = (selected + 1) % len(items)
        elif keyname == b'KEY_PPAGE':
            if page == 0:
                selected = 0
            else:
                selected = (selected - height) % len(items)
        elif keyname == b'KEY_NPAGE':
            if page == pages - 1:
                selected = len(items) - 1
            else:
                selected = (selected + height) % len(items)
        elif keyname == b'^G':
            raise Back()
        elif keyname == b'^X':
            raise Quit()
        elif key == curses.ascii.LF:
            return items[selected]


def repo_name(repo):
    repo_path = Path(repo.path)
    if repo_path.name == '.git':
        repo_path = repo_path.parent
    return repo_path.name


def history_to_path(repo, revision, history):
    parts = [i for i in history if i.type == ObjectType.TREE]
    if len(parts) == 0:
        return ''
    names = [i.name for i in parts if i.name is not None]
    path = PosixPath(*names).as_posix()
    return f'{repo_name(repo)}@{revision}:{path}'


def browse_git(stdscr, repo, commit=None):
    def reset(mode):
        stdscr.clear()
        stdscr.clearok(True)
        stdscr.refresh()
        mode()

    define_styles()
    curses.curs_set(0)

    history = []
    obj = None
    revision = None
    previous = None
    if commit is not None:
        revision = str(commit.short_id)
    while True:
        try:
            if len(history) == 0 and not commit:
                ref_name = browse_refs(stdscr, repo)
                revision = ref_name
                ref = repo.lookup_reference(ref_name)
                commit = ref.peel(ObjectType.COMMIT)
                obj = commit.tree
            elif len(history) == 0 and commit:
                obj = commit.tree
            else:
                if obj:
                    previous = obj
                obj = history.pop()
            while obj.type == ObjectType.TREE or obj.type == ObjectType.COMMIT:
                history.append(obj)
                obj = browse_tree(
                    stdscr,
                    obj,
                    previous,
                    name=history_to_path(repo, revision, history),
                )
                previous = None

            if obj.type == ObjectType.BLOB and not obj.is_binary:
                reset(curses.reset_shell_mode)
                try:
                    display_blob_content(obj.data.decode('utf-8'))
                finally:
                    reset(curses.reset_prog_mode)

        except Back:
            try:
                obj = history.pop()
            except IndexError:
                pass
            continue
        except Quit:
            break
    reset(curses.reset_prog_mode)


def commit_from_flake(repo, flake):
    repository_name = repo_name(repo)
    if flake.name == 'flake.lock':
        pass
    if flake.name == 'flake.nix':
        flake = flake.parent / 'flake.lock'
    elif flake.is_dir() and (flake / 'flake.lock').is_file():
        flake = flake / 'flake.lock'
    else:
        raise Exception("Can't find flake.lock from {flake.as_posix()}")
    if not flake.is_file():
        raise Exception("{flake.as_posix()} doesn't exist")

    with flake.open() as fh:
        data = json.loads(fh.read())
    node = data['nodes'][repository_name]
    return node['locked']['rev']


@click.command('gitbrowser')
@click.option('--commit-id', '-c')
@click.option('--repository-path', '-C', default=os.getcwd())
@click.option('--flake')
@click.pass_context
def main(ctx, commit_id, repository_path, flake):
    if commit_id and flake:
        ctx.fail("Can't use --commit-id and --flake together")

    try:
        repo = Repository(repository_path)
    except GitError as e:
        ctx.fail(str(e))

    if flake:
        commit_id = commit_from_flake(repo, Path(flake))
    commit = None
    if commit_id:
        commit = repo.revparse_single(commit_id)

    curses.wrapper(browse_git, repo, commit)
