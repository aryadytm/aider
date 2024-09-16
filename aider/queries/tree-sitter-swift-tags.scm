; swift.scm

; Punctuation
["." ";" ":" ","] @punctuation.delimiter
["\\(" "(" ")" "[" "]" "{" "}"] @punctuation.bracket

; Identifiers
(attribute) @variable
(type_identifier) @type
(self_expression) @variable.builtin
(user_type (type_identifier) @variable.builtin (#eq? @variable.builtin "Self"))

; Declarations
"func" @keyword.function
[
  (visibility_modifier)
  (member_modifier)
  (function_modifier)
  (property_modifier)
  (parameter_modifier)
  (inheritance_modifier)
] @keyword

(function_declaration (simple_identifier) @method)
(init_declaration ["init" @constructor])
(deinit_declaration ["deinit" @constructor])
(throws) @keyword
"async" @keyword
"await" @keyword
(where_keyword) @keyword
(parameter external_name: (simple_identifier) @parameter)
(parameter name: (simple_identifier) @parameter)
(type_parameter (type_identifier) @parameter)
(inheritance_constraint (identifier (simple_identifier) @parameter))
(equality_constraint (identifier (simple_identifier) @parameter))
(pattern bound_identifier: (simple_identifier)) @variable

[
  "typealias"
  "struct"
  "class"
  "actor"
  "enum"
  "protocol"
  "extension"
  "indirect"
  "nonisolated"
  "override"
  "convenience"
  "required"
  "mutating"
  "associatedtype"
  "package"
] @keyword

(opaque_type ["some" @keyword])
(existential_type ["any" @keyword])

(precedence_group_declaration
 ["precedencegroup" @keyword]
 (simple_identifier) @type)
(precedence_group_attribute
 (simple_identifier) @keyword
 [(simple_identifier) @type
  (boolean_literal) @boolean])

[
  (getter_specifier)
  (setter_specifier)
  (modify_specifier)
] @keyword

(class_body (property_declaration (pattern (simple_identifier) @property)))
(protocol_property_declaration (pattern (simple_identifier) @property))

(import_declaration ["import" @include])

(enum_entry ["case" @keyword])

; Function calls
(call_expression (simple_identifier) @function.call)
(call_expression
  (navigation_expression
    (navigation_suffix (simple_identifier) @function.call)))
((navigation_expression
   (simple_identifier) @type)
   (#match? @type "^[A-Z]"))
(call_expression (simple_identifier) @keyword (#eq? @keyword "defer"))

(try_operator) @operator
(try_operator ["try" @keyword])

(directive) @function.macro
(diagnostic) @function.macro

; Statements
(for_statement ["for" @repeat])
(for_statement ["in" @repeat])
(for_statement (pattern) @variable)
(else) @keyword
(as_operator) @keyword

["while" "repeat" "continue" "break"] @repeat

["let" "var"] @keyword

(guard_statement ["guard" @conditional])
(if_statement ["if" @conditional])
(switch_statement ["switch" @conditional])
(switch_entry ["case" @keyword])
(switch_entry ["fallthrough" @keyword])
(switch_entry (default_keyword) @keyword)
"return" @keyword.return
(ternary_expression
  ["?" ":"] @conditional)

["do" (throw_keyword) (catch_keyword)] @keyword

(statement_label) @label

; Comments
[
 (comment)
 (multiline_comment)
] @comment @spell

; String literals
(line_str_text) @string
(str_escaped_char) @string
(multi_line_str_text) @string
(raw_str_part) @string
(raw_str_end_part) @string
(raw_str_interpolation_start) @punctuation.special
["\"" "\"\"\""] @string

; Lambda literals
(lambda_literal ["in" @keyword.operator])

; Basic literals
[
 (integer_literal)
 (hex_literal)
 (oct_literal)
 (bin_literal)
] @number
(real_literal) @float
(boolean_literal) @boolean
"nil" @variable.builtin

; Regex literals
(regex_literal) @string.regex

; Operators
(custom_operator) @operator
[
 "!" "?" "+" "-" "*" "/" "%" "=" "+=" "-=" "*=" "/=" "<" ">" "<=" ">="
 "++" "--" "&" "~" "%=" "!=" "!==" "==" "===" "??" "->" "..<" "..."
] @operator

(value_parameter_pack ["each" @keyword])
(value_pack_expansion ["repeat" @keyword])
(type_parameter_pack ["each" @keyword])
(type_pack_expansion ["repeat" @keyword])

; Indentation
[
  (protocol_body)
  (class_body)
  (enum_class_body)
  (function_declaration)
  (init_declaration)
  (deinit_declaration)
  (computed_property)
  (subscript_declaration)
  (computed_getter)
  (computed_setter)
  (assignment)
  (control_transfer_statement)
  (for_statement)
  (while_statement)
  (repeat_while_statement)
  (do_statement)
  (if_statement)
  (switch_statement)
  (guard_statement)
  (type_parameters)
  (tuple_type)
  (array_type)
  (dictionary_type)
  (call_expression)
  (tuple_expression)
  (array_literal)
  (dictionary_literal)
  (lambda_literal) 
  (willset_didset_block)
  (willset_clause)
  (didset_clause)
] @indent.begin

((modifiers
  (attribute) @indent.begin))

(function_declaration
  (modifiers
    .
    (attribute)
    (_)* @indent.branch)
  .
  _ @indent.branch
  (#not-has-type? @indent.branch type_parameters parameter))

(ERROR
  [
    "<" 
    "{" 
    "(" 
    "["
  ]
) @indent.begin

(if_statement
  (if_statement) @indent.dedent)

(switch_entry . _ @indent.branch)

(function_declaration ")" @indent.branch)

(type_parameters ">" @indent.branch @indent.end .)
(tuple_expression ")" @indent.branch @indent.end)
(value_arguments ")" @indent.branch @indent.end)
(tuple_type ")" @indent.branch @indent.end)
(modifiers
  (attribute ")" @indent.branch @indent.end))

[
  "}"
  "]"
] @indent.branch @indent.end

[
  (comment)
  (multiline_comment)
  (raw_str_part)
  (multi_line_string_literal)
] @indent.auto

(directive) @indent.ignore

; Regex injection
((regex_literal) @injection.content
 (#set! injection.language "regex"))

; Definitions and references
(import_declaration (identifier) @definition.import)
(function_declaration name: (simple_identifier) @definition.function)

; Scopes
[
 (for_statement)
 (while_statement)
 (repeat_while_statement)
 (do_statement)
 (if_statement)
 (guard_statement)
 (switch_statement)
 (property_declaration)
 (function_declaration)
 (class_declaration)
 (protocol_declaration)
 (lambda_literal)
] @local.scope

; Structure
(function_declaration
  body: (_) @function.inside) @function.around

; Tests
(function_declaration
	name: (simple_identifier) @_name
	(#match? @_name "^test")
) @test.function

; Class, protocol, and other declarations
(class_declaration
  name: (type_identifier) @name) @definition.class

(protocol_declaration
  name: (type_identifier) @name) @definition.interface

(class_declaration
    (class_body
        [
            (function_declaration
                name: (simple_identifier) @name
            )
            (subscript_declaration
                (parameter (simple_identifier) @name)
            )
            (init_declaration "init" @name)
            (deinit_declaration "deinit" @name)
        ]
    )
) @definition.method

(protocol_declaration
    (protocol_body
        [
            (protocol_function_declaration
                name: (simple_identifier) @name
            )
            (subscript_declaration
                (parameter (simple_identifier) @name)
            )
            (init_declaration "init" @name)
        ]
    )
) @definition.method

(class_declaration
    (class_body
        [
            (property_declaration
                (pattern (simple_identifier) @name)
            )
        ]
    )
) @definition.property

(property_declaration
    (pattern (simple_identifier) @name)
) @definition.property

(function_declaration
    name: (simple_identifier) @name) @definition.function