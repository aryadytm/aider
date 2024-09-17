from aider.extensions.patchers.swift_ast.swift_ast_tools import convert_swift_to_ast
from aider.repomap import RepoMap, Tag
import os


def is_swift_file(filename):
    return filename.lower().endswith('.swift')


def patch_render_tree():
    def patched_render_tree(self, abs_fname, rel_fname, lois):
        if is_swift_file(rel_fname):
            with open(abs_fname, 'r') as f:
                swift_code = f.read()
            return convert_swift_to_ast(swift_code)
        return self.original_render_tree(abs_fname, rel_fname, lois)

    RepoMap.original_render_tree = RepoMap.render_tree
    RepoMap.render_tree = patched_render_tree

def apply_patch():
    patch_render_tree()
    
    def patched_get_ranked_tags_map_uncached(self, *args, **kwargs):
        original_result = self.original_get_ranked_tags_map_uncached(*args, **kwargs)
        
        if not original_result:
            return original_result

        swift_files = [tag[0] for tag in original_result if is_swift_file(tag[0])]
        
        if not swift_files:
            return original_result

        swift_trees = {}
        for swift_file in swift_files:
            with open(os.path.join(self.root, swift_file), 'r') as f:
                swift_code = f.read()
            swift_trees[swift_file] = convert_swift_to_ast(swift_code)

        modified_result = []
        for tag in original_result:
            if tag[0] in swift_trees:
                modified_result.append((tag[0], swift_trees[tag[0]]))
            else:
                modified_result.append(tag)

        return modified_result

    RepoMap.original_get_ranked_tags_map_uncached = RepoMap.get_ranked_tags_map_uncached
    RepoMap.get_ranked_tags_map_uncached = patched_get_ranked_tags_map_uncached
