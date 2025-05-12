#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import re
import io
from prettytable import PrettyTable

class Token:
    def __init__(self, token_type, value, line, column, in_comment=False):
        self.token_type = token_type
        self.value = value
        self.line = line
        self.column = column
        self.in_comment = in_comment
    
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
        
        # Define patterns for comments first
        self.comment_specs = [
            ('COMMENT_MULTI', r'\/\*.*?\*\/'),   # Multiline comments (/* */)
            ('COMMENT_SINGLE', r'\/\/.*')        # Single-line comments (//)
        ]
        
        # Definition of token patterns
        self.token_specs = [
            ('STRING',          r'"([^"\\]|\\.)*"'),            # Strings with double quotes
            ('CHAR',            r'\'([^\'\\]|\\.)\''),          # Characters with single quotes
            ('FLOAT',           r'\d+\.\d+([eE][+-]?\d+)?'),    # Floating point numbers with full decimal part
            ('PARTIAL_FLOAT',   r'\d+\.([a-zA-Z_]|\d)*'),       # Floating point numbers with incomplete decimal part
            ('INT',             r'\d+'),                        # Integers
            ('KEYWORD',         r'\b(if|else|end|do|while|switch|case|int|float|main|cin|cout|for|return|char|bool|real|then|until)\b'),  # Keywords
            ('LOGIC_OP',        r'(\&\&|\|\||!)'),              # Logical operators
            ('INCREMENT',       r'\+\+'),                       # Increment operator
            ('DECREMENT',       r'\-\-'),                       # Decrement operator
            ('REL_OP',          r'(<=|>=|==|!=|<|>)'),          # Relational operators
            ('ASSIGN_OP',       r'='),                          # Assignment operator
            ('ARITH_OP',        r'(\+|\-|\*|\/|\%|\^)'),        # Arithmetic operators
            ('DELIMITER',       r'[\(\)\[\]\{\}\,\:\;]'),       # Delimiters
            ('IDENTIFIER',      r'[a-zA-Z_][a-zA-Z0-9_]*'),     # Identifiers
            ('NEWLINE',         r'\n'),                         # Newlines
            ('WHITESPACE',      r'[ \t\r]+'),                   # Whitespace
            ('MISMATCH',        r'.'),                          # Any other character
        ]
        
        # Compile comment patterns
        self.comment_regex = re.compile('|'.join('(?P<%s>%s)' % spec for spec in self.comment_specs), re.DOTALL)
        
        # Compile token patterns
        self.token_regex = '|'.join('(?P<%s>%s)' % spec for spec in self.token_specs)
        self.regex = re.compile(self.token_regex)
    
    def analyze(self, code):
        # Track comment regions
        comment_regions = self._find_comment_regions(code)
        
        line_num = 1
        line_start = 0
        
        # Search for tokens in the code
        for match in self.regex.finditer(code):
            token_type = match.lastgroup
            token_value = match.group()
            start_pos = match.start() 
            end_pos = match.end()
            column = start_pos - line_start + 1
            
            # Check if the token is within a comment region
            in_comment = any(start_pos >= region[0] and end_pos <= region[1] for region in comment_regions)
            
            if token_type == 'NEWLINE':
                line_num += 1
                line_start = match.end()
            elif token_type == 'WHITESPACE':
                continue
            elif token_type == 'MISMATCH' and not in_comment:
                error_desc = f"Unrecognized character: '{token_value}'"
                self.errors.append(LexicalError(error_desc, line_num, column))
            else:
                # Validate specific token types
                if not in_comment:
                    if token_type == 'IDENTIFIER' and len(token_value) > 31:
                        error_desc = f"Identifier exceeds maximum length (31): '{token_value}'"
                        self.errors.append(LexicalError(error_desc, line_num, column))
                    
                    if token_type == 'FLOAT' and '..' in token_value:
                        error_desc = f"Malformed number: '{token_value}'"
                        self.errors.append(LexicalError(error_desc, line_num, column))
                    
                    # Nuevo manejo de flotantes parciales
                    if token_type == 'PARTIAL_FLOAT':
                        error_desc = f"Incomplete floating-point number: '{token_value}'"
                        self.errors.append(LexicalError(error_desc, line_num, column))
                    
                    if token_type == 'STRING' and token_value.count('"') % 2 != 0:
                        error_desc = f"Unclosed string: '{token_value}'"
                        self.errors.append(LexicalError(error_desc, line_num, column))
                    
                    # Add the token to the list only if it's not in a comment
                    self.tokens.append(Token(token_type, token_value, line_num, column, in_comment))
        
        return self.tokens, self.errors
    
    def _find_comment_regions(self, code):
        """
        Find the start and end positions of all comment regions in the code.
        
        :param code: The source code to analyze
        :return: A list of tuples (start, end) representing comment regions
        """
        comment_regions = []
        for match in self.comment_regex.finditer(code):
            comment_regions.append((match.start(), match.end()))
        return comment_regions
    
    def display_results(self):
        # Use StringIO to capture output
        tokens_output = io.StringIO()
        errors_output = io.StringIO()
        
        # Display found tokens (excluding those in comments)
        tokens_to_display = [token for token in self.tokens if not token.in_comment]
        
        if tokens_to_display:
            token_table = PrettyTable()
            token_table.field_names = ["Token Type", "Value", "Line", "Column"]
            for token in tokens_to_display:
                token_table.add_row([token.token_type, token.value, token.line, token.column])
            
            print("=== TOKENS FOUND ===", file=tokens_output)
            print(token_table, file=tokens_output)
            print(file=tokens_output)
            
            # Print to stdout
            print(tokens_output.getvalue())
        else:
            print("No tokens found.")
        
        # Display lexical errors
        if self.errors:
            error_table = PrettyTable()
            error_table.field_names = ["Description", "Line", "Column"]
            for error in self.errors:
                error_table.add_row([error.description, error.line, error.column])
            
            print("=== LEXICAL ERRORS ===", file=errors_output)
            print(error_table, file=errors_output)
            print(file=errors_output)
            
            # Print to stderr
            print(errors_output.getvalue(), file=sys.stderr)
        else:
            print("No lexical errors found.")

def main():
    if len(sys.argv) < 2:
        print("Usage: python lexical_analyzer.py <file>", file=sys.stderr)
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            code = file.read()
        
        analyzer = LexicalAnalyzer()
        analyzer.analyze(code)
        analyzer.display_results()
        
    except FileNotFoundError:
        print(f"Error: Could not find file '{file_path}'", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()