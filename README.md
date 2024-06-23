# gitbrowser

This has been used as a project to start learning Rust: https://github.com/sjagoe/gitbrowser-rs

A simple curses browser for git repositories. Intended for reading
text files from arbitrary revisions in the repository, without
checking out the requisite commit.

Essentially a wrapper around `git ls-tree` and `git cat-file`.
