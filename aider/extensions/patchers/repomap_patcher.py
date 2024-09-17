from aider.extensions.patchers.swift_ast.swift_ast_tools import convert_swift_to_ast
from aider.repomap import RepoMap
import os

MINIMUM_SWIFT_FILES = 3

def is_swift_file(filename):
    return filename.lower().endswith('.swift')

def has_swift_files(file_list):
    return sum(1 for fname in file_list if is_swift_file(fname)) >= MINIMUM_SWIFT_FILES

def convert_swift_file_to_ast(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    return convert_swift_to_ast(content)

def apply_patch():    
    RepoMap.original_get_ranked_tags_map_uncached = RepoMap.get_ranked_tags_map_uncached
    RepoMap.get_ranked_tags_map_uncached = patched_get_ranked_tags_map_uncached

def patched_get_ranked_tags_map_uncached(
        self,
        chat_fnames,
        other_fnames=None,
        max_map_tokens=None,
        mentioned_fnames=None,
        mentioned_idents=None,
    ):
        all_fnames = list(chat_fnames)
        if other_fnames:
            all_fnames.extend(other_fnames)
        
        if not has_swift_files(all_fnames):
            return self.original_get_ranked_tags_map_uncached(
                chat_fnames,
                other_fnames,
                max_map_tokens,
                mentioned_fnames,
                mentioned_idents
            )
        
        tree_str = ""
        
        for fname in all_fnames:
            if is_swift_file(fname):
                ast = convert_swift_file_to_ast(fname)
                tree_str += f"{fname}:\n{ast}\n\n"
            else:
                tree_str += f"{fname}\n\n"
        
        return tree_str
