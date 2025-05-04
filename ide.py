import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPlainTextEdit, QTextEdit, QDockWidget, 
                            QMenuBar, QMenu, QToolBar, QFileDialog, QMessageBox,
                            QVBoxLayout, QWidget, QLabel, QPushButton)
from PyQt6.QtCore import Qt, QProcess, QRect, QSize
from PyQt6.QtGui import QAction, QTextCursor, QSyntaxHighlighter, QTextCharFormat, QPainter, QColor, QIcon
import os
from PyQt6.QtCore import QRegularExpression


class CompilerIDE(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.process = QProcess()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Compiler IDE')
        self.setGeometry(100, 100, 1200, 800)

        # Create central widget (code editor)
        self.editor = CodeEditor()
        self.setCentralWidget(self.editor)

        # Create dock widgets
        self.createDockWindows()
        
        # Create menus
        self.createMenus()
        
        # Create toolbar
        self.createToolBar()
        
        # Configurar barra de estado
        self.statusBar().showMessage('Bora v1.3')
        self.status_position = QLabel()
        self.statusBar().addPermanentWidget(self.status_position)
        
        # Conectar señal de cambio de cursor
        self.editor.cursorPositionChanged.connect(self.update_cursor_position)
        
        self.show()

    def createMenus(self):
        # File menu
        fileMenu = self.menuBar().addMenu('File')
        
        newAct = QAction('New', self)
        newAct.setShortcut('Ctrl+N')
        newAct.triggered.connect(self.newFile)
        fileMenu.addAction(newAct)

        openAct = QAction('Open', self)
        openAct.setShortcut('Ctrl+O')
        openAct.triggered.connect(self.openFile)
        fileMenu.addAction(openAct)

        saveAct = QAction('Save', self)
        saveAct.setShortcut('Ctrl+S')
        saveAct.triggered.connect(self.saveFile)
        fileMenu.addAction(saveAct)

        saveAsAct = QAction('Save As...', self)
        saveAsAct.triggered.connect(self.saveFileAs)
        fileMenu.addAction(saveAsAct)

        closeAct = QAction('Close File', self)
        closeAct.setShortcut('Ctrl+W')  # Atajo similar a VS Code
        closeAct.triggered.connect(self.closeFile)
        fileMenu.addAction(closeAct)

        # Compile menu
        compileMenu = self.menuBar().addMenu('Compile')
        
        lexicalAct = QAction('Lexical Analysis', self)
        lexicalAct.triggered.connect(self.runLexicalAnalysis)
        compileMenu.addAction(lexicalAct)

        syntaxAct = QAction('Syntax Analysis', self)
        syntaxAct.triggered.connect(self.runSyntaxAnalysis)
        compileMenu.addAction(syntaxAct)

        semanticAct = QAction('Semantic Analysis', self)
        semanticAct.triggered.connect(self.runSemanticAnalysis)
        compileMenu.addAction(semanticAct)

        intermediateAct = QAction('Generate Intermediate Code', self)
        intermediateAct.triggered.connect(self.generateIntermediateCode)
        compileMenu.addAction(intermediateAct)

        executeAct = QAction('Execute', self)
        executeAct.triggered.connect(self.executeCode)
        compileMenu.addAction(executeAct)

    def createToolBar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        # Save icon
        save_act = QAction(QIcon.fromTheme('document-save'), '', self)
        save_act.setToolTip('Guardar')
        save_act.triggered.connect(self.saveFile)
        toolbar.addAction(save_act)

        # Exit icon
        close_act = QAction(QIcon.fromTheme('window-close'), '', self)
        close_act.setToolTip('Cerrar archivo')
        close_act.triggered.connect(self.closeFile)
        toolbar.addAction(close_act)

        # Add compilation phase buttons
        lexicalBtn = QPushButton('Lexical', self)
        lexicalBtn.clicked.connect(self.runLexicalAnalysis)
        toolbar.addWidget(lexicalBtn)

        syntaxBtn = QPushButton('Syntax', self)
        syntaxBtn.clicked.connect(self.runSyntaxAnalysis)
        toolbar.addWidget(syntaxBtn)

        semanticBtn = QPushButton('Semantic', self)
        semanticBtn.clicked.connect(self.runSemanticAnalysis)
        toolbar.addWidget(semanticBtn)

        intermediateBtn = QPushButton('Intermediate', self)
        intermediateBtn.clicked.connect(self.generateIntermediateCode)
        toolbar.addWidget(intermediateBtn)

        executeBtn = QPushButton('Execute', self)
        executeBtn.clicked.connect(self.executeCode)
        toolbar.addWidget(executeBtn)

        # Execute icon
        execute_act = QAction(QIcon.fromTheme('media-playback-start'), '', self)
        execute_act.setToolTip('Ejecutar')
        execute_act.triggered.connect(self.executeCode)
        toolbar.addAction(execute_act)
        
    def createDockWindows(self):
        # Create all dock widgets
        
        # Right dock area - Analysis outputs
        self.lexicalDock = QDockWidget("Lexical", self)
        self.lexicalOutput = QPlainTextEdit()
        self.lexicalOutput.setReadOnly(True)
        self.lexicalDock.setWidget(self.lexicalOutput)
        
        self.syntaxDock = QDockWidget("Syntax", self)
        self.syntaxOutput = QPlainTextEdit()
        self.syntaxOutput.setReadOnly(True)
        self.syntaxDock.setWidget(self.syntaxOutput)
        
        self.semanticDock = QDockWidget("Semantic", self)
        self.semanticOutput = QPlainTextEdit()
        self.semanticOutput.setReadOnly(True)
        self.semanticDock.setWidget(self.semanticOutput)
        
        self.hashTableDock = QDockWidget("Hash Table", self)
        self.hashTableOutput = QPlainTextEdit()
        self.hashTableOutput.setReadOnly(True)
        self.hashTableDock.setWidget(self.hashTableOutput)
        
        self.intermediateDock = QDockWidget("Intermediate Code", self)
        self.intermediateOutput = QPlainTextEdit()
        self.intermediateOutput.setReadOnly(True)
        self.intermediateDock.setWidget(self.intermediateOutput)
        
        # Add the first dock widget to the right area
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.lexicalDock)
        
        # Tabify the analysis docks together
        self.tabifyDockWidget(self.lexicalDock, self.syntaxDock)
        self.tabifyDockWidget(self.syntaxDock, self.semanticDock)
        self.tabifyDockWidget(self.semanticDock, self.hashTableDock)
        self.tabifyDockWidget(self.hashTableDock, self.intermediateDock)
        
        # Bottom dock area - Output windows
        self.errorsLexicalDock = QDockWidget("Errores Léxicos", self)
        self.errorsLexicalOutput = QPlainTextEdit()
        self.errorsLexicalOutput.setReadOnly(True)
        self.errorsLexicalDock.setWidget(self.errorsLexicalOutput)
        
        self.errorsSyntaxDock = QDockWidget("Errores Sintácticos", self)
        self.errorsSyntaxOutput = QPlainTextEdit()
        self.errorsSyntaxOutput.setReadOnly(True)
        self.errorsSyntaxDock.setWidget(self.errorsSyntaxOutput)
        
        self.errorsSemanticDock = QDockWidget("Errores Semánticos", self)
        self.errorsSemanticOutput = QPlainTextEdit()
        self.errorsSemanticOutput.setReadOnly(True)
        self.errorsSemanticDock.setWidget(self.errorsSemanticOutput)
        
        self.resultDock = QDockWidget("Resultados", self)
        self.resultOutput = QPlainTextEdit()
        self.resultOutput.setReadOnly(True)
        self.resultDock.setWidget(self.resultOutput)
        
        # Add the first dock widget to the bottom area
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.resultDock)
        
        # Tabify the output docks together
        self.tabifyDockWidget(self.resultDock, self.errorsLexicalDock)
        self.tabifyDockWidget(self.errorsLexicalDock, self.errorsSyntaxDock)
        self.tabifyDockWidget(self.errorsSyntaxDock, self.errorsSemanticDock)
        
        # Make the first tab in each group visible
        self.lexicalDock.raise_()
        self.resultDock.raise_()
        
        # Set features for all dock widgets to prevent closing
        for dock in [self.lexicalDock, self.syntaxDock, self.semanticDock,
                     self.hashTableDock, self.intermediateDock,
                     self.errorsLexicalDock, self.errorsSyntaxDock, 
                     self.errorsSemanticDock, self.resultDock]:
            dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable |
                                QDockWidget.DockWidgetFeature.DockWidgetFloatable)

    def newFile(self):
        if not self.confirmSaveChanges():
            return  # Si el usuario cancela la acción, no se borra el archivo actual
        
        self.editor.clear()
        self.current_file = None
        self.updateWindowTitle()

    def openFile(self):
        if not self.confirmSaveChanges():
            return  # Evitar perder cambios sin guardar
            
        options = QFileDialog.Option.ReadOnly
        fname, _ = QFileDialog.getOpenFileName(
            self, 'Open File', '', 
            'Text Files (*.txt);;Python Files (*.py);;All Files (*)',
            options=options
        )
        
        if fname:
            try:
                with open(fname, 'r') as f:
                    self.editor.setPlainText(f.read())
                self.current_file = fname
                self.document_saved = True
                self.updateWindowTitle()
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Could not open file: {str(e)}')

    def saveFile(self):
        if self.current_file:
            result = self.saveFileToPath(self.current_file)
            return result
        else:
            return self.saveFileAs()

    def saveFileAs(self):
        fname, _ = QFileDialog.getSaveFileName(
            self, 'Save File As', '', 
            'Text Files (*.txt);;Python Files (*.py);;All Files (*)'
        )
        
        if fname:
            result = self.saveFileToPath(fname)
            return result
        return False

    def saveFileToPath(self, path):
        try:
            with open(path, 'w') as f:
                f.write(self.editor.toPlainText())
            self.current_file = path
            self.document_saved = True
            self.updateWindowTitle()
            return True
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Could not save file: {str(e)}')
            return False

    def closeFile(self):
        if not self.confirmSaveChanges():
            return  # Usuario canceló la operación
            
        # Limpiar el editor y restablecer el estado
        self.editor.setPlainText("")
        self.current_file = None
        self.document_saved = True
        self.updateWindowTitle()

    def closeEvent(self, event):
        """Maneja el evento de cierre de la aplicación."""
        if self.confirmSaveChanges():
            event.accept()  # Continuar con el cierre
        else:
            event.ignore()  # Cancelar el cierre

    def confirmSaveChanges(self):
        """
        Pregunta al usuario si desea guardar los cambios antes de cerrar.
        Retorna True si se puede continuar con el cierre, False si se debe cancelar.
        """
        if self.isDocumentModified():
            reply = QMessageBox.question(
                self, 'Documento sin guardar',
                '¿Desea guardar los cambios antes de salir?',
                QMessageBox.StandardButton.Save | 
                QMessageBox.StandardButton.Discard | 
                QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            
            if reply == QMessageBox.StandardButton.Save:
                # Guardar y continuar si se guardó correctamente
                return self.saveFile()
            elif reply == QMessageBox.StandardButton.Cancel:
                # Cancelar el cierre
                return False
            # Si eligió Discard, continuar sin guardar
        
        # Si no hay cambios o eligió Discard, permitir continuar
        return True

    def isDocumentModified(self):
        """
        Comprueba si el documento ha sido modificado desde la última vez que se guardó.
        """
        if not hasattr(self, 'document_saved'):
            return self.editor.toPlainText() != ""
        
        if not self.document_saved:
            return True
        
        # Si tenemos un archivo actual, comprobar si el contenido es diferente al guardado
        if self.current_file:
            try:
                with open(self.current_file, 'r') as f:
                    saved_content = f.read()
                return saved_content != self.editor.toPlainText()
            except Exception:
                return True
        
        # Si no hay archivo y hay contenido, está modificado
        return self.editor.toPlainText() != ""

    def updateWindowTitle(self):
        """Actualiza el título de la ventana mostrando el nombre del archivo."""
        title = "IDE"
        if self.current_file:
            title = f"{os.path.basename(self.current_file)} - IDE"
            if self.isDocumentModified():
                title = f"*{title}"
        self.setWindowTitle(title)

    def runLexicalAnalysis(self):
        if not self.current_file:
            QMessageBox.warning(self, 'Warning', 'Please save the file first')
            return
        
        # Run the lexical analyzer as a separate process
        process = QProcess()
        process.start('python', ['lexical_analyzer.py', self.current_file])
        process.waitForFinished()
        
        # Get the output and display it
        output = process.readAllStandardOutput().data().decode()
        self.lexicalOutput.setPlainText(output)
        
        # Check for errors
        error = process.readAllStandardError().data().decode()
        if error:
            self.errorOutput.append("Lexical Analysis Errors:\n" + error)

    def runSyntaxAnalysis(self):
        if not self.current_file:
            QMessageBox.warning(self, 'Warning', 'Please save the file first')
            return
        
        process = QProcess()
        process.start('python', ['syntax_analyzer.py', self.current_file])
        process.waitForFinished()
        
        output = process.readAllStandardOutput().data().decode()
        self.syntaxOutput.setPlainText(output)
        
        error = process.readAllStandardError().data().decode()
        if error:
            self.errorOutput.append("Syntax Analysis Errors:\n" + error)

    def runSemanticAnalysis(self):
        if not self.current_file:
            QMessageBox.warning(self, 'Warning', 'Please save the file first')
            return
        
        process = QProcess()
        process.start('python', ['semantic_analyzer.py', self.current_file])
        process.waitForFinished()
        
        output = process.readAllStandardOutput().data().decode()
        self.semanticOutput.setPlainText(output)
        
        error = process.readAllStandardError().data().decode()
        if error:
            self.errorOutput.append("Semantic Analysis Errors:\n" + error)

    def generateIntermediateCode(self):
        if not self.current_file:
            QMessageBox.warning(self, 'Warning', 'Please save the file first')
            return
        
        process = QProcess()
        process.start('python', ['intermediate_code_generator.py', self.current_file])
        process.waitForFinished()
        
        output = process.readAllStandardOutput().data().decode()
        self.intermediateOutput.setPlainText(output)
        
        error = process.readAllStandardError().data().decode()
        if error:
            self.errorOutput.append("Intermediate Code Generation Errors:\n" + error)

    def executeCode(self):
        if not self.current_file:
            QMessageBox.warning(self, 'Warning', 'Please save the file first')
            return
        
        process = QProcess()
        process.start('python', ['code_executor.py', self.current_file])
        process.waitForFinished()
        
        output = process.readAllStandardOutput().data().decode()
        self.executionOutput.setPlainText(output)
        
        error = process.readAllStandardError().data().decode()
        if error:
            self.errorOutput.append("Execution Errors:\n" + error)
        
    def update_cursor_position(self):
        cursor = self.editor.textCursor()
        line = cursor.blockNumber() + 1  # Línea basada en 1
        column = cursor.columnNumber() + 1  # Columna basada en 1
        
        if cursor.hasSelection():
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            selected_length = abs(end - start)
        else:
            selected_length = 0
        
        text = f"Línea: {line}, Columna: {column}"
        if selected_length > 0:
            text += f", Seleccionados: {selected_length} caracteres"
        
        self.status_position.setText(text)

class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.highlighter = Highlighter(self.document())
        self.lineNumberArea = LineNumberArea(self)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)

                # Habilitar el desplazamiento horizontal
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        
        self.updateLineNumberAreaWidth()
        self.highlightCurrentLine()

    def lineNumberAreaWidth(self):
        digits = len(str(max(1, self.blockCount())))
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def updateLineNumberAreaWidth(self):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def highlightCurrentLine(self):
        extraSelections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor("#ffffff") 
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QSize(self.codeEditor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(event.rect(), Qt.GlobalColor.lightGray)
        block = self.codeEditor.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.codeEditor.blockBoundingGeometry(block).translated(self.codeEditor.contentOffset()).top()
        bottom = top + self.codeEditor.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(Qt.GlobalColor.black)
                painter.drawText(0, int(top), self.width(), self.codeEditor.fontMetrics().height(),
                                Qt.AlignmentFlag.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + self.codeEditor.blockBoundingRect(block).height()
            blockNumber += 1
class Highlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.rules = []

        # Formato para operadores relacionales y lógicos (color azul marino)
        logic_operator_format = QTextCharFormat()
        logic_operator_format.setForeground(QColor("orange"))

        # Formato para el signo de asignación (=) - azul medio
        assignment_format = QTextCharFormat()
        assignment_format.setForeground(QColor("mediumblue"))


        # Formato para operadores aritméticos (color rojo)
        operator_format = QTextCharFormat()
        operator_format.setForeground(QColor("red"))


         # Formato para palabras clave (verde oscuro)
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor("darkgreen"))


         # Formato para cadenas (contenido en rosa, comillas en azul rey)
        self.string_content_format = QTextCharFormat()
        self.string_content_format.setForeground(QColor("hotpink"))

        self.quote_format = QTextCharFormat()
        self.quote_format.setForeground(QColor("royalblue"))

        # Patrón para cadenas completas (incluye comillas)
        string_pattern = r'"[^"\n]*"'
        self.rules.append((string_pattern, self.string_content_format))


        # Formato para números enteros y reales (color cian)
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("cyan"))

        # Formato para identificadores de variables (color púrpura)
        self.variable_format = QTextCharFormat()
        self.variable_format.setForeground(QColor("purple"))

        # Formato para identificadores de funciones (color verde)
        self.function_format = QTextCharFormat()
        self.function_format.setForeground(QColor("lightgreen"))

        # Formato para comentarios (color amarillo mostaza)
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("goldenrod"))

        # Patrón para operadores relacionales y lógicos
        logic_operator_pattern = r'<=|>=|!=|==|<|>|\&\&|\|\||!'
        self.rules.append((logic_operator_pattern, logic_operator_format))

        # Patrón para signo de asignación =
        assignment_pattern = r'(?<![=!<>])=(?![=])'
        self.rules.append((assignment_pattern, assignment_format))


        # Patrón para operadores aritméticos
        operator_pattern = r'\+|\-|\*|\/|\%|\^|\+\+|\-\-'
        self.rules.append((operator_pattern, operator_format))  # Añadimos la regla

        # Formato para símbolos de puntuación (color gris oscuro)
        symbol_format = QTextCharFormat()
        symbol_format.setForeground(QColor("darkgray"))


        # Patrón para números enteros
        integer_pattern = r'\b\d+\b'
        self.rules.append((integer_pattern, number_format))

        # Patrón para números reales
        float_pattern = r'\b\d+\.\d+\b'
        self.rules.append((float_pattern, number_format))

        self.defined_variables = set()


        # Comentarios de una línea (// ...)
        single_line_comment_pattern = r'//[^\n]*'
        self.rules.append((single_line_comment_pattern, self.comment_format))

        # Patrón para símbolos de puntuación
        symbol_pattern = r'[:\(\)\{\},;]'
        self.rules.append((symbol_pattern, symbol_format))

        

        # Palabras clave reservadas (no resaltarlas como identificadores)
        self.KEYWORDS = {
            "if", "else", "end", "do", "while", "switch", "case", 
            "int", "float", "main", "cin", "cout", "for", "return", 
            "char", "bool", "real", "then", "until"
        }

        

        # Expresiones regulares para comentarios multilínea
        self.comment_start_expression = QRegularExpression(r'/\*')
        self.comment_end_expression = QRegularExpression(r'\*/')

    def highlightBlock(self, text):
        for keyword in self.KEYWORDS:
            pattern = QRegularExpression(r'\b' + QRegularExpression.escape(keyword) + r'\b')
            match_iter = pattern.globalMatch(text)
            while match_iter.hasNext():
                match = match_iter.next()
                start = match.capturedStart()
                length = match.capturedLength()
                self.setFormat(start, length, self.keyword_format)
        # Reglas normales
        for pattern, fmt in self.rules:
            expression = QRegularExpression(pattern)
            i = expression.globalMatch(text)
            while i.hasNext():
                match = i.next()
                token = match.captured(0)
                start = match.capturedStart()
                length = match.capturedLength()

                if token in self.KEYWORDS:
                    self.setFormat(start, length, self.keyword_format)
                    continue

                # Si el identificador es seguido por '(', lo tratamos como función
                if fmt == self.variable_format and len(text) > start + length and text[start + length] == '(':
                    self.setFormat(start, length, self.function_format)
                else:
                    self.setFormat(start, length, fmt)
         # Resaltado especial para comillas y contenido de cadenas
        string_regex = QRegularExpression(r'"[^"\n]*"')
        match_iter = string_regex.globalMatch(text)
        while match_iter.hasNext():
            match = match_iter.next()
            start = match.capturedStart()
            length = match.capturedLength()
            full_text = match.captured(0)

            if len(full_text) >= 2:
                # Resalta las comillas en azul rey
                self.setFormat(start, 1, self.quote_format)  # Comilla inicial
                self.setFormat(start + length - 1, 1, self.quote_format)  # Comilla final

                # Resalta el contenido dentro de las comillas en rosa
                if length > 2:
                    self.setFormat(start + 1, length - 2, self.string_content_format)

        # Comentarios multilínea
        self.setCurrentBlockState(0)

        start_idx = 0
        if self.previousBlockState() != 1:
            start_idx = text.find("/*")

        while start_idx >= 0:
            end_idx = text.find("*/", start_idx)
            if end_idx == -1:
                self.setCurrentBlockState(1)
                comment_length = len(text) - start_idx
            else:
                comment_length = end_idx - start_idx + 2

            self.setFormat(start_idx, comment_length, self.comment_format)
            start_idx = text.find("/*", start_idx + comment_length)
 # Resaltamos como variable

        # Detectar y guardar identificadores definidos por el usuario (declaración o asignación)
        declaration_pattern = QRegularExpression(
            r'\b(?:int|float|char|bool|var)\s+((?:[a-zA-Z_][a-zA-Z0-9_]*\s*,\s*)*[a-zA-Z_][a-zA-Z0-9_]*)')
        assignment_pattern = QRegularExpression(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=')

        # Usamos un set temporal para evitar modificar el original mientras se itera
        new_vars = set()

        # Capturar variables de declaraciones múltiples
        match_iter = declaration_pattern.globalMatch(text)
        while match_iter.hasNext():
            match = match_iter.next()
            vars_group = match.captured(1)
            var_names = [v.strip() for v in vars_group.split(',')]
            for var in var_names:
                if var not in self.KEYWORDS:
                    new_vars.add(var)

        # Capturar variables por asignación
        match_iter = assignment_pattern.globalMatch(text)
        while match_iter.hasNext():
            match = match_iter.next()
            var_name = match.captured(1)
            if var_name not in self.KEYWORDS:
                new_vars.add(var_name)

        # Actualizar variables definidas
        self.defined_variables.update(new_vars)

        # Resaltar variables ya definidas
        for var in list(self.defined_variables):  # Convertimos a lista por seguridad
            if var in self.KEYWORDS:
                continue  # No resaltar si es palabra clave

            var_regex = QRegularExpression(r'\b' + QRegularExpression.escape(var) + r'\b')
            match_iter = var_regex.globalMatch(text)
            while match_iter.hasNext():
                match = match_iter.next()
                start = match.capturedStart()
                length = match.capturedLength()

                # Si el identificador es seguido de '(', es función
                if len(text) > start + length and text[start + length] == '(':
                    self.setFormat(start, length, self.function_format)
                else:
                    self.setFormat(start, length, self.variable_format)




def main():
    app = QApplication(sys.argv)
    ide = CompilerIDE()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()