from swift_ast.swift_ast_tools import convert_swift_to_ast
from aider.repomap import RepoMap, Tag
import os

def extract_swift_tags(ast_string, rel_fname, fname):
    tags = []
    lines = ast_string.split('\n')
    for i, line in enumerate(lines):
        if line.strip().startswith(('class ', 'struct ', 'enum ', 'protocol ', 'func ', 'var ', 'let ')):
            parts = line.strip().split()
            name = parts[1].split('(')[0]  # Remove any parameters for functions
            kind = 'def' if parts[0] in ('class', 'struct', 'enum', 'protocol', 'func') else 'ref'
            tags.append(Tag(rel_fname=rel_fname, fname=fname, line=i+1, name=name, kind=kind))
    return tags

def handle_swift_file(fname, rel_fname, content):
    ast_string = convert_swift_to_ast(content)
    return extract_swift_tags(ast_string, rel_fname, fname)

def get_tags_raw_swift(self, fname, rel_fname):
    content = self.io.read_text(fname)
    return handle_swift_file(fname, rel_fname, content)

def apply_patch():
    original_get_tags_raw = RepoMap.get_tags_raw

    def patched_get_tags_raw(self, fname, rel_fname):
        if os.path.splitext(fname)[1].lower() == '.swift':
            return get_tags_raw_swift(self, fname, rel_fname)
        return original_get_tags_raw(self, fname, rel_fname)

    RepoMap.get_tags_raw = patched_get_tags_raw

    # Modify RepoMap.get_tags to bypass cache for Swift files
    original_get_tags = RepoMap.get_tags

    def patched_get_tags(self, fname, rel_fname):
        if os.path.splitext(fname)[1].lower() == '.swift':
            return self.get_tags_raw(fname, rel_fname)
        return original_get_tags(self, fname, rel_fname)

    RepoMap.get_tags = patched_get_tags
