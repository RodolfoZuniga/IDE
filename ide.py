import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPlainTextEdit, QTextEdit, QDockWidget, 
                            QMenuBar, QMenu, QToolBar, QFileDialog, QMessageBox,
                            QVBoxLayout, QWidget, QLabel, QPushButton, QTreeView, QHeaderView)
from PyQt6.QtCore import Qt, QProcess, QRect, QSize
from PyQt6.QtGui import QAction, QTextCursor, QSyntaxHighlighter, QTextCharFormat, QPainter, QColor, QIcon, QStandardItemModel, QStandardItem
import os
from PyQt6.QtCore import QRegularExpression
import json
from prettytable import PrettyTable

class CompilerIDE(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.process = QProcess()
        self.document_saved = True
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
        
        # Conectar el textChanged del editor para actualizar el título
        self.editor.textChanged.connect(self.updateWindowTitle)
        
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
        closeAct.setShortcut('Ctrl+W')
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
        # Right dock area - Analysis outputs
        self.lexicalDock = QDockWidget("Lexical", self)
        self.lexicalOutput = QPlainTextEdit()
        self.lexicalOutput.setReadOnly(True)
        self.lexicalDock.setWidget(self.lexicalOutput)
        
        self.syntaxDock = QDockWidget("Syntax", self)
        self.syntaxOutput = QPlainTextEdit()
        self.syntaxOutput.setReadOnly(True)
        self.syntaxDock.setWidget(self.syntaxOutput)
        
        # AST Dock Widget
        self.astDock = QDockWidget("Abstract Syntax Tree", self)
        self.astTreeView = QTreeView()
        self.astTreeView.setHeaderHidden(False)
        self.astTreeView.setRootIsDecorated(True)
        self.astTreeView.setExpandsOnDoubleClick(True)
        self.astDock.setWidget(self.astTreeView)
        
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
        self.tabifyDockWidget(self.syntaxDock, self.astDock)
        self.tabifyDockWidget(self.astDock, self.semanticDock)
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
        
        self.executionDock = QDockWidget("Ejecución", self)
        self.executionOutput = QPlainTextEdit()
        self.executionOutput.setReadOnly(True)
        self.executionDock.setWidget(self.executionOutput)
        
        # Add the first dock widget to the bottom area
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.resultDock)
        
        # Tabify the output docks together
        self.tabifyDockWidget(self.resultDock, self.errorsLexicalDock)
        self.tabifyDockWidget(self.errorsLexicalDock, self.errorsSyntaxDock)
        self.tabifyDockWidget(self.errorsSyntaxDock, self.errorsSemanticDock)
        self.tabifyDockWidget(self.errorsSemanticDock, self.executionDock)
        
        # Make the first tab in each group visible
        self.lexicalDock.raise_()
        self.resultDock.raise_()
        
        # Set features for all dock widgets to prevent closing
        for dock in [self.lexicalDock, self.syntaxDock, self.astDock, self.semanticDock,
                     self.hashTableDock, self.intermediateDock,
                     self.errorsLexicalDock, self.errorsSyntaxDock, 
                     self.errorsSemanticDock, self.resultDock, self.executionDock]:
            dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable |
                            QDockWidget.DockWidgetFeature.DockWidgetFloatable)

    def newFile(self):
        if not self.confirmSaveChanges():
            return
        
        self.editor.clear()
        self.current_file = None
        self.document_saved = True
        self.updateWindowTitle()

    def openFile(self):
        if not self.confirmSaveChanges():
            return
            
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
            return
            
        self.editor.setPlainText("")
        self.current_file = None
        self.document_saved = True
        self.updateWindowTitle()

    def closeEvent(self, event):
        if self.confirmSaveChanges():
            event.accept()
        else:
            event.ignore()

    def confirmSaveChanges(self):
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
                return self.saveFile()
            elif reply == QMessageBox.StandardButton.Cancel:
                return False
        return True

    def isDocumentModified(self):
        if not hasattr(self, 'document_saved'):
            return self.editor.toPlainText() != ""
        
        if not self.document_saved:
            return True
        
        if self.current_file:
            try:
                with open(self.current_file, 'r') as f:
                    saved_content = f.read()
                return saved_content != self.editor.toPlainText()
            except Exception:
                return True
        
        return self.editor.toPlainText() != ""

    def updateWindowTitle(self):
        title = "IDE"
        if self.current_file:
            title = f"{os.path.basename(self.current_file)} - IDE"
            if self.isDocumentModified():
                title = f"*{title}"
        self.setWindowTitle(title)

    def handleProcessOutput(self, process, output_widget):
        try:
            output = process.readAllStandardOutput().data().decode('utf-8').strip()
            if output:
                output_widget.setPlainText(output)
        except UnicodeDecodeError:
            output = process.readAllStandardOutput().data().decode('latin-1').strip()
            if output:
                output_widget.setPlainText(output)

    def handleProcessError(self, process, error_widget):
        try:
            error = process.readAllStandardError().data().decode('utf-8').strip()
            if error:
                error_widget.setPlainText(error)
        except UnicodeDecodeError:
            try:
                error = process.readAllStandardError().data().decode('cp1252').strip()
                if error:
                    error_widget.setPlainText(error)
            except UnicodeDecodeError:
                error_widget.setPlainText("Error: Unable to decode process error output.")

    def runLexicalAnalysis(self):
        if not self.current_file:
            save_result = self.saveFile()
            if not save_result:
                QMessageBox.warning(self, 'Warning', 'Please save the file first')
                return
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        lexical_analyzer_path = os.path.join(script_dir, 'lexical_analyzer.py')
        
        self.lexicalOutput.clear()
        self.errorsLexicalOutput.clear()
        
        process = QProcess()
        process.readyReadStandardOutput.connect(lambda: self.handleProcessOutput(process, self.lexicalOutput))
        process.readyReadStandardError.connect(lambda: self.handleProcessError(process, self.errorsLexicalOutput))
        
        process.start('python', [lexical_analyzer_path, self.current_file])
        
        if not process.waitForStarted(5000):
            QMessageBox.critical(self, 'Error', 'Could not start lexical analyzer')

    def build_ast_tree_model(self, ast_dict):
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(['Node Type', 'Value', 'Line', 'Column'])
        
        def add_node(parent_item, node_dict):
            node_type = node_dict.get('node_type', '')
            value = str(node_dict.get('value', ''))
            line = str(node_dict.get('line', ''))
            column = str(node_dict.get('column', ''))
            
            type_item = QStandardItem(node_type)
            value_item = QStandardItem(value)
            line_item = QStandardItem(line)
            column_item = QStandardItem(column)
            
            parent_item.appendRow([type_item, value_item, line_item, column_item])
            
            for child in node_dict.get('children', []):
                add_node(type_item, child)
        
        root_item = model.invisibleRootItem()
        add_node(root_item, ast_dict)
        
        return model

    def runSyntaxAnalysis(self):
        if not self.current_file:
            save_result = self.saveFile()
            if not save_result:
                QMessageBox.warning(self, 'Warning', 'Please save the file first')
                return
        
        # Clear previous outputs
        self.syntaxOutput.clear()
        self.errorsSyntaxOutput.clear()
        
        # Clear previous AST
        self.astTreeView.setModel(None)
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        syntax_analyzer_path = os.path.join(script_dir, 'syntax_analyzer.py')
        
        process = QProcess(self)
        
        # Connect signals for handling output and errors
        process.readyReadStandardOutput.connect(
            lambda: self.handleProcessOutput(process, self.syntaxOutput)
        )
        process.readyReadStandardError.connect(
            lambda: self.handleProcessError(process, self.errorsSyntaxOutput)
        )
        
        process.start('python', [syntax_analyzer_path, self.current_file])
        
        self.statusBar().showMessage('Running syntax analysis...')
        
        if not process.waitForStarted(5000):
            QMessageBox.critical(self, 'Error', 'Could not start syntax analyzer')
            return
        
        if not process.waitForFinished(5000):
            process.kill()
            self.statusBar().showMessage('Syntax analysis timed out')
            QMessageBox.critical(self, 'Error', 'Syntax analysis timed out')
            return
        
        self.statusBar().showMessage('Syntax analysis completed')
        
        # Read any remaining output
        self.handleProcessOutput(process, self.syntaxOutput)
        self.handleProcessError(process, self.errorsSyntaxOutput)
        
        # Try to load and display AST
        ast_file = self.current_file.replace('.txt', '_ast.json')
        try:
            with open(ast_file, 'r', encoding='utf-8') as f:
                ast_dict = json.load(f)
                model = self.build_ast_tree_model(ast_dict)
                self.astTreeView.setModel(model)
                
                # Auto-resize columns
                for i in range(model.columnCount()):
                    self.astTreeView.resizeColumnToContents(i)
                
                # Expand root node
                self.astTreeView.expand(model.index(0, 0))
                
        except FileNotFoundError:
            self.syntaxOutput.appendPlainText("No AST file generated")
        except json.JSONDecodeError:
            self.syntaxOutput.appendPlainText("Invalid AST JSON format")
        
        # Raise the AST dock
        self.astDock.raise_()

    def runSemanticAnalysis(self):
        if not self.current_file:
            save_result = self.saveFile()
            if not save_result:
                QMessageBox.warning(self, 'Warning', 'Please save the file first')
                return
        
        self.semanticOutput.clear()
        self.errorsSemanticOutput.clear()
        
        process = QProcess(self)
        process.readyReadStandardOutput.connect(
            lambda: self.handleProcessOutput(process, self.semanticOutput)
        )
        process.readyReadStandardError.connect(
            lambda: self.handleProcessError(process, self.errorsSemanticOutput)
        )
        
        process.start('python', ['semantic_analyzer.py', self.current_file])
        
        self.statusBar().showMessage('Running semantic analysis...')
        
        if not process.waitForFinished(3000):
            process.kill()
            self.statusBar().showMessage('Semantic analysis timed out')
        else:
            self.statusBar().showMessage('Semantic analysis completed')
            
        self.handleProcessOutput(process, self.semanticOutput)
        self.handleProcessError(process, self.errorsSemanticOutput)
        
        self.semanticDock.raise_()

    def generateIntermediateCode(self):
        if not self.current_file:
            save_result = self.saveFile()
            if not save_result:
                QMessageBox.warning(self, 'Warning', 'Please save the file first')
                return
        
        self.intermediateOutput.clear()
        
        process = QProcess(self)
        process.readyReadStandardOutput.connect(
            lambda: self.handleProcessOutput(process, self.intermediateOutput)
        )
        process.readyReadStandardError.connect(
            lambda: self.handleProcessError(process, self.resultOutput)
        )
        
        process.start('python', ['intermediate_code_generator.py', self.current_file])
        
        self.statusBar().showMessage('Generating intermediate code...')
        
        if not process.waitForFinished(3000):
            process.kill()
            self.statusBar().showMessage('Intermediate code generation timed out')
        else:
            self.statusBar().showMessage('Intermediate code generation completed')
            
        self.handleProcessOutput(process, self.intermediateOutput)
        self.handleProcessError(process, self.resultOutput)
        
        self.intermediateDock.raise_()

    def executeCode(self):
        if not self.current_file:
            save_result = self.saveFile()
            if not save_result:
                QMessageBox.warning(self, 'Warning', 'Please save the file first')
                return
        
        self.executionOutput.clear()
        
        process = QProcess(self)
        process.readyReadStandardOutput.connect(
            lambda: self.handleProcessOutput(process, self.executionOutput)
        )
        process.readyReadStandardError.connect(
            lambda: self.handleProcessError(process, self.resultOutput)
        )
        
        process.start('python', ['code_executor.py', self.current_file])
        
        self.statusBar().showMessage('Executing code...')
        
        if not process.waitForFinished(3000):
            process.kill()
            self.statusBar().showMessage('Code execution timed out')
        else:
            self.statusBar().showMessage('Code execution completed')
            
        self.handleProcessOutput(process, self.executionOutput)
        self.handleProcessError(process, self.resultOutput)
        
        self.executionDock.raise_()
        
    def update_cursor_position(self):
        cursor = self.editor.textCursor()
        line = cursor.blockNumber() + 1
        column = cursor.columnNumber() + 1
        
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
        self.error_format = QTextCharFormat()
        self.error_format.setForeground(QColor("red"))
        self.rules = []
        logic_operator_format = QTextCharFormat()
        logic_operator_format.setForeground(QColor("orange"))
        assignment_format = QTextCharFormat()
        assignment_format.setForeground(QColor("mediumblue"))
        operator_format = QTextCharFormat()
        operator_format.setForeground(QColor("red"))
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor("darkgreen"))
        self.string_content_format = QTextCharFormat()
        self.string_content_format.setForeground(QColor("hotpink"))
        self.quote_format = QTextCharFormat()
        self.quote_format.setForeground(QColor("royalblue"))
        string_pattern = r'"[^"\n]*"'
        self.rules.append((string_pattern, self.string_content_format))
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("cyan"))
        self.variable_format = QTextCharFormat()
        self.variable_format.setForeground(QColor("purple"))
        self.function_format = QTextCharFormat()
        self.function_format.setForeground(QColor("lightgreen"))
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("goldenrod"))
        self.comment_start_expression = QRegularExpression(r'/\*')
        self.comment_end_expression = QRegularExpression(r'\*/')
        single_line_comment_pattern = r'//[^\n]*'
        self.rules.append((single_line_comment_pattern, self.comment_format))
        logic_operator_pattern = r'<=|>=|!=|==|<|>|\&\&|\|\||!'
        self.rules.append((logic_operator_pattern, logic_operator_format))
        assignment_pattern = r'(?<![=!<>])=(?![=])'
        self.rules.append((assignment_pattern, assignment_format))
        operator_pattern = r'\+\+|--|\+|-|\*|/|%|\^'
        self.rules.append((operator_pattern, operator_format))
        symbol_format = QTextCharFormat()
        symbol_format.setForeground(QColor("darkgray"))
        integer_pattern = r'\b\d+\b'
        self.rules.append((integer_pattern, number_format))
        float_pattern = r'\b\d+\.\d+\b'
        self.rules.append((float_pattern, number_format))
        self.defined_variables = set()
        symbol_pattern = r'[:\(\)\{\},;]'
        self.rules.append((symbol_pattern, symbol_format))
        self.KEYWORDS = {
            "if", "else", "end", "do", "while", "switch", "case", 
            "int", "float", "main", "cin", "cout", "for", "return", 
            "char", "bool"
        }

    def highlightBlock(self, text):
        self.setCurrentBlockState(0)
        processed_to_index = 0
        if self.previousBlockState() == 1:
            end_idx = text.find("*/")
            if end_idx == -1:
                self.setFormat(0, len(text), self.comment_format)
                self.setCurrentBlockState(1)
                return
            else:
                self.setFormat(0, end_idx + 2, self.comment_format)
                processed_to_index = end_idx + 2
        
        while True:
            start_idx = text.find("/*", processed_to_index)
            if start_idx == -1:
                break
            if start_idx > processed_to_index:
                text_segment = text[processed_to_index:start_idx]
                self.processNormalText(text_segment, processed_to_index)
            end_idx = text.find("*/", start_idx + 2)
            if end_idx == -1:
                self.setFormat(start_idx, len(text) - start_idx, self.comment_format)
                self.setCurrentBlockState(1)
                return
            else:
                comment_length = end_idx - start_idx + 2
                self.setFormat(start_idx, comment_length, self.comment_format)
                processed_to_index = end_idx + 2

        if processed_to_index < len(text):
            remaining_text = text[processed_to_index:]
            self.processNormalText(remaining_text, processed_to_index)
            
    def processNormalText(self, text_segment, offset=0):
        comment_start_idx = text_segment.find("//")
        if comment_start_idx != -1:
            if comment_start_idx > 0:
                self.processCodeSegment(text_segment[:comment_start_idx], offset)
            comment_length = len(text_segment) - comment_start_idx
            self.setFormat(comment_start_idx + offset, comment_length, self.comment_format)
            return
        self.processCodeSegment(text_segment, offset)
        
    def processCodeSegment(self, text_segment, offset=0):
        for keyword in self.KEYWORDS:
            pattern = QRegularExpression(r'\b' + QRegularExpression.escape(keyword) + r'\b')
            match_iter = pattern.globalMatch(text_segment)
            while match_iter.hasNext():
                match = match_iter.next()
                start = match.capturedStart() + offset
                length = match.capturedLength()
                self.setFormat(start, length, self.keyword_format)
                
        for pattern, fmt in self.rules:
            expression = QRegularExpression(pattern)
            match_iter = expression.globalMatch(text_segment)
            while match_iter.hasNext():
                match = match_iter.next()
                token = match.captured(0)
                start = match.capturedStart() + offset
                length = match.capturedLength()

                if token in self.KEYWORDS:
                    self.setFormat(start, length, self.keyword_format)
                    continue

                if fmt == self.variable_format and len(text_segment) > match.capturedStart() + length and text_segment[match.capturedStart() + length] == '(':
                    self.setFormat(start, length, self.function_format)
                else:
                    self.setFormat(start, length, fmt)
                    
        string_regex = QRegularExpression(r'"[^"\n]*"')
        match_iter = string_regex.globalMatch(text_segment)
        while match_iter.hasNext():
            match = match_iter.next()
            start = match.capturedStart() + offset
            length = match.capturedLength()
            full_text = match.captured(0)

            if len(full_text) >= 2:
                self.setFormat(start, 1, self.quote_format)
                self.setFormat(start + length - 1, 1, self.quote_format)
                if length > 2:
                    self.setFormat(start + 1, length - 2, self.string_content_format)

        declaration_pattern = QRegularExpression(
            r'\b(?:int|float|char|bool|var)\s+((?:[a-zA-Z_][a-zA-Z0-9_]*\s*,\s*)*[a-zA-Z_][a-zA-Z0-9_]*)')
        assignment_pattern = QRegularExpression(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=')

        new_vars = set()
        match_iter = declaration_pattern.globalMatch(text_segment)
        while match_iter.hasNext():
            match = match_iter.next()
            vars_group = match.captured(1)
            var_names = [v.strip() for v in vars_group.split(',')]
            for var in var_names:
                if var not in self.KEYWORDS:
                    new_vars.add(var)

        match_iter = assignment_pattern.globalMatch(text_segment)
        while match_iter.hasNext():
            match = match_iter.next()
            var_name = match.captured(1)
            if var_name not in self.KEYWORDS:
                new_vars.add(var_name)

        self.defined_variables.update(new_vars)

        for var in list(self.defined_variables):
            if var in self.KEYWORDS:
                continue

            var_regex = QRegularExpression(r'\b' + QRegularExpression.escape(var) + r'\b')
            match_iter = var_regex.globalMatch(text_segment)
            while match_iter.hasNext():
                match = match_iter.next()
                start = match.capturedStart() + offset
                length = match.capturedLength()
                if match.capturedStart() + length < len(text_segment) and text_segment[match.capturedStart() + length] == '(':
                    self.setFormat(start, length, self.function_format)
                else:
                    self.setFormat(start, length, self.variable_format)
        
        invalid_char_pattern = r'[^a-zA-Z0-9\s\+\-\*/%=<>!&|()\[\]\{\},;.\'\"-_]'
        expression = QRegularExpression(invalid_char_pattern)
        match_iter = expression.globalMatch(text_segment)
        while match_iter.hasNext():
            match = match_iter.next()
            start = match.capturedStart() + offset
            length = match.capturedLength()
            self.setFormat(start, length, self.error_format)

def main():
    app = QApplication(sys.argv)
    ide = CompilerIDE()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()