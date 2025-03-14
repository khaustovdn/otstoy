import os
import sys
import locale
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
    QWidget,
    QTabWidget,
    QFileDialog,
    QMessageBox,
    QToolBar,
    QMenu,
    QMenuBar,
)


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
        self.output_edit = QTextEdit()
        self.output_edit.setReadOnly(True)

        self.main_layout.addWidget(self.input_edit)
        self.main_layout.addWidget(self.output_edit)
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
                            file_path=path, content="")
                    except Exception as e:
                        QMessageBox.critical(
                            self,
                            "Error",
                            f"Failed to create file: {str(e)}",
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

    def run_parser(self) -> None:
        """
        Run the parser on the current document.
        """
        if doc := self.get_current_doc():
            input_text = doc.input_edit.toPlainText()
            processed = input_text.upper()
            doc.output_edit.setPlainText(processed)

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
