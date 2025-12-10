#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
from typing import Dict, Any, List, Optional, Tuple

class IntermediateCodeGenerator:
    """
    Generador de Código Intermedio (Three-Address Code)
    Recorre el AST Anotado y genera instrucciones intermedias.
    """
    def __init__(self):
        self.instructions: List[str] = []
        self.temp_counter = 0
        self.label_counter = 0
        self.ast: Optional[Dict[str, Any]] = None
        
    def new_temp(self) -> str:
        """Genera un nuevo temporal"""
        temp = f"t{self.temp_counter}"
        self.temp_counter += 1
        return temp
    
    def new_label(self) -> str:
        """Genera una nueva etiqueta"""
        label = f"L{self.label_counter}"
        self.label_counter += 1
        return label
    
    def emit(self, instruction: str):
        """Añade una instrucción al código intermedio"""
        self.instructions.append(instruction)
    
    def load_annotated_ast(self, ast_file_path: str) -> bool:
        """Carga el AST Anotado desde el archivo JSON"""
        try:
            with open(ast_file_path, 'r', encoding='utf-8') as f:
                self.ast = json.load(f)
            return True
        except FileNotFoundError:
            print(f"Error: No se encontró el archivo AST anotado: {ast_file_path}", file=sys.stderr)
            return False
        except json.JSONDecodeError:
            print(f"Error: Formato JSON inválido en: {ast_file_path}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Error al cargar el AST: {str(e)}", file=sys.stderr)
            return False
    
    def generate(self):
        """Punto de entrada principal para generar código intermedio"""
        if not self.ast:
            return
        
        try:
            self.emit("# Inicio del Programa")
            self.visit(self.ast)
            self.emit("# Fin del Programa")
            self.emit("HALT")
        except Exception as e:
            print(f"Error durante la generación de código: {str(e)}", file=sys.stderr)
    
    def visit(self, node: Dict[str, Any]) -> Optional[str]:
        """
        Método visitante que despacha al método específico según el tipo de nodo.
        Retorna el nombre del temporal/variable que contiene el resultado.
        """
        if not node:
            return None
            
        node_type = node.get('node_type')
        if not node_type:
            return None
        
        method_name = f"visit_{node_type}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)
    
    def generic_visit(self, node: Dict[str, Any]) -> Optional[str]:
        """Visitante genérico que recorre los hijos"""
        for child in node.get('children', []):
            self.visit(child)
        return None
    
    # --- Visitantes Estructurales ---
    
    def visit_programa(self, node: Dict[str, Any]) -> Optional[str]:
        """Visita el nodo programa"""
        for child in node.get('children', []):
            self.visit(child)
        return None
    
    def visit_lista_declaracion(self, node: Dict[str, Any]) -> Optional[str]:
        """Visita la lista de declaraciones"""
        for child in node.get('children', []):
            self.visit(child)
        return None
    
    def visit_declaracion_variable(self, node: Dict[str, Any]) -> Optional[str]:
        """Genera código para declaración de variables"""
        var_type = node.get('value')
        for child in node.get('children', []):
            if child.get('node_type') == 'id':
                var_name = child.get('value')
                self.emit(f"DECLARE {var_name} {var_type}")
        return None
    
    def visit_lista_sentencias(self, node: Dict[str, Any]) -> Optional[str]:
        """Visita lista de sentencias"""
        for child in node.get('children', []):
            self.visit(child)
        return None
    
    # --- Visitantes de Sentencias ---
    
    def visit_asignacion(self, node: Dict[str, Any]) -> Optional[str]:
        """Genera código para asignación"""
        children = node.get('children', [])
        if len(children) < 2:
            return None
        
        id_node = children[0]
        rhs_node = children[1]
        
        var_name = id_node.get('value')
        
        # Evaluar el lado derecho
        if rhs_node.get('node_type') == 'cadena':
            # Asignación de cadena
            string_value = rhs_node.get('value')
            self.emit(f"{var_name} = {string_value}")
        else:
            # Evaluar expresión
            result = self.visit(rhs_node)
            if result:
                self.emit(f"{var_name} = {result}")
        
        return None
    
    def visit_seleccion(self, node: Dict[str, Any]) -> Optional[str]:
        """Genera código para if-then-else"""
        children = node.get('children', [])
        
        # Extraer condición, then_block, else_block
        cond_node = None
        then_block = None
        else_block = None
        
        for child in children:
            child_type = child.get('node_type')
            if child_type not in ['if', 'then', 'else']:
                if cond_node is None:
                    cond_node = child
            elif child_type == 'then_block':
                then_block = child
            elif child_type == 'else_block':
                else_block = child
        
        if not cond_node:
            return None
        
        # Evaluar condición
        cond_result = self.visit(cond_node)
        
        label_else = self.new_label()
        label_end = self.new_label()
        
        # Salto condicional
        self.emit(f"IF_FALSE {cond_result} GOTO {label_else}")
        
        # Bloque then
        if then_block:
            for child in then_block.get('children', []):
                self.visit(child)
        
        self.emit(f"GOTO {label_end}")
        
        # Bloque else
        self.emit(f"{label_else}:")
        if else_block:
            for child in else_block.get('children', []):
                self.visit(child)
        
        self.emit(f"{label_end}:")
        
        return None
    
    def visit_iteracion(self, node: Dict[str, Any]) -> Optional[str]:
        """Genera código para while"""
        children = node.get('children', [])
        
        # Extraer condición y cuerpo
        condicion_node = None
        cuerpo_node = None
        
        for child in children:
            if child.get('node_type') == 'condicion':
                condicion_node = child
            elif child.get('node_type') == 'cuerpo':
                cuerpo_node = child
        
        if not condicion_node:
            return None
        
        label_start = self.new_label()
        label_end = self.new_label()
        
        # Inicio del loop
        self.emit(f"{label_start}:")
        
        # Evaluar condición
        cond_children = condicion_node.get('children', [])
        if cond_children:
            cond_result = self.visit(cond_children[0])
            self.emit(f"IF_FALSE {cond_result} GOTO {label_end}")
        
        # Cuerpo del loop
        if cuerpo_node:
            for child in cuerpo_node.get('children', []):
                self.visit(child)
        
        self.emit(f"GOTO {label_start}")
        self.emit(f"{label_end}:")
        
        return None
    
    def visit_repeticion(self, node: Dict[str, Any]) -> Optional[str]:
        """Genera código para do-until"""
        children = node.get('children', [])
        
        # Extraer cuerpo y condición
        cuerpo_node = None
        condicion_node = None
        
        for child in children:
            if child.get('node_type') == 'cuerpo':
                cuerpo_node = child
            elif child.get('node_type') == 'condicion':
                condicion_node = child
        
        label_start = self.new_label()
        
        # Inicio del loop
        self.emit(f"{label_start}:")
        
        # Cuerpo del loop
        if cuerpo_node:
            for child in cuerpo_node.get('children', []):
                self.visit(child)
        
        # Evaluar condición (until = mientras NO se cumpla)
        if condicion_node:
            cond_children = condicion_node.get('children', [])
            if cond_children:
                cond_result = self.visit(cond_children[0])
                self.emit(f"IF_FALSE {cond_result} GOTO {label_start}")
        
        return None
    
    def visit_sent_in(self, node: Dict[str, Any]) -> Optional[str]:
        """Genera código para cin"""
        children = node.get('children', [])
        
        for child in children:
            if child.get('node_type') == 'id':
                var_name = child.get('value')
                self.emit(f"READ {var_name}")
        
        return None
    
    def visit_sent_out(self, node: Dict[str, Any]) -> Optional[str]:
        """Genera código para cout"""
        children = node.get('children', [])
        
        for child in children:
            node_type = child.get('node_type')
            
            if node_type == 'cadena':
                string_value = child.get('value')
                self.emit(f"WRITE {string_value}")
            elif node_type not in ['cout', '<<']:
                # Es una expresión
                result = self.visit(child)
                if result:
                    self.emit(f"WRITE {result}")
        
        return None
    
    # --- Visitantes de Expresiones ---
    
    def visit_expresion_simple(self, node: Dict[str, Any]) -> Optional[str]:
        """Genera código para expresión aritmética (+, -)"""
        op = node.get('value')
        children = node.get('children', [])
        
        if len(children) < 2:
            return None
        
        left = self.visit(children[0])
        right = self.visit(children[1])
        
        if not left or not right:
            return None
        
        temp = self.new_temp()
        self.emit(f"{temp} = {left} {op} {right}")
        
        return temp
    
    def visit_termino(self, node: Dict[str, Any]) -> Optional[str]:
        """Genera código para expresión aritmética (*, /, %)"""
        op = node.get('value')
        children = node.get('children', [])
        
        if len(children) < 2:
            return None
        
        left = self.visit(children[0])
        right = self.visit(children[1])
        
        if not left or not right:
            return None
        
        temp = self.new_temp()
        self.emit(f"{temp} = {left} {op} {right}")
        
        return temp
    
    def visit_factor(self, node: Dict[str, Any]) -> Optional[str]:
        """Genera código para expresión aritmética (^)"""
        op = node.get('value')
        children = node.get('children', [])
        
        if len(children) < 2:
            return None
        
        left = self.visit(children[0])
        right = self.visit(children[1])
        
        if not left or not right:
            return None
        
        temp = self.new_temp()
        self.emit(f"{temp} = {left} {op} {right}")
        
        return temp
    
    def visit_expresion_relacional(self, node: Dict[str, Any]) -> Optional[str]:
        """Genera código para expresión relacional"""
        op = node.get('value')
        children = node.get('children', [])
        
        if len(children) < 2:
            return None
        
        left = self.visit(children[0])
        right = self.visit(children[1])
        
        if not left or not right:
            return None
        
        temp = self.new_temp()
        self.emit(f"{temp} = {left} {op} {right}")
        
        return temp
    
    def visit_expresion_logica(self, node: Dict[str, Any]) -> Optional[str]:
        """Genera código para expresión lógica"""
        op = node.get('value')
        children = node.get('children', [])
        
        if op == '!':
            # Operador unario
            if len(children) < 1:
                return None
            
            operand = self.visit(children[0])
            if not operand:
                return None
            
            temp = self.new_temp()
            self.emit(f"{temp} = ! {operand}")
            return temp
        else:
            # Operadores binarios (&&, ||)
            if len(children) < 2:
                return None
            
            left = self.visit(children[0])
            right = self.visit(children[1])
            
            if not left or not right:
                return None
            
            temp = self.new_temp()
            self.emit(f"{temp} = {left} {op} {right}")
            return temp
    
    # --- Visitantes de Nodos Hoja ---
    
    def visit_id(self, node: Dict[str, Any]) -> Optional[str]:
        """Retorna el nombre de la variable"""
        return node.get('value')
    
    def visit_numero(self, node: Dict[str, Any]) -> Optional[str]:
        """Retorna el valor numérico"""
        return node.get('value')
    
    def visit_bool(self, node: Dict[str, Any]) -> Optional[str]:
        """Retorna el valor booleano"""
        return node.get('value')
    
    def visit_cadena(self, node: Dict[str, Any]) -> Optional[str]:
        """Retorna la cadena"""
        return node.get('value')
    
    # Visitantes adicionales para nodos estructurales
    def visit_main(self, node: Dict[str, Any]) -> Optional[str]:
        return None
    
    def visit_then_block(self, node: Dict[str, Any]) -> Optional[str]:
        for child in node.get('children', []):
            self.visit(child)
        return None
    
    def visit_else_block(self, node: Dict[str, Any]) -> Optional[str]:
        for child in node.get('children', []):
            self.visit(child)
        return None
    
    def visit_condicion(self, node: Dict[str, Any]) -> Optional[str]:
        children = node.get('children', [])
        if children:
            return self.visit(children[0])
        return None
    
    def visit_cuerpo(self, node: Dict[str, Any]) -> Optional[str]:
        for child in node.get('children', []):
            self.visit(child)
        return None
    
    # --- Salida ---
    
    def display_results(self, base_file_path: str):
        """Guarda el código intermedio en un archivo"""
        if not self.instructions:
            print("No se generó código intermedio.", file=sys.stderr)
            return
        
        # Guardar en archivo
        intermediate_file = base_file_path.replace('.txt', '_intermediate.txt')
        try:
            with open(intermediate_file, 'w', encoding='utf-8') as f:
                for instruction in self.instructions:
                    f.write(instruction + '\n')
            
            # Mostrar en consola
            print("=== CÓDIGO INTERMEDIO ===")
            for instruction in self.instructions:
                print(instruction)
            print()
            print(f"Código intermedio guardado en: {intermediate_file}")
            
        except Exception as e:
            print(f"Error al guardar el código intermedio: {str(e)}", file=sys.stderr)


def main():
    if len(sys.argv) < 2:
        print("Usage: python intermediate_code_generator.py <file>", file=sys.stderr)
        sys.exit(1)
    
    file_path = sys.argv[1]
    annotated_ast_file = file_path.replace('.txt', '_annotated_ast.json')
    
    try:
        generator = IntermediateCodeGenerator()
        
        if not generator.load_annotated_ast(annotated_ast_file):
            sys.exit(1)
        
        generator.generate()
        generator.display_results(file_path)
        
    except Exception as e:
        print(f"Error fatal en el generador de código intermedio: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()