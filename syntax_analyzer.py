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
        self.current_token_index = 0
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
            self.current_token_index = 0
            self.current_token = self.tokens[0] if self.tokens else None
            return True
        return False
    
    def _parse_tokens_from_output(self, output: str) -> List[Token]:
        """Parse tokens from lexical analyzer output"""
        tokens = []
        lines = output.split('\n')
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
        error_msg = f"Se esperaba '{expected_value or expected_type}' pero se encontró '{self.current_token.value if self.current_token else 'EOF'}'"
        if self.current_token:
            error_location = (self.current_token.line, self.current_token.column, error_msg)
            if error_location not in self.error_locations:
                self.error_locations.add(error_location)
                self.error(error_msg)
        else:
            self.error(error_msg)
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
        sync_tokens = {';', '}', 'end', 'while', 'do', 'if', 'else', 'cin', 'cout', 'then', 'main', 'int', 'float', 'bool', 'string'}
        
        while self.current_token and self.current_token.value not in sync_tokens:
            self.advance()
        if self.current_token and self.current_token.value in sync_tokens:
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
        program_node = ASTNode("programa", line=1, column=1)
        
        main_token = self.consume('KEYWORD', 'main')
        if not main_token:
            return program_node
        program_node.add_child(ASTNode("main", main_token.value, main_token.line, main_token.column))
        
        if not self.consume('DELIMITER', '{'):
            return program_node
        program_node.add_child(ASTNode("{", "{", main_token.line, main_token.column))
        
        declarations = self.parse_lista_declaracion()
        if declarations:
            program_node.add_child(declarations)
        
        if not self.consume('DELIMITER', '}'):
            return program_node
        program_node.add_child(ASTNode("}", "}", self.current_token.line if self.current_token else 0, self.current_token.column if self.current_token else 0))
        
        return program_node
    
    def parse_lista_declaracion(self) -> Optional[ASTNode]:
        """lista_declaracion → (declaracion | sentencia)*"""
        nodo = ASTNode("lista_declaracion")
        while self.current_token and self.current_token.value != '}':
            decl = self.parse_declaracion()
            if decl:
                nodo.add_child(decl)
            else:
                self.synchronize()
        return nodo if nodo.children else None
    
    def parse_declaracion(self) -> Optional[ASTNode]:
        """declaracion → declaracion_variable | sentencia"""
        if self.match('KEYWORD') and self.current_token.value in ['int', 'float', 'bool', 'string']:
            return self.parse_declaracion_variable()
        return self.parse_sentencia()
    
    def parse_declaracion_variable(self) -> Optional[ASTNode]:
        """declaracion_variable → tipo identificador ( , identificador )* [ = expresion ] ;"""
        tipo_token = self.consume('KEYWORD')
        if not tipo_token or tipo_token.value not in ['int', 'float', 'bool', 'string']:
            return None
        
        nodo = ASTNode(tipo_token.value, tipo_token.value, tipo_token.line, tipo_token.column)
        
        id_token = self.consume('IDENTIFIER')
        if id_token:
            nodo.add_child(ASTNode("id", id_token.value, id_token.line, id_token.column))
        
        while self.match('DELIMITER', ','):
            self.advance()
            next_id = self.consume('IDENTIFIER')
            if next_id:
                nodo.add_child(ASTNode("id", next_id.value, next_id.line, next_id.column))
            else:
                break
        
        if self.match('ASSIGN_OP', '='):
            self.advance()
            expr = self.parse_expresion()
            if expr:
                nodo.add_child(expr)
        
        if not self.consume('DELIMITER', ';'):
            self.synchronize()
        return nodo
    
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
            self.synchronize()
            return None
    
    def parse_seleccion(self) -> Optional[ASTNode]:
        """seleccion → if expresion then lista_sentencias [ else lista_sentencias ] end"""
        nodo = ASTNode("seleccion", line=self.current_token.line, column=self.current_token.column)
        si = self.consume('KEYWORD', 'if')
        if si:
            nodo.add_child(ASTNode("if", si.value, si.line, si.column))
        
        expr = self.parse_expresion()
        if expr:
            nodo.add_child(expr)
        
        entonces = self.consume('KEYWORD', 'then')
        if entonces:
            nodo.add_child(ASTNode("then", entonces.value, entonces.line, entonces.column))
        
        cuerpo_then = self.parse_lista_sentencias()
        if cuerpo_then:
            nodo.add_child(cuerpo_then)
        
        if self.match('KEYWORD', 'else'):
            sino = self.consume('KEYWORD', 'else')
            if sino:
                nodo.add_child(ASTNode("else", sino.value, sino.line, sino.column))
                cuerpo_else = self.parse_lista_sentencias()
                if cuerpo_else:
                    nodo.add_child(cuerpo_else)
        
        fin = self.consume('KEYWORD', 'end')
        if fin:
            nodo.add_child(ASTNode("end", fin.value, fin.line, fin.column))
        
        return nodo
    
    def parse_iteracion(self) -> Optional[ASTNode]:
        """iteracion → while expresion lista_sentencias end"""
        nodo = ASTNode("iteracion", line=self.current_token.line, column=self.current_token.column)
        mientras = self.consume('KEYWORD', 'while')
        if mientras:
            nodo.add_child(ASTNode("while", mientras.value, mientras.line, mientras.column))
        
        expr = self.parse_expresion()
        if expr:
            nodo.add_child(expr)
        
        cuerpo = self.parse_lista_sentencias()
        if cuerpo:
            nodo.add_child(cuerpo)
        
        fin = self.consume('KEYWORD', 'end')
        if fin:
            nodo.add_child(ASTNode("end", fin.value, fin.line, fin.column))
        
        return nodo
    
    def parse_repeticion(self) -> Optional[ASTNode]:
        """repeticion → do lista_sentencias while expresion ;"""
        nodo = ASTNode("repeticion", line=self.current_token.line, column=self.current_token.column)
        hacer = self.consume('KEYWORD', 'do')
        if hacer:
            nodo.add_child(ASTNode("do", hacer.value, hacer.line, hacer.column))
        
        cuerpo = self.parse_lista_sentencias()
        if cuerpo:
            nodo.add_child(cuerpo)
        
        hasta = self.consume('KEYWORD', 'while')  # Changed from 'until' to 'while' to match p2.txt
        if hasta:
            nodo.add_child(ASTNode("while", hasta.value, hasta.line, hasta.column))
        
        expr = self.parse_expresion()
        if expr:
            nodo.add_child(expr)
        
        if not self.consume('DELIMITER', ';'):
            self.synchronize()
        
        return nodo
    
    def parse_sent_in(self) -> Optional[ASTNode]:
        """sent_in → cin >> id ( >> id )* ;"""
        nodo = ASTNode("sent_in", line=self.current_token.line, column=self.current_token.column)
        cin = self.consume('KEYWORD', 'cin')
        if cin:
            nodo.add_child(ASTNode("cin", cin.value, cin.line, cin.column))
        
        while self.match('REL_OP', '>>'):
            flecha = self.consume('REL_OP', '>>')
            if flecha:
                nodo.add_child(ASTNode(">>", flecha.value, flecha.line, flecha.column))
            
            identificador = self.consume('IDENTIFIER')
            if identificador:
                nodo.add_child(ASTNode("id", identificador.value, identificador.line, identificador.column))
            else:
                break
        
        if not self.consume('DELIMITER', ';'):
            self.synchronize()
        return nodo
    
    def parse_sent_out(self) -> Optional[ASTNode]:
        """sent_out → cout << (cadena | expresion) ( << (cadena | expresion) )* ;"""
        nodo = ASTNode("sent_out", line=self.current_token.line, column=self.current_token.column)
        cout = self.consume('KEYWORD', 'cout')
        if cout:
            nodo.add_child(ASTNode("cout", cout.value, cout.line, cout.column))
        
        while self.match('REL_OP', '<<'):
            op = self.consume('REL_OP', '<<')
            if op:
                nodo.add_child(ASTNode("<<", op.value, op.line, op.column))
            
            if self.match('STRING'):
                cadena = self.consume('STRING')
                nodo.add_child(ASTNode("cadena", cadena.value, cadena.line, cadena.column))
            else:
                expr = self.parse_expresion()
                if expr:
                    nodo.add_child(expr)
                else:
                    break
        
        if not self.consume('DELIMITER', ';'):
            self.synchronize()
        return nodo
    
    def parse_asignacion(self) -> Optional[ASTNode]:
        """asignacion → id ( = | ++ | -- ) (expresion | cadena) ;"""
        id_token = self.consume('IDENTIFIER')
        if not id_token:
            return None
        
        op_token = self.current_token
        if not op_token or op_token.token_type not in ['ASSIGN_OP', 'INCREMENT_OP', 'DECREMENT_OP']:
            self.error("Se esperaba '=', '++' o '--' en la asignación")
            self.synchronize()
            return None
        
        self.advance()
        nodo = ASTNode("asignacion", op_token.value, op_token.line, op_token.column)
        nodo.add_child(ASTNode("id", id_token.value, id_token.line, id_token.column))
        
        if op_token.value in ['++', '--']:
            op_aritmetico = ASTNode("op_aritmetico", '+' if op_token.value == '++' else '-', op_token.line, op_token.column)
            op_aritmetico.add_child(ASTNode("id", id_token.value, id_token.line, id_token.column))
            op_aritmetico.add_child(ASTNode("num_entero", "1", op_token.line, op_token.column))
            
            asignacion_nodo = ASTNode("asignacion", "=", op_token.line, op_token.column)
            asignacion_nodo.add_child(ASTNode("id", id_token.value, id_token.line, id_token.column))
            asignacion_nodo.add_child(op_aritmetico)
            if not self.consume('DELIMITER', ';'):
                self.synchronize()
            return asignacion_nodo
        else:
            if self.match('STRING'):
                cadena = self.consume('STRING')
                nodo.add_child(ASTNode("cadena", cadena.value, cadena.line, cadena.column))
            else:
                expr = self.parse_expresion()
                if expr:
                    nodo.add_child(expr)
            if not self.consume('DELIMITER', ';'):
                self.synchronize()
            return nodo
    
    def parse_lista_sentencias(self) -> Optional[ASTNode]:
        """lista_sentencias → sentencia*"""
        nodo = ASTNode("lista_sentencias")
        while self.current_token and self.current_token.value not in {'end', 'else', 'while', '}'}:
            sent = self.parse_sentencia()
            if sent:
                nodo.add_child(sent)
            else:
                break
        return nodo if nodo.children else None
    
    def parse_expresion(self) -> Optional[ASTNode]:
        """expresion → expresion_relacional ( op_logico expresion_relacional )*"""
        nodo = self.parse_expresion_relacional()
        if not nodo:
            return None
        
        while self.match('LOGIC_OP'):
            op_token = self.consume('LOGIC_OP')
            der = self.parse_expresion_relacional()
            if der:
                op_nodo = ASTNode("op_logico", op_token.value, op_token.line, op_token.column)
                op_nodo.add_child(nodo)
                op_nodo.add_child(der)
                nodo = op_nodo
            else:
                self.error(f"Se esperaba una expresión después del operador lógico '{op_token.value}'")
                break
        return nodo
    
    def parse_expresion_relacional(self) -> Optional[ASTNode]:
        """expresion_relacional → expresion_simple [ op_relacional expresion_simple ]"""
        nodo = self.parse_expresion_simple()
        if not nodo:
            return None
        
        if self.match('REL_OP'):
            op_token = self.consume('REL_OP')
            der = self.parse_expresion_simple()
            if der:
                op_nodo = ASTNode("rel_op", op_token.value, op_token.line, op_token.column)
                op_nodo.add_child(nodo)
                op_nodo.add_child(der)
                return op_nodo
            else:
                self.error(f"Se esperaba una expresión después del operador relacional '{op_token.value}'")
        return nodo
    
    def parse_expresion_simple(self) -> Optional[ASTNode]:
        """expresion_simple → termino ( ( + | - ) termino )*"""
        nodo = self.parse_termino()
        if not nodo:
            return None
        
        while self.match('ARITH_OP') and self.current_token.value in ['+', '-']:
            op_token = self.consume('ARITH_OP')
            der = self.parse_termino()
            if der:
                op_nodo = ASTNode("arit_op", op_token.value, op_token.line, op_token.column)
                op_nodo.add_child(nodo)
                op_nodo.add_child(der)
                nodo = op_nodo
            else:
                self.error(f"Se esperaba un término después del operador '{op_token.value}'")
                break
        return nodo
    
    def parse_termino(self) -> Optional[ASTNode]:
        """termino → componente ( ( * | / | % ) componente )*"""
        nodo = self.parse_componente()
        if not nodo:
            return None
        
        while self.match('ARITH_OP') and self.current_token.value in ['*', '/', '%']:
            op_token = self.consume('ARITH_OP')
            der = self.parse_componente()
            if der:
                op_nodo = ASTNode("arit_op", op_token.value, op_token.line, op_token.column)
                op_nodo.add_child(nodo)
                op_nodo.add_child(der)
                nodo = op_nodo
            else:
                self.error(f"Se esperaba un componente después del operador '{op_token.value}'")
                break
        return nodo
    
    def parse_componente(self) -> Optional[ASTNode]:
        """componente → ( expresion ) | num_entero | num_flotante | id | bool_val | cadena | ! componente"""
        if self.match('DELIMITER', '('):
            self.advance()
            nodo = self.parse_expresion()
            if not self.consume('DELIMITER', ')'):
                self.synchronize()
            return nodo
        elif self.match('INT'):
            token = self.consume('INT')
            return ASTNode("num_entero", token.value, token.line, token.column)
        elif self.match('FLOAT'):
            token = self.consume('FLOAT')
            return ASTNode("num_flotante", token.value, token.line, token.column)
        elif self.match('IDENTIFIER'):
            token = self.consume('IDENTIFIER')
            return ASTNode("id", token.value, token.line, token.column)
        elif self.match('KEYWORD') and self.current_token.value in ['true', 'false']:
            token = self.consume('KEYWORD')
            return ASTNode("bool_val", token.value, token.line, token.column)
        elif self.match('STRING'):
            token = self.consume('STRING')
            return ASTNode("cadena", token.value, token.line, token.column)
        elif self.match('LOGIC_OP', '!'):
            op = self.consume('LOGIC_OP', '!')
            nodo = ASTNode("log_op", op.value, op.line, op.column)
            comp = self.parse_componente()
            if comp:
                nodo.add_child(comp)
            else:
                self.error(f"Se esperaba un componente después del operador lógico '!'")
            return nodo
        self.error(f"Componente no válido: '{self.current_token.value if self.current_token else 'EOF'}'")
        return None
    
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