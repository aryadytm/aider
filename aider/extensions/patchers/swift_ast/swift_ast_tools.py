import re
from typing import List

CLASS_PATTERN = r"^(?P<modifiers>(?:public|private|internal|fileprivate|open|static|final|weak|unowned|dynamic|lazy|convenience|required|@objc)\s+)*(?P<type>class|struct)\s+(?P<name>\w+)(?:\s*:\s*(?P<inheritance>[\w\.,\s&]+))?"
PROTOCOL_PATTERN = r"^(?P<modifiers>(?:public|private|internal|fileprivate|@objc)\s+)*protocol\s+(?P<name>\w+)(?:\s*:\s*(?P<inheritance>[\w\.\,\s&]+))?"
EXTENSION_PATTERN = r"^(?P<modifiers>(?:public|private|internal|fileprivate|@objc)\s+)*extension\s+(?P<name>\w+)(?:\s*:\s*(?P<inheritance>[\w\.\,\s&]+))?"
PROPERTY_PATTERN = r"^(?P<modifiers>(?:public|private|internal|fileprivate|static|let|var|lazy|weak|unowned|dynamic|final|@objc)\s+)*(?P<let_var>let|var)\s+(?P<name>\w+)(?:\s*:\s*(?P<type>[\w\.\?\!$$\]\[\(\)\s\<\>\:,@=]+))"
FUNCTION_PATTERN = r"^(?P<modifiers>(?:public|private|internal|fileprivate|static|final|override|open|required|convenience|mutating|nonmutating|unowned|weak|dynamic|@objc|discardableResult)\s+)*func\s+(?P<name>\w+)\s*(?P<generics><[^>]+>)?\s*(?P<parameters>\(.*?\))\s*(?P<throws>throws|rethrows)?\s*(?:->\s*(?P<return_type>[^{]+))?\s*\{?"
INIT_PATTERN = r"^(?P<modifiers>(?:public|private|internal|fileprivate|required|convenience)\s+)?init\s*(?P<parameters>\(.*?\))"
DEINIT_PATTERN = r"^(?P<modifiers>(?:public|private|internal|fileprivate)\s+)?deinit\s*$"
COMPUTED_PROPERTY_PATTERN = r"^(?P<modifiers>(?:public|private|internal|fileprivate|static|lazy|weak|unowned|dynamic|final)\s+)?var\s+(?P<name>\w+)\s*:\s*(?P<type>[\w\.\?\!\[$$\(\)\s\<\>,]+)\s*\{"


class SwiftParserError(Exception):
    def __init__(self, message: str, line_number: int):
        self.message = message
        self.line_number = line_number
        super().__init__(f"Line {line_number}: {message}")


class ASTNode:
    def __init__(
        self,
        node_type: str,
        name: str,
        annotations: List[str] = None,
        parent_type: str = None,
        modifiers: List[str] = None,
    ):
        self.node_type = node_type
        self.name = name
        self.annotations = annotations or []
        self.parent_type = parent_type
        self.modifiers = modifiers or []
        self.properties = []
        self.methods = []
        self.initializers = []
        self.is_extension = node_type == "extension"

    def add_property(self, prop):
        if not any(p["name"] == prop["name"] for p in self.properties):
            self.properties.append(prop)

    def to_string(self, indent: str = "") -> str:
        result = ""
        for annotation in self.annotations:
            result += f"{indent}{annotation}\n"
        modifiers_str = " ".join(self.modifiers).strip()
        if modifiers_str:
            node_declaration = f"{modifiers_str} {self.node_type} {self.name}".strip()
        else:
            node_declaration = f"{self.node_type} {self.name}".strip()
        if self.parent_type:
            node_declaration += f": {self.parent_type}"
        result += f"{indent}{node_declaration}\n"
        for prop in self.properties:
            prop_indent = indent + "  "
            for annotation in prop.get("annotations", []):
                result += f"{prop_indent}{annotation}\n"
            modifiers = " ".join(prop.get("modifiers", [])).strip()
            if modifiers:
                prop_line = (
                    f"{modifiers} {prop['let_var']} {prop['name']}: {prop['type']}"
                )
            else:
                prop_line = f"{prop['let_var']} {prop['name']}: {prop['type']}"
            if "accessor" in prop:
                prop_line += f" {{ {prop['accessor']} }}"
            elif "observer" in prop:
                prop_line += f" {{ {prop['observer']} }}"
            result += f"{prop_indent}{prop_line}\n"
        for method in self.methods:
            method_indent = indent + "  "
            for annotation in method.get("annotations", []):
                result += f"{method_indent}{annotation}\n"
            modifiers = " ".join(method.get("modifiers", [])).strip()
            if modifiers:
                method_decl = f"{modifiers} "
            else:
                method_decl = ""
            if method["type"] == "deinit":
                method_decl += "deinit"
            else:
                method_decl += f"{method['type']} {method['name']}"
                if method.get("generic_params"):
                    method_decl += method["generic_params"]
                method_decl += f"{method['params']}"
                if (
                    method["type"] != "init"
                    and method.get("return_type")
                    and method["return_type"] != "Void"
                ):
                    method_decl += f" -> {method['return_type']}"
                if method.get("throws"):
                    method_decl += f" {method['throws']}"
            result += f"{method_indent}{method_decl}\n"

        for init in self.initializers:
            init_indent = indent + "  "
            for annotation in init.get("annotations", []):
                result += f"{init_indent}{annotation}\n"
            modifiers = " ".join(init.get("modifiers", [])).strip()
            if modifiers:
                init_decl = f"{modifiers} init{init['params']}"
            else:
                init_decl = f"init{init['params']}"
            result += f"{init_indent}{init_decl}\n"
        return result.rstrip()


def parse_annotation(annotation_str: str) -> List[str]:
    annotations = []
    current_annotation = ""
    paren_count = 0

    for char in annotation_str:
        if char == "@" and paren_count == 0 and current_annotation:
            annotations.append(current_annotation.strip())
            current_annotation = "@"
        else:
            current_annotation += char
            if char == "(":
                paren_count += 1
            elif char == ")":
                paren_count -= 1

    if current_annotation:
        annotations.append(current_annotation.strip())

    return annotations


def parse_swift_code(code: str) -> List[ASTNode]:
    lines = code.split("\n")
    ast_nodes = []
    context_stack = []
    current_node = None
    pending_annotations = []
    in_method = False
    brace_count = 0

    for line_number, line in enumerate(lines, 1):
        try:
            original_line = line
            line = line.strip()
            if not line:
                continue

            # Update brace count
            brace_count += line.count("{") - line.count("}")

            annotations = []
            while line.startswith("@"):
                annotation_match = re.match(
                    r'^(@[\w\(\)\.\{\}\[\],\s"\'=<>:-]+)\s*', line
                )
                if annotation_match:
                    annotation = annotation_match.group(1).strip()
                    annotations.append(annotation)
                    line = line[len(annotation_match.group(0)) :].strip()
                else:
                    break
            if annotations:
                pending_annotations.extend(annotations)

            if not line:
                continue

            class_match = re.match(CLASS_PATTERN, line)
            protocol_match = re.match(PROTOCOL_PATTERN, line)
            extension_match = re.match(EXTENSION_PATTERN, line)

            if class_match or protocol_match or extension_match:
                if current_node:
                    ast_nodes.append(current_node)
                    context_stack.pop() if context_stack else None

                combined_annotations = pending_annotations
                pending_annotations = []

                modifiers = []
                if class_match:
                    match = class_match
                    node_type = match.group("type")
                elif protocol_match:
                    match = protocol_match
                    node_type = "protocol"
                else:
                    match = extension_match
                    node_type = "extension"

                if match.group("modifiers"):
                    modifiers = match.group("modifiers").strip().split()

                name = match.group("name")
                parent_type = match.group("inheritance")

                current_node = ASTNode(
                    node_type, name, combined_annotations, parent_type, modifiers
                )
                context_stack.append(current_node)
                continue

            if current_node:
                function_match = re.match(FUNCTION_PATTERN, line)
                if function_match:
                    in_method = True
                    annotations = pending_annotations
                    pending_annotations = []

                    modifiers = []
                    if function_match.group("modifiers"):
                        modifiers = function_match.group("modifiers").strip().split()

                    func_name = function_match.group("name")
                    generics = function_match.group("generics")
                    params = function_match.group("parameters")
                    return_type = (
                        function_match.group("return_type").strip()
                        if function_match.group("return_type")
                        else None
                    )
                    throws = function_match.group("throws")
                    current_node.methods.append(
                        {
                            "annotations": annotations,
                            "modifiers": modifiers,
                            "type": "func",
                            "name": func_name,
                            "generic_params": generics,
                            "params": params,
                            "return_type": return_type,
                            "throws": throws,
                        }
                    )
                    continue

                init_match = re.match(INIT_PATTERN, line)
                if init_match:
                    in_method = True
                    annotations = pending_annotations
                    pending_annotations = []

                    modifiers = []
                    if init_match.group("modifiers"):
                        modifiers = init_match.group("modifiers").strip().split()

                    params = init_match.group("parameters")
                    current_node.initializers.append(
                        {
                            "annotations": annotations,
                            "modifiers": modifiers,
                            "type": "init",
                            "name": "init",
                            "params": params,
                            "return_type": "Void",
                        }
                    )
                    continue

                deinit_match = re.match(DEINIT_PATTERN, line)
                if deinit_match:
                    in_method = True
                    annotations = pending_annotations
                    pending_annotations = []

                    modifiers = []
                    if deinit_match.group("modifiers"):
                        modifiers = deinit_match.group("modifiers").strip().split()

                    current_node.methods.append(
                        {
                            "annotations": annotations,
                            "modifiers": modifiers,
                            "type": "deinit",
                            "name": "deinit",
                            "params": "",
                            "return_type": "Void",
                        }
                    )
                    continue

                if not in_method:
                    property_observer_match = re.match(
                        PROPERTY_PATTERN + r"\s*\{\s*(?P<observer>willSet|didSet)", line
                    )
                    if property_observer_match:
                        annotations = pending_annotations
                        pending_annotations = []

                        modifiers = []
                        if property_observer_match.group("modifiers"):
                            modifiers = (
                                property_observer_match.group("modifiers")
                                .strip()
                                .split()
                            )

                        prop_name = property_observer_match.group("name")
                        prop_type = property_observer_match.group("type")
                        observer = property_observer_match.group("observer")
                        current_node.add_property(
                            {
                                "annotations": annotations,
                                "modifiers": modifiers,
                                "let_var": "var",
                                "name": prop_name,
                                "type": prop_type.strip(),
                                "observer": observer,
                            }
                        )
                        continue

                    computed_property_match = re.match(COMPUTED_PROPERTY_PATTERN, line)
                    if computed_property_match:
                        annotations = pending_annotations
                        pending_annotations = []

                        modifiers = []
                        if computed_property_match.group("modifiers"):
                            modifiers = (
                                computed_property_match.group("modifiers")
                                .strip()
                                .split()
                            )

                        prop_name = computed_property_match.group("name")
                        prop_type = computed_property_match.group("type")
                        current_node.add_property(
                            {
                                "annotations": annotations,
                                "modifiers": modifiers,
                                "let_var": "var",
                                "name": prop_name,
                                "type": prop_type.strip(),
                                "accessor": "computed",
                            }
                        )
                        continue

                    property_match = re.match(PROPERTY_PATTERN, line)
                    if property_match:
                        annotations = pending_annotations
                        pending_annotations = []

                        modifiers = []
                        if property_match.group("modifiers"):
                            modifiers = (
                                property_match.group("modifiers").strip().split()
                            )

                        let_var = property_match.group("let_var")
                        prop_name = property_match.group("name")
                        prop_type = property_match.group("type")
                        current_node.add_property(
                            {
                                "annotations": annotations,
                                "modifiers": modifiers,
                                "let_var": let_var,
                                "name": prop_name,
                                "type": prop_type,
                            }
                        )
                        continue

                if pending_annotations:
                    pending_annotations = []

            # Check if we're exiting a method
            if in_method and brace_count == 0:
                in_method = False

        except Exception as e:
            raise SwiftParserError(f"Unexpected error: {str(e)}", line_number)

    if brace_count != 0:
        raise SwiftParserError("Mismatched braces in the Swift code", len(lines))

    if current_node:
        ast_nodes.append(current_node)

    return ast_nodes


def preprocess_swift_code(swift_code: str) -> str:
    preprocessed_lines = []

    def is_class_like_annotation(annotation: str) -> bool:
        class_like_annotations = [
            "@objc",
            "@available",
            "@main",
            "@UIApplicationMain",
            "@NSApplicationMain",
            "@testable",
            "@objcMembers",
        ]
        return any(
            annotation.startswith(cls_annot) for cls_annot in class_like_annotations
        )

    def is_field_annotation(annotation: str) -> bool:
        field_annotations = [
            "@State",
            "@Binding",
            "@Published",
            "@ObservedObject",
            "@Environment",
            "@EnvironmentObject",
            "@NSManaged",
            "@GKInspectable",
            "@IBOutlet",
            "@IBInspectable",
        ]
        return any(
            annotation.startswith(field_annot) for field_annot in field_annotations
        )

    lines = swift_code.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped_line = line.strip()

        if stripped_line.startswith("@"):
            annotations = []
            while stripped_line.startswith("@"):
                space_index = stripped_line.find(" ")
                if space_index == -1:
                    annotations.append(stripped_line)
                    stripped_line = ""
                else:
                    annotations.append(stripped_line[:space_index])
                    stripped_line = stripped_line[space_index:].strip()

            for annotation in annotations:
                if is_class_like_annotation(annotation):
                    preprocessed_lines.append(line[: line.index("@")] + annotation)
                elif is_field_annotation(annotation):
                    if stripped_line:
                        preprocessed_lines.append(line)
                        break
                else:
                    preprocessed_lines.append(line[: line.index("@")] + annotation)

            if stripped_line:
                preprocessed_lines.append(line[: line.index("@")] + stripped_line)
        else:
            preprocessed_lines.append(line)

        i += 1

    return "\n".join(preprocessed_lines)


def generate_ast_string(ast_nodes: List[ASTNode]) -> str:
    result = ""
    for node in ast_nodes:
        result += node.to_string()
        result += "\n"
    return result.strip()


def convert_swift_to_ast(swift_code: str) -> str:
    """
    NOTE: Use this as main entrypoint when converting Swift code to AST string
    NOTE: This method returns a rendered TREE string. You dont need to use tags anymore!!!
    """
    try:
        preprocessed_code = preprocess_swift_code(swift_code)
        ast_nodes = parse_swift_code(preprocessed_code)
        return generate_ast_string(ast_nodes)
    except SwiftParserError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


def main():
    from swift_example import swift_code_str
    try:
        print("Generated AST with correct indentation:\n===========")
        ast_string = convert_swift_to_ast(swift_code_str)
        print(ast_string)
    except Exception as e:
        print(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    main()
