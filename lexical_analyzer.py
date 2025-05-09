#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import re
import io
from prettytable import PrettyTable

class Token:
    def __init__(self, token_type, value, line, column):
        self.token_type = token_type
        self.value = value
        self.line = line
        self.column = column
    
    def __str__(self):
        return f"Type: {self.token_type}, Value: {self.value}, Line: {self.line}, Column: {self.column}"

class LexicalError:
    def __init__(self, description, line, column):
        self.description = description
        self.line = line
        self.column = column
    
    def __str__(self):
        return f"Error: {self.description}, Line: {self.line}, Column: {self.column}"

class LexicalAnalyzer:
    def __init__(self):
        self.tokens = []
        self.errors = []
        
        # Definición de patrones para tokens
        self.token_specs = [
            ('COMMENT_SINGLE',  r'\/\/.*'),                     # Comentarios de una línea (//)
            ('COMMENT_MULTI',   r'\/\*[\s\S]*?\*\/'),           # Comentarios multilínea (/* */)
            ('STRING',          r'"([^"\\]|\\.)*"'),            # Strings con comillas dobles
            ('CHAR',            r'\'([^\'\\]|\\.)\''),          # Caracteres con comillas simples
            ('FLOAT',           r'\d+\.\d+([eE][+-]?\d+)?'),    # Números de punto flotante
            ('INT',             r'\d+'),                        # Enteros
            ('KEYWORD',         r'\b(if|else|end|do|while|switch|case|int|float|main|cin|cout|for|return|char|bool|real|then|until)\b'),  # Palabras clave
            ('LOGIC_OP',        r'(\&\&|\|\||!)'),              # Operadores lógicos
            ('REL_OP',          r'(<=|>=|==|!=|<|>)'),          # Operadores relacionales
            ('ASSIGN_OP',       r'='),                          # Operador de asignación
            ('ARITH_OP',        r'(\+|\-|\*|\/|\%|\^|\+\+|\-\-)'), # Operadores aritméticos
            ('DELIMITER',       r'[\(\)\[\]\{\}\,\:\;]'),       # Delimitadores
            ('IDENTIFIER',      r'[a-zA-Z_][a-zA-Z0-9_]*'),     # Identificadores
            ('NEWLINE',         r'\n'),                         # Saltos de línea
            ('WHITESPACE',      r'[ \t\r]+'),                   # Espacios en blanco
            ('MISMATCH',        r'.'),                          # Cualquier otro carácter
        ]
        
        # Compilar los patrones en una expresión regular
        self.token_regex = '|'.join('(?P<%s>%s)' % spec for spec in self.token_specs)
        self.regex = re.compile(self.token_regex)
    
    def analyze(self, code):
        line_num = 1
        line_start = 0
        
        # Buscar tokens en el código
        for match in self.regex.finditer(code):
            token_type = match.lastgroup
            token_value = match.group()
            start_pos = match.start() 
            column = start_pos - line_start + 1
            
            if token_type == 'NEWLINE':
                line_num += 1
                line_start = match.end()
            elif token_type == 'WHITESPACE':
                continue
            elif token_type == 'MISMATCH':
                error_desc = f"Carácter no reconocido: '{token_value}'"
                self.errors.append(LexicalError(error_desc, line_num, column))
            else:
                # Para comentarios multilínea, contar líneas dentro del comentario
                if token_type == 'COMMENT_MULTI':
                    lines_in_comment = token_value.count('\n')
                    if lines_in_comment > 0:
                        # Actualizar el número de línea, pero mantener el token en la línea de inicio
                        line_num += lines_in_comment
                        # Calcular la nueva posición de inicio de línea
                        last_newline = token_value.rindex('\n')
                        line_start = start_pos + last_newline + 1
                
                # Verificar longitud de identificadores para detectar errores
                if token_type == 'IDENTIFIER' and len(token_value) > 31:
                    error_desc = f"Identificador excede la longitud máxima (31): '{token_value}'"
                    self.errors.append(LexicalError(error_desc, line_num, column))
                
                # Verificar formateo de punto flotante
                if token_type == 'FLOAT' and '..' in token_value:
                    error_desc = f"Número mal formado: '{token_value}'"
                    self.errors.append(LexicalError(error_desc, line_num, column))
                
                # Verificar strings no cerrados
                if token_type == 'STRING' and token_value.count('"') % 2 != 0:
                    error_desc = f"Cadena no cerrada: '{token_value}'"
                    self.errors.append(LexicalError(error_desc, line_num, column))
                
                # Agregar el token a la lista
                self.tokens.append(Token(token_type, token_value, line_num, column))
        
        return self.tokens, self.errors
    
    def display_results(self):
        # Usar StringIO para capturar la salida y manipularla
        tokens_output = io.StringIO()
        errors_output = io.StringIO()
        
        # Mostrar tokens encontrados en la salida estándar
        if self.tokens:
            token_table = PrettyTable()
            token_table.field_names = ["Tipo de Token", "Valor", "Línea", "Columna"]
            for token in self.tokens:
                token_table.add_row([token.token_type, token.value, token.line, token.column])
            
            print("=== TOKENS ENCONTRADOS ===", file=tokens_output)
            print(token_table, file=tokens_output)
            print(file=tokens_output)
            
            # Imprimir al stdout
            print(tokens_output.getvalue())
        else:
            print("No se encontraron tokens.")
        
        # Mostrar errores léxicos en la salida de error
        if self.errors:
            error_table = PrettyTable()
            error_table.field_names = ["Descripción", "Línea", "Columna"]
            for error in self.errors:
                error_table.add_row([error.description, error.line, error.column])
            
            print("=== ERRORES LÉXICOS ===", file=errors_output)
            print(error_table, file=errors_output)
            print(file=errors_output)
            
            # Imprimir al stderr para que el IDE lo capture en el panel correcto
            print(errors_output.getvalue(), file=sys.stderr)
        else:
            print("No se encontraron errores léxicos.")

def main():
    if len(sys.argv) < 2:
        print("Uso: python lexical_analyzer.py <archivo>", file=sys.stderr)
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            code = file.read()
        
        analyzer = LexicalAnalyzer()
        analyzer.analyze(code)
        analyzer.display_results()
        
    except FileNotFoundError:
        print(f"Error: No se pudo encontrar el archivo '{file_path}'", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()