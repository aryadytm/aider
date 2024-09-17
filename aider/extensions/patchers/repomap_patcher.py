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
    def patched_get_ranked_tags_map_uncached(
        self,
        chat_fnames,
        other_fnames=None,
        max_map_tokens=None,
        mentioned_fnames=None,
        mentioned_idents=None,
    ):
        all_fnames = []  # TODO: combine chat_fnames and other_fnames
        tree_str = ""
        
        # TODO: if there are NO swift files, use the original original_get_ranked_tags_map_uncached
        
        # TODO: there are swift file, loop through all_fnames. if is_swift_file(fname), then convert_swift_to_ast(fname) and append to tree_str along with file path above
        
        pass

    RepoMap.original_get_ranked_tags_map_uncached = RepoMap.get_ranked_tags_map_uncached
    RepoMap.get_ranked_tags_map_uncached = patched_get_ranked_tags_map_uncached
