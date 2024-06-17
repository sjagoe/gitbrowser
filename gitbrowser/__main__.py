from curses.textpad import rectangle
from math import ceil
import curses
import os
import socket

from pygit2 import Repository
from pygit2.enums import ObjectType
from pypager.source import StringSource
from pypager.pager import Pager
import click


class Quit(Exception):
    pass


class Back(Exception):
    pass


def display_blob_content(content):
    p = Pager()
    p.add_source(StringSource(content))
    p.run()


def curses_selector(items, selected_ix, *, height, width, uly, ulx, display):
    items_win = curses.newwin(height, width, uly + 1, ulx + 2)
    for index, item in enumerate(items):
        if index >= height:
            break
        style = curses.color_pair(1) if index == selected_ix else curses.A_NORMAL
        items_win.addstr(index, 0, display(item), style)
    return items_win


def browse_refs(stdscr, repo):
    return browse_objects(
        stdscr,
        list(repo.references),
        name='refs',
        display=lambda i: i,
    )


def browse_tree(stdscr, tree):
    return browse_objects(
        stdscr,
        list(tree),
        name='tree',
        display=lambda i: ' '.join([i.type_str, str(i.id), i.name]),
    )


def pagination(item_count, visible_item_count, selected_ix):
    page_start_ix = selected_ix - (selected_ix % visible_item_count)
    pages = int(ceil(item_count / visible_item_count))
    page = int(ceil(float(page_start_ix) / visible_item_count))
    return page, pages, page_start_ix


def browse_objects(stdscr, items, *, name, display):
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
            style = curses.A_NORMAL
            if index + page_start_ix == selected:
                style = curses.color_pair(1)
            items_win.addstr(index, 0, display(item), style)

        stdscr.refresh()
        items_win.refresh()

        key = stdscr.getch()

        keyname = curses.keyname(key)
        if keyname == b'KEY_UP':
            selected = (selected - 1) % len(items)
        elif keyname == b'KEY_DOWN':
            selected = (selected + 1) % len(items)
        elif keyname == b'^G':
            raise Back()
        elif keyname == b'^X':
            raise Quit()
        elif key == curses.ascii.LF:
            return items[selected]


def browse_git(stdscr, repo, history=None, commit=None):
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.curs_set(0)
    if history is None:
        history = []
    while True:
        try:
            if len(history) == 0 and not commit:
                ref_name = browse_refs(stdscr, repo)
                ref = repo.lookup_reference(ref_name)
                obj = ref.peel(ObjectType.COMMIT).tree
            elif len(history) == 0 and commit:
                obj = commit.tree
            else:
                obj = history.pop()
            while obj.type == ObjectType.TREE or obj.type == ObjectType.COMMIT:
                history.append(obj)
                obj = browse_tree(stdscr, obj)

            if obj.type == ObjectType.BLOB and not obj.is_binary:
                return obj, history

        except Back:
            obj = history.pop()
            continue
        except Quit:
            break
    return None, None


@click.command('gitbrowser')
@click.option('--commit-id', '-c')
@click.option('--repository-path', '-C', default=os.getcwd())
def main(commit_id, repository_path):
    repo = Repository(repository_path)
    commit = None
    if commit_id:
        commit = repo.revparse_single(commit_id)
    history = None
    while True:
        obj, history = curses.wrapper(browse_git, repo, history, commit)
        if obj is None:
            break
        display_blob_content(obj.data.decode('utf-8'))
