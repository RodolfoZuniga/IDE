#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from prettytable import PrettyTable

@dataclass
class Token:
    token_type: str
    value: str
    line: int
    column: int

class ASTNode:
    def __init__(self, node_type: str, value: str = None, line: int = None, column: int = None, children: List['ASTNode'] = None):
        self.node_type = node_type
        self.value = value
        self.line = line
        self.column = column
        self.children = children or []
    
    def add_child(self, child: 'ASTNode'):
        self.children.append(child)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert AST node to dictionary for JSON serialization"""
        result = {
            "node_type": self.node_type,
            "value": self.value,
            "line": self.line,
            "column": self.column,
            "children": [child.to_dict() for child in self.children]
        }
        return result

class SyntaxError:
    def __init__(self, description: str, line: int, column: int):
        self.description = description
        self.line = line
        self.column = column
    
    def __str__(self):
        return f"Error: {self.description} (Línea {self.line}, Columna {self.column})"

class SyntaxAnalyzer:
    def __init__(self):
        self.tokens = []
        self.current_token_index = 0
        self.current_token = None
        self.errors = []
        self.ast = None
    
    def load_tokens(self, file_path: str):
        """Load tokens from lexical analyzer output file"""
        try:
            # First try to run lexical analyzer to get fresh tokens
            import subprocess
            import os
            
            script_dir = os.path.dirname(os.path.abspath(__file__))
            lexical_analyzer_path = os.path.join(script_dir, 'lexical_analyzer.py')
            
            # Run lexical analyzer
            result = subprocess.run(
                ['python', lexical_analyzer_path, file_path],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            # Parse tokens from output
            self.tokens = self._parse_tokens_from_output(result.stdout)
            
            if not self.tokens:
                # Fallback: try to read from a tokens file if it exists
                tokens_file = file_path.replace('.txt', '_tokens.json')
                if os.path.exists(tokens_file):
                    with open(tokens_file, 'r', encoding='utf-8') as f:
                        tokens_data = json.load(f)
                        self.tokens = [Token(**token_data) for token_data in tokens_data]
                        
        except Exception as e:
            print(f"Error loading tokens: {e}", file=sys.stderr)
            return False
        
        if self.tokens:
            self.current_token_index = 0
            self.current_token = self.tokens[0] if self.tokens else None
            return True
        return False
    
    def _parse_tokens_from_output(self, output: str) -> List[Token]:
        """Parse tokens from lexical analyzer output"""
        tokens = []
        lines = output.split('\n')
        in_table = False
        
        # Skip tokens that are typically not needed for parsing
        skip_tokens = {'WHITESPACE', 'NEWLINE', 'COMMENT_SINGLE', 'COMMENT_MULTI'}
        
        for line in lines:
            line = line.strip()
            if '|' in line and not line.startswith('+') and not line.startswith('='):
                parts = [part.strip() for part in line.split('|')]
                if len(parts) >= 5 and parts[1] not in ['Token Type', '']:
                    try:
                        token_type = parts[1]
                        value = parts[2]
                        line_num = int(parts[3])
                        column = int(parts[4])
                        
                        # Corregir tipos de tokens para operadores
                        if value == '++':
                            token_type = 'INCREMENT_OP'
                        elif value == '--':
                            token_type = 'DECREMENT_OP'
                        elif value == '^':
                            token_type = 'ARITH_OP'
                        elif value == '%':
                            token_type = 'ARITH_OP'
                            
                        if token_type not in skip_tokens:
                            tokens.append(Token(token_type, value, line_num, column))
                    except (ValueError, IndexError):
                        continue
        
        return tokens
    
    def advance(self):
        """Move to the next token"""
        self.current_token_index += 1
        if self.current_token_index < len(self.tokens):
            self.current_token = self.tokens[self.current_token_index]
        else:
            self.current_token = None
    
    def peek(self, offset: int = 1) -> Optional[Token]:
        """Look ahead at the next token without consuming it"""
        index = self.current_token_index + offset
        if index < len(self.tokens):
            return self.tokens[index]
        return None
    
    def match(self, expected_type: str, expected_value: str = None) -> bool:
        """Check if current token matches expected type and optionally value"""
        if not self.current_token:
            return False
        
        type_matches = self.current_token.token_type == expected_type
        value_matches = expected_value is None or self.current_token.value == expected_value
        
        return type_matches and value_matches
    
    def consume(self, expected_type: str, expected_value: str = None) -> Optional[Token]:
        """Consume current token if it matches expected type/value"""
        if self.match(expected_type, expected_value):
            token = self.current_token
            self.advance()
            return token
        return None
    
    def error(self, message: str):
        """Add a syntax error"""
        if self.current_token:
            error = SyntaxError(message, self.current_token.line, self.current_token.column)
        else:
            error = SyntaxError(message, 0, 0)
        self.errors.append(error)
    
    def synchronize(self):
        """Synchronize after an error by skipping to next statement"""
        sync_tokens = {';', 'if', 'while', 'do', 'int', 'float', 'bool', 'main'}  # Removed 'char'
        
        while self.current_token and self.current_token.value not in sync_tokens:
            self.advance()
    
    def parse(self) -> Optional[ASTNode]:
        """Main parsing method"""
        try:
            self.ast = self.parse_program()
            return self.ast
        except Exception as e:
            self.error(f"Unexpected error during parsing: {str(e)}")
            return None
    
    def parse_program(self) -> Optional[ASTNode]:
        """programa → main { lista_declaracion }"""
        program_node = ASTNode("Program", line=1, column=1)
        
        # Expect 'main'
        main_token = self.consume('KEYWORD', 'main')
        if not main_token:
            self.error("Se esperaba 'main' al inicio del programa")
            return program_node
        
        # Expect '{'
        if not self.consume('DELIMITER', '{'):
            self.error("Se esperaba '{' después de 'main'")
            self.synchronize()
        
        # Parse lista_declaracion
        while self.current_token and not self.match('DELIMITER', '}'):
            declaration = self.parse_declaracion()
            if declaration:
                program_node.add_child(declaration)
            else:
                self.synchronize()
        
        # Expect '}'
        if not self.consume('DELIMITER', '}'):
            self.error("Se esperaba '}' al final del programa")
        
        return program_node
    
    def parse_declaracion(self) -> Optional[ASTNode]:
        """declaracion → declaracion_variable | lista_sentencias"""
        # Check if it's a variable declaration (starts with type)
        if self.match('KEYWORD') and self.current_token.value in ['int', 'float', 'bool']:  # Removed 'char'
            return self.parse_declaracion_variable()
        else:
            return self.parse_sentencia()
    
    def parse_declaracion_variable(self) -> Optional[ASTNode]:
        """declaracion_variable → tipo identificador ;"""
        if not self.current_token:
            return None
        
        # Parse tipo
        tipo_token = self.consume('KEYWORD')
        if not tipo_token or tipo_token.value not in ['int', 'float', 'bool']:  # Removed 'char'
            self.error("Se esperaba un tipo de dato (int, float, bool)")
            return None
        
        declaration_node = ASTNode("Declaration", tipo_token.value, tipo_token.line, tipo_token.column)
        
        # Parse identificadores (can be multiple separated by commas)
        identifiers = self.parse_identificador_list()
        for identifier in identifiers:
            declaration_node.add_child(identifier)
        
        # Expect ';'
        if not self.consume('DELIMITER', ';'):
            self.error("Se esperaba ';' después de la declaración de variable")
        
        return declaration_node
    
    def parse_identificador_list(self) -> List[ASTNode]:
        """Parse comma-separated list of identifiers"""
        identifiers = []
        
        # First identifier
        if self.match('IDENTIFIER'):
            token = self.consume('IDENTIFIER')
            identifiers.append(ASTNode("Identifier", token.value, token.line, token.column))
        else:
            self.error("Se esperaba un identificador")
            return identifiers
        
        # Additional identifiers separated by commas
        while self.match('DELIMITER', ','):
            self.advance()  # consume comma
            if self.match('IDENTIFIER'):
                token = self.consume('IDENTIFIER')
                identifiers.append(ASTNode("Identifier", token.value, token.line, token.column))
            else:
                self.error("Se esperaba un identificador después de ','")
                break
        
        return identifiers
    
    def parse_sentencia(self) -> Optional[ASTNode]:
        """sentencia → seleccion | iteracion | repeticion | sent_in | sent_out | asignacion"""
        if not self.current_token:
            return None
        
        if self.match('KEYWORD', 'if'):
            return self.parse_seleccion()
        elif self.match('KEYWORD', 'while'):
            return self.parse_iteracion()
        elif self.match('KEYWORD', 'do'):
            return self.parse_repeticion()
        elif self.match('KEYWORD', 'cin'):
            return self.parse_sent_in()
        elif self.match('KEYWORD', 'cout'):
            return self.parse_sent_out()
        elif self.match('IDENTIFIER'):
            return self.parse_asignacion()
        else:
            self.error(f"Sentencia no reconocida: '{self.current_token.value if self.current_token else 'EOF'}'")
            self.advance()
            return None
    
    def parse_asignacion(self) -> Optional[ASTNode]:
        """asignacion → id = sent_expression"""
        if not self.match('IDENTIFIER'):
            return None
        
        id_token = self.consume('IDENTIFIER')
        assignment_node = ASTNode("Assignment", id_token.value, id_token.line, id_token.column)
        
        # Expect '='
        if not self.consume('ASSIGN_OP', '='):
            self.error("Se esperaba '=' en la asignación")
            return assignment_node
        
        # Parse expression
        expression = self.parse_sent_expression()
        if expression:
            assignment_node.add_child(expression)
        
        return assignment_node
    
    def parse_sent_expression(self) -> Optional[ASTNode]:
        """sent_expression → expression ; | ;"""
        if self.match('DELIMITER', ';'):
            self.advance()
            return ASTNode("EmptyExpression")
        
        expression = self.parse_expression()
        
        # Expect ';'
        if not self.consume('DELIMITER', ';'):
            self.error("Se esperaba ';' después de la expresión")
        
        return expression
    
    def parse_seleccion(self) -> Optional[ASTNode]:
        """seleccion → if expression then lista_sentencias [ else lista_sentencias ] end"""
        if_token = self.consume('KEYWORD', 'if')
        if_node = ASTNode("IfStatement", line=if_token.line, column=if_token.column)
        
        # Parse condition
        condition = self.parse_expression()
        if condition:
            if_node.add_child(condition)
        
        # Expect 'then'
        if not self.consume('KEYWORD', 'then'):
            self.error("Se esperaba 'then' después de la condición del if")
        
        # Parse then statements
        then_block = ASTNode("ThenBlock")
        while self.current_token and not self.match('KEYWORD', 'else') and not self.match('KEYWORD', 'end'):
            stmt = self.parse_sentencia()
            if stmt:
                then_block.add_child(stmt)
        
        if_node.add_child(then_block)
        
        # Optional else block
        if self.match('KEYWORD', 'else'):
            self.advance()  # consume 'else'
            else_block = ASTNode("ElseBlock")
            
            while self.current_token and not self.match('KEYWORD', 'end'):
                stmt = self.parse_sentencia()
                if stmt:
                    else_block.add_child(stmt)
            
            if_node.add_child(else_block)
        
        # Expect 'end'
        if not self.consume('KEYWORD', 'end'):
            self.error("Se esperaba 'end' para cerrar la estructura if")
        
        return if_node
    
    def parse_iteracion(self) -> Optional[ASTNode]:
        """iteracion → while expression lista_sentencias end"""
        while_token = self.consume('KEYWORD', 'while')
        while_node = ASTNode("WhileLoop", line=while_token.line, column=while_token.column)
        
        # Parse condition
        condition = self.parse_expression()
        if condition:
            while_node.add_child(condition)
        
        # Parse body
        body = ASTNode("WhileBody")
        while self.current_token and not self.match('KEYWORD', 'end'):
            stmt = self.parse_sentencia()
            if stmt:
                body.add_child(stmt)
        
        while_node.add_child(body)
        
        # Expect 'end'
        if not self.consume('KEYWORD', 'end'):
            self.error("Se esperaba 'end' para cerrar el while")
        
        return while_node
    
    def parse_repeticion(self) -> Optional[ASTNode]:
        """repeticion → do lista_sentencias while expression"""
        do_token = self.consume('KEYWORD', 'do')
        do_node = ASTNode("DoWhileLoop", line=do_token.line, column=do_token.column)
        
        # Parse body
        body = ASTNode("DoBody")
        while self.current_token and not self.match('KEYWORD', 'while'):
            stmt = self.parse_sentencia()
            if stmt:
                body.add_child(stmt)
        
        do_node.add_child(body)
        
        # Expect 'while'
        if not self.consume('KEYWORD', 'while'):
            self.error("Se esperaba 'while' en la estructura do-while")
        
        # Parse condition
        condition = self.parse_expression()
        if condition:
            do_node.add_child(condition)
        
        return do_node
    
    def parse_sent_in(self) -> Optional[ASTNode]:
        """sent_in → cin >> id ;"""
        cin_token = self.consume('KEYWORD', 'cin')
        cin_node = ASTNode("InputStatement", line=cin_token.line, column=cin_token.column)
        
        # Expect '>>'
        if not self.consume('REL_OP', '>>'):
            self.error("Se esperaba '>>' después de 'cin'")
        
        # Expect identifier
        if self.match('IDENTIFIER'):
            id_token = self.consume('IDENTIFIER')
            cin_node.add_child(ASTNode("Identifier", id_token.value, id_token.line, id_token.column))
        else:
            self.error("Se esperaba un identificador después de 'cin >>'")
        
        # Expect ';'
        if not self.consume('DELIMITER', ';'):
            self.error("Se esperaba ';' después de la sentencia de entrada")
        
        return cin_node
    
    def parse_sent_out(self) -> Optional[ASTNode]:
        """sent_out → cout << salida (multiple outputs)"""
        cout_token = self.consume('KEYWORD', 'cout')
        cout_node = ASTNode("OutputStatement", line=cout_token.line, column=cout_token.column)
        
        # Expect '<<'
        if not self.consume('REL_OP', '<<'):
            self.error("Se esperaba '<<' después de 'cout'")
            return cout_node
        
        # Parse first output element
        if self.match('STRING'):
            token = self.consume('STRING')
            cout_node.add_child(ASTNode("String", token.value, token.line, token.column))
        else:
            expression = self.parse_expression()
            if expression:
                cout_node.add_child(expression)
            else:
                self.error("Se esperaba cadena o expresión después de '<<'")
        
        # Parse additional output elements
        while self.match('REL_OP', '<<'):
            self.advance()  # consume '<<'
            if self.match('STRING'):
                token = self.consume('STRING')
                cout_node.add_child(ASTNode("String", token.value, token.line, token.column))
            else:
                expression = self.parse_expression()
                if expression:
                    cout_node.add_child(expression)
                else:
                    self.error("Se esperaba cadena o expresión después de '<<'")
                    break
        
        return cout_node
    
    def parse_expression(self) -> Optional[ASTNode]:
        """expression → expression_simple [ rel_op expresion_simple ]"""
        left = self.parse_expression_simple()
        
        if self.match('REL_OP') and self.current_token.value in ['<', '<=', '>', '>=', '==', '!=']:
            op_token = self.consume('REL_OP')
            right = self.parse_expression_simple()
            
            binary_op = ASTNode("BinaryOperation", op_token.value, op_token.line, op_token.column)
            if left:
                binary_op.add_child(left)
            if right:
                binary_op.add_child(right)
            
            return binary_op
        
        return left
    
    def parse_expression_simple(self) -> Optional[ASTNode]:
        """expression_simple → expression_simple suma_op termino | termino"""
        left = self.parse_termino()
        
        while self.match('ARITH_OP') and self.current_token.value in ['+', '-']:  # Solo + y - binarios
            op_token = self.consume('ARITH_OP')
            right = self.parse_termino()
            
            binary_op = ASTNode("BinaryOperation", op_token.value, op_token.line, op_token.column)
            if left:
                binary_op.add_child(left)
            if right:
                binary_op.add_child(right)
            
            left = binary_op
        
        return left
    
    def parse_termino(self) -> Optional[ASTNode]:
        """termino → termino mult_op factor | factor"""
        left = self.parse_factor()
        
        while self.match('ARITH_OP') and self.current_token.value in ['*', '/', '%']:  # Added '%'
            op_token = self.consume('ARITH_OP')
            right = self.parse_factor()
            
            binary_op = ASTNode("BinaryOperation", op_token.value, op_token.line, op_token.column)
            if left:
                binary_op.add_child(left)
            if right:
                binary_op.add_child(right)
            
            left = binary_op
        
        return left
    
    def parse_factor(self) -> Optional[ASTNode]:
        """factor → componente pot_op factor | componente (right associative)"""
        left = self.parse_componente()
        
        if self.match('ARITH_OP') and self.current_token.value == '^':
            op_token = self.consume('ARITH_OP')
            right = self.parse_factor()  # Right associative
            
            binary_op = ASTNode("BinaryOperation", op_token.value, op_token.line, op_token.column)
            if left:
                binary_op.add_child(left)
            if right:
                binary_op.add_child(right)
            
            return binary_op
        
        return left
    
    def parse_componente(self) -> Optional[ASTNode]:
        """componente → ( expression ) | número | id | bool | op_logico componente | op_unario componente | componente op_unario_post"""
        # Unary prefix operators: +, -, ++, --, !
        if (self.match('ARITH_OP') and self.current_token.value in ['+', '-']) or \
           (self.match('INCREMENT_OP')) or \
           (self.match('DECREMENT_OP')) or \
           (self.match('LOGIC_OP') and self.current_token.value == '!'):
            
            if self.match('ARITH_OP'):
                op_token = self.consume('ARITH_OP')
            elif self.match('INCREMENT_OP'):
                op_token = self.consume('INCREMENT_OP')
            elif self.match('DECREMENT_OP'):
                op_token = self.consume('DECREMENT_OP')
            else:  # LOGIC_OP '!'
                op_token = self.consume('LOGIC_OP')
            
            operand = self.parse_componente()
            unary_op = ASTNode("UnaryOperation", op_token.value, op_token.line, op_token.column, [operand])
            return unary_op
        
        # Parse primary expression
        if self.match('DELIMITER', '('):
            self.advance()  # consume '('
            expression = self.parse_expression()
            if not self.consume('DELIMITER', ')'):
                self.error("Se esperaba ')' para cerrar la expresión")
            primary = expression
        elif self.match('INT'):
            token = self.consume('INT')
            primary = ASTNode("Number", token.value, token.line, token.column)
        elif self.match('FLOAT'):
            token = self.consume('FLOAT')
            primary = ASTNode("Number", token.value, token.line, token.column)
        elif self.match('IDENTIFIER'):
            token = self.consume('IDENTIFIER')
            primary = ASTNode("Identifier", token.value, token.line, token.column)
        elif self.match('KEYWORD') and self.current_token.value in ['true', 'false']:
            token = self.consume('KEYWORD')
            primary = ASTNode("Boolean", token.value, token.line, token.column)
        else:
            self.error(f"Expresión no válida: '{self.current_token.value if self.current_token else 'EOF'}'")
            return None
        
        # Postfix operators: ++, --
        while self.match('INCREMENT_OP') or self.match('DECREMENT_OP'):
            op_token = self.consume(self.current_token.token_type)
            primary = ASTNode("PostfixOperation", op_token.value, op_token.line, op_token.column, [primary])
        
        return primary
    
    def display_results(self):
        """Display parsing results"""
        if self.ast:
            print("=== ABSTRACT SYNTAX TREE ===")
            print(json.dumps(self.ast.to_dict(), indent=2, ensure_ascii=False))
            print()
        
        if self.errors:
            error_table = PrettyTable()
            error_table.field_names = ["Descripción", "Línea", "Columna"]
            for error in self.errors:
                error_table.add_row([error.description, error.line, error.column])
            
            print("=== ERRORES SINTÁCTICOS ===", file=sys.stderr)
            print(error_table, file=sys.stderr)
        else:
            print("Análisis sintáctico completado sin errores.")

def main():
    if len(sys.argv) < 2:
        print("Usage: python syntax_analyzer.py <file>", file=sys.stderr)
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    try:
        analyzer = SyntaxAnalyzer()
        
        if not analyzer.load_tokens(file_path):
            print("Error: No se pudieron cargar los tokens", file=sys.stderr)
            sys.exit(1)
        
        ast = analyzer.parse()
        analyzer.display_results()
        
        # Save AST to JSON file for IDE integration
        if ast:
            ast_file = file_path.replace('.txt', '_ast.json')
            with open(ast_file, 'w', encoding='utf-8') as f:
                json.dump(ast.to_dict(), f, indent=2, ensure_ascii=False)
                
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()