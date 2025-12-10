#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import re
from typing import Dict, Any, List, Optional

class CodeExecutor:
    """
    Ejecutor de Código Intermedio
    Interpreta las instrucciones de tres direcciones generadas.
    """
    def __init__(self):
        self.instructions: List[str] = []
        self.pc = 0  # Program Counter
        self.variables: Dict[str, Any] = {}
        self.labels: Dict[str, int] = {}
        self.output: List[str] = []
        
    def load_intermediate_code(self, file_path: str) -> bool:
        """Carga el código intermedio desde el archivo"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.instructions = [line.strip() for line in f.readlines() if line.strip()]
            
            # Primera pasada: encontrar etiquetas
            self._find_labels()
            return True
            
        except FileNotFoundError:
            print(f"Error: No se encontró el archivo de código intermedio: {file_path}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Error al cargar el código intermedio: {str(e)}", file=sys.stderr)
            return False
    
    def _find_labels(self):
        """Primera pasada: mapear etiquetas a números de línea"""
        for i, instruction in enumerate(self.instructions):
            if instruction.endswith(':'):
                label_name = instruction[:-1]
                self.labels[label_name] = i
    
    def execute(self):
        """Ejecuta el código intermedio"""
        try:
            self.pc = 0
            max_iterations = 100000  # Prevenir loops infinitos
            iteration_count = 0
            
            while self.pc < len(self.instructions) and iteration_count < max_iterations:
                instruction = self.instructions[self.pc]
                iteration_count += 1
                
                # Saltar comentarios y etiquetas
                if instruction.startswith('#') or instruction.endswith(':'):
                    self.pc += 1
                    continue
                
                # Ejecutar instrucción
                if not self._execute_instruction(instruction):
                    break
                
                self.pc += 1
            
            if iteration_count >= max_iterations:
                print("Advertencia: Se alcanzó el límite de iteraciones", file=sys.stderr)
                
        except Exception as e:
            print(f"Error durante la ejecución: {str(e)}", file=sys.stderr)
            print(f"En la instrucción {self.pc}: {self.instructions[self.pc] if self.pc < len(self.instructions) else 'N/A'}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    
    def _execute_instruction(self, instruction: str) -> bool:
        """Ejecuta una instrucción individual. Retorna False si es HALT."""
        
        # HALT - Detener ejecución
        if instruction == 'HALT':
            return False
        
        # DECLARE - Declarar variable
        if instruction.startswith('DECLARE'):
            self._execute_declare(instruction)
            return True
        
        # READ - Leer entrada
        if instruction.startswith('READ'):
            self._execute_read(instruction)
            return True
        
        # WRITE - Escribir salida
        if instruction.startswith('WRITE'):
            self._execute_write(instruction)
            return True
        
        # GOTO - Salto incondicional
        if instruction.startswith('GOTO'):
            self._execute_goto(instruction)
            return True
        
        # IF_FALSE - Salto condicional
        if instruction.startswith('IF_FALSE'):
            self._execute_if_false(instruction)
            return True
        
        # Asignación (contiene '=')
        if '=' in instruction:
            self._execute_assignment(instruction)
            return True
        
        return True
    
    def _execute_declare(self, instruction: str):
        """Ejecuta DECLARE variable tipo"""
        parts = instruction.split()
        if len(parts) >= 3:
            var_name = parts[1]
            var_type = parts[2]
            
            # Inicializar según tipo
            if var_type == 'int':
                self.variables[var_name] = 0
            elif var_type == 'float':
                self.variables[var_name] = 0.0
            elif var_type == 'bool':
                self.variables[var_name] = False
            else:
                self.variables[var_name] = None
    
    def _execute_read(self, instruction: str):
        """Ejecuta READ variable"""
        parts = instruction.split()
        if len(parts) >= 2:
            var_name = parts[1]
            
            try:
                # Leer entrada del usuario
                if sys.stdout.isatty(): # Solo imprimir si es una terminal interactiva
                    print(f"Ingrese valor para {var_name}: ", end='', flush=True)
                user_input = input()
                
                # Intentar convertir a número
                if '.' in user_input:
                    self.variables[var_name] = float(user_input)
                else:
                    try:
                        self.variables[var_name] = int(user_input)
                    except ValueError:
                        # Si no es número, guardar como string
                        self.variables[var_name] = user_input
                        
            except (EOFError, KeyboardInterrupt):
                print(f"\nError: No se pudo leer entrada para {var_name}", file=sys.stderr)
                self.variables[var_name] = 0
    
    def _execute_write(self, instruction: str):
        """Ejecuta WRITE expresion"""
        # Extraer lo que se va a escribir
        match = re.match(r'WRITE\s+(.+)', instruction)
        if match:
            expr = match.group(1).strip()
            
            # Evaluar la expresión
            value = self._evaluate_expression(expr)
            
            # Limpiar comillas si es string literal
            if isinstance(value, str) and value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            
            print(value, flush=True)
            self.output.append(str(value))
    
    def _execute_goto(self, instruction: str):
        """Ejecuta GOTO label"""
        parts = instruction.split()
        if len(parts) >= 2:
            label = parts[1]
            if label in self.labels:
                self.pc = self.labels[label] - 1  # -1 porque se incrementará después
            else:
                print(f"Error: Etiqueta no encontrada: {label}", file=sys.stderr)
    
    def _execute_if_false(self, instruction: str):
        """Ejecuta IF_FALSE condicion GOTO label"""
        match = re.match(r'IF_FALSE\s+(.+?)\s+GOTO\s+(\S+)', instruction, re.DOTALL)
        if match:
            condition = match.group(1)
            label = match.group(2)
            
            # Evaluar condición
            cond_value = self._evaluate_expression(condition)
            
            # Convertir a booleano
            if isinstance(cond_value, (int, float)):
                cond_bool = cond_value != 0
            elif isinstance(cond_value, bool):
                cond_bool = cond_value
            else:
                cond_bool = bool(cond_value)
            
            # Si es falsa, saltar
            if not cond_bool:
                if label in self.labels:
                    self.pc = self.labels[label] - 1  # -1 porque se incrementará después
                else:
                    print(f"Error: Etiqueta no encontrada: {label}", file=sys.stderr)
    
    def _execute_assignment(self, instruction: str):
        """Ejecuta asignación: var = expresion"""
        parts = instruction.split('=', 1)
        if len(parts) == 2:
            var_name = parts[0].strip()
            expr = parts[1].strip()
            
            # Evaluar expresión del lado derecho
            value = self._evaluate_expression(expr)
            
            # Asignar a la variable
            self.variables[var_name] = value
    
    def _evaluate_expression(self, expr: str) -> Any:
        """Evalúa una expresión y retorna su valor"""
        expr = expr.strip()
        
        # String literal
        if expr.startswith('"') and expr.endswith('"'):
            return expr
        
        # Booleanos
        if expr == 'true':
            return True
        if expr == 'false':
            return False
        
        # Número flotante
        try:
            if '.' in expr and not any(op in expr for op in [' ', '+', '-', '*', '/', '%', '^', '<', '>', '=', '!', '&', '|']):
                return float(expr)
        except ValueError:
            pass
        
        # Número entero
        try:
            if not any(op in expr for op in [' ', '+', '-', '*', '/', '%', '^', '<', '>', '=', '!', '&', '|', '.']):
                return int(expr)
        except ValueError:
            pass
        
        # Variable
        if expr in self.variables:
            return self.variables[expr]
        
        # Operación unaria (!)
        if expr.startswith('! '):
            operand = expr[2:].strip()
            val = self._evaluate_expression(operand)
            if isinstance(val, bool):
                return not val
            return not bool(val)
        
        # --- Evaluación de operadores binarios por precedencia (de menor a mayor) ---

        # 1. Operador lógico OR (||)
        left_part, op, right_part = expr.rpartition(' || ')
        if op:
            left = self._evaluate_expression(left_part)
            right = self._evaluate_expression(right_part)
            return self._apply_operator(op.strip(), left, right)

        # 2. Operador lógico AND (&&)
        left_part, op, right_part = expr.rpartition(' && ')
        if op:
            left = self._evaluate_expression(left_part)
            right = self._evaluate_expression(right_part)
            return self._apply_operator(op.strip(), left, right)

        # 3. Operadores relacionales (==, !=, <=, >=, <, >)
        for op in ['==', '!=', '<=', '>=', '<', '>']:
            left_part, found_op, right_part = expr.rpartition(f' {op} ')
            if found_op:
                left = self._evaluate_expression(left_part)
                right = self._evaluate_expression(right_part)
                return self._apply_operator(op, left, right)

        # 4. Operadores aritméticos de adición y sustracción (+, -)
        for op in ['+', '-']:
            left_part, found_op, right_part = expr.rpartition(f' {op} ')
            if found_op:
                left = self._evaluate_expression(left_part)
                right = self._evaluate_expression(right_part)
                return self._apply_operator(op, left, right)

        # 5. Operadores aritméticos de multiplicación, división y módulo (*, /, %)
        for op in ['*', '/', '%']:
            left_part, found_op, right_part = expr.rpartition(f' {op} ')
            if found_op:
                left = self._evaluate_expression(left_part)
                right = self._evaluate_expression(right_part)
                return self._apply_operator(op, left, right)

        # 6. Operador de potencia (^) - asociatividad derecha
        left_part, op, right_part = expr.partition(' ^ ')
        if op:
            left = self._evaluate_expression(left_part)
            right = self._evaluate_expression(right_part)
            return self._apply_operator(op.strip(), left, right)
        
        # Si no se pudo evaluar, retornar 0
        print(f"Advertencia: No se pudo evaluar expresión: '{expr}'", file=sys.stderr)
        return 0
    
    def _apply_operator(self, op: str, left: Any, right: Any) -> Any:
        """Aplica un operador binario"""
        try:
            if op == '+':
                return left + right
            elif op == '-':
                return left - right
            elif op == '*':
                return left * right
            elif op == '/':
                if right == 0:
                    print("Error: División por cero", file=sys.stderr)
                    return 0
                # División entera si ambos son enteros
                if isinstance(left, int) and isinstance(right, int):
                    return left // right
                return left / right
            elif op == '%':
                if right == 0:
                    print("Error: Módulo por cero", file=sys.stderr)
                    return 0
                return left % right
            elif op == '^':
                return left ** right
            elif op == '==':
                return left == right
            elif op == '!=':
                return left != right
            elif op == '<':
                return left < right
            elif op == '>':
                return left > right
            elif op == '<=':
                return left <= right
            elif op == '>=':
                return left >= right
            elif op == '&&':
                # Convertir a booleano correctamente
                left_bool = bool(left) if not isinstance(left, bool) else left
                right_bool = bool(right) if not isinstance(right, bool) else right
                return left_bool and right_bool
            elif op == '||':
                # Convertir a booleano correctamente
                left_bool = bool(left) if not isinstance(left, bool) else left
                right_bool = bool(right) if not isinstance(right, bool) else right
                return left_bool or right_bool
            else:
                print(f"Error: Operador desconocido: {op}", file=sys.stderr)
                return 0
        except Exception as e:
            print(f"Error en operación {op}: {str(e)}", file=sys.stderr)
            return 0
    
    def display_results(self):
        """Muestra los resultados de la ejecución"""
        print("\n" + "="*50)
        print("RESULTADOS DE LA EJECUCIÓN")
        print("="*50)
        
        if self.output:
            print("\nSalida del programa:")
            print("-" * 50)
            for line in self.output:
                print(line)
        else:
            print("\nNo hay salida del programa.")
        
        print("\n" + "="*50)
        print("ESTADO FINAL DE VARIABLES")
        print("="*50)
        if self.variables:
            # Ordenar y mostrar solo variables del usuario (no temporales)
            user_vars = {k: v for k, v in self.variables.items() if not k.startswith('t')}
            if user_vars:
                for var, value in sorted(user_vars.items()):
                    print(f"{var:20} = {value}")
            else:
                print("No hay variables de usuario.")
        else:
            print("No hay variables.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python code_executor.py <file>", file=sys.stderr)
        sys.exit(1)
    
    file_path = sys.argv[1]
    intermediate_file = file_path.replace('.txt', '_intermediate.txt')
    
    try:
        executor = CodeExecutor()
        
        if not executor.load_intermediate_code(intermediate_file):
            print("\nNo se pudo cargar el código intermedio.", file=sys.stderr)
            print("Asegúrese de ejecutar primero la fase de generación de código intermedio.", file=sys.stderr)
            sys.exit(1)
        
        print("="*50)
        print("EJECUCIÓN DEL PROGRAMA")
        print("="*50 + "\n")
        
        executor.execute()
        executor.display_results()
        
    except Exception as e:
        print(f"\nError fatal en el ejecutor: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()