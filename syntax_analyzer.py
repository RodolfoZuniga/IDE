#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from prettytable import PrettyTable
import enum

# Definimos los tipos de tokens como un enumerado para alinearnos con ide copy.py
class TokenType(enum.Enum):
    INTEGER = "INT"
    REAL = "FLOAT"
    IDENTIFIER = "IDENTIFIER"
    RESERVED_WORD = "KEYWORD"
    ARITHMETIC_OPERATOR = "ARITH_OP"
    RELATIONAL_OPERATOR = "REL_OP"
    LOGICAL_OPERATOR = "LOGIC_OP"
    SYMBOL = "DELIMITER"
    ASSIGNMENT = "ASSIGN_OP"
    COMMENT = "COMMENT"
    STREAM_OPERATOR = "STREAM_OP"
    STRING_LITERAL = "STRING"
    CHARACTER_LITERAL = "CHAR"
    HEX_INTEGER = "HEX_INT"
    OCTAL_INTEGER = "OCT_INT"
    BINARY_INTEGER = "BIN_INT"
    INCREMENT_OP = "INCREMENT_OP"
    DECREMENT_OP = "DECREMENT_OP"

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
        if child:
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
        self.current_token_index = -1
        self.current_token = None
        self.errors = []
        self.ast = None
        self.error_locations = set()  # Track errors to avoid duplicates
    
    def load_tokens(self, file_path: str):
        """Load tokens from lexical analyzer output file"""
        try:
            import subprocess
            import os
            
            script_dir = os.path.dirname(os.path.abspath(__file__))
            lexical_analyzer_path = os.path.join(script_dir, 'lexical_analyzer.py')
            
            result = subprocess.run(
                ['python', lexical_analyzer_path, file_path],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            self.tokens = self._parse_tokens_from_output(result.stdout)
            
            if not self.tokens:
                tokens_file = file_path.replace('.txt', '_tokens.json')
                if os.path.exists(tokens_file):
                    with open(tokens_file, 'r', encoding='utf-8') as f:
                        tokens_data = json.load(f)
                        self.tokens = [Token(**token_data) for token_data in tokens_data]
                        
        except Exception as e:
            print(f"Error loading tokens: {e}", file=sys.stderr)
            return False
        
        if self.tokens:
            self.current_token_index = -1
            self.advance()  # Inicializamos el primer token
            return True
        return False
    
    def _parse_tokens_from_output(self, output: str) -> List[Token]:
        """Parse tokens from lexical analyzer output"""
        tokens = []
        lines = output.split('\n')
        skip_tokens = {'WHITESPACE', 'NEWLINE', 'COMMENT_SINGLE', 'COMMENT_MULTI', 'COMMENT'}
        
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
                        
                        # Mapeamos los tipos de tokens a los de TokenType
                        if value == '++':
                            token_type = TokenType.INCREMENT_OP.value
                        elif value == '--':
                            token_type = TokenType.DECREMENT_OP.value
                        elif value == '^' or value == '%':
                            token_type = TokenType.ARITHMETIC_OPERATOR.value
                        elif value in ['+', '-', '*', '/', '+=', '-=', '*=', '/=', '%=', '^=']:
                            token_type = TokenType.ARITHMETIC_OPERATOR.value
                        elif value in ['=', '==', '!=', '<', '>', '<=', '>=']:
                            token_type = TokenType.ASSIGNMENT.value if value == '=' else TokenType.RELATIONAL_OPERATOR.value
                        elif value in ['&&', '||', '!']:
                            token_type = TokenType.LOGICAL_OPERATOR.value
                        elif value in ['>>', '<<']:
                            token_type = TokenType.STREAM_OPERATOR.value
                        elif value in ['(', ')', '{', '}', ',', ';', '[', ']']:
                            token_type = TokenType.SYMBOL.value
                        elif token_type == 'KEYWORD' and value in ['true', 'false']:
                            token_type = TokenType.RESERVED_WORD.value
                        
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
        return self.current_token
    
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
    
    def consume(self, expected_type: str, expected_value: str = None, optional: bool = False) -> Optional[Token]:
        """Consume current token if it matches expected type/value"""
        if self.match(expected_type, expected_value):
            token = self.current_token
            self.advance()
            return token
        if not optional:
            error_msg = f"Se esperaba '{expected_value or expected_type}' pero se encontró '{self.current_token.value if self.current_token else 'EOF'}'"
            error_location = (self.current_token.line if self.current_token else 0,
                            self.current_token.column if self.current_token else 0,
                            error_msg)
            if error_location not in self.error_locations:
                self.error_locations.add(error_location)
                self.error(error_msg)
        return None
    
    def error(self, message: str, line: int = None, column: int = None):
        """Add a syntax error"""
        error = SyntaxError(
            message,
            line if line is not None else (self.current_token.line if self.current_token else 0),
            column if column is not None else (self.current_token.column if self.current_token else 0)
        )
        self.errors.append(error)
    
    def synchronize(self, recover_token: str = None, recover_type: str = None):
        """Synchronize after an error by skipping to next statement"""
        sync_tokens = {';', '}', 'end', 'while', 'do', 'if', 'else', 'cin', 'cout', 'then', 'main', 'int', 'float', 'bool', 'string', 'until'}
        
        while self.current_token:
            if (recover_token and self.current_token.value == recover_token) or \
               (recover_type and self.current_token.token_type == recover_type) or \
               self.current_token.value in sync_tokens:
                if self.current_token.value in sync_tokens:
                    self.advance()
                break
            self.advance()
    
    def parse(self) -> Optional[ASTNode]:
        """Main parsing method"""
        try:
            self.ast = self.parse_program()
            if self.current_token is not None:
                self.error("Hay tokens adicionales después del programa principal")
            return self.ast
        except Exception as e:
            self.error(f"Unexpected error during parsing: {str(e)}")
            return self.ast
    
    def parse_program(self) -> Optional[ASTNode]:
        """programa → main { lista_declaracion }"""
        try:
            program_node = ASTNode("programa", line=1, column=1)
            main_token = self.consume(TokenType.RESERVED_WORD.value, 'main')
            if not main_token:
                return program_node
            program_node.add_child(ASTNode("main", main_token.value, main_token.line, main_token.column))
            
            if not self.consume(TokenType.SYMBOL.value, '{'):
                return program_node
            program_node.add_child(ASTNode("{", "{", main_token.line, main_token.column))
            
            declarations = self.parse_lista_declaracion()
            if declarations:
                program_node.add_child(declarations)
            
            if not self.consume(TokenType.SYMBOL.value, '}', optional=True):
                self.synchronize(recover_token='}')
                if self.current_token and self.current_token.value == '}':
                    self.advance()
            program_node.add_child(ASTNode("}", "}", self.current_token.line if self.current_token else 0, self.current_token.column if self.current_token else 0))
            
            return program_node
        except Exception as e:
            self.error(f"Error en programa: {str(e)}")
            self.synchronize(recover_token='}')
            return ASTNode("programa", children=[ASTNode("main", children=[])])
    
    def parse_lista_declaracion(self) -> Optional[ASTNode]:
        """lista_declaracion → (declaracion_variable | sentencia)*"""
        nodo = ASTNode("lista_declaracion")
        while self.current_token and self.current_token.value != '}':
            try:
                if self.current_token.value in ['int', 'float', 'bool']:
                    decl = self.parse_declaracion_variable()
                    if decl:
                        nodo.add_child(decl)
                else:
                    stmt = self.parse_sentencia()
                    if stmt:
                        nodo.add_child(stmt)
            except Exception as e:
                self.error(f"Error en declaración: {str(e)}")
                self.synchronize(recover_token=';')
        return nodo if nodo.children else None
    
    def parse_declaracion_variable(self) -> Optional[ASTNode]:
        """declaracion_variable → tipo identificador ( , identificador )* ;"""
        try:
            start_token = self.current_token
            tipo_token = self.consume(TokenType.RESERVED_WORD.value)
            if not tipo_token or tipo_token.value not in ['int', 'float', 'bool']:
                self.error(f"Tipo de dato no válido: {tipo_token.value if tipo_token else 'ninguno'}")
                self.synchronize(recover_token=';')
                return ASTNode("declaracion_variable", value="unknown", children=[])
            
            nodo = ASTNode("declaracion_variable", tipo_token.value, tipo_token.line, tipo_token.column)
            id_token = self.consume(TokenType.IDENTIFIER.value)
            if id_token:
                nodo.add_child(ASTNode("id", id_token.value, id_token.line, id_token.column))
            
            while self.match(TokenType.SYMBOL.value, ','):
                self.advance()
                next_id = self.consume(TokenType.IDENTIFIER.value)
                if next_id:
                    nodo.add_child(ASTNode("id", next_id.value, next_id.line, next_id.column))
                else:
                    self.error("Se esperaba un identificador después de ','")
                    break
            
            expected_col = start_token.column + len(tipo_token.value) + sum(
                len(child.value) + 2 for child in nodo.children
            ) - 1
            if not self.current_token or self.current_token.value != ';':
                if self.current_token and self.current_token.token_type == TokenType.RESERVED_WORD.value and \
                   self.current_token.value in ['int', 'float', 'bool']:
                    self.error(f"Se esperaba ';' y se encontró '{self.current_token.value}'", expected_col=expected_col)
                    return nodo
                else:
                    self.error("Se esperaba ';'", expected_col=expected_col)
                    self.synchronize(recover_token=';')
            else:
                self.consume(TokenType.SYMBOL.value, ';')
            
            return nodo
        except Exception as e:
            self.error(f"Error en declaración de variable: {str(e)}")
            self.synchronize(recover_token=';')
            return ASTNode("declaracion_variable", value="unknown", children=[])
    
    def parse_sentencia(self) -> Optional[ASTNode]:
        """sentencia → seleccion | iteracion | repeticion | sent_in | sent_out | asignacion | ;"""
        if not self.current_token:
            return None
        
        if self.match(TokenType.SYMBOL.value, ';'):
            self.advance()
            return ASTNode("sent_expresion")
        
        try:
            if self.match(TokenType.RESERVED_WORD.value, 'if'):
                return self.parse_seleccion()
            elif self.match(TokenType.RESERVED_WORD.value, 'while'):
                return self.parse_iteracion()
            elif self.match(TokenType.RESERVED_WORD.value, 'do'):
                return self.parse_repeticion()
            elif self.match(TokenType.RESERVED_WORD.value, 'cin'):
                return self.parse_sent_in()
            elif self.match(TokenType.RESERVED_WORD.value, 'cout'):
                return self.parse_sent_out()
            elif self.match(TokenType.IDENTIFIER.value):
                return self.parse_asignacion()
            else:
                self.error(f"Sentencia no válida: {self.current_token.value}")
                self.synchronize(recover_token=';')
                return None
        except Exception as e:
            self.error(f"Error procesando sentencia: {str(e)}")
            self.synchronize(recover_token=';')
            return None
    
    def parse_seleccion(self) -> Optional[ASTNode]:
        """seleccion → if expresion then lista_sentencias [ else lista_sentencias ] end"""
        try:
            nodo = ASTNode("seleccion", line=self.current_token.line, column=self.current_token.column)
            if_token = self.consume(TokenType.RESERVED_WORD.value, 'if')
            if if_token:
                nodo.add_child(ASTNode("if", if_token.value, if_token.line, if_token.column))
            
            expr = self.parse_expresion()
            if expr:
                nodo.add_child(expr)
            
            then_token = self.consume(TokenType.RESERVED_WORD.value, 'then')
            if then_token:
                nodo.add_child(ASTNode("then", then_token.value, then_token.line, then_token.column))
            
            then_block = self.parse_lista_sentencias(context='if_then')
            if then_block:
                nodo.add_child(ASTNode("then_block", children=then_block.children))
            
            if self.match(TokenType.RESERVED_WORD.value, 'else'):
                else_token = self.consume(TokenType.RESERVED_WORD.value, 'else')
                if else_token:
                    nodo.add_child(ASTNode("else", else_token.value, else_token.line, else_token.column))
                    else_block = self.parse_lista_sentencias(context='if_else')
                    if else_block:
                        nodo.add_child(ASTNode("else_block", children=else_block.children))
            
            self.consume(TokenType.RESERVED_WORD.value, 'end', optional=True)
            
            return nodo
        except Exception as e:
            self.error(f"Error en estructura if: {str(e)}")
            self.synchronize(recover_token='end')
            return ASTNode("seleccion", children=[])
    
    def parse_iteracion(self) -> Optional[ASTNode]:
        """iteracion → while expresion lista_sentencias end"""
        try:
            nodo = ASTNode("iteracion", line=self.current_token.line, column=self.current_token.column)
            while_token = self.consume(TokenType.RESERVED_WORD.value, 'while')
            if while_token:
                nodo.add_child(ASTNode("while", while_token.value, while_token.line, while_token.column))
            
            expr = self.parse_expresion()
            if expr:
                nodo.add_child(ASTNode("condicion", children=[expr]))
            
            body = self.parse_lista_sentencias(context='while')
            if body:
                nodo.add_child(ASTNode("cuerpo", children=body.children))
            
            self.consume(TokenType.RESERVED_WORD.value, 'end', optional=True)
            
            return nodo
        except Exception as e:
            self.error(f"Error en estructura while: {str(e)}")
            self.synchronize(recover_token='end')
            return ASTNode("iteracion", children=[ASTNode("condicion", children=[ASTNode("error", value="condicion_invalida")]), ASTNode("cuerpo", children=[])])
    
    def parse_repeticion(self) -> Optional[ASTNode]:
        """repeticion → do lista_sentencias until expresion ;"""
        try:
            nodo = ASTNode("repeticion", line=self.current_token.line, column=self.current_token.column)
            do_token = self.consume(TokenType.RESERVED_WORD.value, 'do')
            if do_token:
                nodo.add_child(ASTNode("do", do_token.value, do_token.line, do_token.column))
            
            body = self.parse_lista_sentencias(context='do_until')
            if body:
                nodo.add_child(ASTNode("cuerpo", children=body.children))
            
            until_token = self.consume(TokenType.RESERVED_WORD.value, 'until')
            if until_token:
                nodo.add_child(ASTNode("until", until_token.value, until_token.line, until_token.column))
            
            expr = self.parse_expresion()
            if expr:
                nodo.add_child(ASTNode("condicion", children=[expr]))
            
            self.consume(TokenType.SYMBOL.value, ';', optional=True)
            
            return nodo
        except Exception as e:
            self.error(f"Error en estructura do-until: {str(e)}")
            self.synchronize(recover_token=';')
            return ASTNode("repeticion", children=[])
    
    def parse_sent_in(self) -> Optional[ASTNode]:
        """sent_in → cin >> id ( >> id )* ;"""
        try:
            nodo = ASTNode("sent_in", line=self.current_token.line, column=self.current_token.column)
            cin_token = self.consume(TokenType.RESERVED_WORD.value, 'cin')
            if cin_token:
                nodo.add_child(ASTNode("cin", cin_token.value, cin_token.line, cin_token.column))
            
            while self.match(TokenType.STREAM_OPERATOR.value, '>>'):
                op_token = self.consume(TokenType.STREAM_OPERATOR.value, '>>')
                if op_token:
                    nodo.add_child(ASTNode(">>", op_token.value, op_token.line, op_token.column))
                
                id_token = self.consume(TokenType.IDENTIFIER.value)
                if id_token:
                    nodo.add_child(ASTNode("id", id_token.value, id_token.line, id_token.column))
                else:
                    self.error("Se esperaba un identificador después de '>>'")
                    break
            
            self.consume(TokenType.SYMBOL.value, ';', optional=True)
            return nodo
        except Exception as e:
            self.error(f"Error en sentencia cin: {str(e)}")
            self.synchronize(recover_token=';')
            return ASTNode("sent_in", value="unknown")
    
    def parse_sent_out(self) -> Optional[ASTNode]:
        """sent_out → cout << (cadena | expresion) ( << (cadena | expresion) )* ;"""
        try:
            nodo = ASTNode("sent_out", line=self.current_token.line, column=self.current_token.column)
            cout_token = self.consume(TokenType.RESERVED_WORD.value, 'cout')
            if cout_token:
                nodo.add_child(ASTNode("cout", cout_token.value, cout_token.line, cout_token.column))
            
            while self.match(TokenType.STREAM_OPERATOR.value, '<<'):
                op_token = self.consume(TokenType.STREAM_OPERATOR.value, '<<')
                if op_token:
                    nodo.add_child(ASTNode("<<", op_token.value, op_token.line, op_token.column))
                
                if self.match(TokenType.STRING_LITERAL.value):
                    string_token = self.consume(TokenType.STRING_LITERAL.value)
                    nodo.add_child(ASTNode("cadena", string_token.value, string_token.line, string_token.column))
                else:
                    expr = self.parse_expresion()
                    if expr:
                        nodo.add_child(expr)
                    else:
                        self.error("Se esperaba una cadena o expresión después de '<<'")
                        break
            
            self.consume(TokenType.SYMBOL.value, ';', optional=True)
            return nodo
        except Exception as e:
            self.error(f"Error en sentencia cout: {str(e)}")
            self.synchronize(recover_token=';')
            return ASTNode("sent_out", children=[])
    
    def parse_asignacion(self) -> Optional[ASTNode]:
        """asignacion → id ( = | ++ | -- | += | -= | *= | /= | %= | ^= ) (expresion | cadena) ;"""
        try:
            id_token = self.consume(TokenType.IDENTIFIER.value)
            if not id_token:
                self.error("Se esperaba un identificador")
                return ASTNode("asignacion", value="error", children=[])
            
            op_token = self.current_token
            if not op_token or op_token.token_type not in [TokenType.ASSIGNMENT.value, TokenType.INCREMENT_OP.value, 
                                                        TokenType.DECREMENT_OP.value, TokenType.ARITHMETIC_OPERATOR.value]:
                self.error("Se esperaba '=', '++', '--' o operador compuesto en la asignación")
                self.synchronize(recover_token=';')
                return ASTNode("asignacion", value=id_token.value, children=[])
            
            self.advance()
            nodo = ASTNode("asignacion", id_token.value, op_token.line, op_token.column)
            nodo.add_child(ASTNode("id", id_token.value, id_token.line, id_token.column))
            
            if op_token.value in ['++', '--']:
                operation = ASTNode("expresion_simple", '+' if op_token.value == '++' else '-', op_token.line, op_token.column)
                operation.add_child(ASTNode("id", id_token.value, id_token.line, id_token.column))
                operation.add_child(ASTNode("numero", "1", op_token.line, op_token.column))
                nodo.add_child(operation)
            elif op_token.value in ['+=', '-=', '*=', '/=', '%=', '^=']:
                operator = op_token.value[0]
                right_expr = self.parse_expresion()
                if right_expr:
                    operation = ASTNode("expresion_simple", operator, op_token.line, op_token.column)
                    operation.add_child(ASTNode("id", id_token.value, id_token.line, id_token.column))
                    operation.add_child(right_expr)
                    nodo.add_child(operation)
                else:
                    self.error(f"Se esperaba una expresión después de '{op_token.value}'")
            elif op_token.value == '=':
                if self.match(TokenType.STRING_LITERAL.value):
                    string_token = self.consume(TokenType.STRING_LITERAL.value)
                    nodo.add_child(ASTNode("cadena", string_token.value, string_token.line, string_token.column))
                else:
                    expr = self.parse_expresion()
                    if expr:
                        nodo.add_child(expr)
                    else:
                        self.error("Se esperaba una expresión o cadena después de '='")
            
            self.consume(TokenType.SYMBOL.value, ';', optional=True)
            return nodo
        except Exception as e:
            self.error(f"Error en asignación: {str(e)}")
            self.synchronize(recover_token=';')
            return ASTNode("asignacion", value="error", children=[])
    
    def parse_lista_sentencias(self, context: str = 'default') -> Optional[ASTNode]:
        """lista_sentencias → sentencia*"""
        nodo = ASTNode("lista_sentencias")
        while self.current_token and not self.should_stop_parsing(context):
            try:
                sent = self.parse_sentencia()
                if sent:
                    nodo.add_child(sent)
            except Exception as e:
                self.error(f"Error en sentencia: {str(e)}")
                self.synchronize(recover_token=';')
        return nodo if nodo.children else None
    
    def should_stop_parsing(self, context: str) -> bool:
        """Determina si se debe detener el parsing según el contexto"""
        if not self.current_token:
            return True
        
        value = self.current_token.value
        if self.current_token.token_type == TokenType.RESERVED_WORD.value and \
           value in ['int', 'float', 'bool']:
            return True
        
        if context == 'default':
            return value == '}'
        elif context == 'while':
            return value == 'end'
        elif context == 'do_until':
            return value == 'until'
        elif context == 'if_then':
            return value in ['else', 'end']
        elif context == 'if_else':
            return value == 'end'
        
        return False
    
    def parse_expresion(self) -> Optional[ASTNode]:
        """expresion → expresion_simple [ rel_op expresion_simple | op_logico expresion ]"""
        left = self.parse_expresion_simple()
        if not left:
            return None
        
        while self.current_token and (
            self.current_token.token_type == TokenType.RELATIONAL_OPERATOR.value or
            self.current_token.token_type == TokenType.LOGICAL_OPERATOR.value
        ):
            if self.current_token.token_type == TokenType.RELATIONAL_OPERATOR.value:
                op_token = self.consume(TokenType.RELATIONAL_OPERATOR.value)
                right = self.parse_expresion_simple()
                if right:
                    left = ASTNode("expresion_relacional", op_token.value, op_token.line, op_token.column, children=[left, right])
                else:
                    self.error(f"Se esperaba una expresión después de '{op_token.value}'")
                    break
            else:
                op_token = self.consume(TokenType.LOGICAL_OPERATOR.value)
                right = self.parse_expresion()
                if right:
                    left = ASTNode("expresion_logica", op_token.value, op_token.line, op_token.column, children=[left, right])
                else:
                    self.error(f"Se esperaba una expresión después de '{op_token.value}'")
                    break
        
        return left
    
    def parse_expresion_simple(self) -> Optional[ASTNode]:
        """expresion_simple → termino ( ( + | - | ++ | -- ) termino )*"""
        left = self.parse_termino()
        if not left:
            return None
        
        while self.current_token and (
            self.current_token.token_type == TokenType.ARITHMETIC_OPERATOR.value and self.current_token.value in ['+', '-', '++', '--'] or
            self.current_token.token_type in [TokenType.INCREMENT_OP.value, TokenType.DECREMENT_OP.value]
        ):
            if self.current_token.token_type == TokenType.INCREMENT_OP.value:
                op_token = self.consume(TokenType.INCREMENT_OP.value)
                op_value = '++'
            elif self.current_token.token_type == TokenType.DECREMENT_OP.value:
                op_token = self.consume(TokenType.DECREMENT_OP.value)
                op_value = '--'
            else:
                op_token = self.consume(TokenType.ARITHMETIC_OPERATOR.value)
                op_value = op_token.value
            
            right = self.parse_termino()
            if right:
                left = ASTNode("expresion_simple", op_value, op_token.line, op_token.column, children=[left, right])
            else:
                self.error(f"Se esperaba un término después de '{op_value}'")
                break
        return left
    
    def parse_termino(self) -> Optional[ASTNode]:
        """termino → factor ( ( * | / | % ) factor )*"""
        left = self.parse_factor()
        if not left:
            return None
        
        while self.match(TokenType.ARITHMETIC_OPERATOR.value) and self.current_token.value in ['*', '/', '%']:
            op_token = self.consume(TokenType.ARITHMETIC_OPERATOR.value)
            right = self.parse_factor()
            if right:
                left = ASTNode("termino", op_token.value, op_token.line, op_token.column, children=[left, right])
            else:
                self.error(f"Se esperaba un factor después de '{op_token.value}'")
                break
        return left
    
    def parse_factor(self) -> Optional[ASTNode]:
        """factor → componente ( ^ componente )*"""
        left = self.parse_componente()
        if not left:
            return None
        
        while self.match(TokenType.ARITHMETIC_OPERATOR.value, '^'):
            op_token = self.consume(TokenType.ARITHMETIC_OPERATOR.value, '^')
            right = self.parse_componente()
            if right:
                left = ASTNode("factor", op_token.value, op_token.line, op_token.column, children=[left, right])
            else:
                self.error(f"Se esperaba un componente después de '^'")
                break
        return left
    
    def parse_componente(self) -> Optional[ASTNode]:
        """componente → ( expresion ) | num_entero | num_flotante | id | bool_val | cadena | ! componente"""
        try:
            if self.match(TokenType.SYMBOL.value, '('):
                open_token = self.current_token
                self.advance()
                expr = self.parse_expresion()
                if not self.consume(TokenType.SYMBOL.value, ')'):
                    self.error(f"Se esperaba ')' para cerrar el paréntesis abierto en línea {open_token.line}, columna {open_token.column}")
                    self.synchronize(recover_token=';')
                return expr
            elif self.match(TokenType.INTEGER.value):
                token = self.consume(TokenType.INTEGER.value)
                return ASTNode("numero", token.value, token.line, token.column)
            elif self.match(TokenType.REAL.value):
                token = self.consume(TokenType.REAL.value)
                return ASTNode("numero", token.value, token.line, token.column)
            
            # --- INICIO DE LA CORRECCIÓN ---
            # 1. Comprobar 'true'/'false' (como KEYWORD) PRIMERO.
            elif self.match(TokenType.RESERVED_WORD.value) and self.current_token.value in ['true', 'false']:
                token = self.consume(TokenType.RESERVED_WORD.value)
                return ASTNode("bool", token.value, token.line, token.column)
            
            # 2. Comprobar si es un IDENTIFIER
            elif self.match(TokenType.IDENTIFIER.value):
                token = self.current_token
                
                # 2a. Comprobar si es 'true' o 'false' (en caso de que el léxico falle y lo marque como ID)
                if token.value in ['true', 'false']:
                    self.advance() # Consumir el token
                    return ASTNode("bool", token.value, token.line, token.column)
                
                # 2b. Si no, es un 'id' normal
                else:
                    token = self.consume(TokenType.IDENTIFIER.value) # Consume el ID
                    return ASTNode("id", token.value, token.line, token.column)
            # --- FIN DE LA CORRECCIÓN ---
                
            elif self.match(TokenType.STRING_LITERAL.value):
                token = self.consume(TokenType.STRING_LITERAL.value)
                return ASTNode("cadena", token.value, token.line, token.column)
            elif self.match(TokenType.LOGICAL_OPERATOR.value, '!'):
                op_token = self.consume(TokenType.LOGICAL_OPERATOR.value, '!')
                comp = self.parse_componente()
                if comp:
                    nodo = ASTNode("expresion_logica", op_token.value, op_token.line, op_token.column, children=[comp])
                    return nodo
                else:
                    self.error("Se esperaba un componente después de '!'")
            else:
                self.error(f"Componente no válido: {self.current_token.value if self.current_token else 'EOF'}")
                return None
        except Exception as e:
            self.error(f"Error en componente: {str(e)}")
            self.synchronize(recover_token=';')
            return ASTNode("componente", value="error")
    
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
        
        if ast:
            ast_file = file_path.replace('.txt', '_ast.json')
            with open(ast_file, 'w', encoding='utf-8') as f:
                json.dump(ast.to_dict(), f, indent=2, ensure_ascii=False)
                
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()