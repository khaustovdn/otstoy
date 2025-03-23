import os
import sys
import locale
import bisect
from queue import PriorityQueue
import re
from functools import partial
from typing import Callable, Optional, List, Tuple
from PySide6.QtCore import (
    QLocale,
    QRegularExpression,
    Qt,
    QSize,
    QRect,
    Signal,
    QObject,
    QFileSystemWatcher,
)
from PySide6.QtGui import (
    QTextCharFormat,
    QFont,
    QColor,
    QPainter,
    QKeySequence,
    QSyntaxHighlighter,
    QShortcut,
    QPaintEvent,
    QResizeEvent,
    QIcon,
    QAction,
    QCloseEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTextEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QHeaderView,
    QWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QMessageBox,
    QToolBar,
    QMenu,
    QMenuBar,
)


class Token:
    def __init__(self, type: str, value: str, line: int, column: int):
        self.type = type
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return f"Token({self.type}, {self.value}, {self.line}, {self.column})"


class LexerError:
    def __init__(self, line: int, column: int, message: str):
        self.line = line
        self.column = column
        self.message = message

    def __repr__(self):
        return f"LexerError({self.line}, {self.column}, {self.message})"


class Branch:
    def __init__(self, tokens: List[Token], index: int,
                 current_state: str, edit_count: int, changes: List[tuple]):
        self.tokens = tokens
        self.index = index
        self.current_state = current_state
        self.edit_count = edit_count
        self.changes = changes

    def __lt__(self, other):
        return self.edit_count < other.edit_count


class AdvancedLexer:
    MAX_EDIT_COUNT = 15

    TOKEN_REGEX = [
        (r'const\b', 'CONST'),
        (r'i32\b', 'I32'),
        (r':', 'COLON'),
        (r'=', 'ASSIGN'),
        (r'\+', 'PLUS'),
        (r'-', 'MINUS'),
        (r';', 'SEMICOLON'),
        (r'[a-zA-Z_][a-zA-Z0-9_]*', 'IDENTIFIER'),
        (r'\d+', 'NUMBER'),
        (r'[^\s]', 'INVALID'),
    ]

    DEFAULT_TOKEN_VALUES = {
        'CONST': 'const', 'I32': 'i32', 'COLON': ':', 'ASSIGN': '=', 'IDENTIFIER': 'имя переменной',
        'PLUS': '+', 'MINUS': '-', 'SEMICOLON': ';', 'NUMBER': 'число'
    }

    TRANSITIONS = {
        'START': {'CONST': 'CONSTIDENTIFIER'},
        'CONSTIDENTIFIER': {'IDENTIFIER': 'COLON'},
        'COLON': {'COLON': 'DATATYPE'},
        'DATATYPE': {'I32': 'ASSIGNMENT'},
        'ASSIGNMENT': {'ASSIGN': 'VALUE'},
        'VALUE': {'NUMBER': 'SEMICOLON', 'MINUS': 'WHOLENUMBER'},
        'WHOLENUMBER': {'NUMBER': 'SEMICOLON'},
        'SEMICOLON': {'SEMICOLON': 'END'},
        'END': {}
    }

    def __init__(self, input_text: str):
        self.input_text = input_text
        self.newline_positions = [
            i for i, c in enumerate(input_text) if c == '\n']
        self.tokens: List[Token] = []
        self.errors: List[LexerError] = []
        self.pos = 0
        self.length = len(input_text)

    def get_line_column(self, pos: int) -> Tuple[int, int]:
        line_num = bisect.bisect_right(self.newline_positions, pos) + 1
        if line_num > 1:
            column = pos - self.newline_positions[line_num-2]
        else:
            column = pos + 1
        return line_num, column

    def create_token(self, token_type: str, reference_token: Token, insert_after: bool = False) -> Token:
        value = self.DEFAULT_TOKEN_VALUES.get(token_type, '')
        if reference_token:
            if insert_after:
                new_pos = reference_token.column + len(reference_token.value)
                return Token(token_type, value, reference_token.line, new_pos)
            else:
                return Token(token_type, value, reference_token.line, reference_token.column)

    def lex(self) -> Tuple[List[Token], List[LexerError]]:
        while self.pos < self.length:
            while self.pos < self.length and self.input_text[self.pos].isspace():
                self.pos += 1
            if self.pos >= self.length:
                break

            line, column = self.get_line_column(self.pos)
            matched = False
            for pattern, token_type in self.TOKEN_REGEX:
                regex = re.compile(pattern)
                match = regex.match(self.input_text, self.pos)
                if match:
                    value = match.group(0)
                    if token_type in ('CONST', 'I32'):
                        next_pos = match.end()
                        if (next_pos < self.length and
                                self.input_text[next_pos].isalnum()):
                            continue
                    self.tokens.append(Token(token_type, value, line, column))
                    self.pos = match.end()
                    matched = True
                    break
            if not matched:
                char = self.input_text[self.pos]
                self.errors.append(LexerError(
                    line, column, f"Неожиданный символ: {repr(char)}"))
                self.pos += 1
        return self.tokens, self.errors

    def validate_tokens(self) -> Tuple[List[Token], List[LexerError]]:
        queue = PriorityQueue()
        queue.put((0, Branch(self.tokens.copy(), 0, 'START', 0, [])))
        best = None

        while not queue.empty():
            _, branch = queue.get()

            if best and best.edit_count <= self.MAX_EDIT_COUNT:
                break

            if branch.index >= len(branch.tokens):
                if branch.current_state in ('END', 'START'):
                    if not best or branch.edit_count < best.edit_count:
                        best = branch
                else:
                    self._process_transitions(queue, branch)

            else:
                current_token = branch.tokens[branch.index]
                allowed = self.TRANSITIONS.get(branch.current_state, {}).keys()

                if current_token.type in allowed:
                    self._handle_valid_transition(queue, branch)
                else:
                    self._generate_repair_branches(
                        queue, branch, current_token, allowed)

        return self._finalize_validation(best)

    def _process_transitions(self, queue, branch):
        current_state = branch.current_state
        allowed = self.TRANSITIONS.get(current_state, {}).keys()

        for insert_type in allowed:
            if branch.tokens:
                last_token = branch.tokens[-1]
                line = last_token.line
                column = last_token.column + len(last_token.value)
            else:
                line = 1
                column = 1
            insert_token = Token(
                insert_type,
                self.DEFAULT_TOKEN_VALUES.get(insert_type, ''),
                line,
                column
            )
            new_tokens = branch.tokens.copy()
            new_tokens.append(insert_token)
            new_changes = branch.changes.copy()
            new_changes.append(('insert', len(new_tokens)-1, insert_token))
            next_state = self.TRANSITIONS[current_state][insert_type]

            if branch.edit_count + 1 <= self.MAX_EDIT_COUNT:
                new_branch = Branch(
                    tokens=new_tokens,
                    index=len(new_tokens),
                    current_state=next_state,
                    edit_count=branch.edit_count + 1,
                    changes=new_changes
                )
                queue.put((new_branch.edit_count, new_branch))

    def _handle_valid_transition(self, queue, branch):
        current_token = branch.tokens[branch.index]
        next_state = self.TRANSITIONS[branch.current_state][current_token.type]

        if next_state == 'END':
            new_edit_count = 0
        else:
            new_edit_count = branch.edit_count

        new_branch = Branch(
            tokens=branch.tokens,
            index=branch.index + 1,
            current_state='START' if next_state == 'END' else next_state,
            edit_count=new_edit_count,
            changes=branch.changes.copy()
        )
        queue.put((new_branch.edit_count, new_branch))

    def _generate_repair_branches(self, queue, branch, current_token, allowed):
        self._generate_delete_branch(queue, branch, current_token)
        self._generate_replace_branches(queue, branch, current_token, allowed)
        self._generate_insert_branches(queue, branch, current_token, allowed)

    def _generate_delete_branch(self, queue, branch, current_token):
        new_tokens = branch.tokens.copy()
        del new_tokens[branch.index]
        new_changes = branch.changes.copy()
        new_changes.append(('delete', branch.index, current_token))
        if branch.edit_count + 1 <= self.MAX_EDIT_COUNT:
            new_branch = Branch(
                tokens=new_tokens,
                index=branch.index,
                current_state=branch.current_state,
                edit_count=branch.edit_count + 1,
                changes=new_changes
            )
            queue.put((new_branch.edit_count, new_branch))

    def _generate_replace_branches(self, queue, branch, current_token, allowed):
        current_state = branch.current_state
        for replace_type in allowed:
            new_token = self.create_token(replace_type, current_token)
            new_tokens = branch.tokens.copy()
            new_tokens[branch.index] = new_token
            new_changes = branch.changes.copy()
            new_changes.append(
                ('replace', branch.index, current_token, new_token))
            next_state = self.TRANSITIONS[current_state][replace_type]
            if branch.edit_count + 1 <= self.MAX_EDIT_COUNT:
                new_branch = Branch(
                    tokens=new_tokens,
                    index=branch.index + 1,
                    current_state=next_state,
                    edit_count=branch.edit_count + 1,
                    changes=new_changes
                )
                queue.put((new_branch.edit_count, new_branch))

    def _generate_insert_branches(self, queue, branch, current_token, allowed):
        current_state = branch.current_state
        for insert_type in allowed:
            insert_token = self.create_token(
                insert_type, current_token, insert_after=False)
            new_tokens = branch.tokens.copy()
            new_tokens.insert(branch.index, insert_token)
            new_changes = branch.changes.copy()
            new_changes.append(('insert', branch.index, insert_token))
            next_state = self.TRANSITIONS[current_state][insert_type]
            if branch.edit_count + 1 <= self.MAX_EDIT_COUNT:
                new_branch = Branch(
                    tokens=new_tokens,
                    index=branch.index + 1,
                    current_state=next_state,
                    edit_count=branch.edit_count + 1,
                    changes=new_changes
                )
                queue.put((new_branch.edit_count, new_branch))

    def _finalize_validation(self, best):
        if best:
            self.tokens = best.tokens
            errors = self._generate_errors_from_changes(best.changes)
            return self.tokens, errors
        else:
            return self.tokens, self.errors + [LexerError(0, 0, f"Проверка не удалась: превышен максимальный лимит правок ({self.MAX_EDIT_COUNT})")]

    def _generate_errors_from_changes(self, changes: List[tuple]) -> List[LexerError]:
        errors = []
        for change in changes:
            action = change[0]
            if action == 'delete':
                _, pos, token = change
                errors.append(LexerError(token.line, token.column,
                              f"Удалить неожиданный токен '{token.value}'"))
            elif action == 'replace':
                _, pos, old_token, new_token = change
                errors.append(LexerError(old_token.line, old_token.column,
                                         f"Заменить '{old_token.value}' на '{new_token.value}'"))
            elif action == 'insert':
                _, pos, token = change
                errors.append(LexerError(token.line, token.column,
                              f"Вставить отсутствующий токен '{token.value}'"))
        return errors


class SyntaxHighlighter(QSyntaxHighlighter):
    """
    Handles syntax highlighting for a QTextDocument using predefined rules.
    """

    HighlightRule = Tuple[QRegularExpression, QTextCharFormat]

    def __init__(self, parent: QObject) -> None:
        """
        Initialize the highlighter with default rules.
        """
        super().__init__(parent)
        self.highlighting_rules: List[SyntaxHighlighter.HighlightRule] = []
        self._setup_highlighting_rules()

    def _setup_highlighting_rules(self) -> None:
        """
        Define syntax highlighting rules for keywords.
        """
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(255, 165, 0))  # Orange color
        keyword_format.setFontWeight(QFont.Weight.Bold)

        keywords = [
            "if", "else", "while", "for", "return", "break",
            "function", "var", "let", "const", "true", "false", "null",
        ]

        for word in keywords:
            pattern = QRegularExpression(
                r"\b" + QRegularExpression.escape(word) + r"\b")
            self.highlighting_rules.append((pattern, keyword_format))

    def highlightBlock(self, text: str) -> None:
        """
        Apply syntax highlighting to a block of text.
        """
        for pattern, fmt in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(
                    match.capturedStart(),
                    match.capturedLength(),
                    fmt,
                )


class LineNumberArea(QWidget):
    """
    Display line numbers for a TextEditor.
    """

    def __init__(self, editor: "TextEditor") -> None:
        """
        Initialize the line number area.
        """
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        """
        Return the recommended size for the line number area.
        """
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Paint the line numbers on the widget.
        """
        self.editor.line_number_area_paint_event(event)


class TextEditor(QPlainTextEdit):
    """
    A text editor widget with line number support.
    """

    def __init__(self) -> None:
        """
        Initialize the text editor with a line number area.
        """
        super().__init__()
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.update_line_number_area_width(0)

    def line_number_area_width(self) -> int:
        """
        Calculate the width of the line number area.
        """
        digits = len(str(max(1, self.blockCount())))
        return 10 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_line_number_area_width(self, _: int) -> None:
        """
        Update the viewport margins to accommodate the line number area.
        """
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect: QRect, dy: int) -> None:
        """
        Update the line number area when the editor's viewport changes.
        """
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(
                0, rect.y(), self.line_number_area.width(), rect.height()
            )

    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        Handle resizing of the editor.
        """
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(
                cr.left(),
                cr.top(),
                self.line_number_area_width(),
                cr.height()
            )
        )

    def line_number_area_paint_event(self, event: QPaintEvent) -> None:
        """
        Paint line numbers in the line number area.
        """
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), Qt.GlobalColor.lightGray)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(
            block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(Qt.GlobalColor.black)
                painter.drawText(
                    0,
                    int(top),
                    self.line_number_area.width() - 5,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(block_number + 1),
                )

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1


class DocumentModel(QObject):
    """
    Encapsulates the data and state of a document.
    """

    modified = Signal(bool)
    file_path_changed = Signal(str, str)

    def __init__(self) -> None:
        """
        Initialize the document model.
        """
        super().__init__()
        self._file_path: Optional[str] = None
        self._is_modified: bool = False

    @property
    def file_path(self) -> Optional[str]:
        """
        Return the file path associated with the document.
        """
        return self._file_path

    @file_path.setter
    def file_path(self, value: Optional[str]) -> None:
        """
        Set the file path and emit a signal when changed.
        """
        old_value = self._file_path
        self._file_path = value
        self.file_path_changed.emit(old_value, value)

    @property
    def is_modified(self) -> bool:
        """
        Return whether the document has unsaved changes.
        """
        return self._is_modified

    @is_modified.setter
    def is_modified(self, value: bool) -> None:
        """
        Set the modification state and emit a signal when changed.
        """
        self._is_modified = value
        self.modified.emit(value)


class DocumentWidget(QWidget):
    """
    A widget that manages a text document with input and output areas.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the document widget.
        """
        super().__init__(parent)
        self._is_connected = False
        self._is_reloading = False
        self._is_saving_internally = False
        self.last_saved_mtime: Optional[float] = None

        self.model = DocumentModel()
        self.main_layout = QVBoxLayout(self)

        self.input_edit = TextEditor()
        self.highlighter = SyntaxHighlighter(self.input_edit.document())

        self.output_tabs = QTabWidget()
        self.output_edit = QTextEdit()
        self.output_edit.setReadOnly(True)

        self.error_table = QTableWidget()
        self.error_table.setColumnCount(4)
        self.error_table.setHorizontalHeaderLabels(
            ["Line", "Column", "Type", "Message"]
        )
        self.error_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers)

        header = self.error_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.output_tabs.addTab(self.output_edit, "Output")
        self.output_tabs.addTab(self.error_table, "Errors")

        self.main_layout.addWidget(self.input_edit)
        self.main_layout.addWidget(self.output_tabs)
        self.input_edit.textChanged.connect(self._handle_text_changed)

        self.file_watcher = QFileSystemWatcher()
        self._update_file_watcher()
        self.model.file_path_changed.connect(self._update_file_watcher)

    def save(self, path: str) -> bool:
        """Save document content to specified path."""
        try:
            self._is_saving_internally = True

            if self._is_connected:
                self.file_watcher.fileChanged.disconnect(
                    self._handle_file_changed
                )
                self._is_connected = False

            with open(path, "w", encoding="utf-8") as f:
                f.write(self.input_edit.toPlainText())
            self.model.is_modified = False
            self.last_saved_mtime = os.path.getmtime(path)

            if path not in self.file_watcher.files():
                self.file_watcher.addPath(path)

            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Save failed: {str(e)}")
            return False
        finally:
            if not self._is_connected:
                self.file_watcher.fileChanged.connect(
                    self._handle_file_changed
                )
                self._is_connected = True

            self._is_saving_internally = False

    def _update_file_watcher(
            self,
            old_path: Optional[str] = None,
            new_path: Optional[str] = None
    ) -> None:
        """
        Update file watcher.
        """
        if not hasattr(self, 'file_watcher'):
            return

        if old_path:
            self.file_watcher.removePath(old_path)
        if new_path:
            self.file_watcher.addPath(new_path)

        if self._is_connected:
            self.file_watcher.fileChanged.disconnect(self._handle_file_changed)
            self._is_connected = False

        self.file_watcher.fileChanged.connect(self._handle_file_changed)
        self._is_connected = True

    def _handle_file_changed(self, path: str) -> None:
        """
        Handle external file changes.
        """
        if self._is_saving_internally:
            return

        if path == self.model.file_path and not self._is_reloading:
            try:
                current_mtime = os.path.getmtime(path)
            except OSError:
                current_mtime = None

            if current_mtime == self.last_saved_mtime:
                return

            self._is_reloading = True

            reply = QMessageBox.question(
                self,
                "File Changed",
                f"The file '{os.path.basename(path)}' "
                "has been modified externally. Reload?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._reload_file()
                self.last_saved_mtime = (
                    os.path.getmtime(path)
                    if os.path.exists(path)
                    else None
                )

            self._is_reloading = False

    def _reload_file(self) -> None:
        """
        Reload the file from disk.
        """
        if self.model.file_path and os.path.exists(self.model.file_path):
            try:
                with open(self.model.file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.input_edit.setPlainText(content)
                self.model.is_modified = False
                self._update_file_watcher(
                    old_path=self.model.file_path,
                    new_path=self.model.file_path
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to reload file: {str(e)}",
                )
        else:
            QMessageBox.critical(self, "Error", "File no longer exists.")

    def _handle_text_changed(self) -> None:
        """
        Handle text changes in the input editor.
        """
        if not self.model.is_modified:
            self.model.is_modified = True


class TabManager(QTabWidget):
    """
    Manage multiple document tabs in the application.
    """

    def __init__(self, parent: "MainWindow") -> None:
        """
        Initialize the tab manager.
        """
        super().__init__(parent)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.tabCloseRequested.connect(self.close_tab)
        self._open_files = set()
        self._create_initial_tab()

    def _create_initial_tab(self) -> None:
        """
        Create the initial tab when the application starts.
        """
        self.add_new_tab()

    def add_new_tab(
        self, file_path: Optional[str] = None, content: str = ""
    ) -> Optional[DocumentWidget]:
        """
        Add a new tab with a document widget.
        """
        if file_path and file_path in self._open_files:
            for i in range(self.count()):
                widget = self.widget(i)
                if isinstance(
                    widget,
                    DocumentWidget
                ) and widget.model.file_path == file_path:
                    self.setCurrentIndex(i)
                    return None

        doc = DocumentWidget(self)
        doc.model.file_path = file_path

        doc.input_edit.blockSignals(True)
        doc.input_edit.setPlainText(content)
        doc.input_edit.blockSignals(False)

        doc.model.modified.connect(partial(self._update_tab_title, doc))
        doc.model.file_path_changed.connect(
            partial(self._handle_file_path_change, doc)
        )

        title = os.path.basename(file_path) if file_path else "Untitled"
        index = self.addTab(doc, title)
        self.setCurrentIndex(index)

        if file_path:
            self._open_files.add(file_path)
        return doc

    def _handle_file_path_change(
            self,
            doc: DocumentWidget,
            old_path: Optional[str],
            new_path: Optional[str]
    ) -> None:
        """
        Handle file path change
        """
        if old_path in self._open_files:
            self._open_files.remove(old_path)
        if new_path:
            self._open_files.add(new_path)
        self._update_tab_title(doc)

    @property
    def parent_window(self) -> "MainWindow":
        """
        Return the parent as a MainWindow instance.
        """
        parent = self.parent()
        assert isinstance(
            parent, MainWindow), "Parent must be a MainWindow instance"
        return parent

    def close_tab(self, index: int) -> None:
        """
        Close a tab after confirming unsaved changes.
        """
        widget = self.widget(index)
        if isinstance(widget, DocumentWidget):
            doc = widget
            if doc.model.is_modified:
                reply = QMessageBox.question(
                    self,
                    "Unsaved Changes",
                    "Save changes before closing?",
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No
                    | QMessageBox.StandardButton.Cancel,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    if not self.parent_window.save_document():
                        return
                elif reply == QMessageBox.StandardButton.Cancel:
                    return

            if doc.model.file_path:
                self._open_files.discard(doc.model.file_path)
            self.removeTab(index)
            if self.count() == 0:
                self._create_initial_tab()

    def get_current_document(self) -> Optional[DocumentWidget]:
        """
        Return the currently active document widget.
        """
        widget = self.currentWidget()
        return widget if isinstance(widget, DocumentWidget) else None

    def _update_tab_title(self, doc: DocumentWidget, _=None) -> None:
        """
        Update the tab title based on the document's state.
        """
        index = self.indexOf(doc)
        base_name = os.path.basename(
            doc.model.file_path) if doc.model.file_path else "Untitled"
        title = f"{base_name}{'*' if doc.model.is_modified else ''}"
        self.setTabText(index, title)


class ToolbarManager:
    """
    Manage the toolbar for the main window.
    """

    def __init__(self, parent: QMainWindow) -> None:
        """Initialize the toolbar manager."""
        self.parent = parent
        self.toolbar = QToolBar("Main Toolbar")
        parent.addToolBar(self.toolbar)

    def add_action(
            self,
            icon_name: str,
            text: str,
            callback: Callable
    ) -> QAction:
        """
        Add an action to the toolbar.
        """
        action = QAction(QIcon.fromTheme(icon_name), text, self.parent)
        action.triggered.connect(callback)
        self.toolbar.addAction(action)
        return action


class MenuManager:
    """
    Manage the menu bar for the main window.
    """

    def __init__(self, parent: "MainWindow") -> None:
        """Initialize the menu manager."""
        self.parent = parent
        self.menu_bar = QMenuBar()
        parent.setMenuBar(self.menu_bar)
        self._setup_menus()

    def _setup_menus(self) -> None:
        """
        Set up the menus in the menu bar.
        """
        self._create_file_menu()
        self._create_edit_menu()
        self._create_text_menu()
        self._create_run_menu()
        self._create_help_menu()

    def _create_file_menu(self) -> None:
        """
        Create the File menu.
        """
        menu = self.menu_bar.addMenu("File")
        actions = [
            ("New", "document-new", self.parent.new_document),
            ("Open", "document-open", self.parent.open_document),
            ("Save", "document-save", self.parent.save_document),
            ("Save As", "document-save-as", self.parent.save_document_as),
            ("Exit", "application-exit", self.parent.close),
        ]
        self._add_menu_actions(menu, actions)

    def _create_edit_menu(self) -> None:
        """
        Create the Edit menu.
        """
        menu = self.menu_bar.addMenu("Edit")
        actions = [
            ("Increase Font Size", "zoom-in", self.parent.increase_font_size),
            ("Decrease Font Size", "zoom-out", self.parent.decrease_font_size),
            ("Undo", "edit-undo", self.parent.undo),
            ("Redo", "edit-redo", self.parent.redo),
            ("Cut", "edit-cut", self.parent.cut),
            ("Copy", "edit-copy", self.parent.copy),
            ("Paste", "edit-paste", self.parent.paste),
            ("Delete", "edit-delete", self.parent.delete),
            ("Select All", "edit-select-all", self.parent.select_all),
        ]
        self._add_menu_actions(menu, actions)

    def _create_text_menu(self) -> None:
        """
        Create the Text menu.
        """
        menu = self.menu_bar.addMenu("Text")
        templates = [
            "Problem Statement",
            "Grammar",
            "Grammar Classification",
            "Analysis Method",
            "Error Diagnostics and Neutralization",
            "Test Case",
            "Bibliography",
            "Source Code",
        ]
        for template in templates:
            action = QAction(template, self.parent)
            action.triggered.connect(
                partial(self.parent.insert_text, template))
            menu.addAction(action)

    def _create_run_menu(self) -> None:
        """
        Create the Run menu.
        """
        menu = self.menu_bar.addMenu("Run")
        action = QAction("Run Parser", self.parent)
        action.triggered.connect(self.parent.run_parser)
        menu.addAction(action)

    def _create_help_menu(self) -> None:
        """
        Create the Help menu.
        """
        menu = self.menu_bar.addMenu("Help")
        actions = [
            ("Help", "help-contents", self.parent.show_help),
            ("About", "help-about", self.parent.show_about),
        ]
        self._add_menu_actions(menu, actions)

    def _add_menu_actions(self, menu: QMenu, actions: list) -> None:
        """
        Add actions to a menu.
        """
        for text, icon_name, callback in actions:
            action = QAction(QIcon.fromTheme(icon_name), text, self.parent)
            action.triggered.connect(callback)
            menu.addAction(action)


class MainWindow(QMainWindow):
    """
    The main application window.
    """

    def __init__(self) -> None:
        """
        Initialize the main window.
        """
        super().__init__()
        self.setWindowTitle("Compiler")
        self.setGeometry(100, 100, 800, 600)

        self.tab_manager = TabManager(self)
        self.setCentralWidget(self.tab_manager)
        self.menu_manager = MenuManager(self)
        self.toolbar_manager = ToolbarManager(self)

        self._setup_toolbar()
        self._setup_shortcuts()
        self._setup_font_size()
        self.setAcceptDrops(True)
        self.statusBar().showMessage("Ready")

    def _setup_toolbar(self) -> None:
        """
        Set up the toolbar.
        """
        actions = [
            ("document-new", "New", self.new_document),
            ("document-open", "Open", self.open_document),
            ("document-save", "Save", self.save_document),
            ("edit-undo", "Undo", self.undo),
            ("edit-redo", "Redo", self.redo),
            ("edit-cut", "Cut", self.cut),
            ("edit-copy", "Copy", self.copy),
            ("edit-paste", "Paste", self.paste),
            ("system-run", "Run Parser", self.run_parser),
            ("help-contents", "Help", self.show_help),
        ]
        for icon, text, callback in actions:
            self.toolbar_manager.add_action(icon, text, callback)

    def _setup_shortcuts(self) -> None:
        """
        Set up keyboard shortcuts.
        """
        QShortcut(
            QKeySequence("Ctrl+N"),
            self
        ).activated.connect(
            self.new_document
        )

        QShortcut(
            QKeySequence("Ctrl+O"),
            self
        ).activated.connect(
            self.open_document
        )

        QShortcut(
            QKeySequence("Ctrl+S"),
            self
        ).activated.connect(
            self.save_document
        )

        QShortcut(
            QKeySequence("Ctrl+Shift+S"),
            self
        ).activated.connect(
            self.save_document_as
        )

        QShortcut(
            QKeySequence("Ctrl+Z"),
            self
        ).activated.connect(
            self.undo
        )

        QShortcut(
            QKeySequence("Ctrl+Y"),
            self
        ).activated.connect(
            self.redo
        )

        QShortcut(
            QKeySequence("Ctrl+F"),
            self
        ).activated.connect(
            self.run_parser
        )

        QShortcut(
            QKeySequence("Ctrl+="),
            self
        ).activated.connect(
            self.increase_font_size
        )

        QShortcut(
            QKeySequence("Ctrl+-"),
            self
        ).activated.connect(
            self.decrease_font_size
        )

    def _setup_font_size(self) -> None:
        """
        Initialize the font size for the editor.
        """
        self.font_size = 12
        self.update_font_size()

    def update_font_size(self) -> None:
        """
        Update the font size for all tabs.
        """
        font = QFont()
        font.setPointSize(self.font_size)
        for i in range(self.tab_manager.count()):
            widget = self.tab_manager.widget(i)
            if isinstance(widget, DocumentWidget):
                widget.input_edit.setFont(font)
                widget.output_edit.setFont(font)

    def increase_font_size(self) -> None:
        """
        Increase the font size.
        """
        self.font_size += 1
        self.update_font_size()

    def decrease_font_size(self) -> None:
        """
        Decrease the font size.
        """
        if self.font_size > 1:
            self.font_size -= 1
            self.update_font_size()

    def get_current_doc(self) -> Optional[DocumentWidget]:
        """
        Return the currently active document widget.
        """
        return self.tab_manager.get_current_document()

    def new_document(self) -> None:
        """
        Create a new document tab.
        """
        self.tab_manager.add_new_tab()
        self.statusBar().showMessage("New document created", 5000)

    def open_document(self) -> None:
        """
        Open a document from a file.
        """
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            "",
            "Text Files (*.txt);;All Files (*)",
        )
        if path:
            if not os.path.exists(path):
                reply = QMessageBox.question(
                    self,
                    "File Not Found",
                    "The file does not exist. "
                    "Do you want to create a new file?",
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    try:
                        with open(path, "w", encoding="utf-8") as f:
                            pass
                        self.tab_manager.add_new_tab(
                            file_path=path, content=""
                        )
                        self.statusBar().showMessage(
                            f"Opened {os.path.basename(path)}",
                            5000
                        )
                    except Exception as e:
                        QMessageBox.critical(
                            self,
                            "Error",
                            f"Failed to create file: {str(e)}",
                        )
                        self.statusBar().showMessage(
                            f"Error opening file: {str(e)}",
                            5000
                        )
                        return
                else:
                    return
            else:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    self.tab_manager.add_new_tab(
                        file_path=path, content=content)
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Failed to open file: {str(e)}",
                    )

    def save_document(self) -> bool:
        """
        Save the current document.
        """
        self.statusBar().showMessage("Saving...")

        if doc := self.tab_manager.get_current_document():
            if doc.model.file_path:
                if doc.save(doc.model.file_path):
                    self.tab_manager._update_tab_title(doc)
                    return True
            return self.save_document_as()
        return False

    def save_document_as(self) -> bool:
        """
        Save the current document with a new file path.
        """
        if doc := self.tab_manager.get_current_document():
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Save As",
                "",
                "Text Files (*.txt);;All Files (*)",
            )
            if path:
                if doc.save(path):
                    doc.model.file_path = path
                    self.tab_manager._update_tab_title(doc)
                    return True
        return False

    def _save_to_file(self, path: str, content: str) -> bool:
        """
        Save content to a file.
        """
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save file: {str(e)}",
            )
            return False

    def insert_text(self, text: str) -> None:
        """
        Insert text into the current document.
        """
        if doc := self.get_current_doc():
            doc.input_edit.insertPlainText(f"{text}\n")

    def _simulate_parsing(self, text: str) -> list:
        """
        Simulate parsing and collect errors.
        """
        errors = []
        lines = text.split('\n')
        for i, line in enumerate(lines, 1):
            if 'error' in line.lower():
                errors.append({
                    'line': i,
                    'column': line.lower().index('error') + 1,
                    'type': 'Syntax',
                    'message': 'Example error detected.'
                })
        return errors

    def run_parser(self) -> None:
        self.statusBar().showMessage("Parsing...")
        if doc := self.get_current_doc():
            input_text = doc.input_edit.toPlainText()

            lexer = AdvancedLexer(input_text)

            raw_tokens, lexer_errors = lexer.lex()

            valid_tokens, validation_errors = lexer.validate_tokens()

            all_errors = lexer_errors + validation_errors

            doc.error_table.setRowCount(0)
            for row, error in enumerate(all_errors):
                doc.error_table.insertRow(row)
                doc.error_table.setItem(
                    row, 0, QTableWidgetItem(str(error.line)))
                doc.error_table.setItem(
                    row, 1, QTableWidgetItem(str(error.column)))
                doc.error_table.setItem(
                    row, 2, QTableWidgetItem("Syntax Error"))
                doc.error_table.setItem(
                    row, 3, QTableWidgetItem(error.message))

            output = "Tokens:\n"
            for token in valid_tokens:
                output += (
                    f"{token.type} ({token.value}) "
                    f"at line {token.line}, column {token.column}\n"
                )
            doc.output_edit.setPlainText(output)

            msg = (
                f"Parsing completed with {len(all_errors)} issues. "
                f"Applied {len(validation_errors)} corrections."
                if all_errors
                else "Parsing successful"
            )
            self.statusBar().showMessage(msg, 5000)

    def undo(self) -> None:
        """
        Undo the last action in the current document.
        """
        if doc := self.get_current_doc():
            doc.input_edit.undo()

    def redo(self) -> None:
        """
        Redo the last undone action in the current document.
        """
        if doc := self.get_current_doc():
            doc.input_edit.redo()

    def cut(self) -> None:
        """
        Cut the selected text in the current document.
        """
        if doc := self.get_current_doc():
            doc.input_edit.cut()

    def copy(self) -> None:
        """
        Copy the selected text in the current document.
        """
        if doc := self.get_current_doc():
            doc.input_edit.copy()

    def paste(self) -> None:
        """
        Paste text into the current document.
        """
        if doc := self.get_current_doc():
            doc.input_edit.paste()

    def delete(self) -> None:
        """
        Delete the selected text in the current document.
        """
        if doc := self.get_current_doc():
            doc.input_edit.textCursor().removeSelectedText()

    def select_all(self) -> None:
        """
        Select all text in the current document.
        """
        if doc := self.get_current_doc():
            doc.input_edit.selectAll()

    def show_help(self) -> None:
        """
        Display help information.
        """
        help_text = "Help"
        QMessageBox.information(
            self, "Help", help_text, QMessageBox.StandardButton.Ok
        )

    def show_about(self) -> None:
        """
        Display information about the application.
        """
        QMessageBox.about(
            self,
            "About",
            "Compiler Version 0.1",
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Handle the close event, ensuring unsaved changes are not lost.
        """
        for i in range(self.tab_manager.count()):
            widget = self.tab_manager.widget(i)
            if isinstance(widget, DocumentWidget):
                doc = widget
                if doc.model.is_modified:
                    reply = QMessageBox.question(
                        self,
                        "Unsaved Changes",
                        f"Document '{os.path.basename(doc.model.file_path)}' "
                        "has unsaved changes. Save before closing?"
                        if doc.model.file_path
                        else "Document 'Untitled' has unsaved changes. "
                        "Save before closing?",
                        QMessageBox.StandardButton.Yes
                        | QMessageBox.StandardButton.No
                        | QMessageBox.StandardButton.Cancel,
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        if not self.save_document():
                            event.ignore()
                            return
                    elif reply == QMessageBox.StandardButton.Cancel:
                        event.ignore()
                        return
        event.accept()

    def dragEnterEvent(self, event) -> None:
        """
        Handle drag enter events for file drag-and-drop.
        """
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        """
        Handle drop events for file drag-and-drop.
        """
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    self.tab_manager.add_new_tab(
                        file_path=file_path, content=content)
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Failed to open file: {str(e)}",
                    )


if __name__ == "__main__":
    locale.setlocale(locale.LC_ALL, "ru_RU.UTF-8")
    QLocale.setDefault(
        QLocale(QLocale.Language.Russian, QLocale.Country.Russia))

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
