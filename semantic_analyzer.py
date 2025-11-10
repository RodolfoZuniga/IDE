#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
from prettytable import PrettyTable
from typing import Dict, Any, List, Optional, Tuple

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
        # Tabla para chequeo rápido de tipo y declaración
        self.symbol_table: Dict[str, Dict[str, Any]] = {} 
        self.errors: List[SemanticError] = []
        self.ast: Optional[Dict[str, Any]] = None
        
        # Tabla de Referencias Cruzadas (para mostrar en el IDE)
        self.cross_reference_table: Dict[str, Dict[str, Any]] = {}
        self.current_address = 1 # Para la columna "Dirección"

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
            return
        
        try:
            self.visit(self.ast)
        except Exception as e:
            self.add_error(f"Error inesperado durante el análisis: {str(e)}", 0, 0)

    def visit(self, node: Dict[str, Any]) -> Tuple[str, Any]:
        """
        Método despachador del visitante. Llama a 'visit_NODE_TYPE' o 'generic_visit'.
        Devuelve el tipo semántico del nodo y su valor constante si se puede calcular.
        """
        node_type = node.get('node_type')
        if not node_type:
            return 'unknown', None
            
        method_name = f"visit_{node_type}"
        visitor = getattr(self, method_name, self.generic_visit)
        
        semantic_type, semantic_value = visitor(node)
        
        node['semantic_type'] = semantic_type
        node['semantic_value'] = semantic_value
        
        return semantic_type, semantic_value

    def generic_visit(self, node: Dict[str, Any]) -> Tuple[str, Any]:
        """Visitante genérico para nodos estructurales (recorre hijos)."""
        for child in node.get('children', []):
            self.visit(child)
        return 'structural', None

    # --- Visitantes de Declaración y Estructura ---

    def visit_programa(self, node: Dict[str, Any]) -> Tuple[str, Any]:
        for child in node.get('children', []):
            self.visit(child)
        return 'void', None

    def visit_lista_declaracion(self, node: Dict[str, Any]) -> Tuple[str, Any]:
        for child in node.get('children', []):
            self.visit(child)
        return 'void', None

    def visit_declaracion_variable(self, node: Dict[str, Any]) -> Tuple[str, Any]:
        """Procesa la declaración y la añade a ambas tablas."""
        var_type = node.get('value')
        
        for id_node in node.get('children', []):
            var_name = id_node.get('value')
            line = id_node.get('line')
            column = id_node.get('column')
            
            if var_name in self.symbol_table:
                self.add_error(f"Identificador duplicado '{var_name}'", line, column)
            else:
                self.symbol_table[var_name] = {
                    'type': var_type,
                    'line': line,
                    'column': column,
                    'is_initialized': False, 
                    'const_value': None
                }
                
                self.cross_reference_table[var_name] = {
                    'type': var_type,
                    'lines': [line],
                    'address': self.current_address
                }
                self.current_address += 1
            
            id_node['semantic_type'] = var_type
            
        return 'void', None

    # --- Visitantes de Sentencias ---

    def visit_asignacion(self, node: Dict[str, Any]) -> Tuple[str, Any]:
        """Verifica la asignación, registra el uso y propaga el valor constante."""
        id_node = node['children'][0]
        rhs_node = node['children'][1]
        
        var_name = id_node.get('value')
        line = node.get('line')
        column = node.get('column')
        
        if var_name in self.cross_reference_table:
            self.cross_reference_table[var_name]['lines'].append(line)
        
        if var_name not in self.symbol_table:
            self.add_error(f"Variable no declarada '{var_name}' en asignación", line, column)
            lhs_type = 'error'
        else:
            lhs_type = self.symbol_table[var_name]['type']
        
        id_node['semantic_type'] = lhs_type
        
        # Obtener el tipo y valor de la expresión (RHS)
        rhs_type, rhs_value = self.visit(rhs_node)
        
        # Verificar compatibilidad de tipos
        if lhs_type != 'error' and rhs_type != 'error':
            if lhs_type == rhs_type:
                pass 
            elif lhs_type == 'float' and rhs_type == 'int':
                pass 
            else:
                self.add_error(f"Incompatibilidad de tipos: No se puede asignar '{rhs_type}' a '{lhs_type}'",
                               line, column)
        
        if lhs_type != 'error':
            self.symbol_table[var_name]['is_initialized'] = True
            self.symbol_table[var_name]['const_value'] = rhs_value
                               
        # --- MODIFICACIÓN 1: Propagación de valor a la asignación ---
        # Devolvemos el valor del RHS para que el nodo 'asignacion' también lo tenga
        return 'void', rhs_value
        # --- FIN DE MODIFICACIÓN 1 ---

    def visit_seleccion(self, node: Dict[str, Any]) -> Tuple[str, Any]:
        """Verifica sentencia 'if' (condición debe ser bool)."""
        cond_node = node['children'][1]
        
        cond_type, cond_value = self.visit(cond_node)
        
        if cond_type not in ['bool', 'error']:
            self.add_error(f"La condición 'if' debe ser 'bool', pero se encontró '{cond_type}'",
                           cond_node.get('line'), cond_node.get('column'))
        
        self.visit(node['children'][3]) # then_block
        if len(node['children']) > 4:
            self.visit(node['children'][5]) # else_block
            
        return 'void', None

    def visit_iteracion(self, node: Dict[str, Any]) -> Tuple[str, Any]:
        """Verifica sentencia 'while' (condición debe ser bool)."""
        cond_node = node['children'][1]['children'][0]
        
        cond_type, cond_value = self.visit(cond_node)
        
        if cond_type not in ['bool', 'error']:
            self.add_error(f"La condición 'while' debe ser 'bool', pero se encontró '{cond_type}'",
                           cond_node.get('line'), cond_node.get('column'))

        self.visit(node['children'][2]) # cuerpo
        return 'void', None

    def visit_repeticion(self, node: Dict[str, Any]) -> Tuple[str, Any]:
        """Verifica sentencia 'do-until' (condición debe ser bool)."""
        self.visit(node['children'][1]) # cuerpo
        
        cond_node = node['children'][3]['children'][0]
        cond_type, cond_value = self.visit(cond_node)
        
        if cond_type not in ['bool', 'error']:
            self.add_error(f"La condición 'until' debe ser 'bool', pero se encontró '{cond_type}'",
                           cond_node.get('line'), cond_node.get('column'))

        return 'void', None

    def visit_sent_in(self, node: Dict[str, Any]) -> Tuple[str, Any]:
        """Verifica 'cin' y actualiza el estado de la variable."""
        for child in node.get('children', []):
            if child.get('node_type') == 'id':
                var_name = child.get('value')
                line = child.get('line')
                
                if var_name in self.cross_reference_table:
                    self.cross_reference_table[var_name]['lines'].append(line)

                if var_name not in self.symbol_table:
                    self.add_error(f"Variable no declarada '{var_name}' en 'cin'",
                                   child.get('line'), child.get('column'))
                    child['semantic_type'] = 'error'
                else:
                    child['semantic_type'] = self.symbol_table[var_name]['type']
                    self.symbol_table[var_name]['is_initialized'] = True
                    self.symbol_table[var_name]['const_value'] = None
                    
        return 'void', None

    def visit_sent_out(self, node: Dict[str, Any]) -> Tuple[str, Any]:
        """Verifica 'cout' (visita expresiones hijas)."""
        for child in node.get('children', []):
            if child.get('node_type') not in ['cout', '<<']:
                expr_type, expr_value = self.visit(child)
                if expr_type not in ['int', 'float', 'bool', 'string', 'error']:
                    self.add_error(f"Tipo no imprimible '{expr_type}' en 'cout'",
                                   child.get('line'), child.get('column'))
        return 'void', None

    # --- Visitantes de Expresiones ---

    def _calculate_arithmetic(self, op: str, left_val: Any, right_val: Any, result_type: str, node: Dict) -> Any:
        """Helper para calcular valores aritméticos y chequear errores."""
        if left_val is None or right_val is None:
            return None
        
        try:
            l = float(left_val) if result_type == 'float' else left_val
            r = float(right_val) if result_type == 'float' else right_val

            if op == '+': return l + r
            if op == '-': return l - r
            if op == '*': return l * r
            
            # --- MODIFICACIÓN 2: División Entera vs Flotante ---
            if op == '/':
                if r == 0:
                    self.add_error(f"División por cero en tiempo de compilación", node.get('line'), node.get('column'))
                    return None
                
                if result_type == 'float':
                    return l / r  # División flotante
                else:
                    return l // r # División entera
            # --- FIN DE MODIFICACIÓN 2 ---
            
            if op == '^': return l ** r
            
            if op == '%':
                if result_type == 'float':
                    self.add_error(f"Operador '%' no se puede aplicar a 'float'", node.get('line'), node.get('column'))
                    return None
                if r == 0:
                    self.add_error(f"División por cero (módulo) en tiempo de compilación", node.get('line'), node.get('column'))
                    return None
                return l % r
                
        except Exception as e:
            self.add_error(f"Error en operación aritmética: {e}", node.get('line'), node.get('column'))
            return None
        return None

    def visit_expresion_simple(self, node: Dict[str, Any]) -> Tuple[str, Any]:
        """Operaciones aritméticas (+, -). Devuelve (tipo, valor)."""
        op = node.get('value')
        left_type, left_val = self.visit(node['children'][0])
        right_type, right_val = self.visit(node['children'][1])

        if left_type == 'error' or right_type == 'error':
            return 'error', None

        if left_type not in ['int', 'float'] or right_type not in ['int', 'float']:
            self.add_error(f"Operador aritmético '{op}' no se puede aplicar a '{left_type}' y '{right_type}'",
                           node.get('line'), node.get('column'))
            return 'error', None

        result_type = 'float' if left_type == 'float' or right_type == 'float' else 'int'
        result_val = self._calculate_arithmetic(op, left_val, right_val, result_type, node)
        
        return result_type, result_val

    def visit_termino(self, node: Dict[str, Any]) -> Tuple[str, Any]:
        """Operaciones aritméticas (*, /, %). Devuelve (tipo, valor)."""
        op = node.get('value')
        left_type, left_val = self.visit(node['children'][0])
        right_type, right_val = self.visit(node['children'][1])

        if left_type == 'error' or right_type == 'error':
            return 'error', None

        if left_type not in ['int', 'float'] or right_type not in ['int', 'float']:
            self.add_error(f"Operador aritmético '{op}' no se puede aplicar a '{left_type}' y '{right_type}'",
                           node.get('line'), node.get('column'))
            return 'error', None

        result_type = 'float' if left_type == 'float' or right_type == 'float' else 'int'
        
        # --- MODIFICACIÓN 3: Eliminamos la coerción a float para '/' ---
        # if op == '/' and result_type == 'int': 
        #      result_type = 'float'
        # (Líneas eliminadas)
        # --- FIN DE MODIFICACIÓN 3 ---

        result_val = self._calculate_arithmetic(op, left_val, right_val, result_type, node)
        
        if op == '%' and result_type == 'float':
            # El módulo solo tiene sentido para enteros en este lenguaje
            self.add_error(f"Operador '%' no se puede aplicar a 'float'", node.get('line'), node.get('column'))
            return 'error', None
        
        return result_type, result_val

    def visit_factor(self, node: Dict[str, Any]) -> Tuple[str, Any]:
        """Operaciones aritméticas (^). Devuelve (tipo, valor)."""
        op = node.get('value')
        left_type, left_val = self.visit(node['children'][0])
        right_type, right_val = self.visit(node['children'][1])

        if left_type == 'error' or right_type == 'error':
            return 'error', None

        if left_type not in ['int', 'float'] or right_type not in ['int', 'float']:
            self.add_error(f"Operador aritmético '{op}' no se puede aplicar a '{left_type}' y '{right_type}'",
                           node.get('line'), node.get('column'))
            return 'error', None

        result_type = 'float' if left_type == 'float' or right_type == 'float' else 'int'
        result_val = self._calculate_arithmetic(op, left_val, right_val, result_type, node)
        
        return result_type, result_val


    def visit_expresion_relacional(self, node: Dict[str, Any]) -> Tuple[str, Any]:
        """Operaciones relacionales (==, !=, <, >). Devuelve (bool, valor)."""
        op = node.get('value')
        left_type, left_val = self.visit(node['children'][0])
        right_type, right_val = self.visit(node['children'][1])

        if left_type == 'error' or right_type == 'error':
            return 'bool', None

        numeric_compat = left_type in ['int', 'float'] and right_type in ['int', 'float']
        bool_compat = left_type == 'bool' and right_type == 'bool'

        if not (numeric_compat or bool_compat):
            self.add_error(f"Operador relacional '{op}' no se puede aplicar a '{left_type}' y '{right_type}'",
                           node.get('line'), node.get('column'))
            return 'bool', None
        
        result_val = None
        if left_val is not None and right_val is not None:
            try:
                if op == '==': result_val = left_val == right_val
                elif op == '!=': result_val = left_val != right_val
                elif op == '<':  result_val = left_val < right_val
                elif op == '>':  result_val = left_val > right_val
                elif op == '<=': result_val = left_val <= right_val
                elif op == '>=': result_val = left_val >= right_val
            except Exception as e:
                self.add_error(f"Error en operación relacional: {e}", node.get('line'), node.get('column'))
                result_val = None

        return 'bool', result_val

    def visit_expresion_logica(self, node: Dict[str, Any]) -> Tuple[str, Any]:
        """Operaciones lógicas (&&, ||, !). Devuelve (bool, valor)."""
        op = node.get('value')
        result_val = None
        
        if op == '!': # Unario
            op_type, op_val = self.visit(node['children'][0])
            if op_type not in ['bool', 'error']:
                self.add_error(f"Operador lógico '!' no se puede aplicar a '{op_type}'",
                               node.get('line'), node.get('column'))
                return 'bool', None
            
            if op_val is not None:
                result_val = not op_val
                
        else: # Binario (&&, ||)
            left_type, left_val = self.visit(node['children'][0])
            right_type, right_val = self.visit(node['children'][1])
            
            if left_type not in ['bool', 'error']:
                self.add_error(f"Operador lógico '{op}' requiere 'bool', pero se encontró '{left_type}' (izquierda)",
                               node.get('line'), node.get('column'))
            if right_type not in ['bool', 'error']:
                 self.add_error(f"Operador lógico '{op}' requiere 'bool', pero se encontró '{right_type}' (derecha)",
                                node.get('line'), node.get('column'))

            if left_type == 'error' or right_type == 'error':
                 return 'bool', None

            if left_val is not None and right_val is not None:
                if op == '&&': result_val = left_val and right_val
                elif op == '||': result_val = left_val or right_val

        return 'bool', result_val

    # --- Visitantes de Nodos Hoja ---

    def visit_id(self, node: Dict[str, Any]) -> Tuple[str, Any]:
        """Verifica el uso de un ID, registra su aparición y devuelve su tipo y valor constante."""
        var_name = node.get('value')
        line = node.get('line')

        if var_name in self.cross_reference_table:
            self.cross_reference_table[var_name]['lines'].append(line)

        if var_name not in self.symbol_table:
            self.add_error(f"Variable no declarada '{var_name}'",
                           node.get('line'), node.get('column'))
            return 'error', None
        
        if not self.symbol_table[var_name]['is_initialized']:
            self.add_error(f"Variable '{var_name}' usada antes de ser inicializada",
                           node.get('line'), node.get('column'))
            var_type = self.symbol_table[var_name]['type']
            return var_type, None 

        var_type = self.symbol_table[var_name]['type']
        const_val = self.symbol_table[var_name]['const_value']
        
        return var_type, const_val

    def visit_numero(self, node: Dict[str, Any]) -> Tuple[str, Any]:
        """Infiere el tipo y devuelve el valor numérico."""
        value_str = node.get('value', '')
        try:
            if '.' in value_str:
                return 'float', float(value_str)
            else:
                return 'int', int(value_str)
        except ValueError:
             self.add_error(f"Literal numérico mal formado '{value_str}'", node.get('line'), node.get('column'))
             return 'error', None


    def visit_bool(self, node: Dict[str, Any]) -> Tuple[str, Any]:
        """Devuelve el tipo y valor booleano."""
        value = (node.get('value') == 'true')
        return 'bool', value

    def visit_cadena(self, node: Dict[str, Any]) -> Tuple[str, Any]:
        """Devuelve el tipo y valor de cadena."""
        value = node.get('value')
        return 'string', value

    # --- Salida y Reporte ---

    def display_results(self, base_file_path: str):
        """
        Guarda los artefactos (AST Anotado, Tabla de Símbolos) en archivos JSON
        y reporta errores a stderr.
        """
        
        sym_table_file = base_file_path.replace('.txt', '_symbol_table.json')
        try:
            for var in self.cross_reference_table:
                self.cross_reference_table[var]['lines'].sort() 
                
            with open(sym_table_file, 'w', encoding='utf-8') as f:
                json.dump(self.cross_reference_table, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error al guardar la tabla de símbolos: {e}", file=sys.stderr)

        annotated_ast_file = base_file_path.replace('.txt', '_annotated_ast.json')
        if self.ast:
            try:
                with open(annotated_ast_file, 'w', encoding='utf-8') as f:
                    json.dump(self.ast, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Error al guardar el AST anotado: {e}", file=sys.stderr)
        
        if self.errors:
            error_table = PrettyTable()
            error_table.field_names = ["Descripción", "Línea", "Columna"]
            error_table.align = "l"
            
            print("=== ERRORES SEMÁNTICOS ===", file=sys.stderr)
            for error in self.errors:
                error_table.add_row([error.description, error.line, error.column])
            
            print(error_table, file=sys.stderr)
        else:
            pass


def main():
    if len(sys.argv) < 2:
        print("Usage: python semantic_analyzer.py <file>", file=sys.stderr)
        sys.exit(1)
    
    file_path = sys.argv[1]
    ast_file_path = file_path.replace('.txt', '_ast.json')
    
    try:
        analyzer = SemanticAnalyzer()
        
        if not analyzer.load_ast(ast_file_path):
            analyzer.display_results(file_path)
            sys.exit(1)
        
        analyzer.analyze()
        analyzer.display_results(file_path)
        
    except Exception as e:
        print(f"Error fatal en el analizador semántico: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()