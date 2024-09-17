from aider.extensions.patchers.swift_ast.swift_ast_tools import convert_swift_to_ast
from aider.repomap import RepoMap
import os


def is_swift_file(filename):
    return filename.lower().endswith('.swift')

def has_swift_files(file_list):
    return any(is_swift_file(fname) for fname in file_list)

def convert_swift_file_to_ast(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    return convert_swift_to_ast(content)

def apply_patch():    
    RepoMap.original_get_ranked_tags_map_uncached = RepoMap.get_ranked_tags_map_uncached
    RepoMap.get_ranked_tags_map_uncached = patched_get_ranked_tags_map_uncached
