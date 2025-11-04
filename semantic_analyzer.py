#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
from prettytable import PrettyTable
from typing import Dict, Any, List, Optional

class SemanticError:
    """Clase para almacenar información sobre errores semánticos."""
    def __init__(self, description: str, line: int, column: int):
        self.description = description
        self.line = line if line is not None else 0
        self.column = column if column is not None else 0
    
    def __str__(self):
        return f"Error: {self.description} (Línea {self.line}, Columna {self.column})"

class SemanticAnalyzer:
    """
    Analizador semántico que recorre el AST para construir la tabla de símbolos,
    verificar tipos y detectar errores semánticos.
    """
    def __init__(self):
        self.symbol_table: Dict[str, Dict[str, Any]] = {}
        self.errors: List[SemanticError] = []
        self.ast: Optional[Dict[str, Any]] = None

    def load_ast(self, ast_file_path: str):
        """Carga el AST desde el archivo JSON generado por el analizador sintáctico."""
        try:
            with open(ast_file_path, 'r', encoding='utf-8') as f:
                self.ast = json.load(f)
            return True
        except FileNotFoundError:
            self.add_error(f"No se encontró el archivo AST: {ast_file_path}", 0, 0)
            return False
        except json.JSONDecodeError:
            self.add_error(f"Error al decodificar el archivo AST: {ast_file_path}", 0, 0)
            return False
        except Exception as e:
            self.add_error(f"Error al cargar el AST: {str(e)}", 0, 0)
            return False

    def add_error(self, message: str, line: Optional[int], column: Optional[int]):
        """Añade un error semántico a la lista."""
        self.errors.append(SemanticError(message, line or 0, column or 0))

    def analyze(self):
        """Punto de entrada principal para iniciar el análisis semántico."""
        if not self.ast:
            print("No se ha cargado el AST. Abortando análisis.", file=sys.stderr)
            return
        
        try:
            self.visit(self.ast)
        except Exception as e:
            self.add_error(f"Error inesperado durante el análisis: {str(e)}", 0, 0)

    def visit(self, node: Dict[str, Any]) -> str:
        """
        Método despachador del visitante. Llama a 'visit_NODE_TYPE' o 'generic_visit'.
        Devuelve el tipo semántico del nodo.
        """
        node_type = node.get('node_type')
        if not node_type:
            return 'unknown'
            
        method_name = f"visit_{node_type}"
        visitor = getattr(self, method_name, self.generic_visit)
        
        # Llama al método visitante específico
        semantic_type = visitor(node)
        
        # Anota el nodo con su tipo semántico
        node['semantic_type'] = semantic_type
        return semantic_type

    def generic_visit(self, node: Dict[str, Any]) -> str:
        """Visitante genérico para nodos estructurales (recorre hijos)."""
        for child in node.get('children', []):
            self.visit(child)
        return 'structural' # Tipo por defecto para nodos no-expresión

    # --- Visitantes de Declaración y Estructura ---

    def visit_programa(self, node: Dict[str, Any]) -> str:
        """Visita el nodo raíz del programa."""
        for child in node.get('children', []):
            self.visit(child)
        return 'void'

    def visit_lista_declaracion(self, node: Dict[str, Any]) -> str:
        """Visita la lista de declaraciones y sentencias."""
        for child in node.get('children', []):
            self.visit(child)
        return 'void'

    def visit_declaracion_variable(self, node: Dict[str, Any]) -> str:
        """Procesa la declaración de variables y las añade a la tabla de símbolos."""
        var_type = node.get('value')
        
        for id_node in node.get('children', []):
            var_name = id_node.get('value')
            line = id_node.get('line')
            column = id_node.get('column')
            
            if var_name in self.symbol_table:
                # Error: Variable ya declarada
                self.add_error(f"Identificador duplicado '{var_name}'", line, column)
            else:
                self.symbol_table[var_name] = {
                    'type': var_type,
                    'line': line,
                    'column': column
                }
            
            # Anotamos el nodo 'id' en la declaración
            id_node['semantic_type'] = var_type
            
        return 'void'

    # --- Visitantes de Sentencias ---

    def visit_asignacion(self, node: Dict[str, Any]) -> str:
        """Verifica la asignación (id = expresion)."""
        id_node = node['children'][0]
        rhs_node = node['children'][1]
        
        var_name = id_node.get('value')
        line = node.get('line')
        column = node.get('column')
        
        # 1. Verificar que la variable (LHS) esté declarada
        if var_name not in self.symbol_table:
            self.add_error(f"Variable no declarada '{var_name}' en asignación", line, column)
            lhs_type = 'error'
        else:
            lhs_type = self.symbol_table[var_name]['type']
        
        id_node['semantic_type'] = lhs_type
        
        # 2. Obtener el tipo de la expresión (RHS)
        rhs_type = self.visit(rhs_node)
        
        # 3. Verificar compatibilidad de tipos
        if lhs_type != 'error' and rhs_type != 'error':
            if lhs_type == rhs_type:
                pass  # Tipos idénticos (int=int, float=float, bool=bool)
            elif lhs_type == 'float' and rhs_type == 'int':
                pass  # Promoción válida (float = int)
            else:
                # Error: Tipos incompatibles
                self.add_error(f"Incompatibilidad de tipos: No se puede asignar '{rhs_type}' a '{lhs_type}'",
                               line, column)
                               
        return 'void'

    def visit_seleccion(self, node: Dict[str, Any]) -> str:
        """Verifica sentencia 'if' (condición debe ser bool)."""
        # Hijos: [if, expresion, then, then_block, (else, else_block)]
        cond_node = node['children'][1]
        
        cond_type = self.visit(cond_node)
        
        if cond_type not in ['bool', 'error']:
            self.add_error(f"La condición 'if' debe ser 'bool', pero se encontró '{cond_type}'",
                           cond_node.get('line'), cond_node.get('column'))
        
        # Visitar los bloques 'then' y 'else'
        self.visit(node['children'][3]) # then_block
        if len(node['children']) > 4:
            self.visit(node['children'][5]) # else_block
            
        return 'void'

    def visit_iteracion(self, node: Dict[str, Any]) -> str:
        """Verifica sentencia 'while' (condición debe ser bool)."""
        # Hijos: [while, condicion, cuerpo]
        cond_node = node['children'][1]['children'][0] # Extraer expr de 'condicion'
        
        cond_type = self.visit(cond_node)
        
        if cond_type not in ['bool', 'error']:
            self.add_error(f"La condición 'while' debe ser 'bool', pero se encontró '{cond_type}'",
                           cond_node.get('line'), cond_node.get('column'))

        # Visitar el cuerpo
        self.visit(node['children'][2]) # cuerpo
        return 'void'

    def visit_repeticion(self, node: Dict[str, Any]) -> str:
        """Verifica sentencia 'do-until' (condición debe ser bool)."""
        # Hijos: [do, cuerpo, until, condicion]
        
        # Visitar el cuerpo primero
        self.visit(node['children'][1]) # cuerpo
        
        cond_node = node['children'][3]['children'][0] # Extraer expr de 'condicion'
        cond_type = self.visit(cond_node)
        
        if cond_type not in ['bool', 'error']:
            self.add_error(f"La condición 'until' debe ser 'bool', pero se encontró '{cond_type}'",
                           cond_node.get('line'), cond_node.get('column'))

        return 'void'

    def visit_sent_in(self, node: Dict[str, Any]) -> str:
        """Verifica 'cin' (variables deben estar declaradas)."""
        for child in node.get('children', []):
            if child.get('node_type') == 'id':
                var_name = child.get('value')
                if var_name not in self.symbol_table:
                    self.add_error(f"Variable no declarada '{var_name}' en 'cin'",
                                   child.get('line'), child.get('column'))
                    child['semantic_type'] = 'error'
                else:
                    child['semantic_type'] = self.symbol_table[var_name]['type']
        return 'void'

    def visit_sent_out(self, node: Dict[str, Any]) -> str:
        """Verifica 'cout' (visita expresiones hijas)."""
        for child in node.get('children', []):
            if child.get('node_type') not in ['cout', '<<']:
                expr_type = self.visit(child)
                # cout puede imprimir cualquier tipo básico
                if expr_type not in ['int', 'float', 'bool', 'string', 'error']:
                    self.add_error(f"Tipo no imprimible '{expr_type}' en 'cout'",
                                   child.get('line'), child.get('column'))
        return 'void'

    # --- Visitantes de Expresiones (Devuelven Tipo) ---

    def visit_expresion_simple(self, node: Dict[str, Any]) -> str:
        """Operaciones aritméticas (+, -). Devuelve int o float."""
        op = node.get('value')
        left_type = self.visit(node['children'][0])
        right_type = self.visit(node['children'][1])

        if left_type == 'error' or right_type == 'error':
            return 'error'

        # Solo se permite aritmética en int y float
        if left_type not in ['int', 'float'] or right_type not in ['int', 'float']:
            self.add_error(f"Operador aritmético '{op}' no se puede aplicar a '{left_type}' y '{right_type}'",
                           node.get('line'), node.get('column'))
            return 'error'

        # Promoción de tipo: int + float = float
        if left_type == 'float' or right_type == 'float':
            return 'float'
        else:
            return 'int'

    def visit_termino(self, node: Dict[str, Any]) -> str:
        """Operaciones aritméticas (*, /). Devuelve int o float."""
        # Lógica idéntica a expresion_simple
        return self.visit_expresion_simple(node)

    def visit_factor(self, node: Dict[str, Any]) -> str:
        """Operaciones aritméticas (^). Devuelve int o float."""
        # Lógica idéntica a expresion_simple
        return self.visit_expresion_simple(node)

    def visit_expresion_relacional(self, node: Dict[str, Any]) -> str:
        """Operaciones relacionales (==, !=, <, >). Devuelve bool."""
        op = node.get('value')
        left_type = self.visit(node['children'][0])
        right_type = self.visit(node['children'][1])

        if left_type == 'error' or right_type == 'error':
            return 'bool' # Asumimos que la intención era booleana

        # Permitir comparaciones numéricas (int, float) y booleanas (bool)
        numeric_compat = left_type in ['int', 'float'] and right_type in ['int', 'float']
        bool_compat = left_type == 'bool' and right_type == 'bool'

        if not (numeric_compat or bool_compat):
            self.add_error(f"Operador relacional '{op}' no se puede aplicar a '{left_type}' y '{right_type}'",
                           node.get('line'), node.get('column'))
        
        return 'bool' # El resultado de una relación es siempre bool

    def visit_expresion_logica(self, node: Dict[str, Any]) -> str:
        """Operaciones lógicas (&&, ||, !). Devuelve bool."""
        op = node.get('value')
        
        if op == '!': # Operador unario
            operand_type = self.visit(node['children'][0])
            if operand_type not in ['bool', 'error']:
                self.add_error(f"Operador lógico '!' no se puede aplicar a '{operand_type}'",
                               node.get('line'), node.get('column'))
        else: # Operador binario (&&, ||)
            left_type = self.visit(node['children'][0])
            right_type = self.visit(node['children'][1])
            
            if left_type not in ['bool', 'error']:
                self.add_error(f"Operador lógico '{op}' requiere 'bool', pero se encontró '{left_type}' (izquierda)",
                               node.get('line'), node.get('column'))
            if right_type not in ['bool', 'error']:
                 self.add_error(f"Operador lógico '{op}' requiere 'bool', pero se encontró '{right_type}' (derecha)",
                                node.get('line'), node.get('column'))

        return 'bool' # El resultado de una operación lógica es siempre bool

    # --- Visitantes de Nodos Hoja (Literales e ID) ---

    def visit_id(self, node: Dict[str, Any]) -> str:
        """Verifica el uso de un ID (debe estar declarado)."""
        var_name = node.get('value')
        if var_name not in self.symbol_table:
            self.add_error(f"Variable no declarada '{var_name}'",
                           node.get('line'), node.get('column'))
            return 'error'
        
        # Devuelve el tipo de la variable desde la tabla de símbolos
        return self.symbol_table[var_name]['type']

    def visit_numero(self, node: Dict[str, Any]) -> str:
        """Infiere el tipo de un literal numérico."""
        value_str = node.get('value', '')
        if '.' in value_str:
            return 'float'
        else:
            return 'int'

    def visit_bool(self, node: Dict[str, Any]) -> str:
        """Tipo de un literal booleano."""
        return 'bool'

    def visit_cadena(self, node: Dict[str, Any]) -> str:
        """Tipo de un literal de cadena."""
        # Nota: 'string' no es un tipo declarable en la gramática,
        # solo usable en 'cout' y asignaciones (que fallarán si no es tipo string).
        return 'string'

    # --- Salida y Reporte ---

    def display_results(self, base_file_path: str):
        """Muestra la tabla de símbolos y los errores semánticos."""
        
        print("=== TABLA DE SÍMBOLOS ===")
        sym_table = PrettyTable()
        sym_table.field_names = ["Nombre", "Tipo", "Línea (Decl)", "Columna (Decl)"]
        sym_table.align = "l"
        
        symbol_data_for_json = {}
        
        for name, info in self.symbol_table.items():
            sym_table.add_row([name, info['type'], info['line'], info['column']])
            symbol_data_for_json[name] = info
            
        #print(sym_table)
        #print("\n")
        
        # Guardar tabla de símbolos en JSON
        sym_table_file = base_file_path.replace('.txt', '_symbol_table.json')
        try:
            with open(sym_table_file, 'w', encoding='utf-8') as f:
                json.dump(symbol_data_for_json, f, indent=2, ensure_ascii=False)
            print(f"Tabla de símbolos guardada en: {sym_table_file}")
        except Exception as e:
            print(f"Error al guardar la tabla de símbolos: {e}", file=sys.stderr)

        # Guardar AST anotado
        annotated_ast_file = base_file_path.replace('.txt', '_annotated_ast.json')
        if self.ast:
            try:
                with open(annotated_ast_file, 'w', encoding='utf-8') as f:
                    json.dump(self.ast, f, indent=2, ensure_ascii=False)
                print(f"AST Anotado guardado en: {annotated_ast_file}")
            except Exception as e:
                print(f"Error al guardar el AST anotado: {e}", file=sys.stderr)
        
        print("\n")
        
        # Mostrar errores semánticos (en stderr para el IDE)
        if self.errors:
            error_table = PrettyTable()
            error_table.field_names = ["Descripción", "Línea", "Columna"]
            error_table.align = "l"
            
            print("=== ERRORES SEMÁNTICOS ===", file=sys.stderr)
            for error in self.errors:
                error_table.add_row([error.description, error.line, error.column])
            
            print(error_table, file=sys.stderr)
        else:
            print("Análisis semántico completado sin errores.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python semantic_analyzer.py <file>", file=sys.stderr)
        sys.exit(1)
    
    file_path = sys.argv[1]
    ast_file_path = file_path.replace('.txt', '_ast.json')
    
    try:
        analyzer = SemanticAnalyzer()
        
        if not analyzer.load_ast(ast_file_path):
            analyzer.display_results(file_path) # Mostrará el error de carga
            sys.exit(1)
        
        analyzer.analyze()
        analyzer.display_results(file_path)
        
    except Exception as e:
        print(f"Error fatal en el analizador semántico: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()