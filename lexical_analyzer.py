import sys
import re
from enum import Enum, auto

class TokenType(Enum):
    # Keywords
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    FUNCTION = auto()
    RETURN = auto()
    VAR = auto()
    CONST = auto()
    
    # Literals
    IDENTIFIER = auto()
    NUMBER = auto()
    STRING = auto()
    
    # Operators
    PLUS = auto()
    MINUS = auto()
    MULTIPLY = auto()
    DIVIDE = auto()
    ASSIGN = auto()
    EQUALS = auto()
    NOT_EQUALS = auto()
    LESS_THAN = auto()
    GREATER_THAN = auto()
    LESS_EQUALS = auto()
    GREATER_EQUALS = auto()
    
    # Delimiters
    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    LEFT_BRACE = auto()
    RIGHT_BRACE = auto()
    SEMICOLON = auto()
    COMMA = auto()
    
    # Other
    COMMENT = auto()
    WHITESPACE = auto()
    ERROR = auto()
    EOF = auto()

class Token:
    def __init__(self, type, value, line, column):
        self.type = type
        self.value = value
        self.line = line
        self.column = column
    
    def __str__(self):
        return f"Token({self.type}, '{self.value}', linea={self.line}, columna={self.column})"

class AnalizadorLexico:
    def __init__(self):
        # Define token patterns
        self.token_specs = [
            # Keywords
            ('IF', r'if\b'),
            ('ELSE', r'else\b'),
            ('WHILE', r'while\b'),
            ('FOR', r'for\b'),
            ('FUNCTION', r'function\b'),
            ('RETURN', r'return\b'),
            ('VAR', r'var\b'),
            ('CONST', r'const\b'),
            
            # Literals
            ('NUMBER', r'\d+(\.\d+)?'),
            ('STRING', r'"[^"]*"'),
            ('IDENTIFIER', r'[a-zA-Z_][a-zA-Z0-9_]*'),
            
            # Operators
            ('PLUS', r'\+'),
            ('MINUS', r'-'),
            ('MULTIPLY', r'\*'),
            ('DIVIDE', r'/'),
            ('ASSIGN', r'='),
            ('EQUALS', r'=='),
            ('NOT_EQUALS', r'!='),
            ('LESS_THAN', r'<'),
            ('GREATER_THAN', r'>'),
            ('LESS_EQUALS', r'<='),
            ('GREATER_EQUALS', r'>='),
            
            # Delimiters
            ('LEFT_PAREN', r'\('),
            ('RIGHT_PAREN', r'\)'),
            ('LEFT_BRACE', r'\{'),
            ('RIGHT_BRACE', r'\}'),
            ('SEMICOLON', r';'),
            ('COMMA', r','),
            
            # Other
            ('COMMENT', r'//.*'),
            ('WHITESPACE', r'[ \t]+'),
            ('NEWLINE', r'\n'),
        ]
        
        # Diccionario de traducciones de tipos de token
        self.traducciones = {
            # Keywords
            'IF': 'Palabra clave if',
            'ELSE': 'Palabra clave else',
            'WHILE': 'Palabra clave while',
            'FOR': 'Palabra clave for',
            'FUNCTION': 'Palabra clave FUNCIÓN',
            'RETURN': 'Palabra clave RETORNO',
            'VAR': 'Palabra clave VAR',
            'CONST': 'Palabra clave CONST',
            
            # Literals
            'IDENTIFIER': 'Identificador',
            'NUMBER': 'Número',
            'STRING': 'Cadena',
            
            # Operators
            'PLUS': 'Operador Suma',
            'MINUS': 'Operador Resta',
            'MULTIPLY': 'Operador Multiplicación',
            'DIVIDE': 'Operador División',
            'ASSIGN': 'Operador Asignación',
            'EQUALS': 'Operador Igualdad',
            'NOT_EQUALS': 'Operador Desigualdad',
            'LESS_THAN': 'Operador Menor que',
            'GREATER_THAN': 'Operador Mayor que',
            'LESS_EQUALS': 'Operador Menor o igual',
            'GREATER_EQUALS': 'Operador Mayor o igual',
            
            # Delimiters
            'LEFT_PAREN': 'Paréntesis Izquierdo',
            'RIGHT_PAREN': 'Paréntesis Derecho',
            'LEFT_BRACE': 'Llave Izquierda',
            'RIGHT_BRACE': 'Llave Derecha',
            'SEMICOLON': 'Punto y coma',
            'COMMA': 'Coma',
            
            # Other
            'COMMENT': 'Comentario',
            'ERROR': 'Token Inválido',
            'EOF': 'Fin de Archivo'
        }
        
        # Build the regex pattern
        self.patterns = '|'.join('(?P<%s>%s)' % (name, pattern) for name, pattern in self.token_specs)
        self.regex = re.compile(self.patterns)
        
    def tokenize(self, text):
        tokens = []
        line_num = 1
        line_start = 0
        
        # Find all matches
        for match in re.finditer(self.regex, text):
            token_type = match.lastgroup
            token_value = match.group(token_type)
            column = match.start() - line_start
            
            # Skip whitespace and comments
            if token_type == 'WHITESPACE':
                continue
            elif token_type == 'NEWLINE':
                line_start = match.end()
                line_num += 1
                continue
            elif token_type == 'COMMENT':
                continue
            
            # Get the token type from the enum
            try:
                token_enum = TokenType[token_type]
            except KeyError:
                # If not in enum, it's an error
                token_enum = TokenType.ERROR
            
            token = Token(token_enum, token_value, line_num, column)
            tokens.append(token)
        
        # Add EOF token
        tokens.append(Token(TokenType.EOF, "", line_num, 0))
        return tokens
    
    def analizar_archivo(self, ruta_archivo):
        try:
            with open(ruta_archivo, 'r') as f:
                texto = f.read()
            tokens = self.tokenize(texto)
            return tokens
        except Exception as e:
            print(f"Error al leer o analizar el archivo: {e}", file=sys.stderr)
            return []

def main():
    # Check if file path is provided
    if len(sys.argv) < 2:
        print("Error: Por favor proporcione una ruta de archivo", file=sys.stderr)
        sys.exit(1)
    
    ruta_archivo = sys.argv[1]
    analizador = AnalizadorLexico()
    tokens = analizador.analizar_archivo(ruta_archivo)
    
    # Print tokens in Spanish
    print(f"{'Tipo de Token':<25} {'Valor':<20} {'Línea':<6} {'Columna':<6}")
    print("-" * 60)
    for token in tokens:
        if token.type == TokenType.EOF:
            print(f"{'Fin de Archivo':<25} {'<EOF>':<20} {token.line:<6} {token.column:<6}")
        else:
            # Translate token type to Spanish
            tipo_token_esp = analizador.traducciones.get(token.type.name, token.type.name)
            print(f"{tipo_token_esp:<25} {token.value:<20} {token.line:<6} {token.column:<6}")
    
    # Print summary in Spanish
    token_count = len(tokens) - 1  # Exclude EOF token
    print(f"\nTotal de tokens encontrados: {token_count}")
    
    # Count types of tokens
    token_types = {}
    for token in tokens:
        if token.type != TokenType.EOF:
            if token.type.name in token_types:
                token_types[token.type.name] += 1
            else:
                token_types[token.type.name] = 1
    
    print("\nDistribución de tipos de tokens:")
    for type_name, count in token_types.items():
        # Use Spanish translation for type name
        tipo_token_esp = analizador.traducciones.get(type_name, type_name)
        print(f"{tipo_token_esp:<20}: {count}")

if __name__ == "__main__":
    main()